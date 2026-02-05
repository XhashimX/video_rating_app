import os
import sys
import json
import random
import re
import questionary  # Library for arrow-key menus
from pathlib import Path

# START: CONFIGURATION & CONSTANTS
# The specific path mentioned in your request for saving files
SAVE_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities"
# END: CONFIGURATION

def clear_screen():
    """Clears the console screen for a cleaner UI."""
    os.system('cls' if os.name == 'nt' else 'clear')

def parse_dragged_paths(raw_input):
    """
    Parses a string containing file paths (e.g., from drag & drop).
    Handles paths wrapped in quotes and space-separated paths.
    """
    pattern = r'"([^"]+)"|(\S+)'
    matches = re.findall(pattern, raw_input)
    
    paths = []
    for match in matches:
        p = match[0] if match[0] else match[1]
        if p:
            paths.append(p)
    return paths

def get_file_size_exact(file_path):
    """Returns the exact file size in bytes."""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

# --- SHARED FUNCTION: GENERATE & SAVE JSON ---
def generate_and_save_competition(file_data_list):
    """
    Takes a list of dicts: [{'name': 'file.ext', 'size': 12345}, ...]
    Generates the competition JSON and handles the saving process.
    """
    if not file_data_list:
        print("No data to process.")
        return

    json_output = []
    
    # Process items in pairs of 2
    for i in range(0, len(file_data_list), 2):
        if i + 1 >= len(file_data_list):
            break
            
        item1 = file_data_list[i]
        item2 = file_data_list[i+1]
        
        rating1 = random.uniform(1000.0, 3000.0)
        rating2 = random.uniform(1000.0, 3000.0)
        
        match_obj = {
            "videos": [item1['name'], item2['name']],
            "rating": [rating1, rating2],
            "file_size": [item1['size'], item2['size']],
            "mode": 1,
            "num_videos": 2,
            "ranking_type": "winner_only",
            "competition_type": "balanced_random"
        }
        json_output.append(match_obj)

    final_json_str = json.dumps(json_output, indent=4)
    print("\n" + final_json_str + "\n")
    
    save_choice = questionary.confirm("Do you want to save this to a file?").ask()
    
    if save_choice:
        suffix_choice = questionary.select(
            "Choose filename suffix:",
            choices=["tik", "pic", "Dip"]
        ).ask()
        
        final_suffix = suffix_choice
        if suffix_choice == "Dip":
            final_suffix = "Dib"
            
        random_digits = random.randint(1000, 9999)
        filename = f"topcut_elo_videos_{final_suffix}_{random_digits}.json"
        
        if not os.path.exists(SAVE_DIR):
            try:
                os.makedirs(SAVE_DIR)
            except OSError as e:
                print(f"Error creating directory: {e}")
                input("Press Enter...")
                return

        full_save_path = os.path.join(SAVE_DIR, filename)
        
        try:
            with open(full_save_path, 'w', encoding='utf-8') as f:
                f.write(final_json_str)
            print(f"Successfully saved to: {full_save_path}")
        except Exception as e:
            print(f"Error saving file: {e}")

# --- FEATURE 1: EXTRACT FILE SIZES ---
def feature_extract_sizes(working_dir):
    print("\n--- Extract File Sizes ---")
    
    choice = questionary.select(
        "Choose extraction source:",
        choices=[
            "From all files in the Working Directory",
            "Drag & Drop files (or paste paths)"
        ]
    ).ask()
    
    # List to store dictionaries: {'name': 'filename', 'size': 123}
    extracted_data = []
    
    if choice == "From all files in the Working Directory":
        if not os.path.isdir(working_dir):
            print(f"Error: The directory {working_dir} does not exist.")
            return
        
        files = [f for f in os.listdir(working_dir) if os.path.isfile(os.path.join(working_dir, f))]
        for f in files:
            full_path = os.path.join(working_dir, f)
            size = get_file_size_exact(full_path)
            extracted_data.append({'name': f, 'size': size})
            
    else: # Drag & Drop
        print("\nPlease drag and drop your files here (or paste paths) and press Enter:")
        user_input = input("> ")
        paths = parse_dragged_paths(user_input)
        
        for p in paths:
            p = p.strip().strip("'").strip('"') 
            if os.path.exists(p) and os.path.isfile(p):
                size = get_file_size_exact(p)
                name = os.path.basename(p)
                extracted_data.append({'name': name, 'size': size})
    
    print("\n--- Output (Exact Sizes) ---")
    if not extracted_data:
        print("No files found.")
    else:
        for item in extracted_data:
            print(f"{item['size']}  ({item['name']})")
    
    # New logic: Ask to create competition immediately
    if extracted_data:
        print("\n-------------------------")
        create_now = questionary.confirm("Do you want to create a competition from these files?").ask()
        if create_now:
            generate_and_save_competition(extracted_data)
        else:
            input("\nPress Enter to return to menu...")
    else:
        input("\nPress Enter to return to menu...")

