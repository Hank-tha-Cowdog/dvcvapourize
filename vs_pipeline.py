import argparse

# ============================================================================
# CONFIGURATION - These are now set via command-line arguments
# ============================================================================
INPUT_PATH = None
OUTPUT_DIRECTORY_PATH = None

# ============================================================================
# BATCH PROCESSING CONFIGURATION
# ============================================================================
BATCH_MODE = True  # ← CHANGE THIS: True = process directory, False = single file
SUPPORTED_EXTENSIONS = ['.avi', '.mov', '.mp4', '.mkv', '.mpg', '.mpeg', '.ts', '.mts', '.m2ts', '.mxf', '.dv', '.hdv']
SKIP_EXISTING = True  # Skip files that already have processed versions
PROCESS_SUBDIRECTORIES = False  # Set to True to process subdirectories recursively

# ============================================================================
# SIMPLE TEST/FULL MODE CONTROL - ONLY CHANGE THESE TWO LINES
# ============================================================================
TEST_MODE = True          # ← CHANGE THIS: True = test mode, False = full processing  
TEST_FRAME_COUNT = 200     # ← CHANGE THIS: Number of frames to process in test mode

# ============================================================================
# DEVELOPER TOOLS - DEBUGGING AND PERFORMANCE OPTIONS  
# ============================================================================
DEBUG_MODE = True
ENABLE_PERFORMANCE_PROFILING = True
ENABLE_GPU_MONITORING = True
ENABLE_DETAILED_TIMING = True
PROCESS_DURATION = None  # Advanced: Set to seconds to limit processing time, or None for full file

# ============================================================================
# VAPOURSYNTH OPTIONS
# ============================================================================
# The VapourSynth script will use FFmpegSource2 or automatically fallback to LSMASHSource if needed.
# The `cache=False` parameter is used on the source filter to prevent indexing hangs when piping.
# ============================================================================

# Import all required modules
import os
import sys
import subprocess
import time
import re
from tqdm import tqdm
import signal
import threading
import datetime
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import io
import cProfile
import pstats
import queue
from rewrap import rewrap_to_prores
import glob

# Add Rich library for better terminal UI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn, SpinnerColumn
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Consider installing 'rich' for better terminal UI: pip install rich")

# Add psutil for better process management (optional)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Consider installing 'psutil' for better process cleanup: pip install psutil")

# ============================================================================
# GLOBAL VARIABLES
# ============================================================================
class AppContext:
    def __init__(self):
        self.process = None
        self.process_manager = None
        self.current_frame = 0
        self.frame_count = 0
        self.pbar = None
        self.cmd = None
        self.venv_env = None
        self.has_nvidia_gpu = False
        self.start_time = None
        self.profiler = None
        self.run_dir = None
        self.log_file = None
        self.input_file = None
        self.output_dir = None
        self.output_file = None
        self.vapoursynth_started = False
        self.processing_task_created = False
        self.last_frame_time = None
        self.last_frame_count = 0
        self.processing_start_time = None
        # Batch processing variables
        self.files_to_process = []
        self.current_file_index = 0
        self.total_files = 0
        self.batch_start_time = None
        self.batch_progress = None
        self.current_file_task = None
        self.overall_task = None

context = AppContext()
processing_times = {}

# ============================================================================
# BATCH PROCESSING FUNCTIONS
# ============================================================================

def find_video_files(directory_path):
    """Find all supported video files in the directory"""
    video_files = []
    
    if PROCESS_SUBDIRECTORIES:
        # Recursive search
        for ext in SUPPORTED_EXTENSIONS:
            pattern = os.path.join(directory_path, "**", f"*{ext}")
            video_files.extend(glob.glob(pattern, recursive=True))
    else:
        # Search only in the specified directory
        for ext in SUPPORTED_EXTENSIONS:
            pattern = os.path.join(directory_path, f"*{ext}")
            video_files.extend(glob.glob(pattern))
    
    # Sort files for consistent processing order
    video_files.sort()
    
    return video_files

def get_output_filename(input_file, output_dir):
    """Generate the output filename for a given input file"""
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    return os.path.join(output_dir, f"{base_name}.mov")

def should_skip_file(input_file, output_file):
    """Determine if we should skip processing this file"""
    if not SKIP_EXISTING:
        return False
    
    if os.path.exists(output_file):
        # Check if output file is newer than input file
        input_time = os.path.getmtime(input_file)
        output_time = os.path.getmtime(output_file)
        
        if output_time > input_time:
            output_size = os.path.getsize(output_file)
            if output_size > 1000000:  # At least 1MB
                return True
    
    return False

