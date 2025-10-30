import os

# --- الإعدادات ---
# 1. اسم ملف الأحجام من جهازك (الذي قمت برفعه)
WINDOWS_SIZES_FILE = "windows_sizes.txt"

# 2. اسم ملف الأحجام من Codespace
CODESPACE_SIZES_FILE = "codespace_sizes.txt"

# 3. المجلد الذي سيتم الحذف منه في Codespace
TARGET_DIRECTORY_TO_CLEAN = "/workspaces/video_rating_app/insta"

# 4. قائمة لواحق الصور (يجب أن تكون مطابقة للسكريبتات الأخرى)
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff')
# --- نهاية الإعدادات ---

def read_sizes_to_set(filepath):
    """يقرأ ملف الأحجام ويضعه في مجموعة (set) لسرعة المقارنة."""
    sizes = set()
    try:
        with open(filepath, 'r') as f:
            for line in f:
                try:
                    sizes.add(int(line.strip()))
                except ValueError:
                    continue # تجاهل الأسطر الفارغة أو غير الرقمية
    except FileNotFoundError:
        print(f"[!] خطأ: لم يتم العثور على الملف {filepath}. تأكد من وجوده.")
        return None
    return sizes

def main():
    print("[*] بدء عملية المقارنة...")
    
    # قراءة الأحجام من كلا الملفين
    windows_sizes = read_sizes_to_set(WINDOWS_SIZES_FILE)
    codespace_sizes = read_sizes_to_set(CODESPACE_SIZES_FILE)
    
    if windows_sizes is None or codespace_sizes is None:
        return # توقف إذا لم يتم العثور على أحد الملفات

    # إيجاد الأحجام المكررة (المشتركة بين الملفين)
    duplicate_sizes = windows_sizes.intersection(codespace_sizes)
    
    if not duplicate_sizes:
        print("[+] رائع! لم يتم العثور على أي ملفات مكررة بناءً على الحجم.")
        return
        
    print(f"\n[!] تم العثور على {len(duplicate_sizes)} حجم مكرر.")
    print("    هذا يعني أن هناك ملفات بنفس الحجم على جهازك وفي Codespace.")
    
    # طلب تأكيد من المستخدم قبل الحذف
    confirmation = input("\n[?] هل تريد حذف جميع الصور المكررة من الطرفية (Codespace)؟ اكتب 'نعم' للتأكيد: ").strip().lower()
    
    if confirmation != 'نعم':
        print("[*] تم إلغاء العملية. لم يتم حذف أي ملفات.")
        return
        
    # بدء عملية الحذف
    print("\n[*] بدء عملية حذف الملفات المكررة...")
    deleted_count = 0
    for root, dirs, files in os.walk(TARGET_DIRECTORY_TO_CLEAN):
        for filename in files:
            if filename.lower().endswith(IMAGE_EXTENSIONS):
                full_path = os.path.join(root, filename)
                try:
                    file_size = os.path.getsize(full_path)
                    if file_size in duplicate_sizes:
                        os.remove(full_path)
                        print(f"  [-] تم الحذف: {full_path}")
                        deleted_count += 1
                except OSError as e:
                    print(f"[!] لم يتمكن من حذف {full_path}: {e}")

    print(f"\n[+] اكتمل الحذف. تم حذف {deleted_count} ملف مكرر بنجاح.")

if __name__ == "__main__":
    main()