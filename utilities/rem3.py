import json
import os
import sys

# --- تحديد المسارات ---
json_file_path = "C:/Users/Stark/Download/myhome/video_rating_app/utilities/elo_videos_New folder.json"
video_dir = "C:/Users/Stark/Download/myhome/video_rating_app/NS/TikTok/Elo tik/New folder"
target_tag = "Re" # الوسم المطلوب للفلترة (غير حساس لحالة الأحرف)

print(f"ملف بيانات JSON: {json_file_path}")
print(f"مجلد الفيديوهات: {video_dir}")
print(f"الوسم المطلوب للاحتفاظ به: '{target_tag}'")
print("-" * 30)

# --- التحقق من وجود الملف والمجلد ---
if not os.path.isfile(json_file_path):
    print(f"خطأ: ملف JSON غير موجود: {json_file_path}", file=sys.stderr)
    sys.exit(1)

if not os.path.isdir(video_dir):
    print(f"خطأ: مجلد الفيديوهات غير موجود: {video_dir}", file=sys.stderr)
    sys.exit(1)

# --- قراءة وتحليل ملف JSON ---
try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        print(f"خطأ: ملف JSON '{json_file_path}' لا يحتوي على كائن (قاموس) في المستوى الأعلى.", file=sys.stderr)
        sys.exit(1)
except json.JSONDecodeError:
    print(f"خطأ: تعذر فك ترميز JSON من الملف: {json_file_path}. تأكد من أنه ملف JSON صالح.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"خطأ غير متوقع أثناء قراءة ملف JSON: {e}", file=sys.stderr)
    sys.exit(1)

# --- تحديد الملفات التي تحمل الوسم المطلوب والملفات الأخرى ---
files_to_keep = []
files_to_potentially_delete = []
all_json_files = list(data.keys()) # قائمة بكل الملفات المذكورة في JSON

for filename, metadata in data.items():
    # تحقق من وجود مفتاح 'tags' وأن القيمة ليست فارغة
    tag_value = metadata.get("tags", "") # استخدم .get لتجنب خطأ إذا لم يكن المفتاح موجودًا
    if isinstance(tag_value, str) and tag_value.strip().lower() == target_tag.lower():
        files_to_keep.append(filename)
    else:
        # أضف الملف إلى قائمة الحذف المحتملة فقط إذا كان موجودًا في JSON
        files_to_potentially_delete.append(filename)

# --- عرض الملفات التي سيتم الاحتفاظ بها ---
print("--- الملفات التي تم العثور عليها وتحمل الوسم المطلوب ---")
if not files_to_keep:
    print(f"لم يتم العثور على أي فيديوهات بالوسم '{target_tag}'.")
else:
    for fname in files_to_keep:
        print(f"- {fname}")
print("-" * 30)

# --- التحقق من وجود ملفات للحذف والتأكيد من المستخدم ---
if not files_to_potentially_delete:
    print("لا توجد ملفات أخرى مذكورة في JSON لحذفها من المجلد.")
    sys.exit(0)

print(f"تم العثور على {len(files_to_potentially_delete)} ملفًا مذكورًا في JSON لا يحمل الوسم '{target_tag}'.")
print("سيتم الآن البحث عن هذه الملفات في المجلد وحذفها إذا وُجدت.")
print("\n!!! تحذير: هذه العملية ستحذف الملفات بشكل دائم !!!")

# طلب التأكيد
try:
    # استخدم input() في Python 3
    confirm = input(f"هل أنت متأكد أنك تريد حذف هذه الملفات الـ {len(files_to_potentially_delete)} (التي لا تحمل وسم '{target_tag}') من المجلد '{os.path.basename(video_dir)}'? (اكتب 'نعم' للتأكيد): ").strip().lower()
except EOFError: # التعامل مع حالة عدم وجود إدخال (نادر)
    confirm = "no"

if confirm != "نعم":
    print("تم الإلغاء. لم يتم حذف أي ملفات.")
    sys.exit(0)

# --- عملية الحذف ---
print("\n--- جاري عملية الحذف ---")
deleted_count = 0
not_found_count = 0
error_count = 0

for filename in files_to_potentially_delete:
    file_path_to_delete = os.path.join(video_dir, filename)

    # تحقق مرة أخرى من أن الملف موجود فعليًا قبل محاولة الحذف
    if os.path.isfile(file_path_to_delete):
        try:
            os.remove(file_path_to_delete)
            print(f"تم الحذف: {filename}")
            deleted_count += 1
        except OSError as e:
            print(f" !! خطأ أثناء حذف '{filename}': {e}", file=sys.stderr)
            error_count += 1
        except Exception as e:
            print(f" !! خطأ غير متوقع أثناء حذف '{filename}': {e}", file=sys.stderr)
            error_count += 1
    else:
        # الملف مذكور في JSON ولكن غير موجود في المجلد
        # print(f" - تحذير: الملف '{filename}' غير موجود في المجلد، تم تخطيه.") # يمكنك تفعيل هذا السطر إذا أردت رؤية هذه الرسالة
        not_found_count += 1

# --- طباعة ملخص العملية ---
print("-" * 30)
print("--- اكتملت عملية الحذف ---")
print(f"الملفات التي تم حذفها بنجاح: {deleted_count}")
print(f"الملفات المذكورة في JSON (بدون الوسم المطلوب) ولكن لم يتم العثور عليها في المجلد: {not_found_count}")
print(f"الأخطاء التي حدثت أثناء عملية الحذف: {error_count}")
print(f"الملفات المتبقية (التي تحمل الوسم '{target_tag}'): {len(files_to_keep)}")
print("-" * 30)

