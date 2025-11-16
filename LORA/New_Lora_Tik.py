import json
import os
import cv2
import face_recognition
import numpy as np

# --- CONFIGURATION ---
# Please ensure these paths are correct.
# Using raw strings (r"...") is safer for Windows paths.
JSON_FILE_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"
VIDEOS_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik"
BASE_OUTPUT_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\LORA\tik"
# ---------------------

def get_sharpness(image):
    """Calculates the sharpness of an image using Laplacian variance."""
    if image is None: return 0
    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Compute the Laplacian of the grayscale image and then return the variance
    return cv2.Laplacian(gray, cv2.CV_64F).var()

# --- MODE 1: Thorough (Slow but Accurate) ---
def take_thorough_screenshots(video_path, output_dir, base_filename_num, sharpness_threshold, frame_skip, resize_factor):
    """
    Thoroughly scans every relevant frame of a video to find the best shots.
    Includes detailed debug reporting.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  - ERROR: Could not open video file: {video_path}. Skipping.")
        return 0

    saved_count_for_this_video = 0
    frame_index = 0
    skip_counter = 0
    
    # Debug counters for this specific video
    frames_with_faces = 0
    max_sharpness_found = 0.0

    while True:
        ret, frame = cap.read()
        if not ret: break

        frame_index += 1
        
        if skip_counter > 0:
            skip_counter -= 1
            continue
        
        small_frame = cv2.resize(frame, (0, 0), fx=resize_factor, fy=resize_factor)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")

        if face_locations:
            frames_with_faces += 1
            sharpness = get_sharpness(frame)
            
            if sharpness > max_sharpness_found:
                max_sharpness_found = sharpness
            
            if sharpness > sharpness_threshold:
                current_screenshot_num = base_filename_num + saved_count_for_this_video
                output_path = os.path.join(output_dir, f"{current_screenshot_num}.jpg")
                cv2.imwrite(output_path, frame)
                
                print(f"  - ✅ Saved screenshot {current_screenshot_num}.jpg (Sharpness: {sharpness:.2f})")
                saved_count_for_this_video += 1
                skip_counter = frame_skip
    
    cap.release()
    
    # --- DETAILED DEBUG REPORT ---
    print("    " + "-" * 10 + " THOROUGH MODE DEBUG REPORT " + "-" * 10)
    print(f"    - Total frames checked in video: {frame_index}")
    print(f"    - Frames where a face was detected: {frames_with_faces}")
    print(f"    - Highest sharpness score found (with face): {max_sharpness_found:.2f}")
    print(f"    - Your sharpness threshold was set to: {sharpness_threshold}")
    print("    " + "-" * 42)

    if saved_count_for_this_video == 0:
        print(f"  - ℹ️ INFO: No suitable frames found in '{os.path.basename(video_path)}' with current settings.")

    return saved_count_for_this_video

# --- MODE 2: Fast Sampler (Quick but Less Comprehensive) ---
def take_fast_sample_screenshots(video_path, output_dir, base_filename_num, num_samples, num_to_keep):
    """
    Quickly samples a video, evaluates the samples, and saves the top N best frames.
    Includes detailed debug reporting.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  - ERROR: Could not open video file: {video_path}. Skipping.")
        return 0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < num_samples:
        print(f"  - ℹ️ INFO: Video is too short. Adjusting to {total_frames} samples.")
        num_samples = total_frames
        
    print(f"  -  sampling {num_samples} frames from the video...")
    
    candidate_frames = [] 

    # Step 1: Sampling and Evaluation
    for i in range(num_samples):
        frame_index = int(total_frames * (i / num_samples))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        
        ret, frame = cap.read()
        if not ret: continue

        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
        
        if face_locations:
            sharpness = get_sharpness(frame)
            candidate_frames.append({'frame': frame, 'sharpness': sharpness, 'original_index': frame_index})

    print(f"  - Found {len(candidate_frames)} candidate frames with faces out of {num_samples} samples.")
    if not candidate_frames:
        cap.release()
        return 0
        
    # Step 2: Selection
    candidate_frames.sort(key=lambda x: x['sharpness'], reverse=True)

    # Step 3: Saving
    saved_count = 0
    for i in range(min(num_to_keep, len(candidate_frames))):
        best_candidate = candidate_frames[i]
        
        current_screenshot_num = base_filename_num + i
        output_path = os.path.join(output_dir, f"{current_screenshot_num}.jpg")
        cv2.imwrite(output_path, best_candidate['frame'])
        
        print(f"  - ✅ Saved best sample #{i+1} -> {current_screenshot_num}.jpg (Sharpness: {best_candidate['sharpness']:.2f})")
        saved_count += 1
        
    # --- DETAILED DEBUG REPORT ---
    print("    " + "-" * 10 + " FAST SAMPLER DEBUG REPORT " + "-" * 10)
    print(f"    - Total samples taken: {num_samples}")
    print(f"    - Samples containing a face: {len(candidate_frames)}")
    if candidate_frames:
        sharpness_scores = [c['sharpness'] for c in candidate_frames]
        print(f"    - Sharpness scores found (Best to Worst): {[f'{s:.2f}' for s in sharpness_scores]}")
    print("    " + "-" * 45)

    cap.release()
    return saved_count

