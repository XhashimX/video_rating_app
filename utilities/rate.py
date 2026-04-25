import json
import random
import math
import os

# --- الإعدادات ---
INPUT_FILE = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"
OUTPUT_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities"
BASE_FILENAME = "topcut_elo_videos_A1000 elo tik_"
START_INDEX = 4501
NUMBER_OF_FILES = 12

def generate_fair_distributed_competitions():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: File not found at {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. تجميع الفيديوهات لكل اسم واستبعاد التقييمات الافتراضية
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

    # 2. فلترة المستخدمين: تجاهل من لديه أقل من 8 فيديوهات
    eligible_users = {name: vids for name, vids in names_to_videos.items() if len(vids) >= 8}

    valid_names_data = {}
    selection_ratios = None  # لحفظ النسب العشوائية التي ستطبق على الجميع

    for name, vids in eligible_users.items():
        # ترتيب الفيديوهات تصاعدياً حسب التقييم
        vids_sorted = sorted(vids, key=lambda x: x['rating'])
        total_vids = len(vids_sorted)
        
        # 3. استبعاد أعلى 20% وأقل 20% (تحديد الـ 60% في المنتصف)
        start_idx = int(total_vids * 0.20)
        end_idx = int(total_vids * 0.80)
        middle_pool = vids_sorted[start_idx:end_idx]
        pool_size = len(middle_pool)

        # 4. اختيار الفيديوهات الـ 4
        if selection_ratios is None:
            # للمستخدم الأول: نختار 4 مراكز عشوائية من الوسط
            chosen_indices = random.sample(range(pool_size), 4)
            chosen_indices.sort()
            
            # حساب نسبة كل مركز بالنسبة لحجم المجموعة (من 0.0 إلى 1.0)
            # هذا يضمن العدل للمستخدمين ذوي الأحجام المختلفة
            selection_ratios = [idx / (pool_size - 1) for idx in chosen_indices]
            
            selected_vids = [middle_pool[i] for i in chosen_indices]
        else:
            # لباقي المستخدمين: نطبق نفس النسب المئوية التي تم اختيارها للمستخدم الأول
            selected_vids = []
            for ratio in selection_ratios:
                # تحويل النسبة المئوية إلى "رقم المركز" الفعلي لمجموعة هذا الشخص
                target_idx = int(round(ratio * (pool_size - 1)))
                selected_vids.append(middle_pool[target_idx])
                
        valid_names_data[name] = selected_vids

    # 5. التوزيع العشوائي للمستخدمين على الملفات
    all_names = list(valid_names_data.keys())
    random.shuffle(all_names)

    total_names = len(all_names)
    names_per_file = total_names // NUMBER_OF_FILES
    remainder = total_names % NUMBER_OF_FILES

    print(f"إجمالي الأسماء المؤهلة (8 فيديوهات فأكثر): {total_names}")
    print(f"النسب التي تم اختيارها وتطبيقها على الجميع (داخل الـ 60%): {[round(r, 2) for r in selection_ratios]}")

    current_idx = 0
    file_summary = {}

    for i in range(NUMBER_OF_FILES):
        # حساب كم اسم سيأخذ هذا الملف
        needed_names = names_per_file + (1 if i < remainder else 0)
        chunk_names = all_names[current_idx : current_idx + needed_names]
        current_idx += needed_names
        
        file_num = START_INDEX + i
        full_file_name = f"{BASE_FILENAME}{file_num}.json"
        file_summary[full_file_name] = chunk_names
        
        all_chunk_videos = []
        for name in chunk_names:
            all_chunk_videos.extend(valid_names_data[name])
            
        # خلط الفيديوهات داخل الملف لإنشاء منافسات عشوائية
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

    # طباعة التقرير النهائي
    print("-" * 50)
    print("قائمة الملفات (توزيع عشوائي بحت مع توحيد نسب الفيديوهات):")
    print("-" * 50)
    for file_name, names in file_summary.items():
        print(f"📄 {file_name} | 👥 العدد: {len(names)} | الأسماء: {', '.join(names)}")
        print("-" * 30)

if __name__ == "__main__":
    generate_fair_distributed_competitions()