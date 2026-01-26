import os
import sqlite3
import shutil
import json
from PIL import Image
import imagehash
from pillow_heif import register_heif_opener
import concurrent.futures
import sys

# ==========================================
# CONFIGURATION (MULTI-ROOT)
# ==========================================
# قائمة المجلدات المسموح بالعمل داخلها (الجذور)
ROOT_FOLDERS = [
    r"C:\Users\Stark\Download\myhome\video_rating_app\NS",
    r"C:\Users\Stark\Download\myhome\video_rating_app\insta"
]

REVIEW_FOLDER = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\x2"

# أولويات التفضيل (الأعلى رقم = الأهم)
TIER4_KEYWORD = "A1000 elo pic" # Best
TIER3_PATH_START = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK"
TIER2_PATH_START = r"C:\Users\Stark\Download\myhome\video_rating_app\insta"

DB_FILE = "image_fingerprints.db"
MAP_FILE = "image_review_map.json"
MIN_SIZE_BYTES = 5 * 1024 

register_heif_opener()
VALID_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.heic', '.avif')

# ==========================================
# DATABASE FUNCTIONS
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    phash TEXT,
                    dhash TEXT,
                    scanned INTEGER DEFAULT 0
                )''')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(DB_FILE)

# ==========================================
# HELPER: Strict Multi-Root Check
# ==========================================
def is_valid_file(path):
    """
    التحقق الصارم:
    1. المسار يجب أن يبدأ بأحد المجلدات في ROOT_FOLDERS.
    2. لا مجلدات مخفية.
    3. الحجم > 5KB.
    """
    abs_path = os.path.abspath(path)
    
    # 1. التحقق أن الملف داخل أحد الجذور المسموحة
    is_in_scope = False
    for root in ROOT_FOLDERS:
        if abs_path.startswith(os.path.abspath(root)):
            is_in_scope = True
            break
    
    if not is_in_scope:
        return False

    # 2. التحقق من المجلدات المخفية
    parts = abs_path.split(os.sep)
    for part in parts:
        if part.startswith('.') or part.startswith('$'):
            return False
            
    # 3. التحقق من الوجود والحجم
    try:
        if not os.path.exists(abs_path): return False
        if os.path.getsize(abs_path) < MIN_SIZE_BYTES: return False
    except:
        return False
        
    return True

# ==========================================
# HASHING WORKER
# ==========================================
def calculate_hashes(file_path):
    try:
        with Image.open(file_path) as img:
            p_hash = str(imagehash.phash(img))
            d_hash = str(imagehash.dhash(img))
            return (file_path, p_hash, d_hash)
    except Exception:
        return (file_path, None, None)

# ==========================================
# 1. SCAN (Multi-Root Support)
# ==========================================
def scan_all_images():
    init_db()
    print(f"--- SCANNING IMAGES ---")
    print(f"Roots: {ROOT_FOLDERS}")
    conn = get_db_connection()
    c = conn.cursor()
    
    all_files = []
    print("Listing files from all roots...")
    
    for root_folder in ROOT_FOLDERS:
        if not os.path.exists(root_folder):
            print(f"Warning: Path not found: {root_folder}")
            continue
            
        for root, dirs, files in os.walk(root_folder):
            dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('$')]
            
            for file in files:
                if file.lower().endswith(VALID_EXTENSIONS):
                    full_path = os.path.join(root, file)
                    if is_valid_file(full_path):
                        all_files.append(full_path)
    
    c.execute("SELECT path FROM images")
    existing = set(row[0] for row in c.fetchall())
    
    to_scan = [f for f in all_files if f not in existing]
    print(f"Total valid images in scope: {len(all_files)}")
    print(f"New images to scan: {len(to_scan)}")
    
    if not to_scan:
        print("Nothing new to scan.")
        return

    max_workers = os.cpu_count() or 4
    batch = []
    count = 0
    
    print(f"Starting hash calculation...")
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        for res in executor.map(calculate_hashes, to_scan):
            if res[1] is not None:
                batch.append(res)
            
            count += 1
            if count % 100 == 0:
                sys.stdout.write(f"\rProcessed {count}/{len(to_scan)}")
                sys.stdout.flush()
            
            if len(batch) >= 500:
                c.executemany("INSERT OR IGNORE INTO images (path, phash, dhash, scanned) VALUES (?, ?, ?, 1)", batch)
                conn.commit()
                batch = []
                
    if batch:
        c.executemany("INSERT OR IGNORE INTO images (path, phash, dhash, scanned) VALUES (?, ?, ?, 1)", batch)
        conn.commit()
        
    conn.close()
    print("\nScan Complete.")

# ==========================================
# 2. FIND DUPLICATES
# ==========================================
def find_duplicates(return_matches=False):
    init_db()
    
    print("\nSelect Hashing Method:")
    print("1. pHash (Default)")
    print("2. dHash")
    method_choice = input("Choice (1/2): ").strip()
    hash_column = "dhash" if method_choice == '2' else "phash"
    
    default_threshold = 4 
    try:
        t_input = input(f"Enter Threshold (Default {default_threshold}): ").strip()
        threshold = int(t_input) if t_input else default_threshold
    except:
        threshold = default_threshold
        
    print("\nComparison Mode:")
    print("1. Windowed (Faster)")
    print("2. Full (Slower)")
    mode_choice = input("Choice (1/2): ").strip()
    
    conn = get_db_connection()
    c = conn.cursor()
    print(f"Loading {hash_column} data...")
    
    c.execute(f"SELECT path, {hash_column} FROM images WHERE {hash_column} IS NOT NULL")
    raw_data = c.fetchall()
    
    images = []
    filtered_count = 0
    
    for path, h_str in raw_data:
        if is_valid_file(path):
            try:
                h_obj = imagehash.hex_to_hash(h_str)
                images.append({'path': path, 'hash': h_obj})
            except: pass
        else:
            filtered_count += 1
            
    print(f"Valid images: {len(images)} (Filtered: {filtered_count})")
        
    matches = []
    
    if mode_choice == '2': # Full
        for i in range(len(images)):
            if i % 100 == 0: sys.stdout.write(f"\rComparing {i}/{len(images)}")
            for j in range(i + 1, len(images)):
                diff = images[i]['hash'] - images[j]['hash']
                if diff <= threshold:
                    matches.append((images[i]['path'], images[j]['path'], diff))
    else: # Windowed
        images.sort(key=lambda x: str(x['hash'])) 
        window_size = 20
        for i in range(len(images)):
            if i % 500 == 0: sys.stdout.write(f"\rComparing {i}/{len(images)}")
            for j in range(i + 1, min(i + window_size, len(images))):
                diff = images[i]['hash'] - images[j]['hash']
                if diff <= threshold:
                    matches.append((images[i]['path'], images[j]['path'], diff))

    print(f"\nFound {len(matches)} matches.")
    
    if not return_matches:
        with open("image_report.txt", "w", encoding="utf-8") as f:
            for m in matches: f.write(f"{m[0]} == {m[1]} (Diff: {m[2]})\n")
        print("Report saved.")
        
    return matches

# ==========================================
# 3. COPY FOR REVIEW
# ==========================================
def copy_for_review():
    matches = find_duplicates(return_matches=True)
    if not matches: 
        print("No duplicates found.")
        return
        
    if not os.path.exists(REVIEW_FOLDER): os.makedirs(REVIEW_FOLDER)
    
    review_map = {}
    print("Copying files...")
    
    copied_count = 0
    for idx, (p1, p2, score) in enumerate(matches):
        try:
            if not is_valid_file(p1) or not is_valid_file(p2):
                continue
            
            ext1 = os.path.splitext(p1)[1]
            ext2 = os.path.splitext(p2)[1]
            
            g_name = f"Group_{idx:05d}"
            name1 = f"{g_name}_A_Diff{score}{ext1}"
            name2 = f"{g_name}_B_Diff{score}{ext2}"
            
            dest1 = os.path.join(REVIEW_FOLDER, name1)
            dest2 = os.path.join(REVIEW_FOLDER, name2)
            
            shutil.copy2(p1, dest1)
            shutil.copy2(p2, dest2)
            
            review_map[name1] = p1
            review_map[name2] = p2
            copied_count += 1
        except Exception as e:
            print(f"Error copying: {e}")
            
    with open(MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(review_map, f)
    print(f"Done. Copied {copied_count} pairs.")

# ==========================================
# 4. EXECUTE DELETION (MULTI-TIER LOGIC)
# ==========================================
def get_size_category_score(size_bytes):
    size_kb = size_bytes / 1024
    if 700 <= size_kb <= 1500: return 6
    if 1500 < size_kb <= 3000: return 5
    if 200 <= size_kb < 700: return 4
    if 50 <= size_kb < 200: return 3
    if size_kb > 3000: return 2
    return 1

def get_folder_tier(path):
    norm_path = os.path.normpath(path.lower())
    
    # Tier 4 (Highest)
    if TIER4_KEYWORD.lower() in norm_path: return 4
    
    # Tier 3 (ELO TIK)
    tier3_check = os.path.normpath(TIER3_PATH_START.lower())
    if norm_path.startswith(tier3_check): return 3
    
    # Tier 2 (Insta)
    tier2_check = os.path.normpath(TIER2_PATH_START.lower())
    if norm_path.startswith(tier2_check): return 2
    
    # Tier 1 (Others)
    return 1

def execute_deletion():
    print("\n--- EXECUTION PHASE ---")
    if not os.path.exists(MAP_FILE):
        print("Error: Map file not found.")
        return

    with open(MAP_FILE, 'r', encoding='utf-8') as f:
        review_map = json.load(f)

    remaining_files = os.listdir(REVIEW_FOLDER)
    
    groups = {}
    for filename in remaining_files:
        if not filename.startswith("Group_"): continue
        group_id = filename[:11]
        if group_id not in groups: groups[group_id] = []
        groups[group_id].append(filename)

    print(f"Found {len(groups)} groups.")
    
    to_delete = []
    
    for gid, files in groups.items():
        if len(files) < 2: continue
        
        candidates = []
        for f_name in files:
            if f_name in review_map:
                original_path = review_map[f_name]
                if is_valid_file(original_path):
                    size = os.path.getsize(original_path)
                    folder_tier = get_folder_tier(original_path)
                    cat_score = get_size_category_score(size)
                    
                    candidates.append({
                        'review_name': f_name,
                        'path': original_path,
                        'size': size,
                        'folder_tier': folder_tier,
                        'cat_score': cat_score
                    })
        
        if len(candidates) < 2: continue
        
        # 1. Tier | 2. Category | 3. Size
        candidates.sort(key=lambda x: (
            x['folder_tier'],
            x['cat_score'],
            x['size']
        ), reverse=True)
        
        winner = candidates[0]
        
        for cand in candidates:
            if cand['path'] != winner['path']:
                to_delete.append((cand['path'], cand['review_name']))

    if not to_delete:
        print("No files to delete.")
        return

    print(f"\n[PREVIEW] Found {len(to_delete)} files to delete.")
    for i in range(min(5, len(to_delete))):
        print(f" - {to_delete[i][0]}")
    
    confirm = input(f"\nPERMANENTLY DELETE {len(to_delete)} files? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        return

    deleted_count = 0
    for original_path, review_name in to_delete:
        try:
            if os.path.exists(original_path):
                os.remove(original_path)
            
            review_path = os.path.join(REVIEW_FOLDER, review_name)
            if os.path.exists(review_path):
                os.remove(review_path)
                
            deleted_count += 1
            if deleted_count % 10 == 0: sys.stdout.write(f"\rDeleted {deleted_count}/{len(to_delete)}")
            
        except Exception as e:
            print(f"Error deleting {original_path}: {e}")

    print(f"\n\nDone. Deleted {deleted_count} files.")

if __name__ == "__main__":
    while True:
        print("\n=== IMAGE DEDUPLICATOR PRO (MULTI-ROOT) ===")
        print("1. Scan")
        print("2. Find")
        print("3. Copy")
        print("4. EXECUTE DELETION")
        print("5. Exit")
        c = input("Select: ").strip()
        if c == '1': scan_all_images()
        elif c == '2': find_duplicates()
        elif c == '3': copy_for_review()
        elif c == '4': execute_deletion()
        elif c == '5': break