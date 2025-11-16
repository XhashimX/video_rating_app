import os
import subprocess
import shutil
import re
import questionary
from questionary import Style

# --- SCRIPT CONFIGURATION ---
# Custom style for the prompts to make them stand out.
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),      # Question mark
    ('question', 'bold'),              # Main question text
    ('answer', 'fg:#f44336 bold'),      # Answer text
    ('pointer', 'fg:#673ab7 bold'),      # Pointer in lists
    ('highlighted', 'fg:#673ab7 bold'),  # Highlighted option in lists
    ('selected', 'fg:#cc5454'),          # Selected option
    ('separator', 'fg:#cc5454'),
    ('instruction', 'fg:#aaaaaa'),     # Secondary instructions
    ('text', ''),
    ('disabled', 'fg:#858585 italic')
])

# --- HELPER FUNCTIONS ---

def check_ffmpeg():
    """Checks if ffmpeg is installed and in the system's PATH."""
    if not shutil.which("ffmpeg"):
        print("\n[ERROR] FFmpeg not found.")
        print("Please install FFmpeg and ensure it's in your system's PATH.")
        print("Download from: https://ffmpeg.org/download.html")
        exit(1)
    if not shutil.which("ffprobe"):
        print("\n[ERROR] ffprobe not found (part of FFmpeg).")
        print("Please ensure your FFmpeg installation is complete.")
        exit(1)

def parse_time_to_seconds(time_str):
    """
    Converts a time string (HH:MM:SS, MM:SS, or SS) to total seconds.
    Returns None if the format is invalid.
    """
    parts = str(time_str).split(':')
    seconds = 0
    try:
        if len(parts) == 1:
            seconds = float(parts[0])
        elif len(parts) == 2:
            seconds = int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        else:
            return None
        return seconds
    except ValueError:
        return None

def get_video_duration(video_path):
    """Gets the total duration of the video in seconds using ffprobe."""
    command = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"[ERROR] Could not get duration for '{video_path}'.")
        return None

def generate_output_filename(input_path, suffix):
    """Generates a non-conflicting output filename."""
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_{suffix}{ext}"
    counter = 1
    while os.path.exists(output_path):
        output_path = f"{base}_{suffix}_{counter}{ext}"
        counter += 1
    return output_path

def validate_time_format(text):
    """Validator for questionary to check if a time string is valid."""
    if not re.match(r'^(\d{1,2}:)?(\d{1,2}:)?\d+(\.\d+)?$', text.strip()):
        return "Invalid format. Use HH:MM:SS, MM:SS, or SS."
    return True

def validate_time_range(text):
    """Validator for questionary to check if a time range string is valid."""
    parts = [p.strip() for p in text.split('-')]
    if len(parts) != 2:
        return "Invalid format. Please use 'START - END' (e.g., '1:10 - 1:45')."
    
    start_str, end_str = parts
    start_sec = parse_time_to_seconds(start_str)
    end_sec = parse_time_to_seconds(end_str)

    if start_sec is None:
        return f"Invalid start time format: '{start_str}'"
    if end_sec is None:
        return f"Invalid end time format: '{end_str}'"
    if start_sec >= end_sec:
        return "End time must be after start time."
        
    return True

# --- MAIN HANDLER FUNCTIONS ---

def handle_single_cut(input_video):
    """Cuts a single segment from the video."""
    print("\n--- Cut and Keep a Single Segment ---")
    print("Example: To keep the video from 1 minute 10 seconds to 1 minute 45 seconds, enter: 1:10 - 1:45")
    
    range_str = questionary.text(
        "Enter the time range to keep (format: START - END):",
        validate=validate_time_range,
        style=custom_style
    ).ask()

    if not range_str: return

    start_str, end_str = [p.strip() for p in range_str.split('-')]
    output_video = generate_output_filename(input_video, "trimmed")

    command = [
        'ffmpeg', '-i', input_video,
        '-ss', start_str,
        '-to', end_str,
        '-c', 'copy', # Fast, lossless cut if possible
        '-y', # Overwrite output without asking
        output_video
    ]
    
    return command, output_video

def handle_merge_cuts(input_video):
    """Cuts multiple segments and merges them together."""
    print("\n--- Cut and Merge Multiple Segments ---")
    print("You will enter multiple time ranges. The final video will be a combination of these segments in order.")

    segments = []
    while True:
        range_str = questionary.text(
            f"Enter segment #{len(segments) + 1} to keep (format: START - END):",
            validate=validate_time_range,
            style=custom_style
        ).ask()
        
        if not range_str: break

        start_str, end_str = [p.strip() for p in range_str.split('-')]
        segments.append({'start': start_str, 'end': end_str})

        add_another = questionary.confirm("Add another segment?", default=True, style=custom_style).ask()
        if not add_another:
            break

    if not segments:
        print("No segments provided. Aborting.")
        return None, None

    # Constructing a complex filter command for ffmpeg
    filter_complex = []
    stream_mappings = []
    for i, seg in enumerate(segments):
        start_sec = parse_time_to_seconds(seg['start'])
        end_sec = parse_time_to_seconds(seg['end'])
        # Create a video and audio stream for each segment
        filter_complex.append(f"[0:v]trim=start={start_sec}:end={end_sec},setpts=PTS-STARTPTS[v{i}]")
        filter_complex.append(f"[0:a]atrim=start={start_sec}:end={end_sec},asetpts=PTS-STARTPTS[a{i}]")
        stream_mappings.append(f"[v{i}][a{i}]")

    concat_filter = f"{''.join(stream_mappings)}concat=n={len(segments)}:v=1:a=1[v][a]"
    filter_complex.append(concat_filter)

    output_video = generate_output_filename(input_video, "merged")
    
    command = [
        'ffmpeg', '-i', input_video,
        '-filter_complex', ";".join(filter_complex),
        '-map', '[v]',
        '-map', '[a]',
        '-y',
        output_video
    ]
    
    return command, output_video

