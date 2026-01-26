import json
import os
import math

# تعديل المسار إذا لزم
input_file = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\topcut_elo_videos_A1000 elo tik_414.json"
base_dir = os.path.dirname(input_file)
base_name = "topcut_elo_videos_A1000 elo tik_"
start_index = 7000
competitions_per_file = 8   # كل ملف يحتوي 8 مسابقات

# اقرأ الملف الأصلي
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# تأكد أن كل مسابقة فيها قيمة num_videos صحيحة (نضبطها تلقائياً حسب طول قائمة الفيديوهات)
for comp in data:
    vids = comp.get("videos", [])
    comp["num_videos"] = len(vids)

# أحسب عدد الملفات المطلوبة
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

# اطبع ملخص
print(f"✅ تم إنشاء {len(created_files)} ملف(ملفات):")
for idx in created_files:
    print(f" - {base_name}{idx}.json")

# أنشئ نص الأرشيف المطلوب (يبدأ بـ "},")
archive_entries = []
for idx in created_files:
    archive_entries.append(f'    "topcut_elo_videos_A1000 elo tik_{idx}": {{\n        "initial_participants": 32\n    }}')

archive_text = "},\n" + ",\n".join(archive_entries) + "\n}"

# اطبعه واحفظه كملف نصي داخل نفس المجلد
print("\n\n=== نص الأرشيف (انسخه وألصقه حيث تريد) ===\n")
print(archive_text)

archive_file = os.path.join(base_dir, f"archive_topcut_elo_tik_{created_files[0]}to{created_files[-1]}.txt")
with open(archive_file, "w", encoding="utf-8") as af:
    af.write(archive_text)

print(f"\n✅ تم حفظ نص الأرشيف في: {archive_file}")