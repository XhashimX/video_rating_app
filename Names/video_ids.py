# START: FULL SCRIPT
# -*- coding: utf-8 -*-
import os
import re
import shutil

# ==============================================================================
# 1. Settings
# ==============================================================================
# الملف الذي سيتم تخزين الـ IDs الجديدة فيه (التي لم تكن موجودة في قاعدة البيانات)
OUTPUT_FILE = "temp_extracted_ids_from_videos.txt"

# مسار ملف قاعدة البيانات المرجعية
REFERENCE_DB_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\Names\video_ids_output.txt"

# ==============================================================================
# 2. Helper Functions
# ==============================================================================

def extract_id_from_filename(filename: str) -> str | None:
    """
    Extracts the first sequence of 10 or more consecutive digits from a filename.
    """
    match = re.search(r'\d{10,}', filename)
    if match:
        return match.group(0)
    return None

def load_known_ids(file_path):
    """
    Loads existing IDs from the reference file to ignore them during processing.
    Format expected: 7484711689317846279 : username
    """
    known_ids = set()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if ':' in line:
                        # Take the part before the colon and strip whitespace
                        vid_id = line.split(':')[0].strip()
                        if vid_id.isdigit():
                            known_ids.add(vid_id)
            print(f"ℹ️ Loaded {len(known_ids)} known IDs from database.")
        except Exception as e:
            print(f"⚠️ Warning: Could not read reference DB. Error: {e}")
    else:
        print(f"⚠️ Warning: Reference DB not found at: {file_path}")
        print("   All extracted IDs will be treated as new.")
    return known_ids

# ==============================================================================
# 3. Main Script
# ==============================================================================

def main():
    """The main function to run the script"""
    print("=" * 60)
    print("🚀 Starting: Extract New Video IDs & Organize Unknown Files")
    print("=" * 60)

    # --- Step 0: Load Known IDs ---
    known_ids_set = load_known_ids(REFERENCE_DB_PATH)

    # --- Step 1: Ask the user for the folder paths ---
    paths_input = input("Please enter the full paths to the video folders, separated by a comma (,):\n")
    folder_paths = [path.strip() for path in paths_input.split(',')]

    # --- Step 2: Initialize collections for the final report ---
    # These will collect data from ALL folders (only NEW or UNMATCHED items)
    all_new_found_ids = set()
    all_unmatched_filenames = []
    
    # --- Loop through each provided folder path and process it ---
    for base_path in folder_paths:
        print(f"\n--- Processing Folder: {base_path} ---")

        if not os.path.isdir(base_path):
            print(f"❌ Warning: The path '{base_path}' is not a valid directory. Skipping.")
            continue

        # List to track files that need to be moved for the CURRENT folder
        # This includes: Files with NO ID + Files with NEW ID (not in DB)
        files_to_move_in_current_folder = []
        
        files_scanned = 0
        new_ids_count = 0
        ignored_count = 0

        # Scan the current directory
        for root, dirs, files in os.walk(base_path):
            # Skip the 'no_ids' folder itself if it exists to avoid loop issues
            if 'no_ids' in root:
                continue

            for filename in files:
                # Basic check to process likely video files only (optional, but good practice)
                if not filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                    continue

                files_scanned += 1
                full_path = os.path.join(root, filename)
                video_id = extract_id_from_filename(filename)
                
                is_known = False

                if video_id:
                    if video_id in known_ids_set:
                        # CASE A: ID exists in DB -> IGNORE IT
                        is_known = True
                        ignored_count += 1
                    else:
                        # CASE B: ID is valid but NEW -> Record it and mark for move
                        if video_id not in all_new_found_ids:
                            new_ids_count += 1
                        all_new_found_ids.add(video_id)
                        files_to_move_in_current_folder.append(full_path)
                else:
                    # CASE C: No ID found -> Record filename and mark for move
                    all_unmatched_filenames.append(filename)
                    files_to_move_in_current_folder.append(full_path)

        print(f"✔️ Scan complete for this folder.")
        print(f"   - Scanned: {files_scanned} files.")
        print(f"   - Ignored (Already in DB): {ignored_count} files.")
        print(f"   - New Unique IDs Found: {new_ids_count}")
        print(f"   - Files to be moved (New IDs + No IDs): {len(files_to_move_in_current_folder)}")
            
        # --- Ask the user if they want to move UNKNOWN files for THIS FOLDER ---
        if files_to_move_in_current_folder:
            print("-" * 25)
            print(f"Found {len(files_to_move_in_current_folder)} files that are not in the database (New IDs or No IDs).")
            answer = input(f"Move these files to '{os.path.join(base_path, 'no_ids')}'? (y/n): ").lower().strip()
            
            if answer in ['y', 'yes']:
                no_ids_dir = os.path.join(base_path, 'no_ids')
                print(f"Creating directory: {no_ids_dir}")
                os.makedirs(no_ids_dir, exist_ok=True)
                
                moved_count = 0
                print("Moving files...")
                for source_path in files_to_move_in_current_folder:
                    try:
                        # Check if file still exists (in case of duplicates in walk)
                        if os.path.exists(source_path):
                            file_name = os.path.basename(source_path)
                            dst_path = os.path.join(no_ids_dir, file_name)
                            
                            # Handle name collision in destination
                            if os.path.exists(dst_path):
                                print(f"  - Skipped (File exists in destination): {file_name}")
                            else:
                                shutil.move(source_path, no_ids_dir)
                                moved_count += 1
                    except Exception as e:
                        print(f"  - Error moving {os.path.basename(source_path)}: {e}")
                
                print(f"\n✔️ Move complete. {moved_count} files were moved.")
            else:
                print("\nSkipping move operation for this folder.")
        else:
            print("No unknown files to move.")

    # --- Step 3: Write the consolidated results to the single output file ---
    print("\n" + "=" * 60)
    print("📊 Final Summary (New Data Only):")
    print(f"   - Total NEW unique IDs found: {len(all_new_found_ids)}")
    print(f"   - Total files with no ID: {len(all_unmatched_filenames)}")
    print("=" * 60)

    if not all_new_found_ids and not all_unmatched_filenames:
        print("\n✅ No new data found. Everything matches the database or folders were empty.")
    else:
        print(f"\n💾 Writing new findings to: {OUTPUT_FILE}")
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                # First write the NEW IDs
                if all_new_found_ids:
                    for video_id in sorted(list(all_new_found_ids)):
                        f.write(video_id + "\n")
                
                # Then write the unmatched filenames
                if all_unmatched_filenames:
                    f.write("\nunmatched\n")
                    for filename in sorted(all_unmatched_filenames):
                        f.write(filename + "\n")

            print(f"✔️ Successfully saved temp file.")
        except Exception as e:
            print(f"❌ An error occurred while writing the file: {e}")
            
    print("\n" + "=" * 60)
    print("🎉 Process finished successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
# END: FULL SCRIPT