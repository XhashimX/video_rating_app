# C:/Users/Stark/Download/myhome/video_rating_app/utilities/tournaments_manager.py

import json
import os
import random

JSON_FOLDER = 'C:/Users/Stark/Download/myhome/video_rating_app/utilities'
TOUR_ARCHIVE_PATH = os.path.join(JSON_FOLDER, 'tournamentarchive.json')


def list_json_files():
    """Lists all .json files in the JSON_FOLDER."""
    print(f"Listing JSON files from: {JSON_FOLDER}")
    try:
        if not os.path.exists(JSON_FOLDER):
            print(f"Error: JSON folder not found at {JSON_FOLDER}")
            return []
        
        files = [f for f in os.listdir(JSON_FOLDER) if f.endswith('.json')]
        print(f"Found {len(files)} JSON files.")
        return sorted(files)
    except Exception as e:
        print(f"An error occurred while listing JSON files: {e}")
        return []

def load_tournament_data(filename):
    """Loads data from a specific tournament JSON file."""
    print(f"Loading data from file: {filename}")
    file_path = os.path.join(JSON_FOLDER, filename)
    
    if '..' in filename or filename.startswith('/'):
         print(f"Security warning: Invalid filename '{filename}' blocked.")
         return None

    abs_file_path = os.path.abspath(file_path)
    abs_json_folder = os.path.abspath(JSON_FOLDER)
    if not abs_file_path.startswith(abs_json_folder):
         print(f"Security warning: Attempted to access file outside JSON folder: {abs_file_path}")
         return None

    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"Warning: File is empty: {file_path}")
                return []

            data = json.loads(content)
            print(f"Successfully loaded data from {filename}")
            return data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filename}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading {filename}: {e}")
        return None


def save_tournament_data(filename, data):
    """Saves data to a specific tournament JSON file."""
    print(f"Attempting to save data to file: {filename}")
    file_path = os.path.join(JSON_FOLDER, filename)
    
    if '..' in filename or filename.startswith('/'):
         print(f"Security warning: Invalid filename '{filename}' blocked for saving.")
         return False

    abs_file_path = os.path.abspath(file_path)
    abs_json_folder = os.path.abspath(JSON_FOLDER)
    if not abs_file_path.startswith(abs_json_folder):
         print(f"Security warning: Attempted to save file outside JSON folder: {abs_file_path}")
         return False

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved data to {filename}")
        return True
    except Exception as e:
        print(f"An error occurred while saving {filename}: {e}")
        return False

def delete_competitions(filename, competition_indices):
    """Deletes competitions by their 0-based indices from a file."""
    print(f"Attempting to delete competitions {competition_indices} from {filename}")
    data = load_tournament_data(filename)
    if data is None:
        print("Failed to load data for deletion.")
        return False, "Failed to load tournament data."

    if not isinstance(data, list):
         print("Tournament data is not a list, cannot delete competitions.")
         return False, "Tournament data is not in the expected list format."

    sorted_indices = sorted(competition_indices, reverse=True)
    print(f"Sorted indices for deletion: {sorted_indices}")

    deleted_count = 0
    try:
        for index in sorted_indices:
            if 0 <= index < len(data):
                removed_item = data.pop(index)
                deleted_count += 1
                videos_display = removed_item.get('videos', ['N/A'])[:2]
                print(f"Deleted competition at index {index}: {videos_display}...")
            else:
                print(f"Warning: Index {index} is out of range for deletion.")

        if deleted_count > 0:
            if save_tournament_data(filename, data):
                print(f"Deleted {deleted_count} competitions and saved file.")
                return True, f"Successfully deleted {deleted_count} competitions."
            else:
                print("Failed to save data after deletion.")
                return False, "Successfully deleted competitions in memory, but failed to save file."
        else:
            print("No valid indices provided, no competitions deleted.")
            return True, "No competitions deleted (no valid indices provided)."

    except Exception as e:
        print(f"An error occurred during deletion: {e}")
        return False, f"An error occurred during deletion: {e}"


def paste_competitions(filename, json_string, mode='append'):
    """Pastes competition data from a JSON string into the specified file."""
    print(f"Attempting to paste competitions to {filename} in mode '{mode}'")
    if mode not in ['append', 'replace']:
        print(f"Error: Invalid paste mode '{mode}'")
        return False, "Invalid paste mode specified."

    try:
        json_string = json_string.strip()
        if not json_string:
            return False, "Empty JSON string provided."
            
        pasted_data = json.loads(json_string)
        print("Successfully parsed JSON string.")

        if not isinstance(pasted_data, list):
            if isinstance(pasted_data, dict):
                pasted_data = [pasted_data]
                print("Pasted data was a single object, wrapped in a list.")
            else:
                print("Pasted data is not a list or dict.")
                return False, "Pasted data is not a list of competitions or a single competition object."

        current_data = []
        if mode == 'append':
            current_data = load_tournament_data(filename)
            if current_data is None:
                print(f"Warning: Could not load existing data from {filename} for append, starting with empty data.")
                current_data = []
            elif not isinstance(current_data, list):
                 print(f"Warning: Existing data in {filename} is not a list. Cannot append. Replacing instead.")
                 current_data = []

        if mode == 'replace':
            final_data = pasted_data
            print("Replacing existing data with pasted data.")
        else:
            final_data = current_data + pasted_data
            print(f"Appended {len(pasted_data)} competitions. Total now: {len(final_data)}")

        if save_tournament_data(filename, final_data):
            return True, f"Successfully pasted {len(pasted_data)} competitions to {filename}."
        else:
            return False, f"Successfully parsed pasted data, but failed to save file {filename}."

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in pasted data: {e}")
        return False, "Invalid JSON format in pasted data."
    except Exception as e:
        print(f"An unexpected error occurred during pasting: {e}")
        return False, f"An error occurred during pasting: {e}"


