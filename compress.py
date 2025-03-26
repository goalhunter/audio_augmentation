import os
import subprocess
from pathlib import Path


def convert_audio(input_path, output_format="flac", output_path=None, compression_level=5, 
                 sample_rate=None, channels=None, bit_depth=None, extra_args=None, file_pattern="*.*"):
    """
    Convert audio file(s) to specified format using FFmpeg.
    
    This function can handle both single files and directories of files.
    
    Args:
        input_path (str): Path to input audio file or directory
        output_format (str): Desired output format (e.g., "flac", "mp3", "m4a")
        output_path (str, optional): Path to output file or directory. If None, 
                                    uses input path with appropriate extension.
        compression_level (int, optional): Compression level. For FLAC: 0-12, for MP3: 0-9.
        sample_rate (int, optional): Output sample rate in Hz. Default is None (keep original).
        channels (int, optional): Number of audio channels. Default is None (keep original).
        bit_depth (int, optional): Bit depth (16, 24, or 32). Default is None (keep original).
        extra_args (list, optional): List of additional FFmpeg arguments.
        file_pattern (str, optional): File pattern for batch processing (e.g., "*.wav").
                                     Only used when input_path is a directory.
    
    Returns:
        Union[str, list, None]: Path to output file, list of output files for batch processing,
                               or None if conversion failed.
    """
    # Check if input_path is a directory
    if os.path.isdir(input_path):
        return _batch_convert(
            input_path, output_format, output_path, compression_level, sample_rate,
            channels, bit_depth, extra_args, file_pattern
        )
    else:
        return _single_convert(
            input_path, output_format, output_path, compression_level, sample_rate,
            channels, bit_depth, extra_args
        )


def _get_format_settings(output_format, compression_level):
    """Get the appropriate codec and format-specific settings based on output format."""
    format_settings = {
        'codec': [],
        'format_args': []
    }
    
    output_format = output_format.lower()
    
    if output_format == 'flac':
        format_settings['codec'] = ['-c:a', 'flac']
        if compression_level is not None:
            format_settings['format_args'] = ['-compression_level', str(compression_level)]
    
    elif output_format == 'mp3':
        format_settings['codec'] = ['-c:a', 'libmp3lame']
        if compression_level is not None:
            # Map 0-9 compression level to quality (0 = highest quality, 9 = lowest)
            quality = max(0, min(9, compression_level))
            format_settings['format_args'] = ['-q:a', str(quality)]
    
    elif output_format == 'm4a':
        format_settings['codec'] = ['-c:a', 'aac']
        if compression_level is not None:
            # For AAC, higher is better quality (opposite of MP3)
            # Map compression_level 0-9 to bitrate
            bitrates = {
                0: '384k', 1: '320k', 2: '256k', 3: '224k', 4: '192k',
                5: '160k', 6: '128k', 7: '112k', 8: '96k', 9: '64k'
            }
            bitrate = bitrates.get(compression_level, '128k')
            format_settings['format_args'] = ['-b:a', bitrate]
    
    elif output_format == 'wav':
        format_settings['codec'] = ['-c:a', 'pcm_s16le']  # Default to 16-bit PCM
    
    elif output_format == 'ogg':
        format_settings['codec'] = ['-c:a', 'libvorbis']
        if compression_level is not None:
            # Vorbis quality scale is from -1 to 10
            # Map our 0-9 scale to 0-9
            quality = max(0, min(9, compression_level))
            format_settings['format_args'] = ['-q:a', str(quality)]
    
    else:
        # For other formats, use default codec and let FFmpeg decide
        format_settings['codec'] = ['-c:a', 'copy']
    
    return format_settings


