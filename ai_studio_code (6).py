import os
import librosa
import numpy as np
# START: MODIFIED SECTION
from moviepy import VideoFileClip
# END: MODIFIED SECTION

# START: CONFIGURATION
FOLDER_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK"
# END: CONFIGURATION

def extract_audio_features(video_path):
    try:
        temp_audio = "temp_audio.wav"
        clip = VideoFileClip(video_path)
        
        if clip.audio is None:
            print(f"No audio found in {video_path}")
            clip.close()
            return None
            
        # استخدام subclipped للنسخة الحديثة
        end_time = min(30, clip.duration)
        subclip = clip.subclipped(0, end_time)
        
        # START: MODIFIED SECTION
        # حذفنا verbose=False لأنها لم تعد مدعومة في النسخة الجديدة
        # نكتفي بـ logger=None لإخفاء شريط التقدم
        subclip.audio.write_audiofile(temp_audio, logger=None)
        # END: MODIFIED SECTION
        
        subclip.close()
        clip.close()

        # تحليل الصوت
        y, sr = librosa.load(temp_audio)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        
        # تنظيف الملف المؤقت
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
            
        return np.mean(chroma, axis=1)
        
    except Exception as e:
        print(f"Error processing audio for {video_path}: {e}")
        if os.path.exists("temp_audio.wav"): 
            try:
                os.remove("temp_audio.wav")
            except:
                pass
        return None

def check_audio_similarity(folder_path):
    print(f"--- TEST 3: Audio Fingerprinting in {folder_path} ---")
    
    video_files = [f for f in os.listdir(folder_path) if f.endswith(('.mp4', '.mov', '.avi', '.mkv'))]
    
    if len(video_files) < 2:
        print("Error: Need at least 2 videos to compare.")
        return

    audio_features = {}
    
    for video_file in video_files:
        full_path = os.path.join(folder_path, video_file)
        print(f"Extracting audio features for: {video_file}...")
        features = extract_audio_features(full_path)
        if features is not None:
            audio_features[video_file] = features

    print("\n--- Comparison Result ---")
    files = list(audio_features.keys())
    if len(files) < 2: return

    file1 = files[0]
    file2 = files[1]
    
    feat1 = audio_features[file1]
    feat2 = audio_features[file2]
    
    dist = np.linalg.norm(feat1 - feat2)
    
    print(f"Comparing '{file1}' AND '{file2}'")
    print(f"Audio Distance Score: {dist:.4f}")
    
    # كلما قل الرقم زاد التشابه
    if dist < 0.1: 
        print("CONCLUSION: MATCH (Audio is very similar)")
    else:
        print("CONCLUSION: NO MATCH (Audio differs)")

if __name__ == "__main__":
    check_audio_similarity(FOLDER_PATH)