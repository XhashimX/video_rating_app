# START: ENTIRE FILE "clean_thumbnails.py"

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
from typing import Set, Tuple, List

# --- CONFIGURATION ---
# The log file containing the list of local videos.
LOG_FILE = "local_videos_found.txt"
# The directory where thumbnail images are stored.
THUMBNAILS_DIR = "thumbnails"
# ---------------------

def parse_log_file(log_path: str) -> Set[Tuple[str, str]]:
    """
    Reads the log file and returns a set of (username, video_id) tuples.
    This set allows for very fast lookups.
    """
    if not os.path.exists(log_path):
        print(f"Error: Log file not found at '{log_path}'.")
        print("Please run the 'update_local_status.py' script first to generate it.")
        sys.exit(1)

    local_videos = set()
    # Regex to robustly parse lines like: "User: username_123 | Video ID: 7123..."
    line_regex = re.compile(r"User:\s*(\S+)\s*\|\s*Video ID:\s*(\d+)")

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = line_regex.search(line)
            if match:
                username, video_id = match.groups()
                local_videos.add((username, video_id))
    
    return local_videos

def find_thumbnails_to_delete(thumbnails_path: str, local_videos: Set[Tuple[str, str]]) -> List[str]:
    """
    Scans the thumbnails directory and finds files that match the local video list.
    Returns a list of full file paths to be deleted.
    """
    if not os.path.isdir(thumbnails_path):
        print(f"Error: Thumbnails directory not found at '{thumbnails_path}'.")
        return []

    files_to_delete = []
    # Regex to parse filenames like "username_7123456789012345678.jpg"
    filename_regex = re.compile(r"^([^_]+)_(\d{18,20})\..+$")

    for filename in os.listdir(thumbnails_path):
        match = filename_regex.match(filename)
        if match:
            username, video_id = match.groups()
            if (username, video_id) in local_videos:
                full_path = os.path.join(thumbnails_path, filename)
                files_to_delete.append(full_path)
    
    return files_to_delete

def main():
    """
    Main function to orchestrate the cleaning process.
    """
    print("--- Thumbnail Cleaner for Local Videos ---")

    # Step 1: Parse the log file to get the list of local videos.
    print(f"\n[1] Reading local video list from '{LOG_FILE}'...")
    local_videos_set = parse_log_file(LOG_FILE)
    if not local_videos_set:
        print("No local videos found in the log file. Nothing to do.")
        sys.exit(0)
    print(f"Found {len(local_videos_set)} unique local video entries.")

    # Step 2: Find all matching thumbnails in the thumbnails directory.
    print(f"\n[2] Scanning for matching thumbnails in '{THUMBNAILS_DIR}' directory...")
    thumbnails_to_remove = find_thumbnails_to_delete(THUMBNAILS_DIR, local_videos_set)
    
    if not thumbnails_to_remove:
        print("\nConclusion: No matching thumbnails found to delete. Your directory is clean!")
        sys.exit(0)

    # Step 3: Report findings and ask for user confirmation.
    print("\n--- REPORT ---")
    print(f"Found {len(thumbnails_to_remove)} thumbnail images corresponding to your local videos.")
    # Use os.path.abspath to show the full, unambiguous path
    full_thumbnails_path = os.path.abspath(THUMBNAILS_DIR)
    print(f"These files are located in the directory: '{full_thumbnails_path}'")
    print("\n" + "="*50)
    print("!!! WARNING: THIS ACTION IS IRREVERSIBLE. !!!")
    print("="*50)

    try:
        confirm = input("Are you sure you want to delete these files? (type 'yes' to confirm): ")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)

    # Step 4: Perform deletion if confirmed.
    if confirm.lower().strip() == 'yes':
        print("\n[3] Confirmation received. Proceeding with deletion...")
        deleted_count = 0
        error_count = 0
        for filepath in thumbnails_to_remove:
            try:
                os.remove(filepath)
                deleted_count += 1
            except OSError as e:
                print(f"  - Error deleting file {os.path.basename(filepath)}: {e}")
                error_count += 1
        
        print("\n--- DELETION COMPLETE ---")
        print(f"Successfully deleted: {deleted_count} files.")
        if error_count > 0:
            print(f"Failed to delete: {error_count} files (see errors above).")
    else:
        print("\nOperation aborted. No files were deleted.")

if __name__ == "__main__":
    main()

# END: ENTIRE FILE "clean_thumbnails.py"