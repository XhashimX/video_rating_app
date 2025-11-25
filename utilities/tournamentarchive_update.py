# START: FULL SCRIPT
import json
import os
import shutil
from pathlib import Path

# --- Configuration ---
ARCHIVE_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\tournamentarchive.json"
SOURCE_DB_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"

def clean_filename(filename):
    """
    Removes prefixes like '1000_', '544_' to compare core filenames.
    Logic: If a '_' exists, splits and takes the second part if the first part is digits.
    """
    if not filename or not isinstance(filename, str):
        return filename
    
    parts = filename.split('_', 1)
    if len(parts) > 1 and parts[0].isdigit():
        return parts[1] # Return the part after the first underscore
    return filename

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {path}")
        return None

def main():
    print("=== specialized Data Repair Script ===")

    # 1. Load Data
    print("Loading files...")
    archive_data = load_json(ARCHIVE_PATH)
    source_data = load_json(SOURCE_DB_PATH)

    if not archive_data or not source_data:
        print("Failed to load data. Aborting.")
        return

    # 2. Build Lookup Maps from Source DB (For speed and logic)
    print("Building lookup indexes from source database...")
    
    # Map: File Size -> Correct Filename
    size_to_name_map = {} 
    # Map: Cleaned Filename -> Correct File Size
    clean_name_to_size_map = {} 

    for video_name, data in source_data.items():
        # strict check for file_size existence
        f_size = data.get('file_size')
        
        # Populate Size Map (Only if size is valid)
        if f_size is not None:
            size_to_name_map[f_size] = video_name
        
        # Populate Name Map
        clean = clean_filename(video_name)
        if clean:
            clean_name_to_size_map[clean] = f_size

    print(f"Indexes built. Found {len(size_to_name_map)} unique sizes and {len(clean_name_to_size_map)} unique names.")

    # 3. Process Archive Data
    print("\nStarting repair process...")
    updates_count = 0
    
    # archive_data structure: {"tournament_name": {"top1": {...}, "top2": {...}}}
    for tournament_key, tournament_val in archive_data.items():
        if not isinstance(tournament_val, dict):
            continue

        for rank_key, rank_data in tournament_val.items():
            # We only care about dictionaries (top1, top2, etc.), skipping "initial_participants"
            if not isinstance(rank_data, dict):
                continue

            current_size = rank_data.get('file_size')
            current_video = rank_data.get('video')

            # --- LOGIC 1: Size exists -> Fix Name ---
            if current_size is not None:
                # Check if this size exists in our source DB
                if current_size in size_to_name_map:
                    correct_name = size_to_name_map[current_size]
                    
                    # Update if names are different
                    if current_video != correct_name:
                        print(f"[Name Fix] Size {current_size}: Changed '{current_video}' -> '{correct_name}'")
                        rank_data['video'] = correct_name
                        updates_count += 1
            
            # --- LOGIC 2: Size is Null -> Fix Size (using fuzzy name match) ---
            else:
                # Clean the current name to ignore prefix changes (e.g., 544_ vs 1000_)
                cleaned_current = clean_filename(current_video)
                
                if cleaned_current in clean_name_to_size_map:
                    found_size = clean_name_to_size_map[cleaned_current]
                    
                    if found_size is not None:
                        print(f"[Size Fix] Name '{current_video}': Set size to {found_size}")
                        rank_data['file_size'] = found_size
                        updates_count += 1
                    else:
                        print(f"[Skip] Match found for '{current_video}' but source size is also null.")
                else:
                    # Optional: Print if no match found for a null size
                    # print(f"[Warning] Could not find size for: {current_video}")
                    pass

    # 4. Save Changes
    if updates_count > 0:
        print(f"\nTotal updates made: {updates_count}")
        
        # Create Backup
        backup_path = ARCHIVE_PATH.replace('.json', '_backup.json')
        try:
            shutil.copy(ARCHIVE_PATH, backup_path)
            print(f"Backup created: {backup_path}")
            
            # Write new file
            with open(ARCHIVE_PATH, 'w', encoding='utf-8') as f:
                json.dump(archive_data, f, indent=4)
            print("Successfully saved changes to tournamentarchive.json")
            
        except Exception as e:
            print(f"Error saving file: {e}")
    else:
        print("\nNo updates were required. Data appears consistent with logic.")

if __name__ == "__main__":
    main()
# END: FULL SCRIPT