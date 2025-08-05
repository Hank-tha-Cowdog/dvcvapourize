
import tkinter as tk
from tkinter import ttk

class ProgressView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding="10")

        self.create_widgets()

    def create_widgets(self):
        # File-Level Progress
        file_progress_frame = ttk.LabelFrame(self, text="File Progress", padding="10")
        file_progress_frame.pack(fill="x", expand=True, pady=5)
        file_progress_frame.columnconfigure(0, weight=1)

        self.file_progress_bar = ttk.Progressbar(file_progress_frame, orient="horizontal", length=300, mode="determinate")
        self.file_progress_bar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.file_progress_label = ttk.Label(file_progress_frame, text="0/0 frames | 0.0 fps | ETA: --:--:--")
        self.file_progress_label.grid(row=0, column=1, sticky="w", padx=5)


        # Batch-Level Progress
        batch_progress_frame = ttk.LabelFrame(self, text="Batch Progress", padding="10")
        batch_progress_frame.pack(fill="x", expand=True, pady=5)
        batch_progress_frame.columnconfigure(0, weight=1)

        self.batch_progress_bar = ttk.Progressbar(batch_progress_frame, orient="horizontal", length=300, mode="determinate")
        self.batch_progress_bar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.batch_progress_label = ttk.Label(batch_progress_frame, text="0/0 files | Avg time: --:--:-- | Total ETA: --:--:--")
        self.batch_progress_label.grid(row=0, column=1, sticky="w", padx=5)

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Progress View Test")
    progress_view = ProgressView(root)
    progress_view.pack(fill="both", expand=True)
    root.mainloop()
