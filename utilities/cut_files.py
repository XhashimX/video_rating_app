import json
import os

# المسار إلى الملف الأصلي
input_file = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\topcut_elo_videos_A1000 elo tik_236.json"

# قراءة الملف الأصلي
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# عدد المسابقات في كل ملف
chunk_size = 16

# المسار إلى المجلد
base_dir = os.path.dirname(input_file)

# الاسم الأساسي للملفات الجديدة
base_name = "topcut_elo_videos_A1000 elo tik_"

# الرقم الابتدائي
start_index = 8047

# تقسيم الملفات وكتابتها
archive_entries = []
for i in range(16):  # 16 ملف
    start = i * chunk_size
    end = start + chunk_size
    chunk = data[start:end]
    if not chunk:
        break

    filename = f"{base_name}{start_index + i}.json"
    output_path = os.path.join(base_dir, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunk, f, indent=4, ensure_ascii=False)

    archive_entries.append(
        f'    "topcut_elo_videos_A1000 elo tik_{start_index + i}": {{\n        "initial_participants": 32\n    }}'
    )

# إنشاء الأرشيف النهائي بنفس الصيغة التي طلبتها
archive_text = "},\n" + ",\n".join(archive_entries) + "\n}"

# طباعة النتيجة أو حفظها في ملف
print(archive_text)
