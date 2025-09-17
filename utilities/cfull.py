import json
import re
import os
import random
from itertools import combinations

# --- Basic Settings ---
DATABASE_FILES = [
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo liv.json",
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1400 elo ani.json",
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A2000 elo ani.json",
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo ani.json",
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo tik.json",
    "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo pic.json"
]

DEFAULT_TIKTOK_FILE = "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_A1000 elo tik.json"
DEFAULT_BASE_FOLDER = "C:/Users/Stark/Download/myhome/video_rating_app/NS/TikTok/Elo tik/A1000 elo tik"
DUPLICATE_MOVE_FOLDER = "C:/Users/Stark/Download/myhome/video_rating_app/NS/TikTok/Elo tik/Dib"

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

def get_file_sizes_in_folder(folder_path):
    """Returns a dictionary mapping file sizes to file paths in a folder."""
    size_to_files = {}
    if not os.path.exists(folder_path):
        print(f"Warning: Folder does not exist: {folder_path}")
        return size_to_files
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                file_size = os.path.getsize(file_path)
                if file_size not in size_to_files:
                    size_to_files[file_size] = []
                size_to_files[file_size].append(file_path)
            except OSError:
                print(f"Warning: Could not get size for file: {file_path}")
    
    return size_to_files

# --- Function 1: Extract by size ---
def extract_sizes_from_input_file(filepath):
    """
    Extracts file sizes from a text or JSON file.
    Searches for patterns (Size: size), "file_size": [sizes], or "file_size": size.
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

        # Pattern 3: "file_size": size (single number)
        pattern3 = r'"file_size":\s*(\d+)'
        matches3 = re.findall(pattern3, content)
        for size_str in matches3:
            try:
                sizes.add(int(size_str))
            except ValueError:
                print(f"Warning: Found invalid size (Pattern 3): {size_str}")
        
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
        proceed = input(f"Do you want to apply Function 2 (Make competition) to the output file '{output_file_path}'? (y/n): ").strip().lower()
        if proceed in ['y']:
            return output_file_path
        elif proceed in ['n']:
            return None
        else:
            print("Invalid answer. Please enter 'y' or 'n'.")

# --- Filter Functions ---
def parse_rating_filter(filter_str):
    """Parse rating filter string and return a function that checks if a rating matches."""
    if filter_str.lower() == 'none' or not filter_str.strip():
        return lambda x: True
    
    ranges = []
    for part in filter_str.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                ranges.append((start, end))
            except ValueError:
                print(f"Warning: Invalid range format '{part}', ignoring.")
        else:
            try:
                single_val = int(part)
                ranges.append((single_val, single_val))
            except ValueError:
                print(f"Warning: Invalid rating value '{part}', ignoring.")
    
    def check_rating(rating):
        for start, end in ranges:
            if start <= rating <= end:
                return True
        return False
    
    return check_rating if ranges else lambda x: True

def parse_times_shown_filter(filter_str):
    """Parse times_shown filter string and return a function that checks if times_shown matches."""
    if filter_str.lower() == 'none' or not filter_str.strip():
        return lambda x: True
    
    values = []
    for part in filter_str.split(','):
        try:
            values.append(int(part.strip()))
        except ValueError:
            print(f"Warning: Invalid times_shown value '{part.strip()}', ignoring.")
    
    return (lambda x: x in values) if values else lambda x: True

def parse_tags_filter(filter_str):
    """Parse tags filter string and return a function that checks if any tag matches."""
    if filter_str.lower() == 'none' or not filter_str.strip():
        return lambda x: True
    
    target_tags = [tag.strip().lower() for tag in filter_str.split(',')]
    
    def check_tags(tags_str):
        if not tags_str:
            return False
        video_tags = [tag.strip().lower() for tag in tags_str.split(',')]
        return any(tag in video_tags for tag in target_tags)
    
    return check_tags

def parse_win_rate_filter(filter_str):
    """Parse win_rate filter string and return a function that checks if win_rate matches."""
    if filter_str.lower() == 'none' or not filter_str.strip():
        return lambda x: True
    
    ranges = []
    for part in filter_str.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(float, part.split('-'))
                ranges.append((start, end))
            except ValueError:
                print(f"Warning: Invalid win_rate range format '{part}', ignoring.")
        else:
            try:
                single_val = float(part)
                ranges.append((single_val, single_val))
            except ValueError:
                print(f"Warning: Invalid win_rate value '{part}', ignoring.")
    
    def check_win_rate(win_rate):
        for start, end in ranges:
            if start <= win_rate <= end:
                return True
        return False
    
    return check_win_rate if ranges else lambda x: True

def parse_name_filter(filter_str):
    """Parse name filter string and return a function that checks if any name matches."""
    if filter_str.lower() == 'none' or not filter_str.strip():
        return lambda x: True
    
    target_names = [name.strip().lower() for name in filter_str.split(',')]
    
    def check_name(name_str):
        if not name_str:
            return False
        return name_str.lower() in target_names
    
    return check_name

def apply_filters(videos_data, filters):
    """Apply multiple filters to video data and return filtered results."""
    filtered_data = {}
    
    for video_id, video_info in videos_data.items():
        # Check all filters
        passes_all_filters = True
        
        # Rating filter
        if 'rating' in filters and not filters['rating'](video_info.get('rating', 0)):
            passes_all_filters = False
        
        # Times shown filter
        if 'times_shown' in filters and not filters['times_shown'](video_info.get('times_shown', 0)):
            passes_all_filters = False
        
        # Tags filter
        if 'tags' in filters and not filters['tags'](video_info.get('tags', '')):
            passes_all_filters = False
        
        # Win rate filter
        if 'win_rate' in filters and not filters['win_rate'](video_info.get('win_rate', 0.0)):
            passes_all_filters = False
        
        # Name filter
        if 'name' in filters and not filters['name'](video_info.get('name', '')):
            passes_all_filters = False
        
        if passes_all_filters:
            filtered_data[video_id] = video_info
    
    return filtered_data

# --- Function 2: Make competition ---
def create_competition_groups(videos_data, num_videos_per_competition, preference, num_competitions=None):
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

    processed_filenames = set()
    preferred_groups = []

    if preference == "closest_rating":
        print("Applying preference: Closest rating.")
        video_items.sort(key=lambda item: item[1].get("rating", 0))
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

        while len(group_1000) > 0 and len(group_non_1000) >= (num_videos_per_competition - 1) and num_videos_per_competition > 0:
            if num_videos_per_competition == 1 and len(group_1000) > 0:
                break
            current_group = [group_1000.pop(0)]
            for _ in range(num_videos_per_competition - 1):
                if len(group_non_1000) > 0:
                    current_group.append(group_non_1000.pop(0))
                else:
                    current_group = []
                    break 
            if current_group and len(current_group) == num_videos_per_competition:
                preferred_groups.append(current_group)
                for item in current_group:
                    processed_filenames.add(item[0])
            elif not group_non_1000 and num_videos_per_competition > 1:
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

    # If specific number of competitions requested, randomly select
    if num_competitions and num_competitions < len(all_groups_for_competition):
        all_groups_for_competition = random.sample(all_groups_for_competition, num_competitions)

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
        use_default = input(f"Do you want to create competition for {DEFAULT_TIKTOK_FILE}? (y/n): ").strip().lower()
        if use_default == 'y':
            input_json_path = DEFAULT_TIKTOK_FILE
        else:
            input_json_path = input("Enter the name of the JSON file containing video data: ").strip()

    videos_data = load_json_file(input_json_path)
    if not videos_data or not isinstance(videos_data, dict):
        print("Video data not loaded or format is incorrect (must be a dictionary).")
        return

    # Ask for filters
    print("\nApply filters? Enter filter values or 'none' to skip each filter:")
    
    filters = {}
    
    # Rating filter
    rating_filter_input = input("Rating filter (e.g., '5-8', '7', '1-2,5-6', or 'none'): ").strip()
    if rating_filter_input.lower() != 'none' and rating_filter_input:
        filters['rating'] = parse_rating_filter(rating_filter_input)
    
    # Times shown filter
    times_shown_filter_input = input("Times shown filter (e.g., '100', '50,200,300', or 'none'): ").strip()
    if times_shown_filter_input.lower() != 'none' and times_shown_filter_input:
        filters['times_shown'] = parse_times_shown_filter(times_shown_filter_input)
    
    # Tags filter
    tags_filter_input = input("Tags filter (e.g., 'action', 'comedy,drama', or 'none'): ").strip()
    if tags_filter_input.lower() != 'none' and tags_filter_input:
        filters['tags'] = parse_tags_filter(tags_filter_input)
    
    # Win rate filter
    win_rate_filter_input = input("Win rate filter (e.g., '0.6-0.9', '0.75', or 'none'): ").strip()
    if win_rate_filter_input.lower() != 'none' and win_rate_filter_input:
        filters['win_rate'] = parse_win_rate_filter(win_rate_filter_input)
    
    # Name filter
    name_filter_input = input("Name filter (e.g., 'john', 'mary,jane', or 'none'): ").strip()
    if name_filter_input.lower() != 'none' and name_filter_input:
        filters['name'] = parse_name_filter(name_filter_input)

    # Apply filters if any
    if filters:
        print("Applying filters...")
        videos_data = apply_filters(videos_data, filters)
        print(f"After filtering: {len(videos_data)} videos remain.")
        if not videos_data:
            print("No videos left after filtering. Cannot create competitions.")
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

    # Ask about number of competitions
    use_all = input("Create competitions using all videos? (y/n): ").strip().lower()
    num_competitions = None
    if use_all != 'y':
        while True:
            try:
                num_comp_str = input("How many competitions do you want?: ").strip()
                num_competitions = int(num_comp_str)
                max_possible = len(videos_data) // num_videos_per_competition
                if num_competitions > max_possible:
                    print(f"Too many competitions requested. Maximum possible: {max_possible}")
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

    competition_list = create_competition_groups(videos_data, num_videos_per_competition, preference, num_competitions)

    if competition_list:
        output_filename_base = sanitize_filename(os.path.splitext(os.path.basename(input_json_path))[0])
        output_file_path = f"competitions_{output_filename_base}_{preference}_{random.randint(1000,9999)}.json"
        save_json_file(competition_list, output_file_path)
    else:
        print("No competitions were created.")

# --- Function 3: Compare and Correct ---
def load_master_database(db_files_list):
    """Loads and merges all specified database files into a single master dictionary."""
    master_data = {}
    print("Loading master database files for correction...")
    for db_file_path in db_files_list:
        print(f"  Loading: {db_file_path}")
        data = load_json_file(db_file_path) 
        if data and isinstance(data, dict):
            master_data.update(data)
        elif data is not None:
            print(f"Warning: Data in {db_file_path} is not in the expected dictionary format. Skipping.")
    
    if not master_data:
        print("Error: Master database is empty or could not be loaded.")
        return None, None
    
    master_video_list = list(master_data.values())
    print(f"Master database loaded with {len(master_data)} entries.")
    return master_data, master_video_list

def compare_and_correct_data(master_db_data, target_competition_data):
    """
    Compares target competition data against the master database and corrects entries.
    If a file_size is not found, it's replaced with a random video from the TikTok database.
    """
    corrected_data_list = []

    # Load TikTok database for random replacements
    tiktok_data = load_json_file(DEFAULT_TIKTOK_FILE)
    if not tiktok_data:
        print(f"Error: Could not load TikTok database from {DEFAULT_TIKTOK_FILE}")
        return []
    
    tiktok_video_list = list(tiktok_data.values())
    tiktok_names = list(tiktok_data.keys())

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
            master_lookup_by_size[size] = video_name
        else:
            print(f"Warning: Video '{video_name}' in master database is missing 'file_size'. It cannot be looked up by size.")

    if videos_with_duplicate_sizes:
        print("\nWarning: Multiple videos in the master database share the same file size.")
        print("The correction will use the last video encountered for that size for lookups:")
        for size, names in videos_with_duplicate_sizes.items():
            print(f"  Size {size} is associated with videos: {names}. Using '{master_lookup_by_size[size]}' for corrections.")
        print("-" * 20)

    if not tiktok_video_list:
        print("Error: TikTok video list is empty. Cannot pick random videos.")
        return []

    if not isinstance(target_competition_data, list):
        if isinstance(target_competition_data, dict) and len(target_competition_data) == 1:
            print("Target file is a dictionary. Attempting to use the list from its first value.")
            key = next(iter(target_competition_data))
            target_competition_data = target_competition_data[key]
            if not isinstance(target_competition_data, list):
                print("Error: The value within the dictionary is not a list. Cannot process.")
                return []
        else:
            print("Error: Target file data is not in the expected list format (list of competitions).")
            return []

    for entry_index, entry in enumerate(target_competition_data):
        if not isinstance(entry, dict):
            print(f"Warning: Item at index {entry_index} in target data is not a dictionary. Skipping.")
            corrected_data_list.append(entry)
            continue

        new_entry = json.loads(json.dumps(entry))

        videos = new_entry.get('videos')
        ratings = new_entry.get('rating')
        file_sizes = new_entry.get('file_size')

        if not (isinstance(videos, list) and 
                isinstance(ratings, list) and 
                isinstance(file_sizes, list) and
                len(videos) == len(ratings) == len(file_sizes)):
            print(f"Warning: Skipping entry at index {entry_index} due to malformed or mismatched 'videos', 'rating', or 'file_size' lists.")
            corrected_data_list.append(entry)
            continue
        
        print(f"\nProcessing competition entry {entry_index + 1} with videos: {videos}")
        modifications_in_entry = 0
        for i, current_size_in_competition in enumerate(file_sizes):
            if current_size_in_competition in master_lookup_by_size:
                correct_video_name_from_master = master_lookup_by_size[current_size_in_competition]
                
                if correct_video_name_from_master in master_db_data:
                    master_video_details = master_db_data[correct_video_name_from_master]
                    correct_rating_from_master = master_video_details.get('rating')
                    
                    if videos[i] != correct_video_name_from_master:
                        print(f"  Index {i}: Video name for size {current_size_in_competition} corrected: '{videos[i]}' -> '{correct_video_name_from_master}'")
                        new_entry['videos'][i] = correct_video_name_from_master
                        modifications_in_entry += 1
                    
                    if correct_rating_from_master is not None and ratings[i] != correct_rating_from_master:
                        print(f"  Index {i}: Rating for video '{correct_video_name_from_master}' (size {current_size_in_competition}) corrected: {ratings[i]} -> {correct_rating_from_master}")
                        new_entry['rating'][i] = correct_rating_from_master
                        modifications_in_entry += 1
                    elif correct_rating_from_master is None:
                        print(f"  Index {i}: Video '{correct_video_name_from_master}' in master DB has no rating. Rating {ratings[i]} for size {current_size_in_competition} in competition file remains unchanged.")
                else:
                    print(f"  Internal Warning: Video name '{correct_video_name_from_master}' (looked up by size {current_size_in_competition}) not found in master_db_data. Skipping corrections for this item.")
            else:
                # Size not found in master database, pick a random video from TikTok database
                if tiktok_video_list:
                    random_index = random.randint(0, len(tiktok_video_list) - 1)
                    random_video_details = tiktok_video_list[random_index]
                    random_video_name = tiktok_names[random_index]
                    random_size = random_video_details.get('file_size', 0)
                    random_rating = random_video_details.get('rating', 1000)

                    print(f"  Index {i}: Original size {current_size_in_competition} (video '{videos[i]}') NOT found in master DB.")
                    print(f"    Replacing with random video from TikTok DB: '{random_video_name}' (Size: {random_size}, Rating: {random_rating})")
                    
                    new_entry['videos'][i] = random_video_name
                    new_entry['rating'][i] = random_rating
                    new_entry['file_size'][i] = random_size
                    modifications_in_entry += 1
                else:
                    print(f"  Index {i}: File size {current_size_in_competition} (video '{videos[i]}') not found in master database lookup, AND no random videos available. No correction possible.")
        
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

    corrected_list = compare_and_correct_data(master_data, target_data_list)

    if corrected_list:
        output_filename_base = sanitize_filename(os.path.splitext(os.path.basename(target_file_path))[0])
        output_file_path = f"corrected_competitions_{output_filename_base}_{random.randint(1000,9999)}.json"
        save_json_file(corrected_list, output_file_path)
    elif not target_data_list:
        print("The target competition file was empty. Nothing to correct or save.")
    else:
        print("No data was processed or the correction resulted in an empty list. Output file not saved.")

# --- Function 4: Compare Sizes ---
def function_compare_sizes():
    """
    Function to compare file sizes between base folder and secondary folders.
    """
    print("\n--- Function: Compare Sizes ---")
    
    # Ask for base folder
    use_default_base = input(f"Is the base folder {DEFAULT_BASE_FOLDER}? (y/n): ").strip().lower()
    if use_default_base == 'y':
        base_folder = DEFAULT_BASE_FOLDER
    else:
        base_folder = input("Enter the base folder path: ").strip()
    
    if not os.path.exists(base_folder):
        print(f"Error: Base folder '{base_folder}' does not exist.")
        return
    
    # Ask for secondary folders
    secondary_folders_input = input("Enter secondary folder paths separated by commas: ").strip()
    secondary_folders = [folder.strip() for folder in secondary_folders_input.split(',')]
    
    # Validate secondary folders
    valid_secondary_folders = []
    for folder in secondary_folders:
        if os.path.exists(folder):
            valid_secondary_folders.append(folder)
        else:
            print(f"Warning: Secondary folder '{folder}' does not exist. Skipping.")
    
    if not valid_secondary_folders:
        print("No valid secondary folders found.")
        return
    
    print(f"Base folder: {base_folder}")
    print(f"Secondary folders: {valid_secondary_folders}")
    
    # Get file sizes from base folder
    print("Scanning base folder...")
    base_sizes = get_file_sizes_in_folder(base_folder)
    
    # Get file sizes from secondary folders
    print("Scanning secondary folders...")
    secondary_sizes = {}
    for folder in valid_secondary_folders:
        secondary_sizes[folder] = get_file_sizes_in_folder(folder)
    
    # Find duplicates
    duplicates_found = {}
    for folder, sizes_dict in secondary_sizes.items():
        for size, file_paths in sizes_dict.items():
            if size in base_sizes:
                if size not in duplicates_found:
                    duplicates_found[size] = {
                        'base_files': base_sizes[size],
                        'secondary_files': {}
                    }
                duplicates_found[size]['secondary_files'][folder] = file_paths
    
    if not duplicates_found:
        print("No duplicate files found.")
        return
    
    print(f"\nFound {len(duplicates_found)} duplicate sizes:")
    for size, data in duplicates_found.items():
        print(f"Size {size}:")
        print(f"  Base folder files: {data['base_files']}")
        for folder, files in data['secondary_files'].items():
            print(f"  Secondary folder {folder}: {files}")
    
    # Ask what to do with duplicates
    print("\nWhat do you want to do with duplicates?")
    print("1. Delete duplicates from secondary folders")
    print("2. Move duplicates to", DUPLICATE_MOVE_FOLDER)
    
    while True:
        choice = input("Choose action (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Invalid choice. Please enter 1 or 2.")
    
    if choice == '1':
        # Delete duplicates
        for size, data in duplicates_found.items():
            for folder, files in data['secondary_files'].items():
                for file_path in files:
                    try:
                        os.remove(file_path)
                        print(f"Deleted: {file_path}")
                    except OSError as e:
                        print(f"Error deleting {file_path}: {e}")
    
    elif choice == '2':
        # Move duplicates
        if not os.path.exists(DUPLICATE_MOVE_FOLDER):
            try:
                os.makedirs(DUPLICATE_MOVE_FOLDER)
                print(f"Created directory: {DUPLICATE_MOVE_FOLDER}")
            except OSError as e:
                print(f"Error creating directory {DUPLICATE_MOVE_FOLDER}: {e}")
                return
        
        for size, data in duplicates_found.items():
            for folder, files in data['secondary_files'].items():
                for file_path in files:
                    try:
                        filename = os.path.basename(file_path)
                        destination = os.path.join(DUPLICATE_MOVE_FOLDER, filename)
                        
                        # Handle filename conflicts
                        counter = 1
                        base_name, ext = os.path.splitext(filename)
                        while os.path.exists(destination):
                            new_filename = f"{base_name}_{counter}{ext}"
                            destination = os.path.join(DUPLICATE_MOVE_FOLDER, new_filename)
                            counter += 1
                        
                        import shutil
                        shutil.move(file_path, destination)
                        print(f"Moved: {file_path} -> {destination}")
                    except Exception as e:
                        print(f"Error moving {file_path}: {e}")

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
        print("4. Compare Sizes")
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
            function_compare_sizes()
        elif choice == '5':
            print("Thank you for using the script. Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    print("Note: Ensure database file paths are correct and you have read permissions.")
    main()
