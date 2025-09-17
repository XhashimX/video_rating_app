import json
import re
import os
import random
import shutil
from itertools import combinations

# --- Basic Settings ---
DATABASE_FILES = [
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo liv.json",
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1400 elo ani.json",
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A2000 elo ani.json",
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo ani.json",
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo tik.json",
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_Dib.json",
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo pic.json"
]

FILL_DATABASE_PATH = "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo tik.json"

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

def get_save_path(original_input_path, new_file_pattern):
    """
    Asks the user if they want to overwrite the original file or create a new one.
    Returns the chosen file path.
    """
    while True:
        # Using os.path.basename to keep the prompt clean
        overwrite_choice = input(f"Overwrite the original file '{os.path.basename(original_input_path)}' with the new data? (y/n): ").strip().lower()
        if overwrite_choice == 'y':
            print(f"The original file will be overwritten: {original_input_path}")
            return original_input_path
        elif overwrite_choice == 'n':
            print(f"A new file will be created instead.")
            return new_file_pattern
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

# --- Function 1: Extract by size ---
def extract_sizes_from_input_file(filepath):
    """
    Extracts file sizes from a text or JSON file.
    """
    sizes = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # All patterns to find sizes
        pattern1 = r'\(Size:\s*(\d+)\)'
        pattern2_block = r'"file_size":\s*\[(.*?)\]'
        pattern3 = r'"file_size":\s*(\d+)(?![\],])'

        for p in [pattern1, pattern3]:
             matches = re.findall(p, content)
             for size_str in matches:
                try:
                    sizes.add(int(size_str))
                except ValueError:
                    print(f"Warning: Found invalid size: {size_str}")

        block_matches = re.findall(pattern2_block, content, re.DOTALL)
        for block_content in block_matches:
            size_strs_in_block = re.findall(r'(\d+)', block_content)
            for size_str in size_strs_in_block:
                try:
                    sizes.add(int(size_str))
                except ValueError:
                    print(f"Warning: Found invalid size in block: {size_str}")

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
        if db_data and isinstance(db_data, dict):
            for filename, details in db_data.items():
                if "file_size" in details and details["file_size"] in sizes_set:
                    if filename not in matched_entries:
                        matched_entries[filename] = details
                        print(f"    Match found: {filename} (Size: {details['file_size']})")
        elif db_data is not None:
            print(f"Warning: Data in {db_file_path} is not a dictionary. Skipping.")

    if not matched_entries:
        print("No files matching the specified sizes were found in the databases.")
    else:
        print(f"Found {len(matched_entries)} matching entries.")
    return matched_entries

# MODIFIED FUNCTION
def function_extract_by_size():
    """
    Main function to extract files by size. Lists relevant files first.
    """
    print("\n--- Function: Extract by Size ---")
    
    # --- START OF NEW CODE ---
    # This block lists files matching the criteria before asking for input.
    print("Searching for relevant files in the current directory...")
    current_directory = os.getcwd()
    matching_files = []
    try:
        for filename in os.listdir(current_directory):
            # Check if it's a file and matches the criteria (case-insensitive)
            if os.path.isfile(os.path.join(current_directory, filename)):
                if filename.lower().startswith('topcut') and 'part' not in filename.lower():
                    matching_files.append(filename)
    except Exception as e:
        print(f"Warning: Could not list files in the directory: {e}")

    if matching_files:
        print("\n--- Files starting with 'topcut' (without 'part') ---")
        for i, f in enumerate(matching_files, 1):
            print(f"  {i}. {f}")
        print("--------------------------------------------------\n")
    else:
        print("No files found matching the 'topcut' criteria in this directory.\n")
    # --- END OF NEW CODE ---
    
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
    new_file_pattern = f"extracted_by_size_{output_filename_base}_{random.randint(1000,9999)}.json"
    output_file_path = get_save_path(input_file_path, new_file_pattern)
    save_json_file(matching_data, output_file_path)

    while True:
        proceed = input(f"Do you want to apply Function 2 (Make Competition) to the output file '{output_file_path}'? (y/n): ").strip().lower()
        if proceed in ['y', 'n']:
            return output_file_path if proceed == 'y' else None
        else:
            print("Invalid answer. Please enter 'y' or 'n'.")