def swap_competitors(filename, comp_index1, competitor_index1, comp_index2, competitor_index2):
    """Swaps competitors between two different competitions."""
    print(f"Attempting to swap competitor {competitor_index1} in comp {comp_index1} with competitor {competitor_index2} in comp {comp_index2} in file {filename}")

    if comp_index1 == comp_index2:
        print("Cannot swap competitors within the same competition using this function.")
        return False, "Cannot swap competitors within the same competition."

    data = load_tournament_data(filename)
    if data is None:
        print("Failed to load data for swap.")
        return False, "Failed to load tournament data."

    if not isinstance(data, list):
         print("Tournament data is not a list, cannot swap competitors.")
         return False, "Tournament data is not in the expected list format."

    if not (0 <= comp_index1 < len(data)) or not (0 <= comp_index2 < len(data)):
        print(f"Competition index out of bounds: {comp_index1} or {comp_index2}. File has {len(data)} competitions.")
        return False, "One or both competition indices are out of bounds."

    comp1 = data[comp_index1]
    comp2 = data[comp_index2]

    if not isinstance(comp1.get('videos'), list) or not isinstance(comp2.get('videos'), list):
         print(f"Competitions {comp_index1} or {comp_index2} do not have a 'videos' list.")
         return False, f"Competitions {comp_index1} or {comp_index2} are missing the 'videos' list."

    len1 = len(comp1.get('videos', []))
    len2 = len(comp2.get('videos', []))

    if not (0 <= competitor_index1 < len1) or not (0 <= competitor_index2 < len2):
        print(f"Competitor index out of bounds: {competitor_index1} (comp {comp_index1}, size {len1}) or {competitor_index2} (comp {comp_index2}, size {len2}).")
        return False, "One or both competitor indices are out of bounds for their respective competitions."

    required_keys = ['videos', 'rating', 'file_size']
    for key in required_keys:
        if key not in comp1 or not isinstance(comp1[key], list) or len(comp1[key]) != len1:
             print(f"Competition {comp_index1} is missing or has invalid list for key '{key}'")
             return False, f"Competition {comp_index1} data is malformed (missing or invalid '{key}' list)."
        if key not in comp2 or not isinstance(comp2[key], list) or len(comp2[key]) != len2:
             print(f"Competition {comp_index2} is missing or has invalid list for key '{key}'")
             return False, f"Competition {comp_index2} data is malformed (missing or invalid '{key}' list)."

    try:
        for key in required_keys:
            val1 = comp1[key][competitor_index1]
            val2 = comp2[key][competitor_index2]

            comp1[key][competitor_index1] = val2
            comp2[key][competitor_index2] = val1
            print(f"Swapped '{key}': {val1} <-> {val2}")

        if save_tournament_data(filename, data):
            print("Successfully swapped competitors and saved file.")
            return True, "Competitors swapped successfully."
        else:
            print("Successfully swapped competitors in memory, but failed to save file.")
            return False, "Competitors swapped successfully in memory, but failed to save file."

    except Exception as e:
        print(f"An error occurred during swap: {e}")
        return False, f"An error occurred during swap: {e}"

def format_json_pretty(data):
    """Formats a Python object into a pretty-printed JSON string."""
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error formatting JSON: {e}")
        return str(data)

def load_tournament_archive():
    """Loads the tournament archive JSON file."""
    archive = {}
    if os.path.exists(TOUR_ARCHIVE_PATH):
        try:
            with open(TOUR_ARCHIVE_PATH, 'r', encoding='utf-8') as f:
                archive = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            archive = {}
        except Exception as e:
            print(f"Error loading tournament archive: {e}")
            archive = {}
    return archive

def save_tournament_archive(archive):
    """Saves the tournament archive to its JSON file."""
    try:
        with open(TOUR_ARCHIVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(archive, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving tournament archive: {e}")

def remove_from_archive(filename):
     """Removes an entry from the tournament archive based on JSON filename."""
     archive_key = os.path.splitext(filename)[0]
     archive = load_tournament_archive()
     if archive_key in archive:
          del archive[archive_key]
          save_tournament_archive(archive)
          print(f"Removed '{archive_key}' from tournament archive.")


if __name__ == '__main__':
    print("Listing JSON files:")
    files = list_json_files()
    print(files)

    if files:
        test_file = files[0]
        print(f"\nLoading data from {test_file}:")
        data = load_tournament_data(test_file)
        if data is not None:
            print(f"Loaded {len(data)} competitions.")
        else:
            print("Could not load data from the first file.")
