import os
import sqlite3
import subprocess
import concurrent.futures
import imageio_ffmpeg
import sys
import shutil
import json
import re
from typing import List, Tuple, Optional, Dict

# ==========================================
# إعدادات
# ==========================================
ROOT_FOLDER = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK"
REVIEW_FOLDER = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\x2"
PREFERRED_FOLDER = "A1000 elo tik" # اسم المجلد المفضل
DB_FILE = "video_fingerprints_gpu.db"
MAP_FILE = "review_map.json"
EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
USE_GPU = True 

# ==========================================
# دوال مساعدة
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    visual_hash TEXT,
                    duration REAL,
                    scanned INTEGER DEFAULT 0
                )''')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(DB_FILE)

def get_ffmpeg_hash(file_path):
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        probe_cmd = [ffmpeg_exe, "-i", file_path, "-hide_banner"]
        result = subprocess.run(probe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, errors='ignore')
        duration = 0
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
        if match:
            hrs, mins, secs = match.groups()
            duration = float(hrs)*3600 + float(mins)*60 + float(secs)
        timestamp = max(1, duration / 2)
        cmd = [ffmpeg_exe]
        if USE_GPU: cmd.extend(['-hwaccel', 'auto']) 
        cmd.extend(['-ss', str(timestamp), '-i', file_path, '-vf', 'scale=9:8', '-vframes', '1', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'])
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if not process.stdout or len(process.stdout) < 72: return duration, None
        pixels = list(process.stdout)
        hash_str = "".join(["1" if pixels[i*9+j] > pixels[i*9+j+1] else "0" for i in range(8) for j in range(8)])
        return duration, hex(int(hash_str, 2))[2:]
    except: return 0, None

def worker_process(file_path):
    dur, v_hash = get_ffmpeg_hash(file_path)
    return (file_path, dur, v_hash)

def get_longest_digit_sequence(filename):
    # حساب طول أطول سلسلة أرقام في الاسم
    numbers = re.findall(r'\d+', filename)
    if not numbers: return 0
    return max(len(n) for n in numbers)

# ==========================================
# 1. SCAN
# ==========================================
def scan_all_videos():
    init_db() 
    gpu_status = "ON" if USE_GPU else "OFF"
    print(f"--- SCANNING [GPU: {gpu_status}] ---")
    conn = get_db_connection()
    c = conn.cursor()
    all_files = []
    for root, dirs, files in os.walk(ROOT_FOLDER):
        for file in files:
            if file.lower().endswith(EXTENSIONS): all_files.append(os.path.join(root, file))
    c.execute("SELECT path FROM videos")
    existing = set(row[0] for row in c.fetchall())
    to_scan = [f for f in all_files if f not in existing]
    
    print(f"New files: {len(to_scan)}")
    if not to_scan: return

    max_workers = 10
    batch = []
    count = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        for res in executor.map(worker_process, to_scan):
            batch.append(res)
            count += 1
            if count % 100 == 0: 
                sys.stdout.write(f"\rScanned {count}/{len(to_scan)}")
                sys.stdout.flush()
            if len(batch) >= 100:
                c.executemany("INSERT INTO videos (path, duration, visual_hash, scanned) VALUES (?, ?, ?, 1)", [(x[0], x[1], x[2]) for x in batch])
                conn.commit()
                batch = []
    if batch:
        c.executemany("INSERT INTO videos (path, duration, visual_hash, scanned) VALUES (?, ?, ?, 1)", [(x[0], x[1], x[2]) for x in batch])
        conn.commit()
    conn.close()
    print("\nScan Complete.")

# ==========================================
# 2. FIND
# ==========================================
def find_duplicates(return_matches=False):
    init_db()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT path, visual_hash FROM videos WHERE visual_hash IS NOT NULL")
    videos = [{'path': p, 'hash': int(h, 16)} for p, h in c.fetchall() if h]
    videos.sort(key=lambda x: x['hash'])
    
    matches = []
    window = 20
    print("Comparing...")
    for i in range(len(videos)):
        v1 = videos[i]
        for j in range(i + 1, min(i + window, len(videos))):
            v2 = videos[j]
            xor = v1['hash'] ^ v2['hash']
            if xor == 0: matches.append((v1['path'], v2['path'], 5))
            elif bin(xor).count('1') <= 4: matches.append((v1['path'], v2['path'], 4))
            
    if not return_matches:
        print(f"Found {len(matches)} matches. Check report.")
        with open("report.txt", "w", encoding="utf-8") as f:
            for m in matches: f.write(f"{m[0]} == {m[1]}\n")
    return matches

# ==========================================
# 3. COPY
# ==========================================
def copy_for_review():
    matches = find_duplicates(return_matches=True)
    if not matches: return
    if not os.path.exists(REVIEW_FOLDER): os.makedirs(REVIEW_FOLDER)
    review_map = {}
    print("Copying...")
    for idx, (p1, p2, s) in enumerate(matches):
        try:
            if not os.path.exists(p1) or not os.path.exists(p2): continue
            g = f"Group_{idx:04d}"
            n1 = f"{g}_A_Score{s}{os.path.splitext(p1)[1]}"
            n2 = f"{g}_B_Score{s}{os.path.splitext(p2)[1]}"
            shutil.copy2(p1, os.path.join(REVIEW_FOLDER, n1))
            shutil.copy2(p2, os.path.join(REVIEW_FOLDER, n2))
            review_map[n1] = p1
            review_map[n2] = p2
        except: pass
    with open(MAP_FILE, 'w', encoding='utf-8') as f: json.dump(review_map, f)
    print("Done.")

# ==========================================
# 4. EXECUTE DELETION (THE NEW PART)
# ==========================================
def execute_deletion():
    print("\n--- EXECUTION PHASE ---")
    if not os.path.exists(MAP_FILE):
        print("Error: Map file not found. Did you run step 3?")
        return

    with open(MAP_FILE, 'r', encoding='utf-8') as f:
        review_map = json.load(f)

    # قراءة ما تبقى في مجلد المراجعة
    remaining_files = os.listdir(REVIEW_FOLDER)
    
    # تجميع الملفات حسب المجموعة (Group_XXXX)
    groups = {}
    for filename in remaining_files:
        if not filename.startswith("Group_"): continue
        # استخراج اسم المجموعة (أول 10 حروف: Group_XXXX)
        group_id = filename[:10]
        if group_id not in groups: groups[group_id] = []
        groups[group_id].append(filename)

    print(f"Found {len(groups)} confirmed duplicate groups.")
    print("Applying rules to delete duplicates from SOURCE folders...")
    
    deleted_count = 0
    
    for gid, files in groups.items():
        # نحتاج ملفين على الأقل للمقارنة
        if len(files) < 2: continue
        
        # الحصول على المسارات الأصلية
        candidates = []
        for f_name in files:
            if f_name in review_map:
                original_path = review_map[f_name]
                if os.path.exists(original_path):
                    size = os.path.getsize(original_path)
                    candidates.append({
                        'review_name': f_name,
                        'path': original_path,
                        'size': size,
                        'is_preferred': PREFERRED_FOLDER in original_path,
                        'digit_score': get_longest_digit_sequence(os.path.basename(original_path))
                    })

        if len(candidates) < 2: continue

        # ترتيب المرشحين لاختيار الفائز (الأول في القائمة هو الفائز)
        # الترتيب تنازلي (الأفضل أولاً)
        candidates.sort(key=lambda x: (
            x['size'],           # 1. الحجم الأكبر
            x['is_preferred'],   # 2. المجلد المفضل (True=1 > False=0)
            x['digit_score']     # 3. الاسم الأجمل (أرقام أكثر)
        ), reverse=True)
        
        # تطبيق قاعدة الـ 3 ميجا فرق
        # إذا كان الفرق بين الأول والثاني أقل من 3 ميجا، قد تتغير الأولوية للمجلد المفضل
        winner = candidates[0]
        
        # التحقق الدقيق من قاعدة الـ 3 ميجا
        # إذا كان الثاني (الأصغر) في المجلد المفضل، والأول (الأكبر) ليس فيه
        # والفرق بينهما صغير (أقل من 3 ميجا) -> نفضل الثاني
        second = candidates[1]
        size_diff_mb = (winner['size'] - second['size']) / (1024*1024)
        
        if size_diff_mb < 3.0 and second['is_preferred'] and not winner['is_preferred']:
            winner = second

        # الآن نحذف كل من ليس الفائز
        for cand in candidates:
            if cand['path'] == winner['path']:
                print(f"[KEEP] {os.path.basename(cand['path'])}")
                continue
            
            try:
                print(f"[DELETE] {os.path.basename(cand['path'])}")
                # 1. حذف الملف الأصلي
                os.remove(cand['path'])
                # 2. حذف ملف المراجعة أيضاً للتنظيف
                review_path = os.path.join(REVIEW_FOLDER, cand['review_name'])
                if os.path.exists(review_path):
                    os.remove(review_path)
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {cand['path']}: {e}")

    print("-" * 30)
    print(f"Operation Completed. Deleted {deleted_count} duplicate videos from source.")
    print("You can now delete the 'x2' folder manually.")

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    subprocess.call('', shell=True)
    while True:
        print("\n=== FINAL DEDUPLICATOR ===")
        print("1. Scan")
        print("2. Find")
        print("3. Copy to Review")
        print("4. EXECUTE DELETION (Dangerous)")
        print("5. Exit")
        c = input("Select: ")
        if c == '1': scan_all_videos()
        elif c == '2': find_duplicates()
        elif c == '3': copy_for_review()
        elif c == '4': execute_deletion()
        elif c == '5': break