# --- Filtering Helpers ---
def parse_range_list(input_str, value_type=float):
    """
    Parses a string like '1-3,5,7-9' into a list of (min, max) tuples or single values.
    Returns a list of (low, high) tuples.
    """
    ranges = []
    parts = [p.strip() for p in input_str.split(',') if p.strip()]
    for part in parts:
        if '-' in part:
            low_str, high_str = part.split('-', 1)
            try:
                low = value_type(low_str)
                high = value_type(high_str)
                if low <= high:
                    ranges.append((low, high))
            except ValueError:
                continue
        else:
            try:
                val = value_type(part)
                ranges.append((val, val))
            except ValueError:
                continue
    return ranges

def filter_videos(videos_data):
    """
    Applies multiple filters (rating, times_shown, tags, win_rate, name) to videos_data.
    Returns a filtered dictionary.
    """
    filtered = {}

    # Rating filter
    rating_input = input("Filter by rating (n, exact, range, multiple ranges [e.g. 5, 1-3,7-9]): ").strip().lower()
    rating_ranges = [] if rating_input in ['n', ''] else parse_range_list(rating_input, int)

    # times_shown filter (exact or multiple exact)
    ts_input = input("Filter by times_shown (n, exact, multiple exact [e.g. 50,200,300]): ").strip().lower()
    ts_values = set()
    if ts_input not in ['n', '']:
        for part in ts_input.split(','):
            try:
                ts_values.add(int(part.strip()))
            except ValueError:
                pass

    # tags filter (n, one tag, multiple tags)
    tags_input = input("Filter by tags (n, one or more comma-separated tags [e.g. comedy, action]): ").strip().lower()
    tag_list = [] if tags_input in ['n', ''] else [t.strip() for t in tags_input.split(',') if t.strip()]

    # win_rate filter (n, exact, range, multiple ranges)
    wr_input = input("Filter by win_rate (n, exact, range, multiple ranges [e.g. 0.6-0.9,0.1-0.2]): ").strip().lower()
    wr_ranges = [] if wr_input in ['n', ''] else parse_range_list(wr_input, float)

    # name filter (n, exact, multiple)
    name_input = input("Filter by name (n, one or more comma-separated strings): ").strip().lower()
    name_list = [] if name_input in ['n', ''] else [n.strip() for n in name_input.split(',') if n.strip()]

    for vid, details in videos_data.items():
        keep = True

        if rating_ranges:
            vid_rating = details.get('rating')
            if vid_rating is None or not any(low <= vid_rating <= high for (low, high) in rating_ranges):
                keep = False
        if not keep: continue

        if ts_values:
            vid_ts = details.get('times_shown')
            if vid_ts is None or vid_ts not in ts_values:
                keep = False
        if not keep: continue

        if tag_list:
            vid_tags = details.get('tags', '').lower()
            if not any(tag in vid_tags.split(',') for tag in tag_list):
                keep = False
        if not keep: continue

        if wr_ranges:
            vid_wr = details.get('win_rate')
            if vid_wr is None or not any(low <= vid_wr <= high for (low, high) in wr_ranges):
                keep = False
        if not keep: continue

        if name_list:
            vid_name = details.get('name', '').lower()
            if not any(n in vid_name for n in name_list):
                keep = False
        if not keep: continue

        filtered[vid] = details

    print(f"Filtered videos count: {len(filtered)} out of {len(videos_data)}")
    return filtered

