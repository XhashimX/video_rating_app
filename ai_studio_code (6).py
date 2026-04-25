import os
import shutil
import cv2  # For video dimensions
from PIL import Image  # For image dimensions
from collections import defaultdict

# ================= إعدادات المسار =================
# ضع المسار الخاص بك هنا
SOURCE_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik"

# أسماء المجلدات التي سيتم إنشاؤها
FOLDER_SIZE_ONLY = os.path.join(SOURCE_DIR, "_Check_By_Size")
FOLDER_EXACT_MATCH = os.path.join(SOURCE_DIR, "_Check_By_Size_And_Dim")

# امتدادات الصور والفيديو المدعومة
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}

def get_dimensions(file_path):
    """
    دالة لاستخراج أبعاد الملف (صورة أو فيديو)
    تعيد (العرض, الطول) أو None إذا فشلت
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext in IMAGE_EXTS:
            with Image.open(file_path) as img:
                return img.size # returns (width, height)
        
        elif ext in VIDEO_EXTS:
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                return (width, height)
    except Exception as e:
        print(f"Error reading dimensions for {file_path}: {e}")
    
    return None

def copy_files(file_list, destination_folder, prefix_type="Size"):
    """
    دالة لنسخ الملفات إلى المجلد الجديد مع إعادة تسميتها لتجنب التصادم
    """
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    for i, file_path in enumerate(file_list):
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # نضع حجم الملف في بداية الاسم لكي تظهر الملفات المتشابهة بجانب بعضها عند الترتيب بالاسم
        # مثال: [1024bytes]_1_video.mp4
        new_name = f"[{file_size}b]_{i}_{filename}"
        dest_path = os.path.join(destination_folder, new_name)
        
        try:
            shutil.copy2(file_path, dest_path)
            print(f"Copied to {prefix_type}: {new_name}")
        except Exception as e:
            print(f"Failed to copy {filename}: {e}")

def main():
    print("--- Start Scanning ---")
    
    # 1. تجميع الملفات حسب الحجم (Size Map)
    size_map = defaultdict(list)
    
    for root, dirs, files in os.walk(SOURCE_DIR):
        # نتجاهل مجلدات النتائج حتى لا نعيد فحصها إذا شغلت السكريبت مرتين
        if "_Check_By_" in root:
            continue
            
        for file in files:
            file_path = os.path.join(root, file)
            try:
                size = os.path.getsize(file_path)
                if size > 0: # تجاهل الملفات الفارغة
                    size_map[size].append(file_path)
            except OSError:
                continue

    # فلتر النتائج: نريد فقط الأحجام التي تكررت أكثر من مرة
    potential_duplicates = {k: v for k, v in size_map.items() if len(v) > 1}
    
    print(f"Found {len(potential_duplicates)} groups of files with identical sizes.")

    # 2. المعالجة والنسخ
    files_to_copy_size_only = []
    files_to_copy_exact = []

    for size, paths in potential_duplicates.items():
        # أضف المجموعة لقائمة "الحجم فقط"
        # نقوم بتسطيح القائمة (flatten) لاحقاً، هنا نجمع كل المسارات
        files_to_copy_size_only.extend(paths)

        # الآن نفحص الأبعاد داخل هذه المجموعة
        dim_map = defaultdict(list)
        for path in paths:
            dims = get_dimensions(path)
            if dims:
                # المفتاح هنا هو (الحجم + الأبعاد)
                dim_map[dims].append(path)
            else:
                # إذا لم نستطع قراءة الأبعاد، نضعها في مفتاح "unknown"
                dim_map["unknown"].append(path)

        # إذا وجدنا ملفات تتطابق في الحجم والأبعاد، نضيفها للقائمة الثانية
        for dim_key, dim_paths in dim_map.items():
            if len(dim_paths) > 1:
                files_to_copy_exact.extend(dim_paths)

    # 3. تنفيذ النسخ الفعلي
    if files_to_copy_size_only:
        print(f"\nCopying {len(files_to_copy_size_only)} files to Size-Only folder...")
        copy_files(files_to_copy_size_only, FOLDER_SIZE_ONLY, "SizeOnly")
    else:
        print("No duplicates found by size.")

    if files_to_copy_exact:
        print(f"\nCopying {len(files_to_copy_exact)} files to Exact-Match (Size+Dim) folder...")
        copy_files(files_to_copy_exact, FOLDER_EXACT_MATCH, "Exact")
    else:
        print("No exact matches found.")

    print("\n--- Done! Check the folders inside your directory ---")

if __name__ == "__main__":
    main()