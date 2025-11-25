# START: FULL SCRIPT
# -*- coding: utf-8 -*-
import os
import re
import shutil

# ==============================================================================
# 1. Settings
# ==============================================================================
# The name of the output file that will contain the extracted IDs
OUTPUT_FILE = "temp_extracted_ids_from_videos.txt"

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

# ==============================================================================
# 3. Main Script
# ==============================================================================

def main():
    """The main function to run the script"""
    print("=" * 60)
    print("🚀 Starting: Extract Video IDs from Filenames (Multi-Folder Mode)")
    print("=" * 60)

    # --- Step 1: Ask the user for the folder paths ---
    # START: MODIFIED SECTION
    paths_input = input("Please enter the full paths to the video folders, separated by a comma (,):\n")
    # Split the input string by commas and strip any whitespace from each path
    folder_paths = [path.strip() for path in paths_input.split(',')]
    # END: MODIFIED SECTION

    # --- Step 2: Initialize collections for the final report ---
    # These will collect data from ALL folders
    all_found_ids = set()
    all_unmatched_filenames = []
    
    # START: MODIFIED SECTION
    # --- Loop through each provided folder path and process it ---
    for base_path in folder_paths:
        print(f"\n--- Processing Folder: {base_path} ---")

        # Validate that the current path is a valid directory
        if not os.path.isdir(base_path):
            print(f"❌ Warning: The path '{base_path}' is not a valid directory. Skipping.")
            continue

        # These lists are specific to the CURRENT folder being processed
        current_folder_unmatched_filepaths = []
        files_scanned_in_folder = 0
        ids_found_in_folder = 0

        # Scan the current directory
        for root, dirs, files in os.walk(base_path):
            for filename in files:
                files_scanned_in_folder += 1
                video_id = extract_id_from_filename(filename)
                
                if video_id:
                    if video_id not in all_found_ids:
                        ids_found_in_folder += 1
                    all_found_ids.add(video_id)
                else:
                    # If no ID was found, track it for this specific folder
                    all_unmatched_filenames.append(filename) # Add to global list for the text file
                    full_path = os.path.join(root, filename)
                    current_folder_unmatched_filepaths.append(full_path) # Add to local list for the move operation

        print(f"✔️ Scan complete for this folder.")
        print(f"   - Scanned {files_scanned_in_folder} files.")
        print(f"   - Found {ids_found_in_folder} new unique IDs.")
        if current_folder_unmatched_filepaths:
            print(f"   - Found {len(current_folder_unmatched_filepaths)} files with no valid ID.")
            
        # --- Ask the user if they want to move unmatched files for THIS FOLDER ---
        if current_folder_unmatched_filepaths:
            print("-" * 25)
            answer = input(f"Move the {len(current_folder_unmatched_filepaths)} unmatched files in '{os.path.basename(base_path)}' to a 'no_ids' subfolder? (y/n): ").lower().strip()
            
            if answer in ['y', 'yes']:
                # The destination directory is relative to the CURRENT base_path
                no_ids_dir = os.path.join(base_path, 'no_ids')
                
                print(f"Creating directory: {no_ids_dir}")
                os.makedirs(no_ids_dir, exist_ok=True)
                
                moved_count = 0
                print("Moving files...")
                for source_path in current_folder_unmatched_filepaths:
                    try:
                        shutil.move(source_path, no_ids_dir)
                        # print(f"  - Moved: {os.path.basename(source_path)}") # Optional: uncomment for more detail
                        moved_count += 1
                    except Exception as e:
                        print(f"  - Error moving {os.path.basename(source_path)}: {e}")
                
                print(f"\n✔️ Move complete. {moved_count} files were moved.")
            else:
                print("\nSkipping move operation for this folder.")
    # END: MODIFIED SECTION

    # --- Step 3: Write the consolidated results to the single output file ---
    print("\n" + "=" * 60)
    print("📊 Final Summary Across All Folders:")
    print(f"   - Total unique IDs found: {len(all_found_ids)}")
    print(f"   - Total files with no ID: {len(all_unmatched_filenames)}")
    print("=" * 60)

    if not all_found_ids and not all_unmatched_filenames:
        print("\n✅ No files were found to process in any of the provided directories.")
    else:
        print(f"\n💾 Writing all results to a single file: {OUTPUT_FILE}")
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                if all_found_ids:
                    for video_id in sorted(list(all_found_ids)):
                        f.write(video_id + "\n")
                
                if all_unmatched_filenames:
                    f.write("\nunmatched\n")
                    for filename in sorted(all_unmatched_filenames):
                        f.write(filename + "\n")

            print(f"✔️ Successfully saved {len(all_found_ids)} IDs and {len(all_unmatched_filenames)} unmatched filenames.")
        except Exception as e:
            print(f"❌ An error occurred while writing the file: {e}")
            
    print("\n" + "=" * 60)
    print("🎉 Process finished successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

# END: FULL SCRIPT