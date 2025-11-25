import os
import imagehash
from PIL import Image
# START: MODIFIED SECTION (تحديث الاستدعاء للنسخة الجديدة)
from moviepy import VideoFileClip
# END: MODIFIED SECTION

# START: CONFIGURATION
FOLDER_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK"
# END: CONFIGURATION

def get_frame_hash(video_path):
    try:
        clip = VideoFileClip(video_path)
        frame_time = clip.duration / 2 
        # في النسخة الجديدة get_frame قد يحتاج وقتاً دقيقاً
        frame = clip.get_frame(frame_time)
        clip.close()
        
        image = Image.fromarray(frame)
        return imagehash.phash(image)
    except Exception as e:
        print(f"Error processing {video_path}: {e}")
        return None

def check_visual_hash(folder_path):
    print(f"--- TEST 2: Visual Perceptual Hash (pHash) in {folder_path} ---")
    
    video_files = [f for f in os.listdir(folder_path) if f.endswith(('.mp4', '.mov', '.avi', '.mkv'))]
    
    if len(video_files) < 2:
        print("Error: Need at least 2 videos to compare.")
        return

    hashes = {}
    
    for video_file in video_files:
        full_path = os.path.join(folder_path, video_file)
        print(f"Processing visual fingerprint for: {video_file}...")
        v_hash = get_frame_hash(full_path)
        if v_hash:
            hashes[video_file] = v_hash
            print(f"Hash: {v_hash}")

    print("\n--- Comparison Result ---")
    files = list(hashes.keys())
    if len(files) < 2: return

    file1 = files[0]
    file2 = files[1]
    
    hash1 = hashes[file1]
    hash2 = hashes[file2]
    
    score = hash1 - hash2 
    
    print(f"Comparing '{file1}' AND '{file2}'")
    print(f"Hamming Distance Score: {score}")
    
    if score <= 10: 
        print("CONCLUSION: MATCH (Visually similar)")
    else:
        print("CONCLUSION: NO MATCH (Visually different)")

if __name__ == "__main__":
    check_visual_hash(FOLDER_PATH)