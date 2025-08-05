

import tkinter as tk
from tkinter import ttk, filedialog

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.transient(parent)
        self.grab_set()

        self.python_executable_path = parent.python_executable_path

        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="VapourSynth Python Executable:").grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        entry = ttk.Entry(frame, textvariable=self.python_executable_path, width=60)
        entry.grid(row=1, column=0, sticky="ew")

        browse_button = ttk.Button(frame, text="Browse...", command=self.browse_python)
        browse_button.grid(row=1, column=1, padx=(5, 0))

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        save_button = ttk.Button(button_frame, text="Save", command=self.save_and_close)
        save_button.pack(side="right", padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        cancel_button.pack(side="right")

    def browse_python(self):
        path = filedialog.askopenfilename(
            title="Select Python Executable",
            filetypes=[("Python Executable", "python.exe"), ("All files", "*.*")]
        )
        if path:
            self.python_executable_path.set(path)

    def save_and_close(self):
        # In a real app, you'd save this to a config file
        print(f"Python executable path saved: {self.python_executable_path.get()}")
        self.destroy()

if __name__ == '__main__':
    # This is just for testing the window independently
    root = tk.Tk()
    # A mock parent object for testing
    class MockApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.python_executable_path = tk.StringVar(value="C:\\path\\to\\your\\venv\\Scripts\\python.exe")
    
    mock_app = MockApp()
    settings_button = ttk.Button(mock_app, text="Open Settings", command=lambda: SettingsWindow(mock_app))
    settings_button.pack(padx=20, pady=20)
    mock_app.mainloop()

