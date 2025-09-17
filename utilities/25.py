import json
import os
from collections import defaultdict

# المسارات
competition_file = "/storage/emulated/0/myhome/video_rating_app/utilities/topcut_elo_videos_A1000 elo tik_3234.json"
reference_file = "/storage/emulated/0/myhome/video_rating_app/utilities/elo_videos_A1000 elo tik.json"

# تحميل الملفات
with open(competition_file, "r", encoding="utf-8") as f:
    competitions = json.load(f)

with open(reference_file, "r", encoding="utf-8") as f:
    reference_data = json.load(f)

# إنشاء lookup حسب الحجم
size_to_name = {}
for vid, info in reference_data.items():
    size = info["file_size"]
    name = info["name"]
    size_to_name[size] = name

# إحصاء عدد الفيديوهات لكل اسم
name_counter = defaultdict(int)
total_videos = 0

for comp in competitions:
    sizes = comp["file_size"]
    for sz in sizes:
        name = size_to_name.get(sz, "UNKNOWN")
        name_counter[name] += 1
        total_videos += 1

# حساب النسبة المئوية لكل اسم
result = {}
for name, count in name_counter.items():
    percent = (count / total_videos) * 100
    result[name] = round(percent, 2)

# طباعة النتيجة
for name, percent in result.items():
    print(f"{name}: {percent}%")