def display_batch_summary():
    """Display a summary of files to be processed"""
    print("\n" + "="*80)
    print("🎬 BATCH PROCESSING SUMMARY")
    print("="*80)
    
    if BATCH_MODE:
        print(f"📁 SOURCE DIRECTORY: {INPUT_PATH}")
        print(f"📂 OUTPUT DIRECTORY: {OUTPUT_DIRECTORY_PATH}")
        print(f"🔍 RECURSIVE SEARCH: {'Yes' if PROCESS_SUBDIRECTORIES else 'No'}")
        print(f"⏭️  SKIP EXISTING: {'Yes' if SKIP_EXISTING else 'No'}")
        print(f"📊 TOTAL FILES FOUND: {len(context.files_to_process)}")
        
        if context.files_to_process:
            print(f"\n📝 FILES TO PROCESS:")
            for i, file_path in enumerate(context.files_to_process[:10], 1):  # Show first 10
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                print(f"   {i:2d}. {os.path.basename(file_path)} ({file_size:.1f} MB)")
            
            if len(context.files_to_process) > 10:
                print(f"   ... and {len(context.files_to_process) - 10} more files")
        
        if TEST_MODE:
            print(f"\n🧪 TEST MODE: Processing {TEST_FRAME_COUNT} frames per file")
        else:
            print(f"\n🎞️  FULL MODE: Processing complete files")
    else:
        print(f"📁 SINGLE FILE: {INPUT_PATH}")
        print(f"📂 OUTPUT DIRECTORY: {OUTPUT_DIRECTORY_PATH}")
    
    print("="*80 + "\n")

def process_single_file(input_file_path):
    """Process a single file through the entire pipeline"""
    try:
        # Reset context for this file
        context.input_file = input_file_path
        context.output_file = get_output_filename(input_file_path, context.output_dir)
        context.current_frame = 0
        context.frame_count = 0
        context.vapoursynth_started = False
        context.processing_task_created = False
        context.last_frame_time = None
        context.last_frame_count = 0
        context.processing_start_time = None
        
        log_message(f"Starting processing: {os.path.basename(input_file_path)}")
        
        # Check if we should skip this file
        if should_skip_file(input_file_path, context.output_file):
            log_message(f"Skipping {os.path.basename(input_file_path)} - output already exists and is newer")
            return True
        
        # Step 1: Rewrap the source file
        log_message(f"Rewrapping: {os.path.basename(input_file_path)}")
        rewrapped_file = rewrap_to_prores(input_file_path, context.output_dir)
        if not rewrapped_file:
            log_message(f"Failed to rewrap: {os.path.basename(input_file_path)}")
            return False
        
        context.input_file = rewrapped_file
        
        # Step 2: Get frame count for this file
        context.frame_count = get_frame_count(context.input_file)
        
        # Step 3: Build and execute VapourSynth command
        if not build_and_execute_command():
            log_message(f"Failed to process: {os.path.basename(input_file_path)}")
            return False
        
        # Step 4: Verify output
        if verify_output_quality():
            log_message(f"Successfully processed: {os.path.basename(input_file_path)}")
            if verify_color_space():
                log_message("Color space verification successful - DCI-P3 maintained.")
            return True
        else:
            log_message(f"Output verification failed: {os.path.basename(input_file_path)}")
            return False
            
    except Exception as e:
        log_message(f"Error processing {os.path.basename(input_file_path)}: {str(e)}")
        import traceback
        log_message(f"Traceback: {traceback.format_exc()}")
        return False

def get_frame_count(input_file):
    """Get frame count for a specific file"""
    try:
        # Try reading the container's nb_frames header
        probe_cmd = (
            f'ffprobe -v error -select_streams v:0 '
            f'-show_entries stream=nb_frames '
            f'-of default=noprint_wrappers=1:nokey=1 "{input_file}"'
        )
        result = subprocess.run(probe_cmd, capture_output=True, text=True, shell=True, timeout=10)
        stdout = result.stdout.strip()
        
        if result.returncode == 0 and stdout.isdigit():
            frame_count = int(stdout)
            log_message(f"Frame count detected via metadata: {frame_count}")
            return frame_count
        else:
            # Fallback: compute from duration × framerate
            duration_cmd = (
                f'ffprobe -v error '
                f'-show_entries format=duration '
                f'-of default=noprint_wrappers=1:nokey=1 "{input_file}"'
            )
            dur_res = subprocess.run(duration_cmd, capture_output=True, text=True, shell=True, timeout=10)
            duration = float(dur_res.stdout.strip())

            fr_cmd = (
                f'ffprobe -v error -select_streams v:0 '
                f'-show_entries stream=r_frame_rate '
                f'-of default=noprint_wrappers=1:nokey=1 "{input_file}"'
            )
            fr_res = subprocess.run(fr_cmd, capture_output=True, text=True, shell=True, timeout=10)
            fr_str = fr_res.stdout.strip()
            
            if '/' in fr_str:
                num, den = map(int, fr_str.split('/'))
                fr = num/den
            else:
                fr = float(fr_str)

            frame_count = int(duration * fr)
            log_message(f"Frame count estimated from duration ({duration:.2f}s) * framerate ({fr:.2f}fps): {frame_count}")
            return frame_count
            
    except Exception as e:
        # Ultimate fallback: size-based guess
        file_size = os.path.getsize(input_file) / (1024 * 1024)
        estimated = int((file_size * 8 * 1024 * 1024) / (20_000_000 / 25))  # Assume 25fps for PAL
        log_message(f"Could not determine frame count; using fallback estimation of {estimated} frames due to: {e}")
        return estimated

