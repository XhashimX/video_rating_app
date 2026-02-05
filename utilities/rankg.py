import json
import re
import random

input_file = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\tournamentarchive.json"

# المجال المطلوب
START = 1000
END = 1032

video_list = []  # قائمة لتخزين (اسم الفيديو، الحجم)

# 1. قراءة الملف واستخراج البيانات
try:
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for competition_key, competition_data in data.items():
        # استخراج الرقم من اسم المسابقة
        match = re.search(r'_(\d+)$', competition_key)
        if not match:
            continue

        comp_number = int(match.group(1))
        if START <= comp_number <= END:
            for top_key, top_data in competition_data.items():
                if isinstance(top_data, dict) and "file_size" in top_data:
                    size = top_data["file_size"]
                    name = top_data.get("video", "UNKNOWN_NAME.mp4")
                    video_list.append((name, size))

except FileNotFoundError:
    print(f"Error: The file at {input_file} was not found.")
    exit()

# 2. طباعة إحصائيات سريعة (اختياري، للتأكد فقط)
total_size = sum(size for _, size in video_list)
print(f"Found {len(video_list)} videos.")
print(f"Total Size: {round(total_size / (1024**2), 2)} MB")
print("-" * 30)

# 3. الترتيب العشوائي
random.shuffle(video_list)

# 4. بناء هيكل المسابقة (JSON)
final_competitions = []
chunk_size = 4  # عدد الفيديوهات في كل مسابقة

# تقسيم القائمة إلى مجموعات من 4
for i in range(0, len(video_list), chunk_size):
    group = video_list[i : i + chunk_size]
    
    # تجهيز القوائم الداخلية
    videos_names = [item[0] for item in group]
    videos_sizes = [item[1] for item in group]
    
    # توليد تقييمات عشوائية (بين 900 و 1200 مثلاً)
    videos_ratings = [round(random.uniform(900, 1250), 1) for _ in range(len(group))]

    # إنشاء كائن المسابقة
    comp_entry = {
        "videos": videos_names,
        "rating": videos_ratings,
        "file_size": videos_sizes,
        "mode": 1,
        "num_videos": len(group),
        "ranking_type": "winner_only",
        "competition_type": "balanced_random"
    }
    
    final_competitions.append(comp_entry)

# 5. طباعة النتيجة النهائية بصيغة JSON
print(json.dumps(final_competitions, indent=4, ensure_ascii=False))