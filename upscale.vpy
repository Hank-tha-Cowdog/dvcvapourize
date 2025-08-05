import vapoursynth as vs
from vapoursynth import core
import havsfunc as haf  # QTGMC deinterlacing
import sys
import os
from vsdehalo import fine_dehalo  # optional dehalo

# Set thread count
core.num_threads = 10

def log_format(clip, stage_name):
    if hasattr(clip, 'format') and clip.format is not None:
        info = f"[FORMAT] {stage_name}: {clip.width}x{clip.height}, {clip.format.name}, {clip.format.id}, FPS: {clip.fps}"
        print(info, file=sys.stderr)
    else:
        print(f"[FORMAT] {stage_name}: Format information not available", file=sys.stderr)
    return clip

# Retrieve input file with better error handling
if 'input_file' not in globals():
    raise vs.Error('ERROR: "input_file" not specified. Use `-a input_file="path"` in your vspipe command.')

# Debug: Print the actual path received
print(f"[DEBUG] Raw input_file value: {repr(input_file)}", file=sys.stderr)
print(f"[DEBUG] Resolved input_file path: {os.path.abspath(input_file)}", file=sys.stderr)
print(f"[DEBUG] File exists check: {os.path.exists(input_file)}", file=sys.stderr)

# Validate input file exists
if not os.path.exists(input_file):
    raise vs.Error(f'ERROR: Input file does not exist: {input_file}')

print(f"[INPUT] Loading file: {input_file}", file=sys.stderr)

# Source loading with better error handling
print("[SOURCE] Attempting FFmpegSource2 (cache disabled for piping)", file=sys.stderr)
try:
    clip = core.ffms2.Source(input_file, cache=False)
    print("[SOURCE] FFmpegSource2 loaded successfully", file=sys.stderr)
except Exception as e:
    print(f"[SOURCE] FFmpegSource2 failed: {e}", file=sys.stderr)
    print("[SOURCE] Trying LSMASHSource as fallback", file=sys.stderr)
    try:
        clip = core.lsmas.LWLibavSource(input_file)
        print("[SOURCE] LSMASHSource loaded successfully", file=sys.stderr)
    except Exception as e2:
        print(f"[SOURCE] LSMASHSource also failed: {e2}", file=sys.stderr)
        raise vs.Error(f"Both source plugins failed. FFmpegSource2: {e}, LSMASHSource: {e2}")

clip = log_format(clip, "Source clip")

# -----------------------------------------------------------------
# STEP 1: Upsample to 10-bit 4:2:2 with dithering for high-quality processing
# -----------------------------------------------------------------
clip = core.resize.Point(
    clip,
    format=vs.YUV422P10,
    dither_type="error_diffusion"
)
clip = log_format(clip, "After resize.Point to YUV422P10")

# -----------------------------------------------------------------
# STEP 1b: Set DCI-P3 color space properties
# Note: Color space will be handled by FFmpeg in the pipeline
# -----------------------------------------------------------------
# clip = core.std.SetFrameProps(
#     clip,
#     _ColorSpace=1,    # BT.709 matrix (numeric value)
#     _ColorPrimaries=9, # BT.2020 primaries (numeric value)
#     _Transfer=1,      # BT.709 gamma (numeric value)
#     _ColorRange=1     # Limited range (numeric value)
# )
clip = log_format(clip, "After format conversion (DCI-P3 handled by FFmpeg)")

# -----------------------------------------------------------------
# STEP 2: IMPROVED DEINTERLACING - Fix framerate and chroma issues
# -----------------------------------------------------------------
print("[DEINTERLACE] Starting QTGMC Placebo preset with aggressive motion analysis for fast motion/occlusion", file=sys.stderr)