# --- Function 2: Make competition ---
def create_competition_groups(videos_data, num_videos_per_competition, preference):
    """
    Creates competition groups based on data and a single grouping preference.
    """
    competitions = []
    video_items = list(videos_data.items())

    if not video_items or len(video_items) < num_videos_per_competition:
        print(f"Cannot create competitions. Available videos: {len(video_items)}, Required: {num_videos_per_competition}")
        return []

    processed_filenames = set()
    preferred_groups = []

    # Logic for different preferences (closest_rating, 1000_vs_non_1000, face_vs_body) remains the same
    # ... (code omitted for brevity, it's unchanged) ...

    # Remaining videos for random grouping
    remaining_videos = [item for item in video_items if item[0] not in processed_filenames]
    random.shuffle(remaining_videos)

    all_groups_for_competition = preferred_groups
    for i in range(0, len(remaining_videos), num_videos_per_competition):
        group = remaining_videos[i : i + num_videos_per_competition]
        if len(group) == num_videos_per_competition:
            all_groups_for_competition.append(group)

    # Create competition entries
    for group in all_groups_for_competition:
        competition_entry = {
            "videos": [item[0] for item in group],
            "rating": [item[1].get("rating", 1000) for item in group],
            "file_size": [item[1].get("file_size", 0) for item in group],
            "mode": 1,
            "num_videos": num_videos_per_competition,
            "ranking_type": "winner_only",
            "competition_type": preference if preference != "none" else "random"
        }
        competitions.append(competition_entry)

    print(f"Created {len(competitions)} competitions.")
    return competitions

def function_make_competition(input_json_path=None):
    """
    Main function to create competitions with filtering, limited count, and grouping preferences.
    """
    print("\n--- Function: Make Competition ---")
    default_file = "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo tik.json"
    if not input_json_path:
        use_default = input(f"Do you want to create competitions for file '{default_file}'? (y/n): ").strip().lower()
        if use_default == 'y':
            input_json_path = default_file
        else:
            input_json_path = input("Enter the name of the JSON file containing video data: ").strip()

    if not os.path.exists(input_json_path):
        print(f"Error: File '{input_json_path}' does not exist.")
        return

    videos_data = load_json_file(input_json_path)
    if not videos_data or not isinstance(videos_data, dict):
        print("Video data not loaded or format is incorrect.")
        return

    filtered_videos = filter_videos(videos_data)
    if not filtered_videos:
        print("No videos match the specified filters.")
        return

    # User input for competition settings (num_videos, limited_count, preference)
    # ... (code omitted for brevity, it's unchanged) ...
    while True:
        try:
            num_videos_per_competition = int(input("Number of videos per competition?: ").strip())
            if num_videos_per_competition >= 2: break
            print("Number must be at least 2.")
        except ValueError: print("Invalid input.")

    full_or_limited = input("Create competitions for all possible groups? (y/n): ").strip().lower()
    limited_count = None
    if full_or_limited == 'n':
        while True:
            try:
                limited_count = int(input("Enter the number of competitions to create: ").strip())
                if limited_count >= 1: break
                print("Number must be at least 1.")
            except ValueError: print("Invalid input.")

    print("\nGrouping preferences: 1. closest_rating, 2. 1000_vs_non_1000, 3. face_vs_body, 4. none (random)")
    pref_map = {"1": "closest_rating", "2": "1000_vs_non_1000", "3": "face_vs_body"}
    pref_choice = input("Choose preference (name or number): ").strip().lower()
    preference = pref_map.get(pref_choice, "none" if pref_choice not in pref_map.values() else pref_choice)

    competitions = []
    if full_or_limited == 'y':
        competitions = create_competition_groups(filtered_videos, num_videos_per_competition, preference)
    else: # Limited competitions
        if preference != "none":
            all_groups = create_competition_groups(filtered_videos, num_videos_per_competition, preference)
            if limited_count >= len(all_groups):
                competitions = all_groups
            else:
                competitions = random.sample(all_groups, limited_count)
        else: # Random competitions
            vid_keys = list(filtered_videos.keys())
            for _ in range(limited_count):
                group_keys = random.sample(vid_keys, num_videos_per_competition)
                competition_entry = {
                    "videos": group_keys,
                    "rating": [filtered_videos[k].get("rating", 1000) for k in group_keys],
                    "file_size": [filtered_videos[k].get("file_size", 0) for k in group_keys],
                    # ... other fields
                }
                competitions.append(competition_entry)


    if competitions:
        output_filename_base = sanitize_filename(os.path.splitext(os.path.basename(input_json_path))[0])
        pref_tag = preference if preference != "none" else "random"
        new_file_pattern = f"competitions_{output_filename_base}_{pref_tag}_{random.randint(1000,9999)}.json"
        output_file_path = get_save_path(input_json_path, new_file_pattern)
        save_json_file(competitions, output_file_path)
    else:
        print("No competitions were created.")

