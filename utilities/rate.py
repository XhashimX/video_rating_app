import json
import random
import statistics
import os

INPUT_FILE = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"
OUTPUT_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities"
BASE_FILENAME = "topcut_elo_videos_A1000 elo tik_"
START_INDEX = 6501
NUMBER_OF_FILES = 16

STRONG_NAMES = [
    "hajar0220", "camvred1", "naaghaamm", "Ellv", "ibu2b", 
    "ayllaaa__", "dana.alerksousi8", "Arab", "rahma_ghorbel7", 
    "ldrzelalll", "j_o_d_y02", "Syr", "White", "pr3etty_ysmn", 
    "_s1fa", "japp_leack"
]

def generate_fair_distributed_competitions():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: File not found at {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    names_to_videos = {}
    for vid_path, info in data.items():
        name = info.get('name')
        rating = float(info.get('rating', 1000.0))
        if rating == 1000.0:
            continue
        if name:
            if name not in names_to_videos:
                names_to_videos[name] = []
            names_to_videos[name].append({
                "path": vid_path,
                "rating": rating,
                "file_size": info.get('file_size', 0)
            })

    valid_names_data = {}
    for name, vids in names_to_videos.items():
        if len(vids) <= 4:
            valid_names_data[name] = vids
        else:
            ratings = [v['rating'] for v in vids]
            median_rating = statistics.median(ratings)
            vids_sorted_by_mid = sorted(vids, key=lambda x: abs(x['rating'] - median_rating))
            valid_names_data[name] = vids_sorted_by_mid[:4]

    all_eligible_names = list(valid_names_data.keys())
    
    current_strong_in_data = [n for n in STRONG_NAMES if n in valid_names_data]
    other_names = [n for n in all_eligible_names if n not in current_strong_in_data]

    random.shuffle(current_strong_in_data)
    random.shuffle(other_names)

    total_names = len(all_eligible_names)
    names_per_file = total_names // NUMBER_OF_FILES
    remainder = total_names % NUMBER_OF_FILES

    print(f"إجمالي الأسماء الصالحة: {total_names}")
    print(f"أسماء قوية تم العثور عليها: {len(current_strong_in_data)}")
    print(f"سيتم وضع اسم قوي واحد في كل ملف تقريباً.\n")

    current_other_idx = 0
    file_summary = {}

    for i in range(NUMBER_OF_FILES):
        chunk_names = []
        
        if i < len(current_strong_in_data):
            chunk_names.append(current_strong_in_data[i])
        
        needed_others = (names_per_file + (1 if i < remainder else 0)) - len(chunk_names)
        
        chunk_names.extend(other_names[current_other_idx : current_other_idx + needed_others])
        current_other_idx += needed_others
        
        file_num = START_INDEX + i
        full_file_name = f"{BASE_FILENAME}{file_num}.json"
        file_summary[full_file_name] = chunk_names
        
        all_chunk_videos = []
        for name in chunk_names:
            all_chunk_videos.extend(valid_names_data[name])
            
        random.shuffle(all_chunk_videos)
        
        matchups = []
        for j in range(0, len(all_chunk_videos) - 1, 2):
            v1 = all_chunk_videos[j]
            v2 = all_chunk_videos[j+1]
            matchups.append({
                "videos": [v1["path"], v2["path"]],
                "rating": [v1["rating"], v2["rating"]],
                "file_size": [v1["file_size"], v2["file_size"]],
                "mode": 1,
                "num_videos": 2,
                "ranking_type": "winner_only",
                "competition_type": "random"
            })
            
        file_path = os.path.join(OUTPUT_DIR, full_file_name)
        with open(file_path, 'w', encoding='utf-8') as out_f:
            json.dump(matchups, out_f, indent=4, ensure_ascii=False)

    print("-" * 50)
    print("قائمة الملفات بالتوزيع العادل (الاسم القوي في البداية):")
    print("-" * 50)
    for file_name, names in file_summary.items():
        formatted_names = []
        for n in names:
            if n in STRONG_NAMES:
                formatted_names.append(f"**{n}**")
            else:
                formatted_names.append(n)
        
        print(f"📄 {file_name}")
        print(f"👥 الأسماء: {', '.join(formatted_names)}")
        print("-" * 30)

if __name__ == "__main__":
    generate_fair_distributed_competitions()