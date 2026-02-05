import os
import shutil

# المسار الرئيسي
names_directory = r"C:\Users\Stark\Download\myhome\video_rating_app\Names"

# -------------------------------------------------------------------------
# الأمر الأول: حذف جميع الصور من المجلدات الفرعية فقط
# -------------------------------------------------------------------------
def delete_images_in_subdirs():
    print("\n--- Start: Deleting Images from Subdirectories ---")
    
    # صيغ الصور المستهدفة للحذف
    image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif')
    
    deleted_count = 0
    
    # المرور على جميع المجلدات والملفات
    for root, dirs, files in os.walk(names_directory):
        # تخطي المجلد الرئيسي (نريد حذف صور المجلدات الفرعية فقط)
        if root == names_directory:
            continue
            
        for file in files:
            if file.lower().endswith(image_extensions):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting {file}: {e}")

    print(f"--- Finished. Deleted {deleted_count} images. ---\n")

# -------------------------------------------------------------------------
# الأمر الثاني: نسخ (وليس نقل) جميع الفيديوهات إلى مجلد واحد جديد
# -------------------------------------------------------------------------
def copy_all_videos_to_folder(destination_folder):
    print(f"\n--- Start: Copying Videos to '{destination_folder}' ---")
    
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
        
    # جميع صيغ الفيديو المحتملة
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.3gp', '.ts')
    
    copied_count = 0
    
    for root, dirs, files in os.walk(names_directory):
        # تخطي المجلد الرئيسي إذا كنت لا تريد نسخ الفيديوهات "غير المصنفة" الموجودة فيه
        # (إذا كنت تريد نسخ فيديوهات الروت أيضاً، احذف السطرين التاليين)
        if root == names_directory:
            continue
            
        for file in files:
            if file.lower().endswith(video_extensions):
                source_path = os.path.join(root, file)
                
                # تحديد مسار الوجهة
                dest_path = os.path.join(destination_folder, file)
                
                # معالجة تكرار الأسماء (إذا كان الملف موجوداً مسبقاً، نغير اسمه)
                base, extension = os.path.splitext(file)
                counter = 1
                while os.path.exists(dest_path):
                    new_filename = f"{base}_{counter}{extension}"
                    dest_path = os.path.join(destination_folder, new_filename)
                    counter += 1
                
                try:
                    # shutil.copy2 ينسخ الملف مع الحفاظ على البيانات الوصفية (التاريخ، الخ)
                    shutil.copy2(source_path, dest_path)
                    print(f"Copied: {file} -> {os.path.basename(dest_path)}")
                    copied_count += 1
                except Exception as e:
                    print(f"Error copying {file}: {e}")

    print(f"--- Finished. Copied {copied_count} videos. ---\n")

# -------------------------------------------------------------------------
# التشغيل
# -------------------------------------------------------------------------

if __name__ == "__main__":
    # 1. تنفيذ حذف الصور
    delete_images_in_subdirs()
    
    # 2. تنفيذ نسخ الفيديوهات
    # حدد هنا المسار الذي تريد تجميع الفيديوهات فيه
    target_copy_folder = r"C:\Users\Stark\Download\myhome\video_rating_app\All_Collected_Videos"
    
    copy_all_videos_to_folder(target_copy_folder)