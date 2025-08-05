
import tkinter as tk
from tkinter import ttk

class ParameterPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding="10")
        self.create_widgets()

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # Column 0
        perf_frame = ttk.LabelFrame(self, text="Performance and Threading", padding="10")
        perf_frame.grid(row=0, column=0, sticky="new", padx=5, pady=5)
        self.create_performance_widgets(perf_frame)

        qtgmc_frame = ttk.LabelFrame(self, text="Deinterlacing (QTGMC)", padding="10")
        qtgmc_frame.grid(row=1, column=0, rowspan=2, sticky="new", padx=5, pady=5)
        self.create_qtgmc_widgets(qtgmc_frame)

        # Column 1
        source_frame = ttk.LabelFrame(self, text="Source Loading Options", padding="10")
        source_frame.grid(row=0, column=1, sticky="new", padx=5, pady=5)
        self.create_source_loading_widgets(source_frame)

        chroma_frame = ttk.LabelFrame(self, text="Chroma Cleanup", padding="10")
        chroma_frame.grid(row=1, column=1, sticky="new", padx=5, pady=5)
        self.create_chroma_cleanup_widgets(chroma_frame)

        upscale_frame = ttk.LabelFrame(self, text="Upscaling (NNEDI3)", padding="10")
        upscale_frame.grid(row=2, column=1, sticky="new", padx=5, pady=5)
        self.create_upscaling_widgets(upscale_frame)
        
        format_frame = ttk.LabelFrame(self, text="Format and Color Space", padding="10")
        format_frame.grid(row=3, column=0, sticky="new", padx=5, pady=5)
        self.create_format_widgets(format_frame)

        adv_frame = ttk.LabelFrame(self, text="Advanced Options", padding="10")
        adv_frame.grid(row=3, column=1, sticky="new", padx=5, pady=5)
        self.create_advanced_widgets(adv_frame)

    def _create_slider(self, parent, text, from_, to, default, var, row, col):
        ttk.Label(parent, text=text).grid(row=row, column=col, sticky="w")
        var.set(default)
        slider = ttk.Scale(parent, from_=from_, to=to, orient="horizontal", variable=var)
        slider.grid(row=row, column=col+1, sticky="ew", padx=5)
        label = ttk.Label(parent, text=f"{default}")
        label.grid(row=row, column=col+2, sticky="w")
        slider.configure(command=lambda v, l=label: l.config(text=f"{float(v):.2f}"))

    def create_performance_widgets(self, parent):
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="Thread Count:").grid(row=0, column=0, sticky="w")
        self.thread_count = tk.IntVar(value=10)
        ttk.Spinbox(parent, from_=1, to=32, textvariable=self.thread_count, width=5).grid(row=0, column=1, sticky="w")

    def create_source_loading_widgets(self, parent):
        self.source_filter = tk.StringVar(value="Auto-detect")
        ttk.Radiobutton(parent, text="Auto-detect", variable=self.source_filter, value="Auto-detect").pack(anchor="w")
        ttk.Radiobutton(parent, text="Force FFmpegSource2", variable=self.source_filter, value="FFmpegSource2").pack(anchor="w")
        ttk.Radiobutton(parent, text="Force LSMASHSource", variable=self.source_filter, value="LSMASHSource").pack(anchor="w")

    def create_qtgmc_widgets(self, parent):
        parent.columnconfigure(1, weight=1)
        
        # Preset
        ttk.Label(parent, text="Preset:").grid(row=0, column=0, sticky="w")
        self.qtgmc_preset = tk.StringVar(value="Placebo")
        ttk.Combobox(parent, textvariable=self.qtgmc_preset, values=["Draft", "Fast", "Medium", "Slow", "Slower", "Placebo"]).grid(row=0, column=1, columnspan=2, sticky="ew")

        # Field Order
        ttk.Label(parent, text="Field Order:").grid(row=1, column=0, sticky="w")
        self.field_order = tk.StringVar(value="Top Field First (TFF)")
        field_order_frame = ttk.Frame(parent)
        field_order_frame.grid(row=1, column=1, columnspan=2, sticky="ew")
        ttk.Radiobutton(field_order_frame, text="Auto-detect", variable=self.field_order, value="Auto-detect").pack(side="left", padx=5)
        ttk.Radiobutton(field_order_frame, text="TFF", variable=self.field_order, value="Top Field First (TFF)").pack(side="left", padx=5)
        ttk.Radiobutton(field_order_frame, text="BFF", variable=self.field_order, value="Bottom Field First (BFF)").pack(side="left", padx=5)

        # Sliders
        self.source_matching = tk.DoubleVar()
        self._create_slider(parent, "Source Matching:", 0, 3, 3, self.source_matching, 2, 0)
        self.lossless_mode = tk.IntVar()
        self._create_slider(parent, "Lossless Mode:", 0, 2, 2, self.lossless_mode, 3, 0)
        self.sharpening_control = tk.DoubleVar()
        self._create_slider(parent, "Sharpening:", 0.0, 2.0, 0.0, self.sharpening_control, 4, 0)

        # Motion Analysis
        self.match_enhancement = tk.DoubleVar()
        self._create_slider(parent, "Match Enhancement:", 0.0, 1.0, 0.95, self.match_enhancement, 5, 0)
        self.tr0 = tk.IntVar()
        self._create_slider(parent, "Base Temporal Radius:", 0, 3, 2, self.tr0, 6, 0)
        self.tr1 = tk.IntVar()
        self._create_slider(parent, "Motion Search Radius:", 0, 3, 2, self.tr1, 7, 0)
        self.tr2 = tk.IntVar()
        self._create_slider(parent, "Post-Process Radius:", 0, 3, 2, self.tr2, 8, 0)

        # Noise Processing
        self.enable_noise_processing = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Enable Noise Processing", variable=self.enable_noise_processing).grid(row=9, column=0, sticky="w")
        self.noise_restoration = tk.DoubleVar()
        self._create_slider(parent, "Noise Restoration:", 0.0, 1.0, 0.3, self.noise_restoration, 10, 0)
        self.ez_denoise = tk.DoubleVar()
        self._create_slider(parent, "EZ Denoise:", 0.0, 10.0, 0.0, self.ez_denoise, 11, 0)

        # Chroma Processing
        self.chroma_motion = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Chroma Motion", variable=self.chroma_motion).grid(row=12, column=0, sticky="w")
        self.chroma_noise = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Chroma Noise", variable=self.chroma_noise).grid(row=12, column=1, sticky="w")
        self.precise_mode = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Precise Mode", variable=self.precise_mode).grid(row=12, column=2, sticky="w")

        # Repair Settings
        self.rep0 = tk.IntVar()
        self._create_slider(parent, "Primary Repair:", 0, 5, 4, self.rep0, 13, 0)
        self.rep2 = tk.IntVar()
        self._create_slider(parent, "Secondary Repair:", 0, 5, 4, self.rep2, 14, 0)

        # Border Handling
        self.border_handling = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Border Handling", variable=self.border_handling).grid(row=15, column=0, sticky="w")

        # Frame Rate Conversion
        ttk.Label(parent, text="Frame Rate:").grid(row=16, column=0, sticky="w")
        self.frame_rate = tk.StringVar(value="Convert to Half")
        ttk.Combobox(parent, textvariable=self.frame_rate, values=["Keep Original", "Convert to Half"]).grid(row=16, column=1, columnspan=2, sticky="ew")


    def create_chroma_cleanup_widgets(self, parent):
        parent.columnconfigure(1, weight=1)
        self.prev_frame_weight = tk.DoubleVar()
        self._create_slider(parent, "Previous Frame Weight:", 0.0, 1.0, 0.3, self.prev_frame_weight, 0, 0)
        self.two_frame_weight = tk.DoubleVar()
        self._create_slider(parent, "Two-Frame Weight:", 0.0, 1.0, 0.2, self.two_frame_weight, 1, 0)

        ttk.Label(parent, text="Vertical Strength:").grid(row=2, column=0, sticky="w")
        self.vertical_strength = tk.StringVar(value="Medium")
        ttk.Combobox(parent, textvariable=self.vertical_strength, values=["Light", "Medium", "Strong"]).grid(row=2, column=1, columnspan=2, sticky="ew")
        
        self.aggressive_mode_thresh = tk.IntVar()
        self._create_slider(parent, "Aggressive Mode Threshold:", 1, 10, 3, self.aggressive_mode_thresh, 3, 0)

        self.horizontal_smoothing = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Horizontal Smoothing", variable=self.horizontal_smoothing).grid(row=4, column=0, sticky="w")
        self.horizontal_blend = tk.DoubleVar()
        self._create_slider(parent, "Horizontal Blend:", 0.0, 1.0, 0.5, self.horizontal_blend, 5, 0)


    def create_upscaling_widgets(self, parent):
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="Neural Network Size:").grid(row=0, column=0, sticky="w")
        self.nn_size = tk.StringVar(value="32x6")
        ttk.Combobox(parent, textvariable=self.nn_size, values=["8x6", "16x6", "32x6", "64x6"]).grid(row=0, column=1, columnspan=2, sticky="ew")

        ttk.Label(parent, text="Neuron Count:").grid(row=1, column=0, sticky="w")
        self.neuron_count = tk.StringVar(value="256")
        ttk.Combobox(parent, textvariable=self.neuron_count, values=["16", "32", "64", "128", "256"]).grid(row=1, column=1, columnspan=2, sticky="ew")

        self.quality_level = tk.IntVar()
        self._create_slider(parent, "Quality Level:", 1, 2, 2, self.quality_level, 2, 0)

        ttk.Label(parent, text="Edge Type:").grid(row=3, column=0, sticky="w")
        self.edge_type = tk.StringVar(value="Rectangle")
        edge_type_frame = ttk.Frame(parent)
        edge_type_frame.grid(row=3, column=1, columnspan=2, sticky="ew")
        ttk.Radiobutton(edge_type_frame, text="Rectangle", variable=self.edge_type, value="Rectangle").pack(side="left", padx=5)
        ttk.Radiobutton(edge_type_frame, text="Ellipse", variable=self.edge_type, value="Ellipse").pack(side="left", padx=5)

        ttk.Label(parent, text="Field Processing:").grid(row=4, column=0, sticky="w")
        self.field_processing = tk.StringVar(value="Top Field")
        field_proc_frame = ttk.Frame(parent)
        field_proc_frame.grid(row=4, column=1, columnspan=2, sticky="ew")
        ttk.Radiobutton(field_proc_frame, text="Auto", variable=self.field_processing, value="Auto").pack(side="left", padx=5)
        ttk.Radiobutton(field_proc_frame, text="Top Field", variable=self.field_processing, value="Top Field").pack(side="left", padx=5)
        ttk.Radiobutton(field_proc_frame, text="Bottom Field", variable=self.field_processing, value="Bottom Field").pack(side="left", padx=5)


    def create_format_widgets(self, parent):
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text="Output Format:").grid(row=0, column=0, sticky="w")
        self.output_format = tk.StringVar(value="YUV422P10")
        ttk.Combobox(parent, textvariable=self.output_format, values=["YUV422P10", "YUV444P10", "YUV420P10"]).grid(row=0, column=1, sticky="ew")

        ttk.Label(parent, text="Dithering Method:").grid(row=1, column=0, sticky="w")
        self.dithering = tk.StringVar(value="Error Diffusion")
        ttk.Combobox(parent, textvariable=self.dithering, values=["None", "Ordered", "Error Diffusion"]).grid(row=1, column=1, sticky="ew")

        ttk.Label(parent, text="Color Space Handling:", justify="left", anchor="w").grid(row=2, column=0, sticky="w")
        ttk.Label(parent, text="DCI-P3 properties are applied during final FFmpeg encoding.", justify="left").grid(row=2, column=1, sticky="w")


    def create_advanced_widgets(self, parent):
        parent.columnconfigure(1, weight=1)
        self.debug_output = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="Enable Debug Output", variable=self.debug_output).grid(row=0, column=0, sticky="w")
        self.gpu_monitoring = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="GPU Memory Monitoring", variable=self.gpu_monitoring).grid(row=0, column=1, sticky="w")
        self.performance_profiling = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="Performance Profiling", variable=self.performance_profiling).grid(row=0, column=2, sticky="w")


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Parameter Panel Test")
    canvas = tk.Canvas(root)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    param_panel = ParameterPanel(scrollable_frame)
    param_panel.pack(fill="both", expand=True)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    root.mainloop()
