# START: MODIFIED SECTION
import os
import re
from collections import defaultdict

FOLDER = r"C:\Users\Stark\Download\myhome\video_rating_app\ESRGAN\Real-ESRGAN\results"
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')

def extract_base_filename(filename):
    """
    استخراج الاسم الأساسي بدون لاحقة أو signature:
    مثلاً: 4ZBSV21CQG0JHX8BP4JN46G9Q0_3fc3a8c1.jpeg → 4ZBSV21CQG0JHX8BP4JN46G9Q0
    """
    name_no_ext = os.path.splitext(filename)[0]
    match = re.match(r'^(.+)_([0-9a-f]{8})$', name_no_ext, re.IGNORECASE)
    return match.group(1) if match else name_no_ext

def cleanup_duplicates_by_name_keep_largest(folder_path):
    # خطوة 1: تجميع جميع الملفات حسب الاسم الأساسي
    files_by_base = defaultdict(list)
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(IMAGE_EXT):
            base_name = extract_base_filename(filename)
            full_path = os.path.join(folder_path, filename)
            size = os.path.getsize(full_path)
            files_by_base[base_name].append({"filename": filename, "size": size})

    total_deleted = 0
    print("\nنتائج الحذف حسب الاسم الأساسي:\n")

    for base_name, file_list in files_by_base.items():
        if len(file_list) > 1:
            # ترتيب الملفات تنازلي حسب الحجم (الأكبر أولاً)
            sorted_files = sorted(file_list, key=lambda f: f['size'], reverse=True)
            # إبقاء الأول (الأكبر)
            to_keep = sorted_files[0]['filename']
            print(f"\n[مجموعة] {base_name} - عدد الملفات: {len(file_list)}")
            print(f"  >> يتم الاحتفاظ بـ: {to_keep} ({sorted_files[0]['size']} bytes)")

            # حذف الباقي
            for file_info in sorted_files[1:]:
                file_for_delete = os.path.join(folder_path, file_info['filename'])
                try:
                    os.remove(file_for_delete)
                    print(f"  ❌ تم حذف: {file_info['filename']} ({file_info['size']} bytes)")
                    total_deleted += 1
                except Exception as e:
                    print(f"  ⚠️ فشل حذف {file_info['filename']}: {e}")
    print(f"\n✅ الحذف مكتمل! عدد الملفات المحذوفة: {total_deleted}")

# --- تشغيل السكريبت ---
if __name__ == "__main__":
    cleanup_duplicates_by_name_keep_largest(FOLDER)
# END: MODIFIED SECTION
