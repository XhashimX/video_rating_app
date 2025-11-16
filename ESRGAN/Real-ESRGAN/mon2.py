import os
import shutil
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- 1. الإعدادات ---
SOURCE_FOLDER = r"C:\Users\Stark\Downloads"
DESTINATION_FOLDER = r"C:\Users\Stark\Download\myhome\video_rating_app\ESRGAN\Real-ESRGAN\results"

ALLOWED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff')
# --------------------


class NewFileHandler(FileSystemEventHandler):
    """
    هذه الفئة تتعامل الآن مع إنشاء الملفات وإعادة تسميتها.
    """
    # # START: MODIFIED SECTION
    def process_file(self, file_path):
        """
        دالة مركزية لمعالجة الملفات لتجنب تكرار الكود.
        تقوم بفحص الامتداد ونسخ الملف إذا كان صورة.
        """
        filename = os.path.basename(file_path)
        
        # التحقق من امتداد الملف
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            print(f"📄 ملف تم تجاهله (ليس صورة): {filename}")
            return

        print(f"🖼️ صورة جديدة تم اكتشافها: {filename}")
        
        # ننتظر قليلاً للتأكد من اكتمال كتابة/إعادة تسمية الملف
        time.sleep(1)

        try:
            if os.path.exists(file_path):
                print(f"⏳ جارٍ نسخ الصورة إلى: {DESTINATION_FOLDER}...")
                shutil.copy2(file_path, os.path.join(DESTINATION_FOLDER, filename))
                print(f"✅ تم نسخ الصورة بنجاح: {filename}")
            else:
                print(f"⚠️ تم حذف الصورة المصدر '{filename}' قبل أن يتم نسخها.")
        except Exception as e:
            print(f"❌ حدث خطأ أثناء نسخ الصورة '{filename}': {e}")

    def on_created(self, event):
        """
        يتم استدعاؤها عند إنشاء ملف جديد مباشرة (مثل حفظ صورة من محرر).
        """
        if event.is_directory:
            return
        self.process_file(event.src_path)

    def on_moved(self, event):
        """
        يتم استدعاؤها عند إعادة تسمية ملف (هذا ما يحدث بعد اكتمال التحميل).
        """
        if event.is_directory:
            return
        # نحن نهتم بالمسار الجديد للملف بعد إعادة التسمية
        self.process_file(event.dest_path)
    # # END: MODIFIED SECTION


def start_watching():
    """
    الدالة الرئيسية لإعداد وبدء عملية المراقبة.
    """
    if not os.path.isdir(SOURCE_FOLDER):
        print(f"خطأ: المجلد المصدر غير موجود: {SOURCE_FOLDER}")
        return
    if not os.path.isdir(DESTINATION_FOLDER):
        print(f"خطأ: المجلد الهدف غير موجود: {DESTINATION_FOLDER}")
        return

    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, SOURCE_FOLDER, recursive=False)

    print("=====================================================")
    print(f"🚀 [بدء المراقبة] يتم الآن مراقبة المجلد بحثًا عن صور جديدة:")
    print(f"   المصدر: {SOURCE_FOLDER}")
    print(f"   الوجهة: {DESTINATION_FOLDER}")
    print(f"   الامتدادات المسموحة: {', '.join(ALLOWED_EXTENSIONS)}")
    print("=====================================================")
    print("السكريبت يعمل الآن في الخلفية... اضغط (Ctrl+C) لإيقافه.")

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 [إيقاف] تم إيقاف عملية المراقبة.")
        observer.stop()
    
    observer.join()


if __name__ == "__main__":
    start_watching()