def handle_exclude_cut(input_video):
    """Keeps the entire video except for one specified segment."""
    print("\n--- Exclude a Single Segment ---")
    print("The final video will have the specified time range removed.")
    
    duration = get_video_duration(input_video)
    if duration is None:
        return None, None

    print(f"Video duration: {duration:.2f} seconds.")

    range_str = questionary.text(
        "Enter the time range to EXCLUDE (format: START - END):",
        validate=validate_time_range,
        style=custom_style
    ).ask()

    if not range_str: return None, None
    
    start_str, end_str = [p.strip() for p in range_str.split('-')]
    exclude_start_sec = parse_time_to_seconds(start_str)
    exclude_end_sec = parse_time_to_seconds(end_str)

    # This problem now becomes a merge of two segments:
    # 1. From the beginning to the start of the exclusion.
    # 2. From the end of the exclusion to the end of the video.
    segments_to_keep = []
    if exclude_start_sec > 0:
        segments_to_keep.append({'start': 0, 'end': exclude_start_sec})
    if exclude_end_sec < duration:
        segments_to_keep.append({'start': exclude_end_sec, 'end': duration})

    if not segments_to_keep:
        print("The exclusion range covers the entire video. Nothing to generate.")
        return None, None
        
    # Re-use the merge logic
    filter_complex = []
    stream_mappings = []
    for i, seg in enumerate(segments_to_keep):
        filter_complex.append(f"[0:v]trim=start={seg['start']}:end={seg['end']},setpts=PTS-STARTPTS[v{i}]")
        filter_complex.append(f"[0:a]atrim=start={seg['start']}:end={seg['end']},asetpts=PTS-STARTPTS[a{i}]")
        stream_mappings.append(f"[v{i}][a{i}]")

    concat_filter = f"{''.join(stream_mappings)}concat=n={len(segments_to_keep)}:v=1:a=1[v][a]"
    filter_complex.append(concat_filter)

    output_video = generate_output_filename(input_video, "cutout")

    command = [
        'ffmpeg', '-i', input_video,
        '-filter_complex', ";".join(filter_complex),
        '-map', '[v]',
        '-map', '[a]',
        '-y',
        output_video
    ]

    return command, output_video

# --- MAIN EXECUTION ---

def main():
    """Main function to run the interactive script."""
    check_ffmpeg()
    
    print("--- FFmpeg Interactive Video Cutter ---")
    
    # Get the raw path from the user
    raw_path = questionary.text(
        "Please enter the path to your video file:",
        # The validation now checks the cleaned path
        validate=lambda path: True if os.path.exists(path.strip().strip('"')) else "File not found. Please check the path.",
        style=custom_style
    ).ask()

    if not raw_path:
        print("No input file provided. Exiting.")
        return
        
    # Clean the path by stripping whitespace and surrounding quotes
    input_video = raw_path.strip().strip('"')

    action = questionary.select(
        "What operation would you like to perform?",
        choices=[
            'Cut and Keep a Single Segment',
            'Cut and Merge Multiple Segments',
            'Exclude a Single Segment (Cut out the middle)',
            'Cancel'
        ],
        style=custom_style
    ).ask()

    command = None
    output_video = None

    if action == 'Cut and Keep a Single Segment':
        command, output_video = handle_single_cut(input_video)
    elif action == 'Cut and Merge Multiple Segments':
        command, output_video = handle_merge_cuts(input_video)
    elif action == 'Exclude a Single Segment (Cut out the middle)':
        command, output_video = handle_exclude_cut(input_video)
    else:
        print("Operation cancelled.")
        return

    if command and output_video:
        print("\n" + "="*50)
        print("The following FFmpeg command will be executed:")
        # Print a user-friendly version of the command
        print(" ".join(map(str, command)))
        print("="*50 + "\n")

        confirm = questionary.confirm("Proceed with execution?", default=True, style=custom_style).ask()
        if confirm:
            print(f"Processing... Output will be saved as '{output_video}'")
            try:
                # We use capture_output=False so the ffmpeg progress is shown live
                subprocess.run(command, check=True)
                print(f"\n✅ Success! Video saved to '{output_video}'")
            except subprocess.CalledProcessError as e:
                print(f"\n❌ An error occurred during FFmpeg execution.")
                print(f"Error: {e}")
            except Exception as e:
                print(f"\n❌ An unexpected error occurred: {e}")
        else:
            print("Execution cancelled by user.")

if __name__ == "__main__":
    main()