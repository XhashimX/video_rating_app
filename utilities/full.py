import json
import re
import os
import random
from itertools import combinations

# --- Basic Settings ---
DATABASE_FILES = [
    "/storage/emulated/0/myhome/video_rating_app/utilities/elo_videos_A1000 elo liv.json",
    "/storage/emulated/0/myhome/video_rating_app/utilities/elo_videos_A1400 elo ani.json",
    "/storage/emulated/0/myhome/video_rating_app/utilities/elo_videos_A2000 elo ani.json",
    "/storage/emulated/0/myhome/video_rating_app/utilities/elo_videos_A1000 elo ani.json",
    "/storage/emulated/0/myhome/video_rating_app/utilities/elo_videos_A1000 elo tik.json",
    "/storage/emulated/0/myhome/video_rating_app/utilities/elo_videos_A1000 elo pic.json"
]

# --- Helper Functions ---
def load_json_file(filepath):
    """Loads a JSON file with basic error handling."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file {filepath}")
        return None
    except Exception as e:
        print(f"Unexpected error loading {filepath}: {e}")
        return None

def save_json_file(data, filepath):
    """Saves data to a JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Data successfully saved to: {filepath}")
    except Exception as e:
        print(f"Error saving file {filepath}: {e}")

def sanitize_filename(name):
    """Removes invalid characters from a filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

# --- Function 1: Extract by size ---
def extract_sizes_from_input_file(filepath):
    """
    Extracts file sizes from a text or JSON file.
    Searches for patterns (Size: size) or "file_size": [sizes].
    """
    sizes = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pattern 1: (Size: size)
        pattern1 = r'\(Size:\s*(\d+)\)'
        matches1 = re.findall(pattern1, content)
        for size_str in matches1:
            try:
                sizes.add(int(size_str))
            except ValueError:
                print(f"Warning: Found invalid size (Pattern 1): {size_str}")

        # Pattern 2: "file_size": [sizes]
        pattern2_block = r'"file_size":\s*\[(.*?)\]'
        block_matches = re.findall(pattern2_block, content, re.DOTALL)
        
        for block_content in block_matches:
            size_strs_in_block = re.findall(r'(\d+)', block_content)
            for size_str in size_strs_in_block:
                try:
                    sizes.add(int(size_str))
                except ValueError:
                    print(f"Warning: Found invalid size (Pattern 2): {size_str}")
        
        if not sizes:
            print("No sizes found in the input file.")
        else:
            print(f"Extracted sizes from input file: {sizes}")
        return list(sizes)

    except FileNotFoundError:
        print(f"Error: Input file not found {filepath}")
        return []
    except Exception as e:
        print(f"Error reading input file or extracting sizes: {e}")
        return []

def search_databases_for_sizes(sizes_to_find):
    """
    Searches the specified database files for files matching the given sizes.
    """
    matched_entries = {}
    sizes_set = set(sizes_to_find)

    if not sizes_set:
        print("No sizes to search for.")
        return matched_entries

    print(f"Searching for files with sizes: {sizes_set} in databases...")

    for db_file_path in DATABASE_FILES:
        print(f"  Searching in: {db_file_path}")
        db_data = load_json_file(db_file_path)
        if db_data:
            for filename, details in db_data.items():
                if "file_size" in details and details["file_size"] in sizes_set:
                    if filename not in matched_entries:
                        matched_entries[filename] = details
                        print(f"    Match found: {filename} (Size: {details['file_size']})")
    
    if not matched_entries:
        print("No files matching the specified sizes were found in the databases.")
    else:
        print(f"Found {len(matched_entries)} matching entries.")
    return matched_entries

def function_extract_by_size():
    """
    Main function to extract files by size.
    """
    print("\n--- Function: Extract by Size ---")
    input_file_path = input("Enter the name of the file (txt/json) containing sizes: ").strip()
    
    if not os.path.exists(input_file_path):
        print(f"Error: File '{input_file_path}' does not exist.")
        return None

    extracted_sizes = extract_sizes_from_input_file(input_file_path)
    if not extracted_sizes:
        return None

    matching_data = search_databases_for_sizes(extracted_sizes)
    if not matching_data:
        return None

    output_filename_base = sanitize_filename(os.path.splitext(os.path.basename(input_file_path))[0])
    output_file_path = f"extracted_by_size_{output_filename_base}_{random.randint(1000,9999)}.json"
    
    save_json_file(matching_data, output_file_path)
    
    while True:
        proceed = input(f"Do you want to apply Function 2 (Make competition) to the output file '{output_file_path}'? (yes/no): ").strip().lower()
        if proceed in ['yes', 'y']:
            return output_file_path
        elif proceed in ['no', 'n']:
            return None
        else:
            print("Invalid answer. Please enter 'yes' or 'no'.")


# --- Function 2: Make competition ---
def create_competition_groups(videos_data, num_videos_per_competition, preference):
    """
    Creates competition groups based on data and preferences.
    """
    competitions = []
    video_items = list(videos_data.items()) 
    
    if not video_items:
        print("No videos available to create competitions.")
        return []

    print(f"Available videos: {len(video_items)}")
    if len(video_items) < num_videos_per_competition:
        print(f"Available videos ({len(video_items)}) are less than the required number per competition ({num_videos_per_competition}). Cannot create competitions.")
        return []

    processed_filenames = set() # To track videos already used in preferred groups
    preferred_groups = []

    if preference == "closest_rating":
        print("Applying preference: Closest rating.")
        video_items.sort(key=lambda item: item[1].get("rating", 0))
        # Simple grouping of sorted items
        for i in range(0, len(video_items) - num_videos_per_competition + 1, num_videos_per_competition):
            group = video_items[i : i + num_videos_per_competition]
            if len(group) == num_videos_per_competition:
                preferred_groups.append(group)
                for item in group:
                    processed_filenames.add(item[0])
    
    elif preference == "1000_vs_non_1000":
        print("Applying preference: Rating 1000 vs. non-1000 rating.")
        group_1000 = [item for item in video_items if item[1].get("rating") == 1000 and item[0] not in processed_filenames]
        group_non_1000 = [item for item in video_items if item[1].get("rating") != 1000 and item[0] not in processed_filenames]
        random.shuffle(group_1000)
        random.shuffle(group_non_1000)

        while len(group_1000) > 0 and len(group_non_1000) >= (num_videos_per_competition - 1) and num_videos_per_competition > 0 :
            if num_videos_per_competition == 1 and len(group_1000) > 0: # Should not happen with num_videos_per_competition >= 2
                 break # Avoid infinite loop or error
            current_group = [group_1000.pop(0)]
            for _ in range(num_videos_per_competition - 1):
                if len(group_non_1000) > 0:
                    current_group.append(group_non_1000.pop(0))
                else: # Not enough non_1000, break from forming this group
                    current_group = [] # Discard partial group
                    break 
            if current_group and len(current_group) == num_videos_per_competition:
                preferred_groups.append(current_group)
                for item in current_group:
                    processed_filenames.add(item[0])
            elif not group_non_1000 and num_videos_per_competition > 1: # Ran out of non_1000
                break


    elif preference == "face_vs_body":
        print("Applying preference: Face tag vs. Body tag.")
        group_face = [item for item in video_items if "Face" in item[1].get("tags", "") and item[0] not in processed_filenames]
        group_body = [item for item in video_items if "Body" in item[1].get("tags", "") and item[0] not in processed_filenames]
        random.shuffle(group_face)
        random.shuffle(group_body)
        
        while len(group_face) > 0 and len(group_body) >= (num_videos_per_competition -1) and num_videos_per_competition > 0:
            if num_videos_per_competition == 1 and len(group_face) > 0:
                break
            current_group = [group_face.pop(0)]
            for _ in range(num_videos_per_competition - 1):
                if len(group_body) > 0:
                    current_group.append(group_body.pop(0))
                else:
                    current_group = []
                    break
            if current_group and len(current_group) == num_videos_per_competition:
                preferred_groups.append(current_group)
                for item in current_group:
                    processed_filenames.add(item[0])
            elif not group_body and num_videos_per_competition > 1:
                break
    
    # Remaining videos for random grouping
    remaining_videos = [item for item in video_items if item[0] not in processed_filenames]
    random.shuffle(remaining_videos)
    
    all_groups_for_competition = preferred_groups
    for i in range(0, len(remaining_videos) - num_videos_per_competition + 1, num_videos_per_competition):
        all_groups_for_competition.append(remaining_videos[i : i + num_videos_per_competition])

    # Create competition entries
    for group in all_groups_for_competition:
        if len(group) == num_videos_per_competition:
            competition_entry = {
                "videos": [item[0] for item in group],
                "rating": [item[1].get("rating", 1000) for item in group],
                "file_size": [item[1].get("file_size", 0) for item in group],
                "mode": 1,
                "num_videos": num_videos_per_competition,
                "ranking_type": "winner_only",
                "competition_type": preference if preference and preference != "none" else "random"
            }
            competitions.append(competition_entry)
            
    print(f"Created {len(competitions)} competitions.")
    return competitions


def function_make_competition(input_json_path=None):
    """
    Main function to create competitions.
    """
    print("\n--- Function: Make Competition ---")
    if not input_json_path:
        input_json_path = input("Enter the name of the JSON file containing video data: ").strip()

    videos_data = load_json_file(input_json_path)
    if not videos_data or not isinstance(videos_data, dict):
        print("Video data not loaded or format is incorrect (must be a dictionary).")
        return

    while True:
        try:
            num_vids_str = input("Number of videos per competition?: ").strip()
            num_videos_per_competition = int(num_vids_str)
            if num_videos_per_competition < 2:
                print("Number of videos must be at least 2.")
            else:
                break
        except ValueError:
            print("Invalid input. Please enter a number.")

    print("Available preferences:")
    print("  1. Closest rating (closest_rating)")
    print("  2. Rating 1000 vs. non-1000 (1000_vs_non_1000)")
    print("  3. Face tag vs. Body tag (face_vs_body)")
    print("  4. No preference / Random (none)")
    
    pref_choice = input("Choose preference number or name (or leave empty for 'none'): ").strip().lower()
    preference = "none"
    if pref_choice == "1" or pref_choice == "closest_rating":
        preference = "closest_rating"
    elif pref_choice == "2" or pref_choice == "1000_vs_non_1000":
        preference = "1000_vs_non_1000"
    elif pref_choice == "3" or pref_choice == "face_vs_body":
        preference = "face_vs_body"
    elif pref_choice in ["4", "none", ""]:
        preference = "none"
    else:
        print("Unknown preference choice, using 'none' (random).")

    competition_list = create_competition_groups(videos_data, num_videos_per_competition, preference)

    if competition_list:
        output_filename_base = sanitize_filename(os.path.splitext(os.path.basename(input_json_path))[0])
        output_file_path = f"competitions_{output_filename_base}_{preference}_{random.randint(1000,9999)}.json"
        save_json_file(competition_list, output_file_path)
    else:
        print("No competitions were created.")

# --- Function 3: Compare and Correct (Based on your provided code) ---

def load_master_database(db_files_list):
    """Loads and merges all specified database files into a single master dictionary."""
    master_data = {}
    print("Loading master database files for correction...")
    for db_file_path in db_files_list:
        print(f"  Loading: {db_file_path}")
        data = load_json_file(db_file_path) 
        if data and isinstance(data, dict):
            # Standard dictionary update: if keys (filenames) are duplicated, the last one read wins.
            master_data.update(data)
        elif data is not None: # Loaded but not a dict
            print(f"Warning: Data in {db_file_path} is not in the expected dictionary format. Skipping.")
    
    if not master_data:
        print("Error: Master database is empty or could not be loaded.")
        return None, None # Return None for master_data and master_video_list
    
    # Also return a list of all videos from the master database for random selection
    master_video_list = list(master_data.values())
    print(f"Master database loaded with {len(master_data)} entries.")
    return master_data, master_video_list

def compare_and_correct_data(master_db_data, master_video_list, target_competition_data):
    """
    Compares target competition data against the master database and corrects entries.
    If a file_size is not found, it's replaced with a random video from the master_video_list.
    """
    corrected_data_list = []

    # Create a lookup from the master database: file_size -> video_name
    master_lookup_by_size = {}
    videos_with_duplicate_sizes = {}

    for video_name, video_details in master_db_data.items():
        if 'file_size' in video_details:
            size = video_details['file_size']
            if size in master_lookup_by_size and master_lookup_by_size[size] != video_name:
                if size not in videos_with_duplicate_sizes:
                    videos_with_duplicate_sizes[size] = [master_lookup_by_size[size]]
                videos_with_duplicate_sizes[size].append(video_name)
            master_lookup_by_size[size] = video_name # Last one wins for a given size
        else:
            print(f"Warning: Video '{video_name}' in master database is missing 'file_size'. It cannot be looked up by size.")

    if videos_with_duplicate_sizes:
        print("\nWarning: Multiple videos in the master database share the same file size.")
        print("The correction will use the last video encountered for that size for lookups:")
        for size, names in videos_with_duplicate_sizes.items():
            print(f"  Size {size} is associated with videos: {names}. Using '{master_lookup_by_size[size]}' for corrections.")
        print("-" * 20)

    if not master_video_list:
        print("Error: Master video list is empty. Cannot pick random videos.")
        return []

    if not isinstance(target_competition_data, list):
        print(f"Error: The target competition file data is not a list. Found type: {type(target_competition_data)}.")
        return [] # Return empty list as we expect a list of competitions

    for entry_index, entry in enumerate(target_competition_data):
        if not isinstance(entry, dict):
            print(f"Warning: Item at index {entry_index} in target data is not a dictionary. Skipping.")
            corrected_data_list.append(entry) # Add as-is or skip
            continue

        # Create a deep copy for modification to avoid altering original list items during iteration
        new_entry = json.loads(json.dumps(entry)) 

        videos = new_entry.get('videos')
        ratings = new_entry.get('rating')
        file_sizes = new_entry.get('file_size')

        if not (isinstance(videos, list) and 
                isinstance(ratings, list) and 
                isinstance(file_sizes, list) and
                len(videos) == len(ratings) == len(file_sizes)):
            print(f"Warning: Skipping entry at index {entry_index} due to malformed or mismatched 'videos', 'rating', or 'file_size' lists.")
            corrected_data_list.append(entry) # Add original entry back
            continue
        
        print(f"\nProcessing competition entry {entry_index + 1} with videos: {videos}")
        modifications_in_entry = 0
        for i, current_size_in_competition in enumerate(file_sizes):
            original_video_name = videos[i]
            original_rating = ratings[i]

            if current_size_in_competition in master_lookup_by_size:
                correct_video_name_from_master = master_lookup_by_size[current_size_in_competition]
                
                if correct_video_name_from_master in master_db_data:
                    master_video_details = master_db_data[correct_video_name_from_master]
                    correct_rating_from_master = master_video_details.get('rating')
                    
                    # Correct video name if different
                    if videos[i] != correct_video_name_from_master:
                        print(f"  Index {i}: Video name for size {current_size_in_competition} corrected: '{videos[i]}' -> '{correct_video_name_from_master}'")
                        new_entry['videos'][i] = correct_video_name_from_master
                        modifications_in_entry += 1
                    
                    # Correct rating if different and available in master
                    if correct_rating_from_master is not None and ratings[i] != correct_rating_from_master:
                        print(f"  Index {i}: Rating for video '{correct_video_name_from_master}' (size {current_size_in_competition}) corrected: {ratings[i]} -> {correct_rating_from_master}")
                        new_entry['rating'][i] = correct_rating_from_master
                        modifications_in_entry += 1
                    elif correct_rating_from_master is None:
                        print(f"  Index {i}: Video '{correct_video_name_from_master}' in master DB has no rating. Rating {ratings[i]} for size {current_size_in_competition} in competition file remains unchanged.")
                else:
                    # This should ideally not happen if master_lookup_by_size is built from master_db_data keys
                    print(f"  Internal Warning: Video name '{correct_video_name_from_master}' (looked up by size {current_size_in_competition}) not found in master_db_data. Skipping corrections for this item.")
            else:
                # --- START OF MODIFICATION ---
                # Size not found in master database, pick a random video from master_video_list
                if master_video_list:
                    random_video_details = random.choice(master_video_list)
                    random_video_name = next(key for key, val in master_db_data.items() if val == random_video_details) # Get name from details
                    random_size = random_video_details.get('file_size', 0)
                    random_rating = random_video_details.get('rating', 1000)

                    print(f"  Index {i}: Original size {current_size_in_competition} (video '{videos[i]}') NOT found in master DB.")
                    print(f"    Replacing with random video from master DB: '{random_video_name}' (Size: {random_size}, Rating: {random_rating})")
                    
                    new_entry['videos'][i] = random_video_name
                    new_entry['rating'][i] = random_rating
                    new_entry['file_size'][i] = random_size # Update file_size to the new random one
                    modifications_in_entry += 1
                else:
                    print(f"  Index {i}: File size {current_size_in_competition} (video '{videos[i]}') not found in master database lookup, AND no random videos available. No correction possible.")
                # --- END OF MODIFICATION ---
        
        if modifications_in_entry == 0:
            print(f"  No corrections made for competition entry {entry_index + 1}.")

        corrected_data_list.append(new_entry)

    return corrected_data_list

def function_compare_and_correct():
    """
    Main wrapper for the 'Compare and Correct' functionality.
    """
    print("\n--- Function: Compare and Correct Competition File ---")
    
    master_data, master_video_list = load_master_database(DATABASE_FILES)
    if not master_data:
        print("Cannot proceed without a loaded master database.")
        return

    target_file_path = input("Enter the path of the JSON competition file to be corrected: ").strip()
    if not os.path.exists(target_file_path):
        print(f"Error: Target file '{target_file_path}' not found.")
        return
    
    print(f"Loading target competition file: {target_file_path}")
    target_data_list = load_json_file(target_file_path) 
    
    if target_data_list is None:
        print(f"Failed to load or parse the target competition file: {target_file_path}")
        return
    
    if not isinstance(target_data_list, list):
        # Attempt to handle if the file is a dict with a single key containing the list (common mistake)
        if isinstance(target_data_list, dict) and len(target_data_list) == 1:
            print("Target file is a dictionary. Attempting to use the list from its first value.")
            key = next(iter(target_data_list))
            target_data_list = target_data_list[key]
            if not isinstance(target_data_list, list):
                print("Error: The value within the dictionary is not a list. Cannot process.")
                return
        else:
            print("Error: Target file data is not in the expected list format (list of competitions).")
            return


    corrected_list = compare_and_correct_data(master_data, master_video_list, target_data_list)

    if corrected_list: # Save even if no changes were made, as it represents the "processed" version
        output_filename_base = sanitize_filename(os.path.splitext(os.path.basename(target_file_path))[0])
        output_file_path = f"corrected_competitions_{output_filename_base}_{random.randint(1000,9999)}.json"
        save_json_file(corrected_list, output_file_path)
    elif not target_data_list : # Original target was empty
        print("The target competition file was empty. Nothing to correct or save.")
    else: # Correction process might have failed to produce a list or other issues
        print("No data was processed or the correction resulted in an empty list. Output file not saved.")


# --- Main Program ---
def main():
    for db_path in DATABASE_FILES:
        if not os.path.exists(db_path):
            print(f"Warning: Database file '{db_path}' not found. Some functions may not work correctly.")

    while True:
        print("\n--- Main Menu ---")
        print("1. Extract by Size")
        print("2. Make Competition")
        print("3. Compare and Correct Competition File")
        print("4. Exit")
        choice = input("Select a function (1-4): ").strip()

        if choice == '1':
            output_from_func1 = function_extract_by_size()
            if output_from_func1: 
                function_make_competition(output_from_func1)
        elif choice == '2':
            function_make_competition()
        elif choice == '3':
            function_compare_and_correct()
        elif choice == '4':
            print("Thank you for using the script. Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    print("Note: Ensure database file paths are correct and you have read permissions.")
    main()