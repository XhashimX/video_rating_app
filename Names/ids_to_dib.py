# -*- coding: utf-8 -*-
import os
import re
from pathlib import Path

# ==============================================================================
# 1. الإعدادات - قم بتغيير هذه المسارات لتناسب جهازك
# ==============================================================================

# المسار الكامل لملف txt الذي يحتوي على روابط تيك توك
# ملاحظة: حرف 'r' قبل النص يمنع بايثون من التعامل مع '\' كحرف خاص
INPUT_FILE_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\Names\ids_to_dib.txt"

# المسار الكامل للمجلد الرئيسي الذي يحتوي على فيديوهاتك المحملة
VIDEOS_DIRECTORY_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok"


# ==============================================================================
# 2. الدوال المساعدة - لا تحتاج لتعديل هذا الجزء
# ==============================================================================

# START: MODIFIED SECTION
def extract_id_from_url(url: str) -> str | None:
    """
    يستخرج رقم الـ ID من رابط تيك توك.
    أمثلة: 
    '.../video/7526880825388928274' -> '7526880825388928274'
    '.../hdplay/7554553515532668215.mp4' -> '7554553515532668215'
    """
    url = url.strip()
    if not url:
        return None
    
    try:
        # 1. خذ الجزء الأخير من الرابط بعد آخر علامة '/'
        last_part = url.split('/')[-1]
        
        # 2. افصل هذا الجزء عند أول نقطة '.' لإزالة امتداد الملف مثل .mp4
        #    سيؤدي هذا إلى تحويل '755...215.mp4' إلى '755...215'
        #    وإذا لم يكن هناك نقطة، سيبقى النص كما هو '752...274'
        video_id = last_part.split('.')[0]

        # 3. التحقق من أن الجزء المتبقي هو رقم بالفعل
        if video_id.isdigit():
            return video_id
    except IndexError:
        return None # في حال كان الرابط فارغاً أو غير صالح
    return None
# END: MODIFIED SECTION

def extract_id_from_filename(filename: str) -> str | None:
    """
    يستخرج رقم الـ ID من اسم ملف معقد.
    يبحث عن أول سلسلة أرقام متتالية يزيد طولها عن 10 أرقام.
    """
    # التعبير النمطي (Regex) للبحث عن 11 رقمًا أو أكثر على التوالي
    # \d{11,}  تعني: ابحث عن أي رقم (\d) مكرر 11 مرة أو أكثر ({11,})
    match = re.search(r'\d{11,}', filename)
    
    if match:
        # إذا تم العثور على تطابق، قم بإرجاع السلسلة الرقمية التي تم العثور عليها
        return match.group(0)
    
    return None # إذا لم يتم العثور على تطابق

# ==============================================================================
# 3. السكربت الرئيسي - يقوم بتنفيذ المنطق
# ==============================================================================

def main():
    """الوظيفة الرئيسية لتشغيل السكربت"""
    print("=" * 60)
    print("🚀 بدء عملية فلترة روابط تيك توك المكررة")
    print("=" * 60)

    # تحويل النصوص إلى كائنات Path للتعامل مع المسارات بشكل أفضل
    input_file = Path(INPUT_FILE_PATH)
    videos_dir = Path(VIDEOS_DIRECTORY_PATH)

    # --- الخطوة 1: التحقق من وجود الملف والمجلد ---
    if not input_file.is_file():
        print(f"❌ خطأ: لم يتم العثور على ملف الروابط في المسار:\n{input_file}")
        return
    
    if not videos_dir.is_dir():
        print(f"❌ خطأ: لم يتم العثور على مجلد الفيديوهات في المسار:\n{videos_dir}")
        return

    # --- الخطوة 2: قراءة ملف الروابط واستخراج أرقام الـ ID ---
    print(f"\n[1/4] 🔍 جاري قراءة الروابط من ملف: {input_file.name}")
    url_data = {} # سنستخدم قاموس لتخزين الرابط مع الـ ID الخاص به
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url:
                    video_id = extract_id_from_url(url)
                    if video_id:
                        url_data[video_id] = url
    except Exception as e:
        print(f"❌ حدث خطأ أثناء قراءة الملف: {e}")
        return

    print(f"✔️ تم العثور على {len(url_data)} رابط صالح.")

    # --- الخطوة 3: مسح مجلد الفيديوهات واستخراج أرقام الـ ID الموجودة ---
    print(f"\n[2/4] 📂 جاري مسح مجلد الفيديوهات وجميع المجلدات الفرعية...")
    
    # نستخدم Set لتخزين أرقام الـ ID الموجودة لأنها أسرع في البحث وتمنع التكرار
    existing_video_ids = set()
    total_files_scanned = 0

    # os.walk يقوم بالمرور على المجلد وجميع المجلدات الفرعية تلقائياً
    for root, dirs, files in os.walk(videos_dir):
        for filename in files:
            total_files_scanned += 1
            video_id = extract_id_from_filename(filename)
            if video_id:
                existing_video_ids.add(video_id)
    
    print(f"✔️ تم مسح {total_files_scanned} ملف والعثور على {len(existing_video_ids)} فيديو محمل بالفعل.")

    # --- الخطوة 4: تحديد الروابط الفريدة (الجديدة) ---
    print("\n[3/4] 🔄 جاري مقارنة القوائم وتحديد الروابط الجديدة...")
    
    unique_urls_to_download = []
    for video_id, url in url_data.items():
        # إذا كان ID الفيديو غير موجود في مجموعة الفيديوهات المحملة، فهو رابط جديد
        if video_id not in existing_video_ids:
            unique_urls_to_download.append(url)

    total_urls = len(url_data)
    total_unique = len(unique_urls_to_download)
    total_duplicates = total_urls - total_unique
    
    print(f"✔️ المقارنة انتهت:")
    print(f"   - إجمالي الروابط: {total_urls}")
    print(f"   - روابط مكررة (موجودة): {total_duplicates}")
    print(f"   - روابط فريدة (جديدة): {total_unique}")

    # --- الخطوة 5: كتابة الروابط الفريدة في ملف جديد ---
    if not unique_urls_to_download:
        print("\n[4/4] ✅ لا توجد روابط جديدة لتحميلها. كل شيء محدث!")
    else:
        # تحديد اسم ومسار الملف الجديد بجوار الملف الأصلي
        output_file = input_file.with_name("unique_links_to_download.txt")
        print(f"\n[4/4] 💾 جاري كتابة الروابط الجديدة في ملف: {output_file.name}")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for url in unique_urls_to_download:
                    f.write(url + "\n")
            print(f"✔️ تم حفظ {total_unique} رابط جديد بنجاح في المسار:\n{output_file}")
        except Exception as e:
            print(f"❌ حدث خطأ أثناء كتابة الملف الجديد: {e}")

    print("\n" + "=" * 60)
    print("🎉 اكتملت العملية بنجاح!")
    print("=" * 60)


if __name__ == "__main__":
    main()