import subprocess
import os
import sys

def get_video_info(source_file):
    """
    Get video information from the source file to make informed decisions about rewrapping.
    Returns a dictionary with video properties.
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_name,pix_fmt,width,height,field_order,r_frame_rate',
            '-show_entries', 'format=format_name',
            '-of', 'default=noprint_wrappers=1',
            source_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        info = {}
        for line in result.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                info[key] = value
        
        return info
    except subprocess.CalledProcessError as e:
        print(f"Error getting video info: {e}", file=sys.stderr)
        print(f"ffprobe stderr: {e.stderr}", file=sys.stderr)
        return None

def needs_rewrapping(source_file, video_info):
    """
    Determine if the file needs rewrapping based on format and codec.
    Returns True if rewrapping is needed, False otherwise.
    """
    if not video_info:
        # If we can't get info, assume it needs rewrapping for safety
        print("Warning: Could not analyze video info, proceeding with rewrapping", file=sys.stderr)
        return True
    
    format_name = video_info.get('format_name', '').lower()
    codec_name = video_info.get('codec_name', '').lower()
    
    # File extension check
    file_ext = os.path.splitext(source_file)[1].lower()
    
    print(f"File analysis: format={format_name}, codec={codec_name}, extension={file_ext}")
    
    # Always rewrap these formats/extensions
    needs_rewrap_formats = [
        'avi',           # AVI containers
        'matroska',      # MKV files
        'mp4',           # MP4 files
        'mpeg',          # MPEG files
        'mpegts',        # Transport streams
        'mxf',           # MXF files
    ]
    
    needs_rewrap_extensions = [
        '.avi', '.mkv', '.mp4', '.m4v', '.mpg', '.mpeg', 
        '.ts', '.mts', '.m2ts', '.mxf', '.dv', '.hdv'
    ]
    
    # Check if format or extension indicates rewrapping is needed
    format_needs_rewrap = any(fmt in format_name for fmt in needs_rewrap_formats)
    extension_needs_rewrap = file_ext in needs_rewrap_extensions
    
    # Already in MOV/QuickTime format with ProRes? Check if we can skip
    if 'mov' in format_name or 'quicktime' in format_name:
        if 'prores' in codec_name:
            print("File is already ProRes in QuickTime container - checking if rewrap is still needed...")
            # Even ProRes files might need color space updates
            return True  # For now, always rewrap to ensure DCI-P3 color space
        else:
            print("File is QuickTime/MOV but not ProRes - rewrapping needed")
            return True
    
    if format_needs_rewrap or extension_needs_rewrap:
        print(f"Rewrapping needed: format_match={format_needs_rewrap}, extension_match={extension_needs_rewrap}")
        return True
    
    print("File appears to be in suitable format, but rewrapping for consistency")
    return True  # Default to rewrapping for pipeline consistency

def detect_interlacing(video_info):
    """
    Detect if the video is interlaced and determine field order.
    Returns tuple: (is_interlaced, top_field_first)
    """
    field_order = video_info.get('field_order', '').lower()
    height = int(video_info.get('height', 0))
    
    # Common interlaced indicators
    interlaced_indicators = ['tt', 'bb', 'tb', 'bt']
    is_interlaced = any(indicator in field_order for indicator in interlaced_indicators)
    
    # Height-based heuristics for common formats
    if not is_interlaced:
        # PAL DV/HDV: 576 or 1080 lines often interlaced
        # NTSC DV: 480 lines often interlaced
        if height in [480, 576, 1080]:
            print(f"Height {height} suggests likely interlaced content")
            is_interlaced = True
    
    # Determine field order
    top_field_first = True  # Default for PAL
    if 'bb' in field_order or 'bt' in field_order:
        top_field_first = False
    elif height == 480:  # NTSC is typically bottom field first
        top_field_first = False
    
    print(f"Interlacing detection: interlaced={is_interlaced}, top_field_first={top_field_first}")
    return is_interlaced, top_field_first

def rewrap_to_prores(source_file, output_directory):
    """
    Converts a video file to ProRes 422 HQ in a QuickTime container using ffmpeg.
    Preserves interlaced field structure - NO deinterlacing is performed.
    This maintains the original interlaced format while converting to ProRes.
    Now includes DCI-P3 color space support and enhanced format detection.
    """
    if not os.path.exists(source_file):
        print(f"Error: Source file not found at {source_file}", file=sys.stderr)
        return None

    # Get video information
    print(f"Analyzing source file: {source_file}")
    video_info = get_video_info(source_file)
    
    # Check if rewrapping is actually needed
    if not needs_rewrapping(source_file, video_info):
        print(f"File {source_file} does not require rewrapping, returning original path")
        return source_file

    base_name = os.path.basename(source_file)
    # Remove extension from base name and add .mov
    base_name_no_ext = os.path.splitext(base_name)[0]
    output_file = os.path.join(output_directory, f"{base_name_no_ext}_prores.mov")

    # Detect interlacing
    is_interlaced, top_field_first = detect_interlacing(video_info) if video_info else (True, True)

    # Build command with enhanced format handling
    command = [
        'ffmpeg',
        '-i', source_file,
        '-c:v', 'prores_ks',        # ProRes encoder
        '-profile:v', '3',          # ProRes 422 HQ profile
        '-pix_fmt', 'yuv422p10le',  # 10-bit 4:2:2 format
    ]
    
    # Add interlacing flags only if detected as interlaced
    if is_interlaced:
        command.extend([
            '-flags', '+ildct+ilme',    # Preserve interlaced encoding flags
            '-top', '1' if top_field_first else '0',  # Field order
        ])
        print(f"Applying interlaced encoding: top_field_first={top_field_first}")
    else:
        print("Progressive encoding (no interlacing flags)")
    
    # Add color space settings
    command.extend([
        '-color_primaries', '12',         # DCI-P3 primaries (numeric)
        '-color_trc', '11',               # DCI-P3 transfer function (numeric)
        '-colorspace', '12',              # DCI-P3 matrix (numeric)
        '-color_range', 'tv',             # Limited range
        '-c:a', 'pcm_s24le',             # High-quality uncompressed audio
        '-y',                            # Overwrite output file if it exists
        output_file
    ])

    print(f"Converting {source_file} to ProRes 422 HQ:")
    print(f"  Source format: {video_info.get('format_name', 'unknown') if video_info else 'unknown'}")
    print(f"  Source codec: {video_info.get('codec_name', 'unknown') if video_info else 'unknown'}")
    print(f"  Interlaced: {is_interlaced}")
    print(f"  Output: {output_file}")
    print("  Color space: DCI-P3")
    
    try:
        # Show the full command for debugging
        if video_info:
            print(f"FFmpeg command: {' '.join(command)}")
        
        # Using capture_output=True to hide ffmpeg's verbose output from the console
        # and only show it if there's an error.
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        
        # Verify output file was created and has reasonable size
        if os.path.exists(output_file):
            output_size = os.path.getsize(output_file)
            if output_size > 1000000:  # At least 1MB
                print(f"ProRes encoding completed successfully.")
                print(f"Output file size: {output_size / (1024*1024):.1f} MB")
                return output_file
            else:
                print(f"Error: Output file too small ({output_size} bytes)", file=sys.stderr)
                return None
        else:
            print("Error: Output file was not created", file=sys.stderr)
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"Error during ProRes encoding: {e}", file=sys.stderr)
        print(f"ffmpeg stderr:\n{e.stderr}", file=sys.stderr)
        
        # Provide helpful error messages for common issues
        if "Invalid pixel format" in e.stderr:
            print("Hint: Source file may have an unsupported pixel format", file=sys.stderr)
        elif "No such file or directory" in e.stderr:
            print("Hint: Check that ffmpeg is installed and in PATH", file=sys.stderr)
        elif "Permission denied" in e.stderr:
            print("Hint: Check write permissions for output directory", file=sys.stderr)
            
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return None

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python rewrap.py <source_file> <output_directory>")
        print("  Converts video files to ProRes 422 HQ with DCI-P3 color space")
        print("  Supports: .avi, .mkv, .mp4, .mpg, .ts, .mxf, .dv, .hdv, and more")
        sys.exit(1)
    
    source = sys.argv[1]
    output_dir = sys.argv[2]
    
    if not os.path.isdir(output_dir):
        print(f"Error: Output directory not found at {output_dir}", file=sys.stderr)
        sys.exit(1)

    rewrapped_path = rewrap_to_prores(source, output_dir)
    if rewrapped_path:
        print(f"Output file: {rewrapped_path}")
    else:
        print("Rewrapping failed", file=sys.stderr)
        sys.exit(1)