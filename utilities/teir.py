import json
import os
import sys
import random

# Define the input and output file paths
# Ensure these paths are correct for your environment
ARCHIVE_FILE = '/storage/emulated/0/myhome/video_rating_app/utilities/tournamentarchive.json'
PROCESSED_ITEMS_FILE = '/storage/emulated/0/myhome/video_rating_app/utilities/processed_items.json' # Output file for sorted item data (now includes videos/images)
TOP_TOURNAMENT_FILE = '/storage/emulated/0/myhome/video_rating_app/utilities/top.json' # Output file for the weight range tournament

# Define common video and image file extensions
VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']

# Define the new standard weighting rules based on percentage of base weight
STANDARD_WEIGHT_RULES = {
    "top1": {"base_percent": 0.50, "bonus_percent": 0.10}, # 50% base + 10% bonus = 60% of base weight
    "top2": {"base_percent": 0.30, "bonus_percent": 0.05}, # 30% base + 5% bonus = 35% of base weight
    "top3": {"base_percent": 0.10, "bonus_percent": 0.00}, # 10% base + 0% bonus = 10% of base weight
    "top4": {"base_percent": 0.10, "bonus_percent": 0.00}  # 10% base + 0% bonus = 10% of base weight
}

# Define the special weighting rules for tournaments with only 2 ranked items
TWO_ITEM_WEIGHT_RULES = {
    "top1": 0.60, # 60% of base weight
    "top2": 0.40  # 40% of base weight
}

# List of relevant top ranks we process
RELEVANT_RANKS = ["top1", "top2", "top3", "top4"]