def build_and_execute_command():
    """Build and execute the VapourSynth processing command"""
    try:
        # Build VapourSynth command
        script_path = "upscale.vpy"
        
        vspipe_args = [
            'vspipe',
            '-a', f'input_file={context.input_file}',
            script_path
        ]

        # Add frame range arguments
        if TEST_MODE:
            vspipe_args.extend(['-s', '0', '-e', str(TEST_FRAME_COUNT - 1)])
        elif context.frame_count and context.frame_count > 0:
            vspipe_args.extend(['-s', '0', '-e', str(context.frame_count - 1)])

        vspipe_args.append('-')  # Pipe to stdout

        vspipe_cmd = ' '.join(f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in vspipe_args)

        # Build FFmpeg command
        expected_width = 3840
        expected_height = 2160
        raw_fps = "25/1"
        
        ffmpeg_cmd = (
            f'ffmpeg -f rawvideo -pix_fmt yuv422p10le -s {expected_width}x{expected_height} -r {raw_fps} -i - '
            f'-c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le '
            f'-color_range tv -color_primaries 12 -color_trc 11 -colorspace 12 '
            f'-video_track_timescale 25 -y "{context.output_file}"'
        )

        context.cmd = f"{vspipe_cmd} | {ffmpeg_cmd}"
        
        log_message(f"Processing command: {context.cmd}")
        
        # Execute the command
        context.process_manager = ProcessManager(context.cmd, env=context.venv_env, timeout=30)
        context.process = context.process_manager.start()

        if not context.process:
            log_message("Failed to start processing")
            return False

        # Start monitoring
        progress_thread = threading.Thread(target=monitor_progress, name="ProgressMonitor")
        progress_thread.daemon = True
        progress_thread.start()

        # Wait for completion
        try:
            while context.process.poll() is None:
                try:
                    context.process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    continue
                except KeyboardInterrupt:
                    log_message("Keyboard interrupt detected", force_console=True)
                    context.process_manager.stop()
                    raise
        finally:
            context.process_manager.stop()

        return context.process.returncode == 0
        
    except Exception as e:
        log_message(f"Error in build_and_execute_command: {str(e)}")
        return False

# ============================================================================
# EXISTING FUNCTION DEFINITIONS (keeping all the original functions)
# ============================================================================

def record_timing(stage_name):
    """Record time taken for a specific processing stage"""
    if ENABLE_DETAILED_TIMING:
        now = time.time()
        if 'last_time' in processing_times:
            elapsed = now - processing_times['last_time']
            processing_times[stage_name] = elapsed
            print(f"Time for {stage_name}: {elapsed:.2f} seconds")
        processing_times['last_time'] = now