# --- FEATURE 2: COMPETITION GENERATOR ---
def feature_create_competition():
    print("\n--- Create Competition JSON ---")
    
    print("Drag & Drop your files here (to use Real Names & Sizes) OR paste file sizes:")
    print("(Note: If pasting raw numbers, random names will be generated)")
    user_input = input("> ")
    
    paths = parse_dragged_paths(user_input)
    file_data_list = []
    
    # Check if input looks like paths that actually exist
    is_paths = any(os.path.exists(p) for p in paths) if paths else False

    if is_paths:
        # User provided real files -> Use Real Names
        for p in paths:
            if os.path.exists(p) and os.path.isfile(p):
                size = get_file_size_exact(p)
                name = os.path.basename(p)
                file_data_list.append({'name': name, 'size': size})
    else:
        # User provided raw numbers -> Use Random Names
        clean_input = re.sub(r'[^\d\s]', '', user_input) 
        tokens = clean_input.split()
        for t in tokens:
            if t.isdigit():
                size = int(t)
                # Generate random name because we don't have a real file
                rand_name = f"{random.randint(1000, 9999)}_video_{random.randint(100000, 999999)}.mp4"
                file_data_list.append({'name': rand_name, 'size': size})
    
    if not file_data_list:
        print("No valid input found.")
        input("Press Enter...")
        return

    # Use the shared function
    generate_and_save_competition(file_data_list)
    
    input("\nPress Enter to return to menu...")

# --- FEATURE 3: REMOVE DUPLICATES ---
def feature_remove_duplicates(working_dir):
    print("\n--- Remove Duplicates (Smart Cleanup) ---")
    print(f"Scanning directory: {working_dir}")
    
    if not os.path.isdir(working_dir):
        print("Invalid directory.")
        return

    grouped_files = {}
    pattern = re.compile(r'^(.*?)(\s\(\d+\))?(\.[^.]*)?$')
    
    files_in_dir = [f for f in os.listdir(working_dir) if os.path.isfile(os.path.join(working_dir, f))]
    
    for filename in files_in_dir:
        match = pattern.match(filename)
        if match:
            base_name = match.group(1)
            number_part = match.group(2)
            extension = match.group(3) if match.group(3) else ""
            
            priority = 0
            if number_part:
                num_str = re.search(r'\d+', number_part).group()
                priority = int(num_str)
            
            full_path = os.path.join(working_dir, filename)
            file_size = get_file_size_exact(full_path)
            
            unique_key = (base_name, extension, file_size)
            
            if unique_key not in grouped_files:
                grouped_files[unique_key] = []
            
            grouped_files[unique_key].append({
                "priority": priority,
                "path": full_path,
                "name": filename
            })

    files_to_delete = []
    
    print("\n--- Deletion Plan ---")
    for key, file_list in grouped_files.items():
        if len(file_list) > 1:
            file_list.sort(key=lambda x: x["priority"])
            
            keeper = file_list[0]
            duplicates_to_remove = file_list[1:]
            
            print(f"\nGroup: {keeper['name']} (Size: {key[2]})")
            print(f"  [KEEPING]: {keeper['name']}")
            
            for dup in duplicates_to_remove:
                print(f"  [TO DELETE]: {dup['name']}")
                files_to_delete.append(dup['path'])

    if not files_to_delete:
        print("\nNo duplicates found matching the criteria.")
        input("\nPress Enter to return to menu...")
        return
        
    print("\n-------------------------")
    
    proceed = questionary.confirm(f"Found {len(files_to_delete)} duplicate(s) to delete. Are you sure you want to proceed?").ask()
    
    if proceed:
        deleted_count = 0
        print("\nDeleting files...")
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                print(f"  Deleted: {os.path.basename(file_path)}")
                deleted_count += 1
            except Exception as e:
                print(f"  FAILED to delete {os.path.basename(file_path)}: {e}")
        print(f"\nOperation complete. Deleted {deleted_count} files.")
    else:
        print("\nDeletion cancelled by user.")
        
    input("\nPress Enter to return to menu...")

# --- MAIN LOOP ---
def main():
    clear_screen()
    print("Welcome to the Multi-Tool Script.")

    try:
        downloads_path = str(Path.home() / "Downloads")
    except Exception:
        downloads_path = "Could not find Downloads folder"

    default_paths = [
        ("Default Downloads Folder", downloads_path),
        ("ELO TIK Main", r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK"),
        ("ELO TIK A1000 tik", r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik"),
        ("ELO TIK A1000 pic", r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo pic"),
        ("ELO TIK Dip", r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\Dip"),
    ]
    
    path_choices = [
        questionary.Choice(title=f"{name}: {path}", value=path)
        for name, path in default_paths
    ]
    path_choices.append(questionary.Separator())
    path_choices.append(questionary.Choice(title="Enter a custom path...", value="custom"))

    chosen_path = questionary.select(
        "Please select a working directory (use Arrow Keys):",
        choices=path_choices
    ).ask()

    if chosen_path == "custom":
        target_dir = input("Please enter the custom directory path: ").strip()
        if target_dir.startswith('"') and target_dir.endswith('"'):
            target_dir = target_dir[1:-1]
    else:
        target_dir = chosen_path

    if not target_dir or not os.path.isdir(target_dir):
        print(f"Error: The selected path '{target_dir}' is not a valid directory. Exiting.")
        sys.exit()

    while True:
        clear_screen()
        print(f"Working Directory: {target_dir}")
        
        answer = questionary.select(
            "Select an action (use Arrow Keys):",
            choices=[
                "1. Extract File Sizes",
                "2. Create Competition (JSON)",
                "3. Remove Duplicates",
                "Exit"
            ]
        ).ask()
        
        if answer == "1. Extract File Sizes":
            feature_extract_sizes(target_dir)
        elif answer == "2. Create Competition (JSON)":
            feature_create_competition()
        elif answer == "3. Remove Duplicates":
            feature_remove_duplicates(target_dir)
        elif answer == "Exit":
            print("Goodbye!")
            sys.exit()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit()