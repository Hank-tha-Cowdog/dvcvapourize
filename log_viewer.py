
import tkinter as tk
from tkinter import ttk

class LogViewer(ttk.LabelFrame):
    def __init__(self, parent, text="Log Viewer", **kwargs):
        super().__init__(parent, text=text, **kwargs)
        self.create_widgets()

    def create_widgets(self):
        self.log_text = tk.Text(self, height=10, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Add some example log entries
        self.log_text.insert("end", "[2025-07-17 10:00:00] INFO: Application started.\n")
        self.log_text.insert("end", "[2025-07-17 10:00:05] INFO: VapourSynth script loaded.\n")
        self.log_text.configure(state="disabled")

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Log Viewer Test")
    log_viewer = LogViewer(root)
    log_viewer.pack(fill="both", expand=True, padx=10, pady=10)
    root.mainloop()