# --- MAIN SCRIPT ---
def main():
    """Main function to guide the user and run the script."""
    # 1. Load JSON
    print("Step 1: Loading JSON data...")
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            video_data = json.load(f)
        print("JSON data loaded successfully.")
    except Exception as e:
        print(f"FATAL ERROR: Could not load or parse JSON file. Details: {e}")
        return

    # 2. Display Names
    print("\nStep 2: Finding available names...")
    all_names = sorted(list(set(details['name'] for details in video_data.values() if details.get('name'))))
    if not all_names:
        print("FATAL ERROR: No names found in the JSON file.")
        return
    print("Available names found:")
    for name in all_names: print(f"- {name}")
    print("-" * 20)

    # 3. Get User Input
    chosen_name = input("Step 3: Enter the name you want to process: ")
    if chosen_name not in all_names:
        print(f"FATAL ERROR: Name '{chosen_name}' not found.")
        return
    
    # [NEW] Choose Mode
    print("\nStep 4: Choose extraction mode:")
    print("  1. Thorough Mode (Slow, checks all frames, highly accurate)")
    print("  2. Fast Sampler Mode (Fast, takes samples, good for quick previews)")
    mode_choice = input("Enter mode number (1 or 2): ")

    # Mode-specific settings
    if mode_choice == '1':
        print("\nConfiguring Thorough Mode...")
        try:
            sharpness_input = float(input("  - Enter sharpness threshold (e.g., 40.0 for lower quality, 100.0 for high): "))
            skip_input = int(input("  - Enter frames to skip after a good shot (e.g., 24 for 1 second): "))
            resize_input = float(input("  - Enter resize factor for speed (0.5=fast, 0.75=accurate): "))
            if not (0.1 <= resize_input <= 1.0): raise ValueError("Resize factor out of range.")
        except ValueError as e:
            print(f"FATAL ERROR: Invalid number. {e}")
            return
    elif mode_choice == '2':
        print("\nConfiguring Fast Sampler Mode...")
        try:
            samples_input = int(input("  - How many samples to take per video? (e.g., 20): "))
            keep_input = int(input("  - How many of the BEST samples to keep? (e.g., 2): "))
        except ValueError:
            print("FATAL ERROR: Invalid integer entered.")
            return
    else:
        print("FATAL ERROR: Invalid mode choice. Please enter 1 or 2.")
        return

    # 4. Filter and Sort
    print("\nStep 5: Filtering and sorting videos by rating...")
    user_videos = [details for details in video_data.values() if details.get('name') == chosen_name]
    user_videos.sort(key=lambda x: x.get('rating', 0), reverse=True)
    print(f"Found {len(user_videos)} videos for '{chosen_name}'.")

    # 5. Prepare Output Directory
    output_directory = os.path.join(BASE_OUTPUT_DIR, chosen_name)
    os.makedirs(output_directory, exist_ok=True)
    print(f"Output will be saved to: {output_directory}\n")

    # 6. Index Video Files
    print("Step 6: Indexing video files by size... please wait.")
    size_to_path_map = {}
    for filename in os.listdir(VIDEOS_DIR):
        full_path = os.path.join(VIDEOS_DIR, filename)
        if os.path.isfile(full_path):
            try:
                size_to_path_map[os.path.getsize(full_path)] = full_path
            except OSError as e: print(f"Could not access {full_path}: {e}")
    print("Indexing complete.\n")

    # 7. Process Videos
    print(f"--- STARTING BATCH PROCESSING for '{chosen_name}' ---")
    total_screenshots_saved = 0
    for i, video_info in enumerate(user_videos):
        print(f"\n[{i+1}/{len(user_videos)}] Processing video rated {video_info.get('rating', 0):.2f}...")
        file_size = video_info.get('file_size')
        if not file_size:
            print(f"  - ⚠️ WARNING: Video entry has no file_size. Skipping.")
            continue

        video_path = size_to_path_map.get(file_size)
        if video_path:
            print(f"  - Found video file: {os.path.basename(video_path)}")
            if mode_choice == '1':
                num_saved = take_thorough_screenshots(video_path, output_directory, total_screenshots_saved + 1, sharpness_input, skip_input, resize_input)
            else: # mode_choice == '2'
                num_saved = take_fast_sample_screenshots(video_path, output_directory, total_screenshots_saved + 1, samples_input, keep_input)
            total_screenshots_saved += num_saved
        else:
            print(f"  - ⚠️ WARNING: Could not find video with size {file_size} bytes. Skipping.")

    print(f"\n--- BATCH PROCESSING COMPLETE ---")
    print(f"Total screenshots saved for '{chosen_name}': {total_screenshots_saved}")

if __name__ == "__main__":
    main()