# Enhanced QTGMC settings for aggressive motion analysis - FIXED FPS AND QUALITY
deinterlaced = haf.QTGMC(
    clip,
    Preset="Placebo",          # Maximum quality preset for flexibility
    TFF=True,                  # Top field first for PAL
    SourceMatch=3,             # Enable source matching for better motion
    Lossless=2,                # RESTORED: High quality lossless mode (remove InputType=1)
    NoiseProcess=1,            # Enable noise processing
    NoiseRestore=0.3,          # REDUCED: Less noise restoration
    Sharpness=0.0,             # NO SHARPENING as requested
    EZDenoise=0.0,             # Keep denoising disabled
    # Chroma-specific settings
    ChromaMotion=True,         # Enable chroma motion compensation
    ChromaNoise=True,          # Enable chroma noise processing
    Precise=True,              # More precise processing
    # Advanced motion settings - VERIFIED PARAMETERS
    MatchEnhance=0.95,         # Very high motion matching enhancement
    TR0=2,                     # Base temporal radius (Placebo supports this)
    TR1=2,                     # Motion search temporal radius
    TR2=2,                     # Post-processing temporal radius
    Rep0=4,                    # Repair level for temporal inconsistencies
    Rep2=4,                    # Secondary repair level
    # Border handling
    Border=True,               # Handle frame borders better
    # REMOVED InputType=1 to allow Lossless=2
    # Frame rate handling
    FPSDivisor=2               # Convert 50i to 25p properly
)
deinterlaced = log_format(deinterlaced, "After improved QTGMC")

# -----------------------------------------------------------------
# STEP 2b: CONDITIONAL FRAMERATE CORRECTION (only if needed)
# -----------------------------------------------------------------
# Check if QTGMC produced the correct framerate
if deinterlaced.fps != 25.0:
    print(f"[FPS] QTGMC output fps: {deinterlaced.fps}, correcting to 25fps", file=sys.stderr)
    deinterlaced = core.std.AssumeFPS(
        deinterlaced,
        fpsnum=25,
        fpsden=1
    )
    deinterlaced = log_format(deinterlaced, "After FPS correction to 25p")
else:
    print(f"[FPS] QTGMC output fps correct: {deinterlaced.fps}", file=sys.stderr)

# -----------------------------------------------------------------
# STEP 3: Square-pixel conversion (16:9 DAR → 1:1 PAR)
# Note: Correcting 1440x1080 HDV PAR to 1920x1080 square pixels
# -----------------------------------------------------------------
dar = 16/9
new_w = int(round(dar * deinterlaced.height))
if new_w % 2:
    new_w += 1

deinterlaced = core.resize.Spline36(
    deinterlaced,
    width=new_w,
    height=deinterlaced.height
)
deinterlaced = log_format(deinterlaced, "After square-pixel conversion")

# -----------------------------------------------------------------
# STEP 4: Enhanced chroma cleanup for high-contrast edges
# -----------------------------------------------------------------
print("[CLEANUP] Applying enhanced chroma processing for high-contrast motion", file=sys.stderr)

# Separate luma and chroma for individual processing
y_plane = core.std.ShufflePlanes(deinterlaced, 0, vs.GRAY)
u_plane = core.std.ShufflePlanes(deinterlaced, 1, vs.GRAY)
v_plane = core.std.ShufflePlanes(deinterlaced, 2, vs.GRAY)

# NEW: Stage 1 - MULTIPLE temporal averaging for motion artifacts
print("[TEMPORAL] Applying multiple temporal chroma smoothing passes", file=sys.stderr)
# Multiple temporal passes with different weights and frame shifts
u_temp1 = core.std.Merge(u_plane, u_plane.std.DuplicateFrames([0]), weight=0.3)     # 30% previous frame
u_temp2 = core.std.Merge(u_temp1, u_plane.std.DuplicateFrames([0,0]), weight=0.2)  # 20% 2-frame shift
v_temp1 = core.std.Merge(v_plane, v_plane.std.DuplicateFrames([0]), weight=0.3)     # 30% previous frame
v_temp2 = core.std.Merge(v_temp1, v_plane.std.DuplicateFrames([0,0]), weight=0.2)  # 20% 2-frame shift

# Stage 2: MULTI-PASS vertical smoothing for remaining motion artifacts
print("[MULTIPASS] Applying multi-pass vertical smoothing", file=sys.stderr)
u_clean1a = core.std.Convolution(u_temp2, matrix=[1, 3, 1], mode='v')  # First pass: gentler
u_clean1b = core.std.Convolution(u_clean1a, matrix=[1, 3, 1], mode='v')  # Second pass: compound effect
v_clean1a = core.std.Convolution(v_temp2, matrix=[1, 3, 1], mode='v')  # First pass: gentler
v_clean1b = core.std.Convolution(v_clean1a, matrix=[1, 3, 1], mode='v')  # Second pass: compound effect

