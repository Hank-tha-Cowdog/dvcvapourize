
import tkinter as tk
from tkinter import ttk, filedialog

class FileSelector(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding="10")

        self.create_widgets()

    def create_widgets(self):
        # Input Path
        ttk.Label(self, text="Input:").grid(row=0, column=0, sticky="w")
        self.input_path = tk.StringVar()
        input_entry = ttk.Entry(self, textvariable=self.input_path, width=50)
        input_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.columnconfigure(1, weight=1)

        browse_button = ttk.Button(self, text="Browse...", command=self.browse_input)
        browse_button.grid(row=0, column=2, padx=5)

        # Output Path
        ttk.Label(self, text="Output:").grid(row=1, column=0, sticky="w")
        self.output_path = tk.StringVar()
        output_entry = ttk.Entry(self, textvariable=self.output_path, width=50)
        output_entry.grid(row=1, column=1, sticky="ew", padx=5)

        browse_output_button = ttk.Button(self, text="Browse...", command=self.browse_output)
        browse_output_button.grid(row=1, column=2, padx=5)

        # Options
        options_frame = ttk.Frame(self)
        options_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=10)

        self.processing_mode = tk.StringVar(value="Single File")
        single_file_radio = ttk.Radiobutton(options_frame, text="Single File", variable=self.processing_mode, value="Single File", command=self.toggle_batch_mode)
        single_file_radio.pack(side="left", padx=5)
        batch_mode_radio = ttk.Radiobutton(options_frame, text="Batch Mode", variable=self.processing_mode, value="Batch Mode", command=self.toggle_batch_mode)
        batch_mode_radio.pack(side="left", padx=5)


        self.recursive = tk.BooleanVar()
        self.recursive_check = ttk.Checkbutton(options_frame, text="Process Subdirectories", variable=self.recursive, state="disabled")
        self.recursive_check.pack(side="left", padx=5)

        self.skip_existing = tk.BooleanVar(value=True)
        skip_check = ttk.Checkbutton(options_frame, text="Skip Existing Files", variable=self.skip_existing)
        skip_check.pack(side="left", padx=5)

        # Test Mode
        test_mode_frame = ttk.Frame(self)
        test_mode_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=10)

        self.test_mode = tk.BooleanVar()
        test_mode_check = ttk.Checkbutton(test_mode_frame, text="Test Mode", variable=self.test_mode, command=self.toggle_test_mode)
        test_mode_check.pack(side="left", padx=5)

        self.test_frame_count = tk.IntVar(value=200)
        self.test_frame_slider = ttk.Scale(test_mode_frame, from_=10, to=25000, orient="horizontal", variable=self.test_frame_count, length=200, state="disabled")
        self.test_frame_slider.pack(side="left", padx=5)
        
        self.test_frame_entry = ttk.Entry(test_mode_frame, textvariable=self.test_frame_count, width=7, state="disabled")
        self.test_frame_entry.pack(side="left", padx=5)
        
        self.test_frame_label = ttk.Label(test_mode_frame, text="frames", state="disabled")
        self.test_frame_label.pack(side="left")


    def browse_input(self):
        if self.processing_mode.get() == "Batch Mode":
            path = filedialog.askdirectory()
        else:
            path = filedialog.askopenfilename()
        if path:
            self.input_path.set(path)

    def browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_path.set(path)

    def toggle_batch_mode(self):
        if self.processing_mode.get() == "Batch Mode":
            self.recursive_check.config(state="normal")
        else:
            self.recursive_check.config(state="disabled")

    def toggle_test_mode(self):
        state = "normal" if self.test_mode.get() else "disabled"
        self.test_frame_slider.config(state=state)
        self.test_frame_entry.config(state=state)
        self.test_frame_label.config(state=state)


if __name__ == '__main__':
    root = tk.Tk()
    root.title("File Selector Test")
    file_selector = FileSelector(root)
    file_selector.pack(fill="both", expand=True)
    root.mainloop()