# --- Function 3: Compare and Correct (Based on your provided code) ---
def load_master_database(db_files_list):
    master_data = {}
    print("Loading master database...")
    for db_file_path in db_files_list:
        data = load_json_file(db_file_path)
        if data and isinstance(data, dict):
            master_data.update(data)
    if not master_data:
        print("Error: Master database is empty.")
    else:
        print(f"Master database loaded with {len(master_data)} entries.")
    return master_data

def compare_and_correct_data(master_db_data, fill_db_data, target_competition_data):
    # ... (code omitted for brevity, it's unchanged) ...
    return [] # Placeholder

def function_compare_and_correct():
    print("\n--- Function: Compare and Correct Competition File ---")
    master_data = load_master_database(DATABASE_FILES)
    if not master_data: return
    
    fill_data = load_json_file(FILL_DATABASE_PATH)
    if not fill_data: print(f"Warning: Fill database not loaded.")
    
    target_file_path = input("Enter the path of the JSON competition file to correct: ").strip()
    if not os.path.exists(target_file_path):
        print(f"Error: Target file '{target_file_path}' not found.")
        return

    target_data_list = load_json_file(target_file_path)
    if not isinstance(target_data_list, list):
        print("Error: Target file data is not a list of competitions.")
        return

    corrected_list = compare_and_correct_data(master_data, fill_data, target_data_list)
    if corrected_list:
        output_filename_base = sanitize_filename(os.path.splitext(os.path.basename(target_file_path))[0])
        new_file_pattern = f"corrected_{output_filename_base}_{random.randint(1000,9999)}.json"
        output_file_path = get_save_path(target_file_path, new_file_pattern)
        save_json_file(corrected_list, output_file_path)
    else:
        print("No corrections made or needed.")


# --- Function 4: Compare and Handle Duplicate Files by Size ---
# ... (code omitted for brevity, it's unchanged) ...
def function_compare_files_by_size():
    print("\n--- Function: Compare and Handle Duplicate Files by Size ---")
    # The logic for this function remains the same.
    pass

# --- Main Program ---
def main():
    for db_path in DATABASE_FILES:
        if not os.path.exists(db_path):
            print(f"Warning: Database file '{db_path}' not found.")

    while True:
        print("\n--- Main Menu ---")
        print("1. Extract by Size")
        print("2. Make Competition")
        print("3. Compare and Correct Competition File")
        print("4. Compare and Handle Duplicate Files by Size")
        print("5. Exit")
        choice = input("Select a function (1-5): ").strip()

        if choice == '1':
            output_from_func1 = function_extract_by_size()
            if output_from_func1:
                function_make_competition(output_from_func1)
        elif choice == '2':
            function_make_competition()
        elif choice == '3':
            function_compare_and_correct()
        elif choice == '4':
            function_compare_files_by_size()
        elif choice == '5':
            print("Thank you for using the script. Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    print("Note: Ensure database file paths and folder paths are correct.")
    main()