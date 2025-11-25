# START: ENTIRE FILE "filter_unique_videos.py"
# -*- coding: utf-8 -*-
import os
import re
from pathlib import Path

# ==============================================================================
# الإعدادات
# ==============================================================================

# 1. ملف الروابط التي تريد تحميلها
INPUT_FILE_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\Names\ids_to_dib.txt"

# 2. مجلد الفيديوهات المحملة فعلياً
VIDEOS_DIRECTORY_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok"

# 3. ملف قاعدة البيانات النصية (الجديد)
# START: MODIFIED SECTION
DATABASE_FILE_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\Names\video_ids_output.txt"
# END: MODIFIED SECTION

# ==============================================================================
# الدوال المساعدة
# ==============================================================================

def extract_id_from_url(url: str) -> str | None:
    """يستخرج ID الفيديو من الرابط"""
    url = url.strip()
    if not url: return None
    try:
        last_part = url.split('/')[-1]
        video_id = last_part.split('.')[0]
        if video_id.isdigit():
            return video_id
    except IndexError:
        return None
    return None

def extract_id_from_filename(filename: str) -> str | None:
    """يستخرج ID الفيديو من اسم الملف"""
    match = re.search(r'\d{11,}', filename)
    if match:
        return match.group(0)
    return None

# ==============================================================================
# السكربت الرئيسي
# ==============================================================================

def main():
    print("=" * 60)
    print("🚀 بدء عملية فلترة الروابط (المجلد + قاعدة البيانات النصية)")
    print("=" * 60)

    input_file = Path(INPUT_FILE_PATH)
    videos_dir = Path(VIDEOS_DIRECTORY_PATH)
    database_file = Path(DATABASE_FILE_PATH)

    # 1. التحقق من الملفات الأساسية
    if not input_file.is_file():
        print(f"❌ خطأ: ملف الروابط غير موجود: {input_file}")
        return

    # 2. قراءة الروابط المراد تحميلها
    print(f"\n[1/4] 🔍 قراءة الروابط من: {input_file.name}")
    url_data = {}
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url:
                    video_id = extract_id_from_url(url)
                    if video_id:
                        url_data[video_id] = url
    except Exception as e:
        print(f"❌ خطأ في قراءة ملف الروابط: {e}")
        return
    print(f"✔️ العدد الكلي للروابط المدخلة: {len(url_data)}")

    # 3. تجميع الـ IDs الموجودة (من المجلد + من الملف النصي)
    print(f"\n[2/4] 📂 تجميع البيانات الموجودة مسبقاً...")
    existing_video_ids = set()

    # أ) المسح من المجلد الفعلي
    if videos_dir.is_dir():
        files_count = 0
        for root, dirs, files in os.walk(videos_dir):
            for filename in files:
                vid_id = extract_id_from_filename(filename)
                if vid_id:
                    existing_video_ids.add(vid_id)
                    files_count += 1
        print(f"   • من المجلد الفعلي: تم العثور على {files_count} ملف.")
    else:
        print(f"   ⚠️ تنبيه: مجلد الفيديوهات غير موجود، سيتم الاعتماد على الملف النصي فقط.")

    # ب) المسح من قاعدة البيانات النصية (video_ids_output.txt)
    # START: MODIFIED SECTION
    if database_file.is_file():
        db_count = 0
        try:
            with open(database_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # النمط هو: 70300131... : username
                    # نقسم السطر عند العلامة ':' ونأخذ الجزء الأول
                    parts = line.split(':')
                    if parts:
                        vid_id = parts[0].strip()
                        # نتأكد أنه رقم وصحيح
                        if vid_id.isdigit() and len(vid_id) > 10:
                            existing_video_ids.add(vid_id)
                            db_count += 1
            print(f"   • من قاعدة البيانات النصية: تم العثور على {db_count} سجل.")
        except Exception as e:
            print(f"   ❌ خطأ أثناء قراءة قاعدة البيانات النصية: {e}")
    else:
        print(f"   ⚠️ تنبيه: ملف قاعدة البيانات النصية غير موجود ({database_file.name}).")
    # END: MODIFIED SECTION

    print(f"   📊 الإجمالي الكلي للفيديوهات الموجودة (بدون تكرار): {len(existing_video_ids)}")

    # 4. المقارنة
    print("\n[3/4] 🔄 جاري الفلترة...")
    unique_urls = []
    for video_id, url in url_data.items():
        # الشرط: إذا لم يكن الـ ID موجوداً في مجموعتنا الشاملة
        if video_id not in existing_video_ids:
            unique_urls.append(url)

    # 5. الحفظ
    if not unique_urls:
        print("\n[4/4] ✅ كل الروابط موجودة مسبقاً. لا يوجد شيء جديد للتحميل.")
    else:
        output_file = input_file.with_name("unique_links_to_download.txt")
        print(f"\n[4/4] 💾 حفظ الروابط الجديدة في: {output_file.name}")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for url in unique_urls:
                    f.write(url + "\n")
            print(f"🎉 تم استخراج {len(unique_urls)} رابط جديد جاهز للتحميل.")
        except Exception as e:
            print(f"❌ خطأ في الحفظ: {e}")

    print("=" * 60)

if __name__ == "__main__":
    main()
# END: ENTIRE FILE "filter_unique_videos.py"