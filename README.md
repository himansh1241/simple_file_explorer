A lightweight and clean file explorer built using Python and Tkinter.
It replicates basic file-manager features like browsing directories, opening files, and performing common file operations — all inside a custom GUI.
Perfect for beginners exploring GUI development or anyone who wants a simple cross-platform file manager.

📘 Project Structure:
file_explorer.py   -- Main application file
README.md          -- Project documentation

⸻

🚀 Features
	•	📂 Browse directories in a TreeView UI
	•	🔍 Double-click or press Enter to open files/folders
	•	➕ Create new folders
	•	✏️ Rename files/folders
	•	🗑️ Delete items safely
	•	📄 Copy / Cut / Paste support
	•	🎨 Light & Dark mode toggle
	•	🖱️ Right-click context menu
	•	📝 Status bar for quick feedback
	•	🪟 Works on Windows, macOS, and Linux

⸻

🛠️ Tech Stack
	•	Python 3.x
	•	Tkinter (ttk widgets)
	•	Built-in Python modules:
	•	os
	•	shutil
	•	subprocess
	•	platform
	•	datetime
	•	tkinter components

⸻

🔧 How It Works

  The app uses:
	•	TreeView to display directory contents
	•	os.scandir() for fast directory reading
	•	shutil for file operations
	•	subprocess / os.startfile to open files natively
	•	Tkinter dialogs for rename, new folder, and warnings
	•	A custom clipboard system for copy & cut operations
	•	Theming logic to switch between light and dark modes
