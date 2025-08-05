
import tkinter as tk
from tkinter import ttk
from components.file_selector import FileSelector
from components.parameter_panel import ParameterPanel
from components.progress_view import ProgressView
from components.log_viewer import LogViewer
from components.settings_window import SettingsWindow
import sys
import os

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HDVapourize")
        self.geometry("800x800")

        # App-wide configuration
        self.python_executable_path = tk.StringVar()

        # Set application icon
        try:
            if sys.platform == "darwin":
                icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icons", "32x32.png"))
                self.icon = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, self.icon)
            else:
                icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icons", "icon.ico"))
                self.iconbitmap(icon_path)
        except tk.TclError as e:
            print(f"Icon not found, skipping icon setting: {e}")

        self.create_widgets()

    def open_settings(self):
        SettingsWindow(self)

    def create_widgets(self):
        # Header Region
        header_frame = ttk.Frame(self, padding="10")
        header_frame.pack(fill="x")
        header_frame.columnconfigure(0, weight=1)

        # Title and Icon (Row 0)
        title_container = ttk.Frame(header_frame)
        title_container.grid(row=0, column=0, pady=(0, 10))

        try:
            icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icons", "32x32.png"))
            self.title_icon = tk.PhotoImage(file=icon_path)
            icon_label = ttk.Label(title_container, image=self.title_icon)
            icon_label.pack(side="left", padx=(0, 5))
        except tk.TclError:
            print("Title icon not found.")

        title_label = ttk.Label(title_container, text="HDVapourize", font=("", 16, "bold"))
        title_label.pack(side="left")

        # Action Buttons (Row 1)
        button_container = ttk.Frame(header_frame)
        button_container.grid(row=1, column=0)

        settings_button = ttk.Button(button_container, text="Settings", command=self.open_settings)
        settings_button.pack(side="left", padx=5)

        stop_button = ttk.Button(button_container, text="Stop")
        stop_button.pack(side="left", padx=5)

        start_button = ttk.Button(button_container, text="Start Processing")
        start_button.pack(side="left", padx=5)

        # Main content area
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Input/Output Panel
        io_panel = FileSelector(main_frame)
        io_panel.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Parameter Control Panel
        param_canvas = tk.Canvas(main_frame)
        param_canvas.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        param_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=param_canvas.yview)
        param_scrollbar.grid(row=1, column=1, sticky="ns")

        param_canvas.configure(yscrollcommand=param_scrollbar.set)

        param_frame = ParameterPanel(param_canvas)
        param_window = param_canvas.create_window((0, 0), window=param_frame, anchor="nw")

        def on_canvas_configure(event):
            canvas_width = event.width
            param_canvas.itemconfig(param_window, width=canvas_width)

        param_canvas.bind("<Configure>", on_canvas_configure)
        param_frame.bind("<Configure>", lambda e: param_canvas.configure(scrollregion=param_canvas.bbox("all")))


        # Progress and Status Region
        status_frame = ttk.Frame(self, padding="10")
        status_frame.pack(fill="x", pady=5)

        progress_view = ProgressView(status_frame)
        progress_view.pack(fill="x", expand=True)

        log_viewer = LogViewer(status_frame)
        log_viewer.pack(fill="x", expand=True, pady=5)


if __name__ == "__main__":
    app = App()
    app.mainloop()
