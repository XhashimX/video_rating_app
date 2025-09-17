import json


def process_json_files(file_entries):
    """
    Extracts a specified number of entries from each provided JSON file and combines them into a new JSON file.
    The extracted entries remain in the original files.

    Args:
        file_entries (dict): A dictionary where keys are JSON file paths and values are the number of entries to extract.
    """
    combined_data = {}

    for filename, n_entries in file_entries.items():
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                print(f"Error: {filename} does not contain a JSON object.")
                continue
        except FileNotFoundError:
            print(f"Error: File {filename} not found.")
            continue
        except json.JSONDecodeError:
            print(f"Error: {filename} contains invalid JSON.")
            continue

        extracted = dict(list(data.items())[:n_entries])
        combined_data.update(extracted)

        print(f"Extracted {len(extracted)} entries from {filename}.")

    try:
        with open("combined_data.json", 'w') as outfile:
            json.dump(combined_data, outfile, indent=4)
    except Exception as e:
        print(f"Error writing combined_data.json: {e}")
        return

    print("Extraction successful. Combined data saved to 'combined_data.json'.")


if __name__ == '__main__':
    file_entries = {}

    file_names_input = input("Enter JSON file names separated by commas: ")
    file_names = [name.strip()
                  for name in file_names_input.split(",") if name.strip()]

    if not file_names:
        print("No file names provided.")
    else:
        for filename in file_names:
            while True:
                try:
                    n_entries = int(
                        input(
                            f"Enter the number of entries to extract from {filename}: "))
                    if n_entries < 0:
                        print("Please enter a non-negative integer.")
                        continue
                    file_entries[filename] = n_entries
                    break
                except ValueError:
                    print("Invalid input: Please enter an integer.")
        process_json_files(file_entries)
