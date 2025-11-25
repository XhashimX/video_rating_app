import json
import os
import random
import math

# === تعديل المسارات والأسماء هنا إذا لزم ===
input_file = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\topcut_elo_videos_A1000 elo tik_8099.json"
base_dir = os.path.dirname(input_file)
base_name = "topcut_elo_videos_A1000 elo tik_"
start_index = 8836      # يبدأ من 8836 كما طلبت
index_step = 4          # الفواصل بين الأسماء: 8836, 8840, 8844, ...
competitions_per_file = 8   # كل ملف يحتوي 8 مسابقات
pair_size = 2           # كل مسابقة جديدة تحتوي على 2 فيديو (كما في الأصل)

# === اقرأ الملف الأصلي ===
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# === اجمع كل الفيديوهات (مع rating و file_size) في قائمة مفردة ===
items = []  # كل عنصر: (video, rating, file_size)
for comp in data:
    vids = comp.get("videos", [])
    rats = comp.get("rating", [])
    sizes = comp.get("file_size", [])
    # إذا طول القوائم غير متساوٍ، نملأ بقيم افتراضية إن لزم (الحالة النادرة)
    maxlen = max(len(vids), len(rats), len(sizes))
    for i in range(maxlen):
        v = vids[i] if i < len(vids) else ""
        r = rats[i] if i < len(rats) else 1000.0
        s = sizes[i] if i < len(sizes) else 0
        items.append((v, r, s))

total_items = len(items)
if total_items < pair_size:
    raise SystemExit("لا يوجد فيديوهات كافية لإعادة التجميع.")

# === خلط عشوائي تام لكل الفيديوهات ===
random.shuffle(items)

# === نكوّن مسابقات جديدة بتجميع كل pair_size عناصر معاً ===
new_competitions = []
for i in range(0, (total_items // pair_size) * pair_size, pair_size):
    chunk = items[i:i+pair_size]
    videos = [it[0] for it in chunk]
    ratings = [it[1] for it in chunk]
    file_sizes = [it[2] for it in chunk]

    comp = {
        "videos": videos,
        "rating": ratings,
        "file_size": file_sizes,
        "mode": 1,
        "num_videos": pair_size,
        "ranking_type": "winner_only",
        "competition_type": "random"
    }
    new_competitions.append(comp)

# إذا كانت هناك عنصر واحد زائد (عدد فردي من الفيديوهات)، نحتفظ به في ملف منفصل كتحذير
leftover = total_items % pair_size
if leftover != 0:
    print(f"⚠️ يوجد {leftover} فيديو(هات) متبقية لم تُستخدم لأنها لا تكمل زوجاً من {pair_size} فيديوهات. تم تجاهلها.")

# === تقسيم المسابقات الجديدة إلى ملفات كل ملف يحتوي competitions_per_file مسابقات ===
num_new_comps = len(new_competitions)
num_files = math.ceil(num_new_comps / competitions_per_file)

created_files = []
current_index = start_index
ci = 0
for file_idx in range(num_files):
    start = file_idx * competitions_per_file
    end = start + competitions_per_file
    chunk = new_competitions[start:end]
    if not chunk:
        continue

    filename = f"{base_name}{current_index}.json"
    output_path = os.path.join(base_dir, filename)

    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(chunk, out, ensure_ascii=False, indent=4)

    created_files.append(current_index)
    ci += 1
    current_index += index_step

print(f"✅ تم إنشاء {len(created_files)} ملف(ملفات).")
for idx in created_files:
    print(f" - {base_name}{idx}.json")

# === أنشئ نص الأرشيف بالصّيغة المطلوبة ونطبعها ونحفظها في ملف نصي ===
# ملاحظة: حسب المثال المطلوب، يبدأ النص بـ "},"
archive_entries = []
for idx in created_files:
    archive_entries.append(f'    "topcut_elo_videos_A1000 elo tik_{idx}": {{\n        "initial_participants": 32\n    }}')

archive_text = "},\n" + ",\n".join(archive_entries) + "\n}"

# اطبع للأرشفة
print("\n\n=== نص الأرشيف (انسخه وألصقه حيث تريد) ===\n")
print(archive_text)

# واحفظه في ملف نصي داخل نفس المجلد
archive_file = os.path.join(base_dir, f"archive_topcut_elo_tik_{created_files[0]}_to_{created_files[-1]}.txt")
with open(archive_file, "w", encoding="utf-8") as af:
    af.write(archive_text)

print(f"\n✅ حفظت نص الأرشيف في: {archive_file}")
