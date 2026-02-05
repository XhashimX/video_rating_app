import json
import os
import math

# المسار الجديد
input_file = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\topcut_elo_videos_A1000 elo tik_523.json"
base_dir = os.path.dirname(input_file)

base_name = "topcut_elo_videos_A1000 elo tik_"
start_index = 1034
competitions_per_file = 8   # كل ملف يحتوي 8 مسابقات

# قراءة الملف الأصلي
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# ضبط num_videos تلقائياً حسب عدد الفيديوهات الحقيقي
for comp in data:
    comp["num_videos"] = len(comp.get("videos", []))

# حساب عدد الملفات
total = len(data)
num_files = math.ceil(total / competitions_per_file)

created_files = []
for i in range(num_files):
    start = i * competitions_per_file
    end = start + competitions_per_file
    chunk = data[start:end]
    if not chunk:
        continue

    idx = start_index + i
    filename = f"{base_name}{idx}.json"
    out_path = os.path.join(base_dir, filename)

    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(chunk, out, ensure_ascii=False, indent=4)

    created_files.append(idx)

print(f"✅ تم إنشاء {len(created_files)} ملف(ملفات):")
for idx in created_files:
    print(f" - {base_name}{idx}.json")

# إنشاء نص الأرشفة
archive_entries = []
for idx in created_files:
    archive_entries.append(
        f'    "topcut_elo_videos_A1000 elo tik_{idx}": {{\n'
        f'        "initial_participants": 32\n'
        f'    }}'
    )

archive_text = "},\n" + ",\n".join(archive_entries) + "\n}"

print("\n=== نص الأرشيف ===\n")
print(archive_text)

archive_file = os.path.join(
    base_dir,
    f"archive_topcut_elo_tik_{created_files[0]}to{created_files[-1]}.txt"
)
with open(archive_file, "w", encoding="utf-8") as af:
    af.write(archive_text)

print(f"\n✅ تم حفظ ملف الأرشيف في:\n{archive_file}")