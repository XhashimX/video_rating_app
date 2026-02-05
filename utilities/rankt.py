import json
import os
import math

# مسار الملف الذي يحتوي على المسابقات
input_file = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\topcut_elo_videos_A1000 elo tik_612.json"
base_dir = os.path.dirname(input_file)

base_name = "topcut_elo_videos_A1000 elo tik_"

# الإعدادات المطلوبة
start_index = 2100         # رقم البداية
step = 4                    # مقدار الزيادة (القفزة) في التسمية
competitions_per_file = 4   # كل ملف يحتوي 8 مسابقات

# قراءة الملف الأصلي
try:
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"❌ الخطأ: الملف غير موجود في المسار:\n{input_file}")
    exit()

# ضبط num_videos تلقائياً حسب عدد الفيديوهات الحقيقي (تحسين إضافي)
for comp in data:
    comp["num_videos"] = len(comp.get("videos", []))

# حساب عدد الملفات المطلوبة
total = len(data)
num_files = math.ceil(total / competitions_per_file)

created_files = []

for i in range(num_files):
    start = i * competitions_per_file
    end = start + competitions_per_file
    chunk = data[start:end]
    
    if not chunk:
        continue

    # حساب الرقم بناءً على البداية والقفزة (7760, 7764, 7768...)
    idx = start_index + (i * step)
    
    filename = f"{base_name}{idx}.json"
    out_path = os.path.join(base_dir, filename)

    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(chunk, out, ensure_ascii=False, indent=4)

    created_files.append(idx)

# طباعة النتائج
print(f"✅ تم إنشاء {len(created_files)} ملف(ملفات) بنجاح:")
for idx in created_files:
    print(f" - {base_name}{idx}.json")

# إنشاء نص الأرشفة بالنمط المطلوب
archive_entries = []
for idx in created_files:
    archive_entries.append(
        f'    "{base_name}{idx}": {{\n'
        f'        "initial_participants": 32\n'
        f'    }}'
    )

archive_text = "},\n" + ",\n".join(archive_entries) + "\n}"

print("\n=== نص الأرشيف (لنسخه) ===\n")
print(archive_text)

# حفظ نص الأرشيف في ملف نصي لسهولة الوصول إليه
archive_filename = f"archive_list_{created_files[0]}_to_{created_files[-1]}.txt"
archive_file_path = os.path.join(base_dir, archive_filename)

with open(archive_file_path, "w", encoding="utf-8") as af:
    af.write(archive_text)

print(f"\n✅ تم حفظ ملف نص الأرشيف في:\n{archive_file_path}")