def log_message(message, print_to_console=True, force_console=False):
    """Log message to file and optionally to console"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}"
    
    # Log to file if available
    if context.log_file:
        try:
            with open(context.log_file, 'a', encoding='utf-8') as f:
                f.write(full_message + "\n")
                f.flush()
        except Exception as e:
            if not hasattr(context, '_log_error_shown'):
                print(f"!!! LOGGING ERROR: {str(e)}")
                context._log_error_shown = True
    
    # Console output
    if print_to_console:
        if force_console or context.pbar is None:
            print(full_message)

def debug_log(message):
    """Log message only when in debug mode"""
    if DEBUG_MODE:
        log_message(f"[DEBUG] {message}")
        
        debug_file = os.path.join(context.run_dir, "debug_log.txt")
        with open(debug_file, 'a') as f:
            f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def save_performance_profile():
    """Save the performance profile data to a file"""
    if not ENABLE_PERFORMANCE_PROFILING or context.profiler is None:
        log_message("Performance profiling was not enabled or profiler is None")
        return
        
    try:
        context.profiler.disable()
        
        profile_path = os.path.join(context.run_dir, "performance_profile.txt")
        log_message(f"Saving performance profile to {profile_path}")
        
        s = io.StringIO()
        
        try:
            import pstats
            ps = pstats.Stats(context.profiler, stream=s).sort_stats('cumulative')
            ps.print_stats(50)
        except ImportError:
            log_message("Error: pstats module not available, using basic profiling output")
            s.write("pstats module not available for detailed profiling output\n")
            s.write(str(context.profiler))
        
        with open(profile_path, 'w') as f:
            f.write("VapourSynth Processing Pipeline Performance Profile\n")
            f.write("=================================================\n\n")
            f.write(s.getvalue())
            
            if processing_times and len(processing_times) > 1:
                f.write("\n\nStage Timing Information:\n")
                f.write("========================\n\n")
                for stage, duration in processing_times.items():
                    if stage != 'last_time':
                        f.write(f"{stage}: {duration:.2f} seconds\n")
                        
            total_time = time.time() - context.start_time
            f.write(f"\nTotal processing time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)\n")
            if total_time > 0 and context.frame_count and context.frame_count > 0:
                f.write(f"Average processing speed: {context.frame_count/total_time:.2f} frames per second\n")
            
        log_message(f"Performance profile saved to {profile_path}")
        return True
    except Exception as e:
        log_message(f"Error saving performance profile: {str(e)}")
        import traceback
        log_message(f"Traceback: {traceback.format_exc()}")
        return False

def signal_handler(sig, frame):
    """Handle interrupt signals gracefully with improved cleanup"""
    log_message(f"Received signal {sig}, shutting down gracefully...", force_console=True)
    
    # Stop all monitoring threads first
    if hasattr(context, 'process_manager') and context.process_manager:
        try:
            context.process_manager.stop()
        except Exception as e:
            log_message(f"Error stopping process manager: {str(e)}", force_console=True)
    
    # Gracefully terminate the main process
    if context.process is not None:
        try:
            log_message("Terminating VapourSynth/FFmpeg processes...", force_console=True)
            context.process.terminate()
            
            try:
                context.process.wait(timeout=15)
                log_message("Process terminated gracefully", force_console=True)
            except subprocess.TimeoutExpired:
                log_message("Process not responding after 15 seconds, forcing kill...", force_console=True)
                context.process.kill()
                
                try:
                    context.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    log_message("Process forcefully terminated", force_console=True)
                
        except Exception as e:
            log_message(f"Error terminating process: {str(e)}", force_console=True)
    
    # Clean up progress bar
    if hasattr(context, 'pbar') and context.pbar:
        try:
            if hasattr(context.pbar, 'stop'):
                context.pbar.stop()
            elif hasattr(context.pbar, 'close'):
                context.pbar.close()
        except:
            pass
    
    # Clean up batch progress
    if hasattr(context, 'batch_progress') and context.batch_progress:
        try:
            context.batch_progress.stop()
        except:
            pass
    
    log_message("Saving performance data before exit...", force_console=True)
    try:
        if ENABLE_PERFORMANCE_PROFILING and hasattr(context, 'profiler') and context.profiler is not None:
            save_performance_profile()
    except Exception as e:
        log_message(f"Error saving profile on exit: {str(e)}", force_console=True)
    
    log_message("Cleanup complete. Exiting...", force_console=True)
    sys.exit(0)

def monitor_progress():
    """Monitor processing progress and update progress bar"""
    import time
    import re
    
    context.current_frame = 0
    
    try:
        if context.process is None:
            log_message("No process to monitor", force_console=True)
            return
            
        if RICH_AVAILABLE and BATCH_MODE:
            # In batch mode, update the current file progress
            if context.current_file_task is not None:
                for line in iter(context.process.stderr.readline, ''):
                    current_time = time.time()
                    if not line:
                        break
                        
                    line = line.strip()
                    if not line:
                        continue
                    
                    if DEBUG_MODE and line:
                        debug_log(f"STDERR: {line}")
                    
                    if context.process.poll() is not None:
                        break
                    
                    # Detect VapourSynth processing start
                    if not context.vapoursynth_started and (
                        "[FORMAT]" in line or 
                        "[SOURCE]" in line or
                        "FFmpegSource2 loaded successfully" in line or
                        "LSMASHSource loaded successfully" in line
                    ):
                        context.vapoursynth_started = True
                        if DEBUG_MODE:
                            debug_log(f"VapourSynth detected from line: {line}")
                    
                    # Update frame progress
                    frame_patterns = [
                        r'frame=\s*(\d+)',
                        r'Output (\d+) frames',
                        r'(\d+) frames in',
                    ]
                    
                    for pattern in frame_patterns:
                        try:
                            frame_match = re.search(pattern, line, re.IGNORECASE)
                            if frame_match:
                                current_frame = int(frame_match.group(1))
                                if current_frame > context.current_frame:
                                    context.current_frame = current_frame
                                    
                                    # Calculate speed
                                    if context.last_frame_time is not None:
                                        time_diff = current_time - context.last_frame_time
                                        frame_diff = current_frame - context.last_frame_count
                                        if time_diff > 0 and frame_diff > 0:
                                            fps = frame_diff / time_diff
                                            speed_text = f"{fps:.1f} fps"
                                        else:
                                            speed_text = "calculating..."
                                    else:
                                        speed_text = "starting..."
                                    
                                    context.last_frame_time = current_time
                                    context.last_frame_count = current_frame
                                    
                                    # Update progress
                                    if TEST_MODE:
                                        completed = min(current_frame, TEST_FRAME_COUNT)
                                        total = TEST_FRAME_COUNT
                                    else:
                                        completed = current_frame
                                        total = context.frame_count if context.frame_count else current_frame + 1000
                                    
                                    context.batch_progress.update(
                                        context.current_file_task,
                                        completed=completed,
                                        total=total,
                                        speed=speed_text
                                    )
                                break
                        except (ValueError, AttributeError):
                            continue
        else:
            # Fallback or single file mode - use existing progress monitoring
            # ... (existing non-batch progress monitoring code)
            pass
            
    except Exception as e:
        log_message(f"Error in progress monitoring: {str(e)}", force_console=True)

# ... (Include all other existing functions: setup_venv_environment, verify_output_quality, 
# verify_color_space, detect_nvidia_gpu, monitor_gpu_memory, ProcessWatchdog, ProcessManager, etc.)

def setup_venv_environment():
    """Configure environment to use venv packages with VapourSynth"""
    venv_python = sys.executable
    venv_dir = os.path.dirname(venv_python)
    venv_site_packages = os.path.join(venv_dir, "..", "Lib", "site-packages")
    venv_site_packages = os.path.abspath(venv_site_packages)
    
    env = os.environ.copy()
    
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = venv_site_packages + ";" + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = venv_site_packages
    
    env["PATH"] = venv_dir + ";" + env["PATH"]
    
    print(f"[VENV] Using Python: {venv_python}")
    print(f"[VENV] Added to PYTHONPATH: {venv_site_packages}")
    
    return env

def verify_output_quality():
    """Verify the output file integrity and quality"""
    if not os.path.exists(context.output_file):
        log_message("Output verification: File does not exist")
        return False
        
    file_size = os.path.getsize(context.output_file)
    if file_size < 1000000:  # Less than 1MB
        log_message(f"Output verification: File too small ({file_size} bytes)")
        return False
        
    try:
        probe_cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{context.output_file}"'
        result = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            duration_str = result.stdout.strip()
            if duration_str.lower() in ['n/a', 'na', '']:
                log_message("Output verification: Duration unavailable but file exists and has good size")
                return True
            try:
                duration = float(duration_str)
                log_message(f"Output verification: File is valid with duration {duration:.2f} seconds")
                return True
            except ValueError:
                log_message(f"Output verification: Could not parse duration '{duration_str}' but file appears valid")
                return True
        else:
            log_message(f"Output verification: ffprobe failed with return code {result.returncode}")
            return False
    except Exception as e:
        log_message(f"Output verification error: {str(e)}")
        return False

def verify_color_space():
    """Verify the output file has correct DCI-P3 color space"""
    if not os.path.exists(context.output_file):
        log_message("Color space verification: File does not exist")
        return False
        
    try:
        probe_cmd = (
            f'ffprobe -v error -select_streams v:0 '
            f'-show_entries stream=color_primaries,color_trc,colorspace,color_range '
            f'-of default=noprint_wrappers=1 "{context.output_file}"'
        )
        result = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            output_lines = result.stdout.strip().split('\n')
            color_info = {}
            for line in output_lines:
                if '=' in line:
                    key, value = line.split('=', 1)
                    color_info[key] = value
            
            log_message(f"Color space verification: {color_info}")
            
            expected_primaries = ['smpte432', '12']
            expected_trc = ['smpte428', '11']
            expected_colorspace = ['smpte432', '12']
            
            primaries_ok = any(exp in color_info.get('color_primaries', '').lower() for exp in expected_primaries)
            trc_ok = any(exp in color_info.get('color_trc', '').lower() for exp in expected_trc)
            colorspace_ok = any(exp in color_info.get('colorspace', '').lower() for exp in expected_colorspace)
            
            if primaries_ok and trc_ok and colorspace_ok:
                log_message("✅ Color space verification: Proper DCI-P3 color space detected")
                return True
            else:
                log_message("⚠️  Color space verification: May not have correct DCI-P3 color space")
                return False
        else:
            log_message(f"Color space verification: ffprobe failed with return code {result.returncode}")
            return False
    except Exception as e:
        log_message(f"Color space verification error: {str(e)}")
        return False

def detect_nvidia_gpu():
    """Detect if NVIDIA GPU is available for monitoring"""
    try:
        result = subprocess.run('nvidia-smi', capture_output=True, text=True, shell=True)
        return result.returncode == 0
    except:
        return False

def monitor_gpu_memory():
    """Check GPU memory usage once at startup"""
    if not context.has_nvidia_gpu:
        return
        
    try:
        cmd = 'nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            memory_used, memory_total = map(int, result.stdout.strip().split(','))
            usage_percent = (memory_used / memory_total) * 100
            
            log_message(f"GPU Memory at startup: {memory_used}MB / {memory_total}MB ({usage_percent:.1f}%)")
            
            if usage_percent > 80:
                log_message(f"WARNING: GPU memory usage is high at startup: {usage_percent:.1f}%")
    except Exception as e:
        log_message(f"Error checking GPU memory: {str(e)}")

class ProcessWatchdog:
    """Watchdog to monitor process health and handle frozen states"""
    def __init__(self, process, timeout=30, check_interval=1):
        self.process = process
        self.timeout = timeout
        self.check_interval = check_interval
        self.last_output_time = time.time()
        self.output_detected = False
        self.stop_event = threading.Event()
        self._output_queue = queue.Queue()
        
    def reset_timer(self):
        """Reset the last output time"""
        self.last_output_time = time.time()
        self.output_detected = True
        
    def check_process_health(self):
        """Check if process is healthy based on output and resource usage"""
        current_time = time.time()
        
        if self.process.poll() is not None:
            return False
            
        try:
            while True:
                self._output_queue.get_nowait()
                self.reset_timer()
        except queue.Empty:
            pass
            
        if current_time - self.last_output_time > self.timeout and self.output_detected:
            return False
            
        return True
        
    def monitor(self):
        """Main monitoring loop"""
        while not self.stop_event.is_set():
            if not self.check_process_health():
                log_message("Process appears to be frozen, initiating cleanup...", force_console=True)
                self.cleanup()
                break
            time.sleep(self.check_interval)
    
    def cleanup(self):
        """Clean up a frozen or stuck process"""
        try:
            if self.process.poll() is None:
                log_message("Terminating frozen process...", force_console=True)
                self.process.terminate()
                
                for _ in range(5):
                    if self.process.poll() is not None:
                        break
                    time.sleep(0.5)
                    
                if self.process.poll() is None:
                    log_message("Process not responding to terminate, forcing kill...", force_console=True)
                    self.process.kill()
        except Exception as e:
            log_message(f"Error during process cleanup: {str(e)}", force_console=True)
    
    def start(self):
        """Start the watchdog monitor in a separate thread"""
        self.monitor_thread = threading.Thread(target=self.monitor)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop(self):
        """Stop the watchdog monitor"""
        self.stop_event.set()
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)

class ProcessManager:
    """Manages process lifecycle and monitoring"""
    def __init__(self, cmd, env=None, timeout=30):
        self.cmd = cmd
        self.env = env
        self.timeout = timeout
        self.process = None
        self.watchdog = None
        
    def start(self):
        """Start the process and monitoring"""
        try:
            log_message("Starting process with command: " + self.cmd)
            self.process = subprocess.Popen(
                self.cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=self.env,
                bufsize=1,
                close_fds=False
            )
            
            return self.process
        except Exception as e:
            log_message(f"Error starting process: {str(e)}", force_console=True)
            return None
    
    def stop(self):
        """Stop the process and cleanup"""
        if self.watchdog:
            self.watchdog.stop()
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    log_message("Process didn't terminate gracefully, forcing kill", force_console=True)
                    self.process.kill()
            except Exception as e:
                log_message(f"Error during process termination: {str(e)}", force_console=True)
                
    def is_running(self):
        """Check if process is still running"""
        return self.process and self.process.poll() is None

def initialize_parallel():
    """Initialize components in parallel to reduce startup time"""
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        
        def init_vapoursynth():
            try:
                import vapoursynth as vs
                core = vs.core
                core.num_threads = multiprocessing.cpu_count()
                return True
            except Exception as e:
                log_message(f"Error initializing VapourSynth: {str(e)}")
                return False
        
        def init_filesystem():
            try:
                if BATCH_MODE:
                    if not os.path.exists(INPUT_PATH):
                        log_message(f"ERROR: Input directory does not exist: {INPUT_PATH}")
                        return False
                else:
                    if not os.path.exists(INPUT_PATH):
                        log_message(f"ERROR: Input file does not exist: {INPUT_PATH}")
                        return False
                    
                if not os.path.exists(OUTPUT_DIRECTORY_PATH):
                    try:
                        os.makedirs(OUTPUT_DIRECTORY_PATH)
                    except Exception as e:
                        log_message(f"ERROR: Cannot create output directory: {str(e)}")
                        return False
                return True
            except Exception as e:
                log_message(f"Error in filesystem initialization: {str(e)}")
                return False
        
        def init_logging():
            try:
                with open(context.log_file, 'w') as f:
                    f.write("")
                return True
            except Exception as e:
                print(f"ERROR: Cannot initialize logging: {str(e)}")
                return False
        
        futures.append(executor.submit(init_vapoursynth))
        futures.append(executor.submit(init_filesystem))
        futures.append(executor.submit(init_logging))
        
        results = [f.result() for f in futures]
        return all(results)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    global INPUT_PATH, OUTPUT_DIRECTORY_PATH, BATCH_MODE, PROCESS_SUBDIRECTORIES, TEST_MODE, TEST_FRAME_COUNT

    parser = argparse.ArgumentParser(description="HDVapourize VapourSynth Pipeline")
    parser.add_argument('--input', required=True, help='Input file or directory')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--batch_mode', action='store_true', help='Enable batch processing for a directory')
    parser.add_argument('--recursive', action='store_true', help='Process subdirectories recursively in batch mode')
    parser.add_argument('--test_mode', action='store_true', help='Run in test mode')
    parser.add_argument('--test_frames', type=int, default=200, help='Number of frames to process in test mode')
    args = parser.parse_args()

    INPUT_PATH = args.input
    OUTPUT_DIRECTORY_PATH = args.output
    BATCH_MODE = args.batch_mode
    PROCESS_SUBDIRECTORIES = args.recursive
    TEST_MODE = args.test_mode
    TEST_FRAME_COUNT = args.test_frames

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize timing
    context.start_time = time.time()
    context.batch_start_time = time.time()
    processing_times['last_time'] = time.time()
    record_timing("initialization")

    # Set up venv environment
    context.venv_env = setup_venv_environment()

    # Set up paths and determine processing mode
    if BATCH_MODE and os.path.isdir(INPUT_PATH):
        # Batch processing mode
        log_message(f"BATCH MODE: Processing directory {INPUT_PATH}")
        context.files_to_process = find_video_files(INPUT_PATH)
        context.total_files = len(context.files_to_process)
        
        if not context.files_to_process:
            print(f"ERROR: No supported video files found in {INPUT_PATH}")
            print(f"Supported extensions: {', '.join(SUPPORTED_EXTENSIONS)}")
            sys.exit(1)
            
    elif not BATCH_MODE or os.path.isfile(INPUT_PATH):
        # Single file mode
        log_message(f"SINGLE FILE MODE: Processing {INPUT_PATH}")
        if not os.path.exists(INPUT_PATH):
            print(f"ERROR: Input file does not exist: {INPUT_PATH}")
            sys.exit(1)
        context.files_to_process = [INPUT_PATH]
        context.total_files = 1
    else:
        print(f"ERROR: Invalid input path: {INPUT_PATH}")
        print("Path must be either a file (for single mode) or directory (for batch mode)")
        sys.exit(1)

    context.output_dir = OUTPUT_DIRECTORY_PATH

    # Check network drive accessibility
    network_drive = os.path.splitdrive(context.output_dir)[0] + '\\'
    print(f"Checking network path: {context.output_dir}")

    try:
        if not os.path.exists(context.output_dir):
            os.makedirs(context.output_dir, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Cannot access/create output directory: {context.output_dir}")
        print(f"Error details: {str(e)}")
        sys.exit(1)

    print(f"Output directory is accessible: {context.output_dir}")

    # Create timestamp and set up logging
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logs_dir = os.path.join(context.output_dir, f"pipeline_logs_{timestamp}")
    os.makedirs(logs_dir, exist_ok=True)
    context.run_dir = logs_dir

    # Set up log file
    log_filename = f"vapoursynth_batch_log_{timestamp}.txt" if BATCH_MODE else f"vapoursynth_log_{timestamp}.txt"
    context.log_file = os.path.join(context.run_dir, log_filename)

    try:
        with open(context.log_file, 'w') as f:
            f.write(f"VapourSynth Processing Log - {timestamp}\n")
            f.write("="*50 + "\n\n")
        log_message("Log file initialized successfully")
    except Exception as e:
        print(f"WARNING: Cannot create log file: {str(e)}")
        context.log_file = None

    # Initialize profiler
    if ENABLE_PERFORMANCE_PROFILING:
        try:
            import cProfile
            context.profiler = cProfile.Profile()
            context.profiler.enable()
        except ImportError:
            print("Profiling modules not available - performance profiling disabled")

    # Initialize GPU monitoring
    context.has_nvidia_gpu = detect_nvidia_gpu()
    if context.has_nvidia_gpu:
        log_message("NVIDIA GPU detected - GPU memory monitoring available")
    else:
        log_message("No NVIDIA GPU detected")

    # Initialize parallel processing
    if not initialize_parallel():
        log_message("Initialization failed. Please check the logs for details.")
        sys.exit(1)

    record_timing("initialization_complete")

    # Display batch summary
    display_batch_summary()

    # Start batch processing
    if BATCH_MODE and RICH_AVAILABLE:
        # Rich progress bar for batch processing
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TextColumn("[green]{task.fields[speed]}")
        ) as progress:
            context.batch_progress = progress
            
            # Create overall progress task
            context.overall_task = progress.add_task(
                f"[cyan]Processing {context.total_files} files...",
                total=context.total_files,
                speed=""
            )
            
            # Create current file task (will be updated per file)
            context.current_file_task = progress.add_task(
                "[yellow]Preparing...",
                total=100,
                speed=""
            )
            
            # Process each file
            successful_files = 0
            failed_files = 0
            
            for i, file_path in enumerate(context.files_to_process):
                context.current_file_index = i
                
                # Update overall progress
                progress.update(
                    context.overall_task,
                    completed=i,
                    description=f"[cyan]Processing file {i+1}/{context.total_files}: {os.path.basename(file_path)}"
                )
                
                # Update current file task
                progress.update(
                    context.current_file_task,
                    completed=0,
                    total=100,
                    description=f"[yellow]Processing: {os.path.basename(file_path)}",
                    speed=""
                )
                
                # Process the file
                start_file_time = time.time()
                if process_single_file(file_path):
                    successful_files += 1
                    log_message(f"✅ Successfully processed: {os.path.basename(file_path)}")
                else:
                    failed_files += 1
                    log_message(f"❌ Failed to process: {os.path.basename(file_path)}")
                
                file_time = time.time() - start_file_time
                
                # Update current file as completed
                progress.update(
                    context.current_file_task,
                    completed=100,
                    description=f"[green]Completed: {os.path.basename(file_path)} ({file_time/60:.1f}m)"
                )
            
            # Final update
            progress.update(
                context.overall_task,
                completed=context.total_files,
                description=f"[green]Batch complete: {successful_files} successful, {failed_files} failed"
            )
            
            time.sleep(2)  # Show final status briefly
    
    else:
        # Fallback processing without Rich or single file mode
        successful_files = 0
        failed_files = 0
        
        for i, file_path in enumerate(context.files_to_process):
            print(f"\n{'='*60}")
            print(f"Processing file {i+1}/{context.total_files}: {os.path.basename(file_path)}")
            print(f"{'='*60}")
            
            start_file_time = time.time()
            if process_single_file(file_path):
                successful_files += 1
                print(f"✅ Successfully processed: {os.path.basename(file_path)}")
            else:
                failed_files += 1
                print(f"❌ Failed to process: {os.path.basename(file_path)}")
            
            file_time = time.time() - start_file_time
            print(f"File processing time: {file_time/60:.1f} minutes")

    # Final summary
    total_time = time.time() - context.batch_start_time
    
    print(f"\n{'='*80}")
    print("🎬 BATCH PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"📊 TOTAL FILES: {context.total_files}")
    print(f"✅ SUCCESSFUL: {successful_files}")
    print(f"❌ FAILED: {failed_files}")
    print(f"⏱️  TOTAL TIME: {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)")
    
    if successful_files > 0:
        avg_time_per_file = total_time / context.total_files
        print(f"📈 AVERAGE TIME PER FILE: {avg_time_per_file/60:.1f} minutes")
    
    print(f"📁 OUTPUT DIRECTORY: {context.output_dir}")
    print(f"📝 LOG FILES: {context.run_dir}")
    print(f"{'='*80}")

    # Save performance profile
    if ENABLE_PERFORMANCE_PROFILING and context.profiler:
        log_message("Generating performance profile...")
        save_performance_profile()

    log_message("Batch processing completed.")

if __name__ == "__main__":
    main()