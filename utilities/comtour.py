import json
import glob
import os

# المسارات
tournament_file = "/storage/emulated/0/myhome/video_rating_app/utilities/tournamentarchive.json"
elo_files_pattern = "/storage/emulated/0/myhome/video_rating_app/utilities/elo_videos_*.json"

# تحميل ملف tournamentarchive.json
with open(tournament_file, "r", encoding="utf-8") as f:
    tournament_data = json.load(f)

# إنشاء قاموس: {file_size: video_name} من ملفات elo_videos_*
size_to_name = {}
for elo_file in glob.glob(elo_files_pattern):
    with open(elo_file, "r", encoding="utf-8") as f:
        elo_data = json.load(f)
        for video_name, video_info in elo_data.items():
            size_to_name[video_info["file_size"]] = video_name

# تعديل أسماء الفيديوهات في ملف tournamentarchive.json
for tournament_name, details in tournament_data.items():
    for key in ["top1", "top2", "top3", "top4"]:
        if key in details:
            size = details[key]["file_size"]
            if size in size_to_name:
                details[key]["video"] = size_to_name[size]

# حفظ التعديلات
with open(tournament_file, "w", encoding="utf-8") as f:
    json.dump(tournament_data, f, ensure_ascii=False, indent=4)

print("تم تحديث أسماء الفيديوهات في", tournament_file)