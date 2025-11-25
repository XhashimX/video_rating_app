import os
# START: MODIFIED SECTION (تحديث الاستدعاء للنسخة الجديدة)
from moviepy import VideoFileClip
# END: MODIFIED SECTION

# START: CONFIGURATION
# تأكد أن هذا المسار صحيح ويحتوي على الفيديوهات
FOLDER_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK"
# END: CONFIGURATION

def check_duration_similarity(folder_path):
    print(f"--- TEST 1: Duration Comparison in {folder_path} ---")
    
    video_files = [f for f in os.listdir(folder_path) if f.endswith(('.mp4', '.mov', '.avi', '.mkv'))]
    
    if len(video_files) < 2:
        print("Error: Need at least 2 videos in the folder to compare.")
        return

    video_data = {}

    for video_file in video_files:
        full_path = os.path.join(folder_path, video_file)
        try:
            clip = VideoFileClip(full_path)
            duration = clip.duration 
            video_data[video_file] = duration
            clip.close() 
            print(f"File: {video_file} | Duration: {duration} seconds")
        except Exception as e:
            print(f"Error reading {video_file}: {e}")

    print("\n--- Comparison Result ---")
    files = list(video_data.keys())
    if len(files) < 2: return # حماية إضافية

    file1 = files[0]
    file2 = files[1]
    
    dur1 = video_data[file1]
    dur2 = video_data[file2]
    
    diff = abs(dur1 - dur2)
    
    print(f"Comparing '{file1}' AND '{file2}'")
    print(f"Difference in duration: {diff} seconds")
    
    if diff < 0.1:
        print("CONCLUSION: MATCH (Based on duration)")
    else:
        print("CONCLUSION: NO MATCH (Duration differs)")

if __name__ == "__main__":
    check_duration_similarity(FOLDER_PATH)