def _single_convert(input_file, output_format="flac", output_file=None, compression_level=5, 
                   sample_rate=None, channels=None, bit_depth=None, extra_args=None):
    """Helper function to convert a single file to specified format."""
    if not os.path.exists(input_file):
        print(f"Input file not found: {input_file}")
        return None
    
    # Get appropriate file extension
    format_extensions = {
        'flac': '.flac',
        'mp3': '.mp3',
        'm4a': '.m4a',
        'wav': '.wav',
        'ogg': '.ogg',
        'aac': '.aac',
        'wma': '.wma',
        'alac': '.m4a',
    }
    
    output_extension = format_extensions.get(output_format.lower(), f'.{output_format}')
    
    if output_file is None:
        output_file = os.path.splitext(input_file)[0] + output_extension
    
    # Build the FFmpeg command
    cmd = ['ffmpeg', '-i', input_file]
    
    # Get format-specific settings
    format_settings = _get_format_settings(output_format, compression_level)
    cmd.extend(format_settings['codec'])
    cmd.extend(format_settings['format_args'])
    
    # Add sample rate if specified
    if sample_rate:
        cmd.extend(['-ar', str(sample_rate)])
    
    # Add channels if specified
    if channels:
        cmd.extend(['-ac', str(channels)])
    
    # Add bit depth if specified (mainly applies to FLAC and WAV)
    if bit_depth and output_format.lower() in ['flac', 'wav']:
        if output_format.lower() == 'flac':
            if bit_depth == 16:
                cmd.extend(['-sample_fmt', 's16'])
            elif bit_depth == 24:
                cmd.extend(['-sample_fmt', 's32'])
            elif bit_depth == 32:
                cmd.extend(['-sample_fmt', 's32'])
        elif output_format.lower() == 'wav':
            if bit_depth == 16:
                cmd.extend(['-c:a', 'pcm_s16le'])
            elif bit_depth == 24:
                cmd.extend(['-c:a', 'pcm_s24le'])
            elif bit_depth == 32:
                cmd.extend(['-c:a', 'pcm_s32le'])
    
    # Add any extra arguments
    if extra_args:
        cmd.extend(extra_args)
    
    # Add output file
    cmd.append(output_file)
    
    # Execute the FFmpeg command
    try:
        result = subprocess.run(cmd, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        print(f"Successfully converted {input_file} to {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error converting file: {e.stderr.decode()}")
        return None


def _batch_convert(input_dir, output_format="flac", output_dir=None, compression_level=5, 
                  sample_rate=None, channels=None, bit_depth=None, extra_args=None, 
                  file_pattern="*.*"):
    """Helper function to convert a directory of files to specified format."""
    
    # Create output directory if specified and doesn't exist
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
    
    # Get all matching files in the directory
    audio_files = list(Path(input_dir).glob(file_pattern))
    
    if not audio_files:
        print(f"No files matching pattern '{file_pattern}' found in {input_dir}")
        return []
    
    # Get appropriate file extension
    format_extensions = {
        'flac': '.flac',
        'mp3': '.mp3',
        'm4a': '.m4a',
        'wav': '.wav',
        'ogg': '.ogg',
        'aac': '.aac',
        'wma': '.wma',
        'alac': '.m4a',
    }
    
    output_extension = format_extensions.get(output_format.lower(), f'.{output_format}')
    
    successful_conversions = []
    for audio_file in audio_files:
        audio_path = str(audio_file)
        
        # Skip files that are already in the target format
        if audio_path.lower().endswith(output_extension):
            continue
        
        if output_dir is not None:
            # Create output file path in the output directory
            filename = os.path.basename(audio_path)
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(output_dir, base_name + output_extension)
        else:
            # Create output file in the same directory
            output_path = os.path.splitext(audio_path)[0] + output_extension
        
        # Convert the file
        result = _single_convert(
            audio_path, output_format, output_path, compression_level,
            sample_rate, channels, bit_depth, extra_args
        )
        
        if result:
            successful_conversions.append(result)
    
    print(f"Converted {len(successful_conversions)} files to {output_format} format")
    return successful_conversions


# # Example usage:
# if __name__ == "__main__":
#     # Example 1: Convert a single file to FLAC
#     # convert_audio("path/to/audio.mp3", output_format="flac")
    
#     # Example 2: Convert a single file to MP3
#     # convert_audio("path/to/audio.wav", output_format="mp3", compression_level=2)
    
#     # Example 3: Batch convert all WAV files in a directory to M4A
#     # convert_audio("path/to/directory", output_format="m4a",
#     #              output_path="path/to/output_directory",
#     #              file_pattern="*.wav")
    
#     # Interactive mode
#     print("Audio Format Converter")
#     print("Enter input path (file or directory):")
#     input_path = input("> ")
    
#     if os.path.exists(input_path):
#         print("Enter output format (flac, mp3, m4a, wav, ogg, etc.):")
#         output_format = input("> ").lower() or "flac"
        
#         if os.path.isdir(input_path):
#             print("Enter file pattern (e.g., *.wav, *.mp3, press Enter for all files):")
#             pattern = input("> ") or "*.*"
#             convert_audio(input_path, output_format=output_format, file_pattern=pattern)
#         else:
#             convert_audio(input_path, output_format=output_format)
#     else:
#         print(f"Path not found: {input_path}")