# Stage 3: ADAPTIVE chroma processing - stronger processing only where chroma varies significantly
print("[ADAPTIVE] Applying adaptive chroma processing", file=sys.stderr)
u_aggressive = core.std.Convolution(u_clean1b, matrix=[1, 4, 1], mode='v')  # Aggressive processing
v_aggressive = core.std.Convolution(v_clean1b, matrix=[1, 4, 1], mode='v')  # Aggressive processing

# Create adaptive masks - apply aggressive processing only where chroma differences are significant
u_adaptive = core.std.Expr([u_clean1b, u_aggressive], 'x y - abs 3 > y x ?')  # Use aggressive if difference > 3
v_adaptive = core.std.Expr([v_clean1b, v_aggressive], 'x y - abs 3 > y x ?')  # Use aggressive if difference > 3

# Stage 4: REDUCED horizontal smoothing for edge artifacts (50% less aggressive)
print("[HORIZONTAL] Applying reduced horizontal smoothing", file=sys.stderr)
# CHANGED: Blend 50% original with 50% smoothed (was 100% smoothed)
u_horizontal = core.std.Convolution(u_adaptive, matrix=[1, 2, 1], mode='h')
u_clean2 = core.std.Merge(u_adaptive, u_horizontal, weight=0.5)  # 50% blend instead of full smoothing
v_horizontal = core.std.Convolution(v_adaptive, matrix=[1, 2, 1], mode='h')
v_clean2 = core.std.Merge(v_adaptive, v_horizontal, weight=0.5)  # 50% blend instead of full smoothing

# Recombine planes
processed = core.std.ShufflePlanes([y_plane, u_clean2, v_clean2], [0, 0, 0], vs.YUV)
processed = log_format(processed, "After comprehensive chroma cleanup: temporal + multipass + adaptive + reduced horizontal")

# -----------------------------------------------------------------
# STEP 5: Temporal consistency (MVTools) - Optional for stability
# -----------------------------------------------------------------
# Commenting out for now, but available if needed
# super_clip = core.mv.Super(processed, pel=2)
# mvbw = core.mv.Analyse(super_clip, isb=True, delta=1, overlap=4, blksize=8)
# mvfw = core.mv.Analyse(super_clip, isb=False, delta=1, overlap=4, blksize=8)
# processed = core.mv.Degrain1(
#     processed,
#     super_clip,
#     mvbw,
#     mvfw,
#     thsad=400
# )
# processed = log_format(processed, "After MVTools")

# -----------------------------------------------------------------
# STEP 6: Final 2× exact upscale using NNEDI3 (1920x1080 → 3840x2160)
# -----------------------------------------------------------------
print("[UPSCALE] Starting NNEDI3 2x upscaling to 4K", file=sys.stderr)

# Double height with NNEDI3
up = core.nnedi3.nnedi3(
    processed,
    field=1,     # use top field
    dh=True,     # double height
    nsize=6,     # 32x6 neighborhood
    nns=4,       # 256 neurons
    qual=2,      # highest quality
    etype=0      # rectangle
)
up = log_format(up, "After NNEDI3 height doubling")

# Transpose to double width
up = up.std.Transpose()

# Double height (width) with NNEDI3
up = core.nnedi3.nnedi3(
    up,
    field=1,     # use top field
    dh=True,
    nsize=6,
    nns=4,
    qual=2,
    etype=0
)
up = log_format(up, "After NNEDI3 width doubling")

# Transpose back to original orientation
final = up.std.Transpose()
final = log_format(final, "Final output (NNEDI3 2×)")

# -----------------------------------------------------------------
# FINAL STEP: Sanitize format for piping while preserving DCI-P3 color space
# -----------------------------------------------------------------
final = core.resize.Point(final, format=vs.YUV422P10)
# Note: DCI-P3 color space properties will be set by FFmpeg during encoding
# final = core.std.SetFrameProps(
#     final,
#     _ColorSpace=1,    # BT.709 matrix (numeric value)
#     _ColorPrimaries=9, # BT.2020 primaries (numeric value)
#     _Transfer=1,      # BT.709 gamma (numeric value)
#     _ColorRange=1     # Limited range (numeric value)
# )
final = log_format(final, "After format sanitization (DCI-P3 will be applied by FFmpeg)")

print("[COMPLETE] VapourSynth processing pipeline complete - DCI-P3 color space will be applied by FFmpeg", file=sys.stderr)

# Set as output
final.set_output()