def load_existing_processed_items(file_path):
    """Loads existing processed item data from the JSON file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"Existing processed item data loaded from {file_path}.")
            # Convert list to dict for easier lookup by file_size
            return {item['file_size']: item for item in data if 'file_size' in item}
        except (json.JSONDecodeError, Exception) as e:
            print(f"Warning: Could not load or decode existing processed items from {file_path}: {e}. Starting fresh processing.")
            return {}
    else:
        print(f"No existing processed item data found at {file_path}.")
        return {}

def process_tournament_archive(input_path, output_path):
    """
    Reads the tournament archive, processes item data, calculates weights based on new rules,
    handles duplicates, merges with existing data, and saves the sorted combined data.
    """
    # 1. Load existing processed data
    existing_item_data_by_size = load_existing_processed_items(output_path)

    # 2. Process the tournament archive
    print(f"Attempting to read archive from: {input_path}")
    if not os.path.exists(input_path):
        print(f"Error: Archive file not found at {input_path}")
        # If archive is not found, just save back the existing data if any
        if existing_item_data_by_size:
            print("Saving back the existing processed data as archive was not found.")
            processed_items_list = list(existing_item_data_by_size.values())
            processed_items_list.sort(key=lambda x: x.get('total_weight', 0), reverse=True)
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_items_list, f, indent=4, ensure_ascii=False)
                print(f"Existing processed data saved successfully to: {output_path}")
            except Exception as e:
                 print(f"Error occurred while writing existing processed data to {output_path}: {e}")
            return processed_items_list
        return None

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            archive_data = json.load(f)
        print("Archive file loaded successfully.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_path}. Check file format.")
        # If archive is invalid, save back existing data if any
        if existing_item_data_by_size:
            print("Saving back the existing processed data due to archive reading error.")
            processed_items_list = list(existing_item_data_by_size.values())
            processed_items_list.sort(key=lambda x: x.get('total_weight', 0), reverse=True)
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_items_list, f, indent=4, ensure_ascii=False)
                print(f"Existing processed data saved successfully to: {output_path}")
            except Exception as e:
                 print(f"Error occurred while writing existing processed data to {output_path}: {e}")
            return processed_items_list
        return None # Can't proceed without valid archive or existing data

    # Dictionary to store data for items found in the archive during this run
    archive_item_data_by_size = {}

    print("Processing tournament data from archive...")
    for tournament_key, tournament_data in archive_data.items():
        try:
            # Extract base weight from the tournament key
            base_weight_str = tournament_key.split('.', 1)[0]
            base_weight = float(base_weight_str)
        except (ValueError, IndexError):
            print(f"Warning: Could not parse base weight from key '{tournament_key}'. Skipping tournament.")
            continue

        # Determine if it's the special 2-item tournament case
        present_relevant_ranks = [rank for rank in RELEVANT_RANKS if rank in tournament_data]
        is_two_item_tournament = (len(present_relevant_ranks) == 2 and
                                   "top1" in present_relevant_ranks and
                                   "top2" in present_relevant_ranks and
                                   "top3" not in present_relevant_ranks and
                                   "top4" not in present_relevant_ranks)


        # Process top ranked items
        for rank_key in RELEVANT_RANKS:
            if rank_key in tournament_data:
                item_info = tournament_data[rank_key]
                try:
                    item_name = item_info.get("video", item_info.get("image")) # Handle 'video' or 'image' key
                    file_size = item_info.get("file_size")
                    latest_rating = item_info.get("new_rating", item_info.get("old_rating", 0))

                    if item_name is None or file_size is None:
                         print(f"Warning: Missing item name or file size in {tournament_key} - {rank_key}. Skipping entry.")
                         continue

                    # Determine file extension
                    _, file_extension = os.path.splitext(item_name)
                    file_extension = file_extension.lower() # Convert to lowercase for comparison

                    # Calculate the weight based on the new rules
                    appearance_weight = 0
                    if is_two_item_tournament and rank_key in TWO_ITEM_WEIGHT_RULES:
                        appearance_weight = TWO_ITEM_WEIGHT_RULES[rank_key] * base_weight
                    elif rank_key in STANDARD_WEIGHT_RULES:
                        rule = STANDARD_WEIGHT_RULES[rank_key]
                        appearance_weight = (rule["base_percent"] + rule["bonus_percent"]) * base_weight
                    # else: weight remains 0 for unknown ranks

                    # Add or update data for this item's appearance in this archive run
                    if file_size not in archive_item_data_by_size:
                         archive_item_data_by_size[file_size] = {
                            "item_name": item_name, # Use the name from this appearance
                            "file_extension": file_extension, # Store the extension
                            "total_weight": appearance_weight,
                            "latest_rating": latest_rating, # Use the rating from this appearance
                            "file_size": file_size,
                            "_found_in_archive_run": True # Mark it as found in this run
                         }
                    else:
                        # Add weight for this appearance to the temporary archive data
                        archive_item_data_by_size[file_size]["total_weight"] += appearance_weight
                        # Optionally update name/rating/extension to the latest one encountered in the archive run
                        # archive_item_data_by_size[file_size]["item_name"] = item_name
                        # archive_item_data_by_size[file_size]["latest_rating"] = latest_rating
                        # archive_item_data_by_size[file_size]["file_extension"] = file_extension


                except Exception as e:
                    print(f"Warning: Error processing item data for {tournament_key} - {rank_key}: {e}. Skipping entry.")
                    continue

    # 3. Merge archive data with existing data
    combined_item_data_by_size = {}

    # Start with all items found in the current archive processing run
    combined_item_data_by_size.update(archive_item_data_by_size)

    # Add items from the existing processed file that were *not* found in this archive run
    for file_size, item_data in existing_item_data_by_size.items():
        # Check if this item (by size) was found in the current archive processing
        # We use the '_found_in_archive_run' flag we added temporarily
        if file_size not in combined_item_data_by_size:
             # This item was in the existing file but not found in the archive this run
             # Assume it was manually added or from a previous archive not fully processed.
             # Add its existing data.
             combined_item_data_by_size[file_size] = item_data
             combined_item_data_by_size[file_size]['_found_in_archive_run'] = False # Mark as not found in this run

    # Remove the temporary flag before saving
    for item_data in combined_item_data_by_size.values():
        item_data.pop('_found_in_archive_run', None)


    # Convert the combined data into a list for sorting
    processed_items_list = list(combined_item_data_by_size.values())

    # Sort the list by total_weight in descending order
    processed_items_list.sort(key=lambda x: x.get('total_weight', 0), reverse=True)

    # Save the sorted combined data to the output file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_items_list, f, indent=4, ensure_ascii=False)
        print(f"Processed and merged item data saved successfully to: {output_path}")
        return processed_items_list
    except Exception as e:
        print(f"Error occurred while writing processed data to {output_path}: {e}")
        return processed_items_list


def get_integer_input(prompt):
    """Helper function to get valid integer input from the user."""
    while True:
        try:
            value = int(input(prompt))
            if value >= 0: # Allow 0 for number of participants or manual additions if needed
                 return value
            else:
                 print("Please enter a non-negative number.")
        except ValueError:
            print("Invalid input. Please enter an integer.")

def get_float_input(prompt):
    """Helper function to get valid float input from the user."""
    while True:
        try:
            value = float(input(prompt))
            if value >= 0: # Allow 0 for weight if needed
                 return value
            else:
                 print("Please enter a non-negative number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def filter_items_by_type(items_list, item_type):
    """Filters a list of items based on their file extension."""
    if item_type == 'video':
        allowed_extensions = VIDEO_EXTENSIONS
    elif item_type == 'image':
        allowed_extensions = IMAGE_EXTENSIONS
    else: # 'all' or unknown type
        return items_list

    return [item for item in items_list if item.get('file_extension') in allowed_extensions]


def create_new_tournament(items_list, num_participants, selection_method, output_file=None, item_type_filter='all'):
    """
    Creates a new tournament structure from a list of selected items.
    Assumes items_list already contains the items intended for the tournament.
    Includes filtering by item type.
    """
    if not items_list:
        print("Error: No item data available to create a tournament.")
        return None

    # Apply item type filter
    filtered_items_list = filter_items_by_type(items_list, item_type_filter)

    if not filtered_items_list:
        print(f"No {item_type_filter} items available to create a tournament after filtering.")
        return None


    # Ensure we don't ask for more participants than available in the provided filtered list
    if num_participants > len(filtered_items_list):
        print(f"Warning: Requested {num_participants} participants, but only {len(filtered_items_list)} {item_type_filter} items available. Using all available {item_type_filter} items.")
        num_participants = len(filtered_items_list)
        selected_items = filtered_items_list # Use all provided filtered items
    else:
         # If we are here, the selection logic (random, top, range+manual)
         # has already selected the 'num_participants' or fewer items from the *original* list.
         # We now need to select *from the filtered list*.

         # For manual selection, the filtering happens *before* this function
         if selection_method == 'manual' or selection_method == 'weight_range_and_manual':
             # Manual selection already provides the exact list
             selected_items = filtered_items_list # Use the list as provided (already filtered if needed)
             num_participants = len(selected_items) # Adjust num_participants if the manual list was smaller than expected

         else:
            # For automatic selection methods (random, top, etc.), select from the filtered list
            if selection_method == "top":
                selected_items = filtered_items_list[:num_participants]
            elif selection_method == "bottom":
                selected_items = filtered_items_list[-num_participants:]
            elif selection_method == "middle":
                list_length = len(filtered_items_list)
                start_index = max(0, (list_length - num_participants) // 2)
                selected_items = filtered_items_list[start_index : start_index + num_participants]
            elif selection_method == "random":
                 selected_items = random.sample(filtered_items_list, num_participants)
            else:
                 print(f"Error: Unknown selection method '{selection_method}'. Cannot create tournament.")
                 return None


    if not selected_items:
        print("No items selected for the tournament after filtering.")
        return None

    # Calculate the total weight of the selected items
    total_tournament_weight = sum(item.get('total_weight', 0) for item in selected_items)
    print(f"\nCreating a new tournament with {len(selected_items)} {item_type_filter} participants using '{selection_method}' selection.")
    print(f"Total accumulated weight of this tournament: {total_tournament_weight:.2f}")

    # Prepare the tournament structure - assuming 1v1 matches
    # Shuffle the selected items to randomize pairings
    random.shuffle(selected_items)

    tournament_structure = []
    num_matches = len(selected_items) // 2
    for i in range(num_matches):
        item1 = selected_items[i * 2]
        item2 = selected_items[i * 2 + 1]

        match = {
            "items": [item1.get("item_name", "X"), item2.get("item_name", "X")], # Use 'X' placeholder
            "rating": [item1.get("latest_rating", 0), item2.get("latest_rating", 0)], # Use 0 placeholder
            "file_size": [item1.get("file_size"), item2.get("file_size")], # File size is essential
            "mode": 1, # Assuming 1v1 mode
            "num_items": 2, # Changed from num_videos
            "ranking_type": "winner_only",
            "competition_type": selection_method # Indicate how participants were selected
        }
        tournament_structure.append(match)

    # Handle the case of an odd number of participants
    if len(selected_items) % 2 != 0:
        bye_item = selected_items[-1]
        print(f"Note: Item '{bye_item.get('item_name', 'X')}' (size: {bye_item.get('file_size')}) has a potential 'bye' as there's an odd number of participants.")


    # Save the structure if an output file path is provided
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                 json.dump(tournament_structure, f, indent=4, ensure_ascii=False)
            print(f"New tournament structure saved successfully to: {output_file}")
        except Exception as e:
            print(f"Error occurred while writing tournament structure to {output_file}: {e}")
    else:
        # Print to console if no output file specified
        print("\n--- New Tournament Structure ---")
        print(json.dumps(tournament_structure, indent=4, ensure_ascii=False))
        print("------------------------------")

    return tournament_structure


# --- Main execution ---
if __name__ == "__main__":
    # Part 1: Process the archive and save the sorted combined item list
    # This function now handles loading existing data and merging
    processed_items_list = process_tournament_archive(ARCHIVE_FILE, PROCESSED_ITEMS_FILE)

    if processed_items_list is None:
        # Processing failed and no existing data was salvageable
        print("Script cannot proceed without valid item data. Exiting.")
        sys.exit(1)

    # Filter items for the tournament part - only include those with weight > 0
    # Unless it's the manual creation mode
    items_with_weight = [item for item in processed_items_list if item.get("total_weight", 0) > 0]

    print(f"\nFound {len(processed_items_list)} unique items in total (by file size).")
    print(f"Found {len(items_with_weight)} items with a total weight > 0 (eligible for most tournament types).")

    # Part 2: Ask about creating a new tournament
    while True:
        create_tournament_input = input("\nDo you want to create a new tournament structure? (yes/no): ").lower()
        if create_tournament_input in ["yes", "y", "no", "n"]:
            break
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

    if create_tournament_input in ["yes", "y"]:

        # --- Ask user to filter by file type ---
        item_type_filter = 'all' # Default
        while True:
             type_choice = input("Filter tournament participants by type? (videos/images/all): ").lower()
             if type_choice in ['videos', 'images', 'all']:
                  # ******* التعديل هنا *******
                  if type_choice == 'videos':
                      item_type_filter = 'video'
                  elif type_choice == 'images':
                      item_type_filter = 'image'
                  else:
                      item_type_filter = 'all'
                  # *************************
                  break
             else:
                 print("Invalid choice. Please enter 'videos', 'images', or 'all'.")

        # Apply the initial filter based on user choice before showing selection methods
        if item_type_filter != 'all':
            # If filtering, work with the filtered list for subsequent selection methods
            filtered_items_with_weight = filter_items_by_type(items_with_weight, item_type_filter)
            all_available_items_for_selection = filter_items_by_type(processed_items_list, item_type_filter)
            print(f"Filtered to {len(filtered_items_with_weight)} {item_type_filter} items with weight > 0.")
            print(f"Filtered to {len(all_available_items_for_selection)} total unique {item_type_filter} items.")
        else:
             filtered_items_with_weight = items_with_weight
             all_available_items_for_selection = processed_items_list


        if not all_available_items_for_selection:
             print(f"No {item_type_filter} items found with any weight. Cannot create a tournament.")
             sys.exit(1)


        print("\nChoose tournament selection method:")
        print("1: Randomly select items from the filtered list (weight > 0)")
        print("2: Select the highest weighted items (Top N, weight > 0)")
        print("3: Select the lowest weighted items (Bottom N, weight > 0)")
        print("4: Select items from the middle of the list (Middle N, weight > 0)")
        print("5: Manually add items by size and custom weight (creates tournament from scratch - Ignores filter)") # Manual can add anything
        print("6: Filter items by weight range + optional manual inclusion (Uses filter for range pool)")


        selection_methods = {
            "1": "random",
            "2": "top",
            "3": "bottom",
            "4": "middle",
            "5": "manual",
            "6": "weight_range_and_manual" # Renamed for clarity
        }

        selected_method = None
        while selected_method is None:
            method_choice = input("Enter your choice (1-6): ")
            selected_method = selection_methods.get(method_choice)
            if selected_method is None:
                print("Invalid choice. Please enter a number between 1 and 6.")
            # Add checks for methods that require items with weight > 0
            if selected_method in ["random", "top", "bottom", "middle"] and not filtered_items_with_weight:
                 print(f"Cannot use this method as no filtered {item_type_filter} items have a weight > 0.")
                 selected_method = None # Reset to ask again

        selected_items_for_tournament = [] # List that will hold the final selection of items

        if selected_method == "manual":
            # Method 5: Manually add items - ignores type filter as user provides size/weight
            print("\n--- Manual Tournament Creation ---")
            num_manual_items = get_integer_input("Enter the total number of items to add manually: ")
            for i in range(num_manual_items):
                print(f"--- Item {i + 1} ---")
                file_size = get_integer_input("Enter file size (integer): ")
                total_weight = get_float_input("Enter item weight (number): ")
                item_name = input("Enter item name (e.g., 'video.mp4' or 'image.jpg'): ")
                _, file_extension = os.path.splitext(item_name)
                file_extension = file_extension.lower()

                # Create an item dictionary with required structure keys
                selected_items_for_tournament.append({
                    "item_name": item_name,
                    "file_extension": file_extension,
                    "total_weight": total_weight,
                    "latest_rating": 0, # Placeholder rating
                    "file_size": file_size # File size is essential
                })
            num_participants = len(selected_items_for_tournament) # Participants are just the manual items
            # For manual selection, we pass the exact list to create_new_tournament
            # The internal filtering in create_new_tournament won't affect this manual list
            # as it's already finalized. We just pass the list and its size.
            create_new_tournament(selected_items_for_tournament, num_participants, selected_method, None, 'all') # Pass 'all' as filter is not relevant here

        elif selected_method == "weight_range_and_manual":
            # Method 6: Filter by weight range + optional manual inclusion
            print("\n--- Tournament by Weight Range ---")
            # Use the already filtered list (if any) for the range part
            items_for_range_selection = filtered_items_with_weight

            if not items_for_range_selection:
                print(f"No filtered {item_type_filter} items with weight > 0 available for range selection.")
                # Check if manual addition is still possible
                add_manual_only = input("No items in filtered list with weight > 0. Do you want to proceed with ONLY manual inclusion? (yes/no): ").lower()
                if add_manual_only in ["yes", "y"]:
                    # Redirect to manual creation logic
                    print("Proceeding with manual creation.")
                    selected_method = "manual" # Change method to manual
                    # Jump back to the manual creation block logic (a bit clunky, could refactor)
                    # For now, let's just ask for manual items here directly
                    print("\n--- Manual Inclusion Only ---")
                    num_manual_items = get_integer_input("Enter the total number of items to add manually: ")
                    for i in range(num_manual_items):
                        print(f"--- Item {i + 1} ---")
                        file_size = get_integer_input("Enter file size (integer): ")
                        total_weight = get_float_input("Enter item weight (number): ")
                        item_name = input("Enter item name (e.g., 'video.mp4' or 'image.jpg'): ")
                        _, file_extension = os.path.splitext(item_name)
                        file_extension = file_extension.lower()
                        selected_items_for_tournament.append({
                            "item_name": item_name,
                            "file_extension": file_extension,
                            "total_weight": total_weight,
                            "latest_rating": 0,
                            "file_size": file_size
                        })
                    num_participants = len(selected_items_for_tournament)
                    if selected_items_for_tournament:
                        # Pass 'all' as filter is ignored for manual, but structure expects it
                        create_new_tournament(selected_items_for_tournament, num_participants, "manual", None, 'all')
                    else:
                         print("No manual items added. No tournament created.")
                    sys.exit(0) # Exit after manual creation if range selection wasn't possible
                else:
                    print("Cannot create this type of tournament without items in range or manual inclusion.")
                    sys.exit(1) # Exit if neither is possible


            min_weight = get_float_input("Enter minimum weight: ")
            max_weight = get_float_input("Enter maximum weight: ")

            range_filtered_pool = [
                item for item in items_for_range_selection
                if min_weight <= item.get("total_weight", 0) <= max_weight
            ]

            print(f"Found {len(range_filtered_pool)} {item_type_filter} items in the weight range [{min_weight:.2f} - {max_weight:.2f}] with weight > 0.")

            manual_included_items = []
            add_manual_to_range = input("Do you want to manually include specific items from the *processed list* in this range tournament? (yes/no): ").lower()
            if add_manual_to_range in ["yes", "y"]:
                 # When manually including, we can pick *any* item from the *total* processed list,
                 # regardless of the initial video/image filter or weight > 0 requirement.
                 print(f"Manually adding from all {len(processed_items_list)} unique processed items.")
                 num_manual_add = get_integer_input("Enter the number of items to include manually: ")
                 manual_add_sizes = []
                 for i in range(num_manual_add):
                     size_input = get_integer_input(f"Enter file size for manual item {i+1} (must exist in processed list): ")
                     manual_add_sizes.append(size_input)

                 # Find these items in the overall processed_items_list
                 manual_sizes_set = set(manual_add_sizes)
                 items_to_add_by_size = {item['file_size']: item for item in processed_items_list if item['file_size'] in manual_sizes_set}

                 found_count = 0
                 for size in manual_add_sizes:
                     if size in items_to_add_by_size:
                          item_to_add = items_to_add_by_size[size]
                          manual_included_items.append(item_to_add)
                          found_count += 1
                          # IMPORTANT: Remove manually added items from the 'range_filtered_pool'
                          # so they are not selected randomly again.
                          # We must filter the range_filtered_pool list *before* selecting randomly.
                          range_filtered_pool = [item for item in range_filtered_pool if item['file_size'] != size]
                     else:
                          print(f"Warning: Item with size {size} not found in the processed list. It will not be included.")

                 print(f"Successfully found and included {found_count} manual items.")
                 print(f"{len(range_filtered_pool)} {item_type_filter} items remaining in the filtered range pool.")


            # Determine total participants needed and select from remaining pool
            max_possible_participants = len(manual_included_items) + len(range_filtered_pool)
            if max_possible_participants == 0:
                 print("No items available (manual + range pool) to create the tournament.")
                 sys.exit(1)

            num_participants = get_integer_input(f"Enter the total number of participants for the tournament (including manual, max {max_possible_participants}): ")

            if num_participants < len(manual_included_items):
                 print(f"Warning: Requested {num_participants} participants, but {len(manual_included_items)} items were manually included. Using only the manually included items.")
                 selected_items_for_tournament = manual_included_items
            else:
                 # Select additional items randomly from the remaining filtered pool
                 needed_from_pool = num_participants - len(manual_included_items)
                 needed_from_pool = min(needed_from_pool, len(range_filtered_pool)) # Don't select more than available

                 if needed_from_pool > 0:
                     randomly_selected_from_pool = random.sample(range_filtered_pool, needed_from_pool)
                     selected_items_for_tournament = manual_included_items + randomly_selected_from_pool
                 else:
                     selected_items_for_tournament = manual_included_items

                 print(f"Selected {len(selected_items_for_tournament)} total participants ({len(manual_included_items)} manual + {len(selected_items_for_tournament) - len(manual_included_items)} from pool).")

            # For method 6 (weight_range_and_manual), we will save to top.json
            output_tournament_file = TOP_TOURNAMENT_FILE

            if selected_items_for_tournament:
                 # Pass the list of selected items to the creation function
                 # Pass 'all' as the filter type to the creation function, as manual adds can be anything
                 # The filtering by video/image was done *before* this selection process,
                 # determining the pool of items available *for automatic selection*.
                 create_new_tournament(selected_items_for_tournament, len(selected_items_for_tournament), selected_method, output_tournament_file, 'all') # Pass 'all' here

            else:
                 print("No items were selected for the tournament based on your criteria.")


        else:
            # Methods 1-4: random, top, bottom, middle from the FILTERED list with weight > 0
            # The filtering by item_type_filter has already happened, resulting in filtered_items_with_weight
            if not filtered_items_with_weight:
                print(f"No filtered {item_type_filter} items with weight > 0 available. Cannot create this type of tournament.")
                sys.exit(1) # Or loop back to menu

            max_participants = len(filtered_items_with_weight)
            num_participants = get_integer_input(f"Enter the number of participants for the new tournament (max {max_participants}): ")
            if num_participants > max_participants:
                 print(f"Warning: Requested {num_participants} participants, but only {max_participants} available in filtered list with weight > 0. Using all available eligible items.")
                 num_participants = max_participants

            # Select items based on the chosen method from the filtered_items_with_weight list
            if selected_method == "top":
                selected_items_for_tournament = filtered_items_with_weight[:num_participants]
            elif selected_method == "bottom":
                selected_items_for_tournament = filtered_items_with_weight[-num_participants:]
            elif selected_method == "middle":
                list_length = len(filtered_items_with_weight)
                start_index = max(0, (list_length - num_participants) // 2)
                selected_items_for_tournament = filtered_items_with_weight[start_index : start_index + num_participants]
            elif selected_method == "random":
                 selected_items_for_tournament = random.sample(filtered_items_with_weight, num_participants)
            # num_participants is already set here

            # --- Create the tournament structure using the selected videos ---
            # For methods 1-4, we are working with the pre-filtered list.
            # The create_new_tournament function *will* re-filter based on item_type_filter
            # passed to it, which should match the filter already applied.
            if selected_items_for_tournament:
                 create_new_tournament(selected_items_for_tournament, len(selected_items_for_tournament), selected_method, None, item_type_filter)
            else:
                 print("No items were selected for the tournament based on your criteria.")


    print("\nScript finished.")