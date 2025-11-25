import json
import os
import math

# === تعديل المسارات والأسماء هنا إذا لزم ===
input_file = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\topcut_elo_videos_A1000 elo tik_284.json"
base_dir = os.path.dirname(input_file)
base_name = "topcut_elo_videos_A1000 elo til_"   # اسم الملفات المطلوبة (لاحظ "til" كما طلبت)
start_index = 8061
chunk_size = 4   # كل ملف يحتوي 4 مسابقات

# اقرأ الملف الأصلي
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

total = len(data)
num_files = math.ceil(total / chunk_size)

archive_entries = []

for i in range(num_files):
    start = i * chunk_size
    end = start + chunk_size
    chunk = data[start:end]
    if not chunk:
        continue

    filename = f"{base_name}{start_index + i}.json"
    output_path = os.path.join(base_dir, filename)

    # اكتب القطعة إلى الملف الجديد
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(chunk, out, ensure_ascii=False, indent=4)

    archive_entries.append(f'"{base_name}{start_index + i}": {{\n        "initial_participants": 32\n    }}')

print(f"✅ تم تقسيم الملف إلى {num_files} ملف(ملفات).")
print("الملفات المُنشأة:")
for i in range(num_files):
    print(f" - {base_name}{start_index + i}.json")

# أنشئ نص الأرشيف بالصّيغة المطلوبة (يبدأ بعد قوس إغلاق سابق لذلك نبدؤه بـ "},")
archive_text = "},\n" + ",\n".join([f"    {entry}" for entry in archive_entries]) + "\n}"
# طباعة الأرشيف على الشاشة
print("\n\n=== نص الأرشيف (انسخه وألصقه حيث تريد) ===\n")
print(archive_text)

# احفظ الأرشيف في ملف نصي داخل نفس المجلد (اختياري ومفيد)
archive_file = os.path.join(base_dir, "archive_topcut_elo_{}_{}.txt".format(start_index, start_index+num_files-1))
with open(archive_file, "w", encoding="utf-8") as af:
    af.write(archive_text)

print(f"\n✅ كما حفظت نص الأرشيف في: {archive_file}")
