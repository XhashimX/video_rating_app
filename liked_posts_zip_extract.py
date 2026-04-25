
import os
import zipfile
import shutil
import tempfile
from PIL import Image

# --- PRE-REQUISITE ---
# This script requires the 'Pillow' library to check image dimensions.
# Before running, open your PC's Command Prompt (CMD) or PowerShell and type:
# pip install Pillow

# --- CONFIGURATION ---
# The path where your downloaded zip file is located.
ZIP_FILE_PATH = r"C:\Users\Stark\Downloads\Downloaded_Media.zip"

# File extensions to differentiate between images and videos for specific checks.
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}

def get_image_dimensions(filepath):
    """Helper function to get image dimensions (width, height)."""
    try:
        with Image.open(filepath) as img:
            return img.size
    except Exception:
        return (0, 0) # Return a default value if the image is corrupt or not an image.

def get_unique_filename(directory, filename):
    """Helper function to generate a new filename if it already exists (e.g., 'image_1.jpg')."""
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = f"{name}_{counter}{ext}"
    while os.path.exists(os.path.join(directory, new_filename)):
        counter += 1
        new_filename = f"{name}_{counter}{ext}"
    return new_filename

def build_archive_index(archive_user_folder):
    """
    Scans the existing user's archive folder and stores file data (name, size, dimensions)
    to speed up the comparison process later.
    """
    index = {}
    for filename in os.listdir(archive_user_folder):
        filepath = os.path.join(archive_user_folder, filename)
        if os.path.isfile(filepath):
            ext = os.path.splitext(filename)[1].lower()
            size = os.path.getsize(filepath)
            dims = get_image_dimensions(filepath) if ext in IMAGE_EXTENSIONS else None
            index[filepath] = {
                'name': filename,
                'size': size,
                'dims': dims
            }
    return index

def process_and_merge(new_user_folder, archive_user_folder):
    """The main function that implements the strict merging rules."""
    archive_index = build_archive_index(archive_user_folder)

    for new_filename in os.listdir(new_user_folder):
        new_filepath = os.path.join(new_user_folder, new_filename)
        if not os.path.isfile(new_filepath):
            continue

        ext = os.path.splitext(new_filename)[1].lower()
        new_size = os.path.getsize(new_filepath)
        new_dims = get_image_dimensions(new_filepath) if ext in IMAGE_EXTENSIONS else None

        is_image = ext in IMAGE_EXTENSIONS
        is_video = ext in VIDEO_EXTENSIONS

        is_duplicate = False
        rename_needed = False

        # Rule 1: Check for a direct name match
        target_path = os.path.join(archive_user_folder, new_filename)
        if target_path in archive_index:
            exist_data = archive_index[target_path]
            if is_video:
                if exist_data['size'] == new_size:
                    is_duplicate = True # Same name, same size (video) -> Duplicate
                else:
                    rename_needed = True # Same name, different size (video) -> Rename
            elif is_image:
                if exist_data['dims'] == new_dims:
                    is_duplicate = True # Same name, same dimensions (image) -> Duplicate
                else:
                    rename_needed = True # Same name, different dimensions (image) -> Rename
            else: # Other file types
                rename_needed = True # Same name -> Rename for safety

        # Rule 2: If no name match, check for content match (size/dims)
        if not is_duplicate and not rename_needed:
            for arch_path, arch_data in archive_index.items():
                if arch_data['size'] == new_size: # Potential match found based on size
                    if is_video:
                        is_duplicate = True # A video with the exact same size exists -> Duplicate
                        break
                    elif is_image:
                        if arch_data['dims'] == new_dims:
                            is_duplicate = True # An image with same size AND dimensions exists -> Duplicate
                            break

        # Execute Actions: Move, Rename, or Ignore
        if is_duplicate:
            print(f"[-] Duplicate ignored: {new_filename}")
        else:
            final_filename = new_filename
            # Rename if needed, or if a file with the same name exists (edge case)
            if rename_needed or os.path.exists(os.path.join(archive_user_folder, new_filename)):
                final_filename = get_unique_filename(archive_user_folder, new_filename)
                print(f"[*] Renamed: '{new_filename}' -> '{final_filename}'")

            final_path = os.path.join(archive_user_folder, final_filename)
            shutil.move(new_filepath, final_path)
            print(f"[+] Added new file: {final_filename}")

            # Update the index to account for the newly added file in this session
            archive_index[final_path] = {'name': final_filename, 'size': new_size, 'dims': new_dims}

def main():
    print("=== Welcome to the Smart Instagram Archive Merger ===")

    # 1. Check if the ZIP file exists
    if not os.path.exists(ZIP_FILE_PATH):
        print(f"Error: ZIP file not found at the specified path: {ZIP_FILE_PATH}")
        print("Please check the 'ZIP_FILE_PATH' variable at the top of the script.")
        input("Press Enter to exit...")
        return

    # 2. Ask the user for the old archive path
    archive_dir = input("Please enter the path to your EXISTING archive folder: ").strip('"').strip("'")

    if not os.path.exists(archive_dir):
        print("Error: The archive path you entered does not exist.")
        input("Press Enter to exit...")
        return

    print("\nProcessing... this may take a moment.")

    # 3. Use a temporary directory for safe extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(ZIP_FILE_PATH, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
        except zipfile.BadZipFile:
            print(f"Error: The file at {ZIP_FILE_PATH} is not a valid ZIP file or is corrupted.")
            input("Press Enter to exit...")
            return

        # 4. Iterate through the extracted user folders
        for item in os.listdir(temp_dir):
            new_user_folder = os.path.join(temp_dir, item)

            if os.path.isdir(new_user_folder):
                user_name = item
                archive_user_folder = os.path.join(archive_dir, user_name)

                print(f"\n---> Checking user: {user_name}")

                # If the user does not exist in the old archive, move the whole folder
                if not os.path.exists(archive_user_folder):
                    shutil.move(new_user_folder, archive_user_folder)
                    print(f"[++] New user folder '{user_name}' moved to archive.")
                else:
                    # If user exists, start the smart merge process
                    process_and_merge(new_user_folder, archive_user_folder)

    print("\n=== Merge process completed successfully! ===")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
