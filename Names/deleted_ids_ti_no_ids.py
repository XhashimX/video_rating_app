# START: FULL SCRIPT
# -*- coding: utf-8 -*-
import os
import shutil

# ==============================================================================
# 1. Settings
# ==============================================================================
# The fixed path to the file containing deleted video IDs.
DELETED_IDS_FILE_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\Names\deleted_ids.txt"

# ==============================================================================
# 2. Helper Functions
# ==============================================================================

def load_deleted_ids(filepath: str) -> set:
    """
    Reads the deleted IDs file and returns a set of IDs for fast lookup.
    """
    if not os.path.exists(filepath):
        print(f"❌ Error: The deleted IDs file was not found at:\n{filepath}")
        return set() # Return an empty set
    
    deleted_ids_set = set()
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stripped_line = line.strip()
            if stripped_line: # Ensure the line is not empty
                deleted_ids_set.add(stripped_line)
                
    return deleted_ids_set

# ==============================================================================
# 3. Main Script
# ==============================================================================

def main():
    """The main function to run the script"""
    print("=" * 60)
    print("🚀 Starting: Find and Move Videos with Deleted IDs")
    print("=" * 60)

    # --- Step 1: Load the deleted IDs ---
    deleted_ids = load_deleted_ids(DELETED_IDS_FILE_PATH)
    
    if not deleted_ids:
        print("The deleted_ids.txt file is empty or was not found. Nothing to do.")
        return
        
    print(f"✔️ Loaded {len(deleted_ids)} IDs from the deleted list.")

    # --- Step 2: Ask the user for the folder to search ---
    search_path = input("\nPlease enter the full path to the root folder you want to scan: ")

    if not os.path.isdir(search_path):
        print(f"\n❌ Error: The path '{search_path}' is not a valid directory.")
        return

    # --- Step 3: Scan all directories and collect files to move ---
    print(f"\n📂 Scanning directory '{search_path}' and all subdirectories...")
    
    # We will use a dictionary to group files by their parent directory
    # Structure: {'parent_directory_path': [list_of_full_file_paths]}
    files_to_move_map = {}
    
    for root, dirs, files in os.walk(search_path):
        for filename in files:
            # Check if any of the deleted IDs exist in the filename
            for deleted_id in deleted_ids:
                if deleted_id in filename:
                    # If we find a match, we record it and stop checking this file
                    file_path = os.path.join(root, filename)
                    
                    # Add the file to our dictionary, grouped by its parent folder ('root')
                    if root not in files_to_move_map:
                        files_to_move_map[root] = []
                    files_to_move_map[root].append(file_path)
                    
                    break # Move to the next file once a match is found

    # --- Step 4: Report the findings to the user ---
    if not files_to_move_map:
        print("\n✔️ Scan complete. No videos with deleted IDs were found.")
        return
    
    print("\n📊 Scan Complete. The following files were found:")
    total_files_found = 0
    for dir_path, files_list in files_to_move_map.items():
        count = len(files_list)
        total_files_found += count
        print(f"   - Found {count} videos with deleted IDs in path: {dir_path}")

    # --- Step 5: Ask for confirmation to move the files ---
    print("-" * 60)
    answer = input(f"Do you want to move all {total_files_found} files to a 'no_ids' subfolder in their respective directories? (y/n): ").lower().strip()

    if answer in ['y', 'yes']:
        print("\n🚚 Moving files...")
        moved_count = 0
        
        # Iterate through the dictionary we built
        for dir_path, files_list in files_to_move_map.items():
            # The destination folder is relative to the directory where the files were found
            no_ids_dir = os.path.join(dir_path, 'no_ids')
            os.makedirs(no_ids_dir, exist_ok=True) # Create the folder if it doesn't exist
            
            # Move each file in the list for this directory
            for file_path in files_list:
                try:
                    shutil.move(file_path, no_ids_dir)
                    moved_count += 1
                except Exception as e:
                    print(f"  - Error moving {os.path.basename(file_path)}: {e}")

        print(f"\n✔️ Move complete. {moved_count} files were successfully moved.")
    else:
        print("\nSkipping move operation. No files were changed.")
        
    print("\n" + "=" * 60)
    print("🎉 Process finished successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()

# END: FULL SCRIPT