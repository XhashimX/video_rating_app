
import os
import shutil
import sys

# --- تحديد المسارات ---
# المسار إلى ملف النص الذي يحوي أسماء الملفات
list_file_path = "/storage/emulated/0/myhome/video_rating_app/utilities/filtered_elo_videos_A1000 elo tik_titles.txt"

# المسار إلى المجلد الذي يحتوي على الفيديوهات الأصلية
source_dir = "/storage/emulated/0/Download/NS/TikTok/Elo tik/A1000 elo tik"

# المسار إلى المجلد الذي تريد نقل الفيديوهات إليه
dest_dir = "/storage/emulated/0/Download/NS/TikTok/Elo tik/New folder"

print(f"ملف قائمة الفيديوهات: {list_file_path}")
print(f"مجلد المصدر: {source_dir}")
print(f"مجلد الوجهة: {dest_dir}")
print("-" * 30) # خط فاصل

# --- التحقق من وجود مجلد المصدر وملف القائمة ---
if not os.path.isdir(source_dir):
    print(f"خطأ: مجلد المصدر غير موجود: {source_dir}", file=sys.stderr)
    sys.exit(1) # الخروج من السكربت مع رمز خطأ

if not os.path.isfile(list_file_path):
    print(f"خطأ: ملف القائمة غير موجود: {list_file_path}", file=sys.stderr)
    sys.exit(1)

# --- إنشاء مجلد الوجهة إذا لم يكن موجودًا ---
# exist_ok=True تعني أنه لن يحدث خطأ إذا كان المجلد موجودًا بالفعل
try:
    os.makedirs(dest_dir, exist_ok=True)
    print(f"تم التأكد من وجود مجلد الوجهة أو إنشائه: {dest_dir}")
except OSError as e:
    print(f"خطأ: لم يتمكن من إنشاء مجلد الوجهة '{dest_dir}': {e}", file=sys.stderr)
    sys.exit(1)

# --- قراءة أسماء الملفات من الملف النصي ---
try:
    with open(list_file_path, 'r', encoding='utf-8') as f:
        # قراءة كل الأسطر وإزالة المسافات البيضاء الزائدة (مثل سطر جديد \n)
        filenames_to_move = [line.strip() for line in f if line.strip()] # تجاهل الأسطر الفارغة
except FileNotFoundError:
    # هذا يجب ألا يحدث بسبب التحقق أعلاه، لكنه آمن
    print(f"خطأ: ملف القائمة غير موجود (خطأ داخلي): {list_file_path}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"خطأ أثناء قراءة ملف القائمة '{list_file_path}': {e}", file=sys.stderr)
    sys.exit(1)

if not filenames_to_move:
    print("تحذير: ملف القائمة فارغ أو لا يحتوي على أسماء ملفات صالحة. لن يتم نقل أي شيء.")
    sys.exit(0)

print(f"تم العثور على {len(filenames_to_move)} اسم ملف في القائمة.")

# --- عملية نقل الملفات ---
moved_count = 0
not_found_count = 0
error_count = 0

for filename in filenames_to_move:
    # إنشاء المسار الكامل لملف المصدر
    source_file_path = os.path.join(source_dir, filename)
    # إنشاء المسار الكامل لملف الوجهة
    dest_file_path = os.path.join(dest_dir, filename)

    # التحقق مما إذا كان ملف المصدر موجودًا بالفعل
    if os.path.isfile(source_file_path):
        try:
            print(f"جاري نقل: {filename} ...")
            # نقل الملف
            shutil.move(source_file_path, dest_file_path)
            moved_count += 1
            # لا داعي لطباعة تأكيد هنا لتجنب إغراق الشاشة، يمكن إضافتها إذا أردت
        except OSError as e: # يلتقط أخطاء مثل مشاكل الأذونات، القرص ممتلئ، إلخ.
            print(f" !! خطأ أثناء نقل '{filename}': {e}", file=sys.stderr)
            error_count += 1
        except Exception as e: # لأي أخطاء غير متوقعة أخرى
             print(f" !! خطأ غير متوقع أثناء نقل '{filename}': {e}", file=sys.stderr)
             error_count += 1
    else:
        # إذا لم يتم العثور على الملف في مجلد المصدر
        print(f" !! تحذير: الملف '{filename}' لم يتم العثور عليه في المصدر '{source_dir}'.")
        not_found_count += 1

# --- طباعة ملخص العملية ---
print("-" * 30)
print("--- اكتملت العملية ---")
print(f"الملفات التي تم نقلها بنجاح: {moved_count}")
print(f"الملفات المذكورة في القائمة ولكن لم يتم العثور عليها في المصدر: {not_found_count}")
print(f"الأخطاء التي حدثت أثناء عملية النقل: {error_count}")
print("-" * 30)
