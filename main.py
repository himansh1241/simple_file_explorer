import os
import shutil
import subprocess
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import platform
from datetime import datetime

APP_NAME = "Simple File Explorer"
PLATFORM = platform.system().lower()

# Utilities

def human_size(n):
    try:
        n = float(n)
    except Exception:
        return "-"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:3.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def format_mtime(ts):
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"


def open_path(path):
    try:
        if PLATFORM.startswith("windows"):
            os.startfile(path)
        elif PLATFORM.startswith("darwin") or PLATFORM == "macos":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception as e:
        messagebox.showerror("Open error", f"Could not open {path}: {e}")
        return False

# Main Application Class

class FileExplorerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1000x700")

        # theme state
        self.dark_mode = False

        # state
        self.current_path = tk.StringVar(value=os.getcwd())
        self.status_text = tk.StringVar(value="Ready")
        self.clipboard = {"path": None, "action": None}  # action: 'copy' or 'cut'
        self._ctx_path = None  # temporary path for context-menu actions

        # build UI
        self._setup_style()
        self._build_toolbar()
        self._build_treeview()
        self._build_statusbar()
        self._bind_shortcuts()

        # initial load
        self.load_directory(self.current_path.get())

    # UI builders

    def _setup_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # light default
        style.configure("TFrame", background="#f2f5f8")
        style.configure("TLabel", background="#f2f5f8")
        style.configure("TButton", padding=6, relief="flat")
        style.map("TButton", background=[("active", "#d0d7de")])

        # tile styles (kept for future use, harmless)
        style.configure("Tile.TFrame", background="#ffffff")
        style.configure("Tile.TLabel", background="#ffffff")

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=6)
        toolbar.pack(fill="x")

        # compact buttons (small, arranged)
        btn_back = ttk.Button(toolbar, text="◀", width=3, command=self.navigate_parent)
        btn_new = ttk.Button(toolbar, text="New", width=6, command=self.create_folder)
        btn_delete = ttk.Button(toolbar, text="Del", width=6, command=self.delete_item)
        btn_copy = ttk.Button(toolbar, text="Copy", width=6, command=self.copy_item)
        btn_cut = ttk.Button(toolbar, text="Cut", width=6, command=self.cut_item)
        btn_paste = ttk.Button(toolbar, text="Paste", width=6, command=self.paste_item)
        btn_open = ttk.Button(toolbar, text="Open", width=6, command=self.open_selected)
        # theme icon button
        btn_theme = ttk.Button(toolbar, text="🌗", width=4, command=self.toggle_theme)

        for w in (btn_back, btn_new, btn_delete, btn_copy, btn_cut, btn_paste, btn_open, btn_theme):
            w.pack(side="left", padx=4, pady=2)

        entry = ttk.Entry(toolbar, textvariable=self.current_path)
        entry.pack(side="right", padx=6, fill="x", expand=True)
        entry.bind("<Return>", lambda e: self.load_directory(self.current_path.get()))

    def _build_treeview(self):
        frame = ttk.Frame(self.root, padding=(8, 6))
        frame.pack(fill="both", expand=True)

        columns = ("name", "type", "size", "modified")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="Name")
        self.tree.column("name", anchor="w", width=450)
        self.tree.heading("type", text="Type")
        self.tree.column("type", width=80, anchor="center")
        self.tree.heading("size", text="Size")
        self.tree.column("size", width=100, anchor="e")
        self.tree.heading("modified", text="Modified")
        self.tree.column("modified", width=160, anchor="center")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # events and context menu
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Return>", self.on_enter_key)
        self._build_context_menu()
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Control-Button-1>", self._show_context_menu)
        self.tree.bind("<Button-2>", self._show_context_menu)

    def _build_context_menu(self):
        self.ctx_menu = tk.Menu(self.root, tearoff=0)
        self.ctx_menu.add_command(label="Open", command=self.open_selected)
        self.ctx_menu.add_command(label="Copy", command=self.copy_item)
        self.ctx_menu.add_command(label="Cut", command=self.cut_item)
        self.ctx_menu.add_command(label="Paste", command=self.paste_item)
        self.ctx_menu.add_command(label="Rename", command=self.rename_item)
        self.ctx_menu.add_command(label="Delete", command=self.delete_item)

    def _show_context_menu(self, event):
        # clear any tile ctx path
        self._ctx_path = None
        try:
            iid = self.tree.identify_row(event.y)
            if iid:
                self.tree.selection_set(iid)
            self.ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                self.ctx_menu.grab_release()
            except Exception:
                pass

    def _build_statusbar(self):
        status = ttk.Frame(self.root)
        status.pack(fill="x")
        lbl = ttk.Label(status, textvariable=self.status_text, anchor="w")
        lbl.pack(fill="x", padx=6, pady=4)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        style = ttk.Style(self.root)
        if self.dark_mode:
            # frames & labels
            style.configure("TFrame", background="#1e1e1e")
            style.configure("TLabel", background="#1e1e1e", foreground="#ffffff")
            style.configure("TButton", background="#2d2d2d", foreground="#ffffff")
            style.map("TButton", background=[("active", "#3a3a3a")])
            # treeview
            style.configure("Treeview", background="#252525", fieldbackground="#252525", foreground="#e6e6e6")
            style.configure("Treeview.Heading", background="#2b2b2b", foreground="#ffffff")
        else:
            style.configure("TFrame", background="#f2f5f8")
            style.configure("TLabel", background="#f2f5f8", foreground="#000000")
            style.configure("TButton", background="#e6e9ed", foreground="#000000")
            style.map("TButton", background=[("active", "#d0d7de")])
            style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground="#000000")
            style.configure("Treeview.Heading", background="#f0f0f0", foreground="#000000")
        # refresh view
        self.load_directory(self.current_path.get())

    def _bind_shortcuts(self):
        # common shortcuts
        self.root.bind("<Control-c>", lambda e: self.copy_item())
        self.root.bind("<Control-x>", lambda e: self.cut_item())
        self.root.bind("<Control-v>", lambda e: self.paste_item())
        self.root.bind("<F5>", lambda e: self.load_directory(self.current_path.get()))

    # Core actions

    def update_status(self, text, seconds=None):
        self.status_text.set(text)
        if seconds:
            self.root.after(int(seconds * 1000), lambda: self.status_text.set(""))

    def load_directory(self, path):
        path = os.path.abspath(path or os.getcwd())
        if not os.path.exists(path):
            messagebox.showerror("Path error", f"Path does not exist:\n{path}")
            return

        self.current_path.set(path)
        # clear tree
        for i in self.tree.get_children():
            self.tree.delete(i)

        try:
            with os.scandir(path) as it:
                entries = sorted(it, key=lambda e: (not e.is_dir(), e.name.lower()))
                for entry in entries:
                    name = entry.name
                    is_dir = entry.is_dir()
                    t = "Folder" if is_dir else "File"
                    size = "-" if is_dir else human_size(entry.stat().st_size)
                    mtime = format_mtime(entry.stat().st_mtime)
                    self.tree.insert("", "end", values=(name, t, size, mtime))
            self.update_status(f"Loaded: {path}")
        except PermissionError:
            messagebox.showerror("Permission denied", f"Cannot access: {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _selected_item_path(self):
        # prefer context-menu tile path when set
        if getattr(self, "_ctx_path", None):
            return self._ctx_path
        sel = self.tree.selection()
        if not sel:
            return None
        name = self.tree.item(sel[0])["values"][0]
        return os.path.join(self.current_path.get(), name)

    def on_double_click(self, event=None):
        self.open_selected()

    def on_enter_key(self, event=None):
        self.open_selected()

    def open_selected(self):
        path = self._selected_item_path()
        if not path:
            return
        if os.path.isdir(path):
            self.load_directory(path)
        else:
            open_path(path)

    def navigate_parent(self):
        parent = os.path.dirname(self.current_path.get())
        if parent and parent != self.current_path.get():
            self.load_directory(parent)

    def create_folder(self):
        name = simpledialog.askstring("New folder", "Folder name:")
        if not name:
            return
        target = os.path.join(self.current_path.get(), name)
        try:
            os.makedirs(target, exist_ok=False)
            self.load_directory(self.current_path.get())
            self.update_status(f"Created folder: {name}", seconds=3)
        except FileExistsError:
            messagebox.showwarning("Exists", "Folder already exists.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_item(self):
        path = self._selected_item_path()
        if not path:
            messagebox.showinfo("Select", "Select an item to delete.")
            return
        name = os.path.basename(path)
        if not messagebox.askyesno("Confirm", f"Delete '{name}' permanently?"):
            return
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.load_directory(self.current_path.get())
            self.update_status(f"Deleted: {name}", seconds=3)
        except Exception as e:
            messagebox.showerror("Delete error", str(e))

    def copy_item(self):
        path = self._selected_item_path()
        if not path:
            messagebox.showinfo("Select", "Select an item to copy.")
            return
        self.clipboard["path"] = path
        self.clipboard["action"] = "copy"
        self.update_status(f"Copied: {os.path.basename(path)}", seconds=2)

    def cut_item(self):
        path = self._selected_item_path()
        if not path:
            messagebox.showinfo("Select", "Select an item to cut.")
            return
        self.clipboard["path"] = path
        self.clipboard["action"] = "cut"
        self.update_status(f"Cut: {os.path.basename(path)}", seconds=2)

    def paste_item(self):
        src = self.clipboard.get("path")
        action = self.clipboard.get("action")
        if not src or not os.path.exists(src):
            messagebox.showinfo("Clipboard", "Nothing to paste or source no longer exists.")
            return
        basename = os.path.basename(src)
        dest = os.path.join(self.current_path.get(), basename)
        try:
            if os.path.isdir(src):
                # avoid pasting into itself
                if os.path.commonpath([src, dest]) == os.path.abspath(src):
                    messagebox.showerror("Paste error", "Cannot paste a folder into itself.")
                    return
                if action == "copy":
                    shutil.copytree(src, dest)
                else:
                    shutil.move(src, dest)
            else:
                if action == "copy":
                    shutil.copy2(src, dest)
                else:
                    shutil.move(src, dest)
            # if cut, clear clipboard
            if action == "cut":
                self.clipboard = {"path": None, "action": None}
            self.load_directory(self.current_path.get())
            self.update_status(f"Pasted: {basename}", seconds=3)
        except Exception as e:
            messagebox.showerror("Paste error", str(e))

    def rename_item(self):
        src = self._selected_item_path()
        if not src:
            messagebox.showinfo("Select", "Select an item to rename.")
            return
        new_name = simpledialog.askstring("Rename", "New name:", initialvalue=os.path.basename(src))
        if not new_name or new_name == os.path.basename(src):
            return
        dest = os.path.join(self.current_path.get(), new_name)
        try:
            os.rename(src, dest)
            self.load_directory(self.current_path.get())
            self.update_status(f"Renamed to: {new_name}", seconds=3)
        except Exception as e:
            messagebox.showerror("Rename error", str(e))

# Entry point

def main():
    root = tk.Tk()
    app = FileExplorerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()