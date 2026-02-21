import os

def resolve_size_duplicates(directory_path):
    if not os.path.exists(directory_path):
        print(f"Error: The path {directory_path} does not exist.")
        return

    while True:
        size_dict = {}
        files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
        
        has_duplicates = False
        
        for filename in files:
            full_path = os.path.join(directory_path, filename)
            file_size = os.path.getsize(full_path)
            
            if file_size not in size_dict:
                size_dict[file_size] = []
            size_dict[file_size].append(full_path)

        for size, paths in size_dict.items():
            if len(paths) > 1:
                has_duplicates = True
                for i in range(1, len(paths)):
                    file_to_modify = paths[i]
                    try:
                        with open(file_to_modify, 'ab') as f:
                            f.write(b'\0')
                        print(f"Modified: {file_to_modify} (Added 1 byte)")
                    except Exception as e:
                        print(f"Could not modify {file_to_modify}: {e}")
                
                break
        
        if not has_duplicates:
            print("Success: No more duplicate sizes found.")
            break

target_directory = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\Dib"
resolve_size_duplicates(target_directory)