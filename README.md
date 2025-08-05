# 🎬 DVC Vapourize

**Professional DV to 4K ProRes upscaling pipeline with advanced deinterlacing and chroma cleanup**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![VapourSynth](https://img.shields.io/badge/VapourSynth-R57%2B-green.svg)](http://vapoursynth.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com)

> Transform your legacy DV footage into pristine 4K ProRes with professional-grade deinterlacing, chroma cleanup, and neural network upscaling.

## ✨ Features

- 🚀 **QTGMC Deinterlacing** - Industry-standard motion-compensated deinterlacing
- 🧠 **NNEDI3 Neural Upscaling** - AI-powered 2× upscaling to 4K (3840×2160)
- 🎯 **Advanced Chroma Cleanup** - Multi-pass temporal and spatial chroma artifact removal
- 🎨 **DCI-P3 Color Space** - Professional color space handling for cinema workflows
- 📁 **Batch Processing** - Process entire directories with progress monitoring
- 🖥️ **GUI & CLI** - Both graphical interface and command-line operation
- ⚡ **Optimized Pipeline** - Multi-threaded processing with performance profiling
- 📊 **Rich Progress Tracking** - Real-time frame-by-frame progress with ETA

## 🎯 Designed For

- **DV Footage** (720×576 PAL, 720×480 NTSC)
- **Legacy Video Formats** (AVI, MKV, MP4, MXF, DV, HDV)
- **Professional Post-Production** workflows
- **Archive Restoration** projects

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **FFmpeg** (in system PATH)
- **VapourSynth R57+**

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv dvc_vapourize_env

# Activate environment
# Windows:
dvc_vapourize_env\Scripts\activate
# macOS/Linux:
source dvc_vapourize_env/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. VapourSynth Setup

Install VapourSynth and required plugins:

```bash
# Install vsrepo (VapourSynth plugin manager)
pip install vsrepo

# Install required plugins
vsrepo install qtgmc
vsrepo install nnedi3
vsrepo install havsfunc
vsrepo install ffms2
vsrepo install lsmas
vsrepo install mvtools
vsrepo install vsdehalo

# Update all plugins
vsrepo upgrade-all
```

### 3. Run the Application

#### GUI Mode
```bash
python main_window.py
```

#### Command Line Mode
```bash
# Single file processing
python vs_pipeline.py --input "input_video.avi" --output "output_directory"

# Batch processing with test mode
python vs_pipeline.py --input "input_directory" --output "output_directory" --batch_mode --test_mode --test_frames 500

# Full batch processing with recursive subdirectory scanning
python vs_pipeline.py --input "input_directory" --output "output_directory" --batch_mode --recursive
```

## 📋 Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Input file or directory path | Required |
| `--output` | Output directory path | Required |
| `--batch_mode` | Enable batch processing | Single file |
| `--recursive` | Process subdirectories | Disabled |
| `--test_mode` | Process limited frames for testing | Disabled |
| `--test_frames` | Number of frames in test mode | 200 |

## 🔧 Processing Pipeline

```
Input DV Video → Rewrap to ProRes → VapourSynth Processing → Final ProRes 422 HQ
                        ↓                       ↓                        ↓
                Format Detection    ┌─ Deinterlacing (QTGMC)    DCI-P3 Color Space
                Color Space Setup   ├─ Chroma Cleanup           Professional Codec
                Audio Preservation  ├─ Square Pixel Conversion  4K Resolution
                                   ├─ NNEDI3 2× Upscaling      
                                   └─ Format Optimization       
```

### Processing Stages

1. **Analysis & Rewrapping** - Detect format, rewrap to ProRes container
2. **Deinterlacing** - QTGMC with Placebo preset for maximum quality
3. **Chroma Cleanup** - Multi-pass temporal and spatial artifact removal
4. **Pixel Aspect Correction** - Convert DV to square pixels (1920×1080)
5. **Neural Upscaling** - NNEDI3 2× upscaling to 4K (3840×2160)
6. **Final Encoding** - ProRes 422 HQ with DCI-P3 color space

## 🎛️ Advanced Configuration

### VapourSynth Scripts

- **`upscale.vpy`** - Main processing pipeline
- **`rewrap.py`** - Format conversion and analysis

### Key Parameters

```python
# QTGMC Settings
Preset="Placebo"          # Maximum quality
SourceMatch=3             # Advanced source matching
Lossless=2               # High quality mode
MatchEnhance=0.95        # Motion matching enhancement

# NNEDI3 Settings
nsize=6                  # 32×6 neighborhood
nns=4                    # 256 neurons
qual=2                   # Highest quality
```

## 📁 Supported Formats

### Input Formats
- **Containers**: AVI, MKV, MP4, MOV, MXF, TS, M2TS, DV, HDV
- **Codecs**: DV, HDV, H.264, MPEG-2, ProRes
- **Resolutions**: 720×576 (PAL DV), 720×480 (NTSC DV), 1440×1080 (HDV)

### Output Format
- **Container**: QuickTime MOV
- **Codec**: ProRes 422 HQ (10-bit 4:2:2)
- **Resolution**: 3840×2160 (4K UHD)
- **Color Space**: DCI-P3
- **Audio**: PCM 24-bit uncompressed

## 🛠️ Troubleshooting

### Common Issues

**VapourSynth Import Errors**
```bash
# Ensure VapourSynth is properly installed
python -c "import vapoursynth; print('VapourSynth OK')"

# Check plugin installation
vsrepo installed
```

**FFmpeg Not Found**
```bash
# Verify FFmpeg installation
ffmpeg -version

# Add FFmpeg to system PATH
```

**Memory Issues**
- Reduce thread count in settings
- Enable test mode for large files
- Process smaller batches

### Performance Optimization

- **CPU**: Use thread count = CPU cores
- **RAM**: 16GB+ recommended for 4K processing
- **Storage**: SSD recommended for temp files
- **GPU**: NVIDIA GPU optional for monitoring

## 📊 Performance Metrics

Typical processing times (DV → 4K):
- **Test Mode** (200 frames): ~2-5 minutes
- **Full Video** (25fps PAL): ~0.1-0.5× real-time
- **Batch Processing**: Automatic queue management

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/enhancement`)
3. Commit changes (`git commit -am 'Add enhancement'`)
4. Push to branch (`git push origin feature/enhancement`)
5. Create Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **VapourSynth Team** - Powerful video processing framework
- **QTGMC** by Vit - Industry-standard deinterlacing
- **NNEDI3** - Neural network edge-directed interpolation
- **FFmpeg** - Universal media processing

## 📞 Support

- 📖 **Documentation**: Check the code comments and docstrings
- 🐛 **Issues**: Report bugs via GitHub Issues
- 💬 **Discussions**: Join GitHub Discussions for help

---

**Developed and tested on Windows 11 | Compatible with macOS and Linux**
