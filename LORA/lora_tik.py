import json
import os
import cv2 # OpenCV library for video processing

# --- CONFIGURATION ---
# Please ensure these paths are correct.
# Using raw strings (r"...") is safer for Windows paths.
JSON_FILE_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"
VIDEOS_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik"
BASE_OUTPUT_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\LORA\tik"
# ---------------------

def take_screenshots(video_path, output_dir, base_filename_num):
    """
    Opens a video file and takes two screenshots at specific times.
    - Screenshot 1 at 1.0 second.
    - Screenshot 2 at 7.0 seconds.
    The screenshots are named numerically based on base_filename_num.
    """
    if not os.path.exists(video_path):
        print(f"  - WARNING: Video file not found at {video_path}. Skipping.")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  - ERROR: Could not open video file: {video_path}. Skipping.")
        return

    # Take screenshot at 1 second (1000 milliseconds)
    cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
    success, frame1 = cap.read()
    if success:
        output_path1 = os.path.join(output_dir, f"{base_filename_num}.jpg")
        cv2.imwrite(output_path1, frame1)
        print(f"  - Saved screenshot {base_filename_num}.jpg")
    else:
        print(f"  - WARNING: Could not read frame at 1 second from {os.path.basename(video_path)}.")

    # Take screenshot at 7 seconds (7000 milliseconds)
    cap.set(cv2.CAP_PROP_POS_MSEC, 7000)
    success, frame2 = cap.read()
    if success:
        output_path2 = os.path.join(output_dir, f"{base_filename_num + 1}.jpg")
        cv2.imwrite(output_path2, frame2)
        print(f"  - Saved screenshot {base_filename_num + 1}.jpg")
    else:
        print(f"  - WARNING: Could not read frame at 7 seconds from {os.path.basename(video_path)}.")

    cap.release() # Important: release the video capture object

def main():
    """Main function to run the script."""
    # 1. Load JSON data
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            video_data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: JSON file not found at: {JSON_FILE_PATH}")
        return
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON. Please check the file format in: {JSON_FILE_PATH}")
        return

    # 2. Get all unique names and display them
    all_names = sorted(list(set(details['name'] for details in video_data.values() if details.get('name'))))
    if not all_names:
        print("No names found in the JSON file.")
        return

    print("Available names:")
    for name in all_names:
        print(f"- {name}")
    print("-" * 20)

    # 3. Get user input
    chosen_name = input("Enter the name you want to process: ")

    if chosen_name not in all_names:
        print(f"ERROR: Name '{chosen_name}' not found in the list.")
        return

    # 4. Filter videos for the chosen name and sort by rating (highest first)
    user_videos = []
    for video_filename, details in video_data.items():
        if details.get('name') == chosen_name:
            # We add the original filename in case we need it for debugging
            details['original_filename'] = video_filename
            user_videos.append(details)

    # Sort the list of videos by 'rating' in descending order
    user_videos.sort(key=lambda x: x['rating'], reverse=True)

    if not user_videos:
        print(f"No videos found for name '{chosen_name}'.") # Should not happen if name is in list, but good practice
        return

    print(f"\nFound {len(user_videos)} videos for '{chosen_name}'. Processing in order of rating...")

    # 5. Prepare the output directory
    output_directory = os.path.join(BASE_OUTPUT_DIR, chosen_name, "screenshots")
    os.makedirs(output_directory, exist_ok=True)
    print(f"Output will be saved to: {output_directory}\n")

    # 6. Create a map of file sizes to file paths for quick lookup
    # This is much faster than searching the directory for each video
    print("Indexing video files by size... please wait.")
    size_to_path_map = {}
    for filename in os.listdir(VIDEOS_DIR):
        full_path = os.path.join(VIDEOS_DIR, filename)
        if os.path.isfile(full_path):
            try:
                file_size = os.path.getsize(full_path)
                size_to_path_map[file_size] = full_path
            except OSError as e:
                print(f"Could not access {full_path}: {e}")
    print("Indexing complete.\n")

    # 7. Process each video
    screenshot_counter = 1
    for video_info in user_videos:
        file_size = video_info.get('file_size')
        if not file_size:
            print(f"WARNING: Video entry '{video_info['original_filename']}' has no file_size. Skipping.")
            continue

        # Find the video path using its unique file size
        video_path = size_to_path_map.get(file_size)

        if video_path:
            print(f"Processing video rated {video_info['rating']:.2f} (File: {os.path.basename(video_path)})...")
            take_screenshots(video_path, output_directory, screenshot_counter)
            # Each video gets two screenshots, so we increment the counter by 2
            screenshot_counter += 2
        else:
            print(f"WARNING: Could not find a video in '{VIDEOS_DIR}' with size {file_size} bytes. Skipping.")

    print("\nProcessing complete.")


if __name__ == "__main__":
    main()