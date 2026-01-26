import json
import re

input_file = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\tournamentarchive.json"

# المجال المطلوب
START = 7057
END = 7081

total_size = 0
video_sizes = []

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
                total_size += size
                video_sizes.append((top_data.get("video", "UNKNOWN"), size))

print("عدد الفيديوهات:", len(video_sizes))
print("إجمالي الحجم بالبايت:", total_size)
print("إجمالي الحجم بالميغابايت:", round(total_size / (1024**2), 2))
print("إجمالي الحجم بالغيغابايت:", round(total_size / (1024**3), 3))

print("\nتفاصيل الأحجام:")
for video, size in video_sizes:
    print(f"{video} -> {size}")