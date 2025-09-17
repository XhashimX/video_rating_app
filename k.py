import os
import sys

# --- الإعدادات ---
# الجزء القديم من المسار الذي نريد البحث عنه
OLD_PATH_PART = 'C:/Users/Stark/Download/myhome/video_rating_app/'

# الجزء الجديد من المسار الذي نريد الاستبدال به
# ملاحظة: استخدمنا الشرطة المائلة للأمام لتجنب المشاكل في بايثون
NEW_PATH_PART = 'C:/Users/Stark/Download/myhome/video_rating_app/'

# امتدادات الملفات التي سيتم فحصها وتعديلها
FILE_EXTENSIONS_TO_CHECK = ('.py', '.html', '.css', '.js', '.json', '.txt')
# -----------------

def find_and_replace_download_paths():
    """
    يبحث في المشروع عن المسارات التي تبدأ من مجلد التحميلات في أندرويد
    ويستبدلها بالمسار الجديد الصحيح في ويندوز.
    """
    project_root = os.getcwd()
    print(f"[*] بدء عملية البحث والاستبدال عن مسارات التحميل في: {project_root}")
    
    total_files_scanned = 0
    total_files_modified = 0
    total_replacements = 0

    for root, dirs, files in os.walk(project_root):
        if 'venv' in dirs:
            dirs.remove('venv')
            print(f"[*] تم تجاهل المجلد: {os.path.join(root, 'venv')}")

        for filename in files:
            if filename.endswith(FILE_EXTENSIONS_TO_CHECK):
                file_path = os.path.join(root, filename)
                total_files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        original_content = f.read()
                    
                    # قم بالاستبدال
                    new_content = original_content.replace(OLD_PATH_PART, NEW_PATH_PART)
                    
                    if new_content != original_content:
                        # احسب عدد التغييرات في هذا الملف
                        replacements_in_file = original_content.count(OLD_PATH_PART)
                        total_replacements += replacements_in_file
                        
                        print(f"[+] تم تعديل {replacements_in_file} مسار(ات) في الملف: {file_path}")
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        total_files_modified += 1
                        
                except Exception as e:
                    print(f"[!] حدث خطأ أثناء معالجة الملف {file_path}: {e}")

    print("\n--- اكتملت العملية ---")
    print(f"[*] إجمالي الملفات التي تم فحصها: {total_files_scanned}")
    print(f"[*] إجمالي الملفات التي تم تعديلها: {total_files_modified}")
    print(f"[*] إجمالي المسارات التي تم استبدالها: {total_replacements}")
    if total_files_modified == 0:
        print("[*] لم يتم العثور على أي مسارات تبدأ بـ 'C:/Users/Stark/Download/myhome/video_rating_app/'.")

if __name__ == '__main__':
    print("="*60)
    print("تحذير: هذا السكريبت سيقوم بتعديل المسارات التي تبدأ من مجلد Download.")
    print(f"سيتم استبدال كل ظهور للمسار:\n  '{OLD_PATH_PART}'\nبالمسار:\n  '{NEW_PATH_PART}'")
    print("="*60)
    
    confirm = input("هل أنت متأكد أنك تريد المتابعة؟ (اكتب 'نعم' للتنفيذ): ")
    if confirm.lower() == 'نعم':
        find_and_replace_download_paths()
    else:
        print("تم إلغاء العملية بناءً على طلبك.")