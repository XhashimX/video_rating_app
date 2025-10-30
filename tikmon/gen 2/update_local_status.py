# START: ENTIRE FILE "update_local_status.py"

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
from typing import Set

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("خطأ: مكتبة 'BeautifulSoup' غير موجودة.")
    print("الرجاء تثبيتها باستخدام الأمر: pip install beautifulsoup4")
    sys.exit(1)

# --- الإعدادات ---
# تأكد من أن هذا المسار يطابق المسار في ملف tracker.py
LOCAL_VIDEOS_PATH = "C:/Users/Stark/Download/myhome/video_rating_app/NS/TikTok"
HTML_FILE = "index.html"
# START: MODIFIED SECTION - إضافة اسم ملف الإخراج النصي
OUTPUT_TEXT_FILE = "local_videos_found.txt"
# END: MODIFIED SECTION
# -----------------

def scan_local_videos(path: str) -> Set[str]:
    """
    يقوم بمسح المجلد المحلي وكل المجلدات الفرعية ويستخرج كل أرقام التعريف المحتملة للفيديوهات.
    """
    print("\n" + "="*70)
    print("                   🔍 بدء مسح الملفات المحلية...")
    print("="*70)
    print(f"   • المسار الهدف: {path}")

    local_ids = set()
    if not os.path.isdir(path):
        print(f"   • ⚠️ تحذير: المسار '{path}' غير موجود. سيتم تخطي عملية المسح.")
        return local_ids

    start_time = time.time()
    file_count = 0

    # استخدام os.walk للمرور على كل المجلدات والملفات الفرعية
    for root, _, files in os.walk(path):
        for filename in files:
            file_count += 1
            # البحث عن أي تسلسل من 18 إلى 20 رقماً في اسم الملف
            # هذا التعبير مرن ويجد رقم التعريف حتى لو كان جزءاً من اسم أطول
            found_ids = re.findall(r'(\d{18,20})', filename)
            if found_ids:
                local_ids.update(found_ids)
            
            if file_count % 2000 == 0:
                print(f"      - تم مسح {file_count} ملف...")

    end_time = time.time()
    print("\n   • ✅ اكتمل المسح بنجاح!")
    print(f"      - تم فحص {file_count} ملف.")
    print(f"      - تم العثور على {len(local_ids)} رقم تعريف فريد.")
    print(f"      - استغرقت العملية {end_time - start_time:.2f} ثانية.")
    print("="*70)

    return local_ids

def update_html_file(html_path: str, local_ids: Set[str]):
    """
    يقرأ ملف HTML، ويضيف علامة 'local' للفيديوهات الموجودة محلياً، ويسجلها في ملف نصي.
    """
    print("\n" + "="*70)
    print(f"                   🎨 تحديث ملف '{html_path}'...")
    print("="*70)

    if not os.path.exists(html_path):
        print(f"   • ❌ خطأ: ملف '{html_path}' غير موجود. لا يمكن المتابعة.")
        return

    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
    except Exception as e:
        print(f"   • ❌ خطأ أثناء قراءة أو تحليل ملف HTML: {e}")
        return

    video_cards = soup.find_all('div', class_='video-card')
    if not video_cards:
        print("   • ⚠️ لم يتم العثور على أي فيديوهات في ملف HTML.")
        return

    print(f"   • تم العثور على {len(video_cards)} فيديو في الصفحة.")
    
    update_count = 0
    # START: MODIFIED SECTION - إنشاء قائمة لتخزين الفيديوهات التي تم العثور عليها
    found_videos_log = []
    # END: MODIFIED SECTION

    for card in video_cards:
        id_element = card.find('div', string=re.compile(r'ID: \d+'))
        if not id_element:
            continue
        
        match = re.search(r'\d+', id_element.get_text())
        if not match:
            continue
        
        video_id = match.group(0)

        if video_id in local_ids:
            current_classes = card.get('class', [])
            if 'local' not in current_classes:
                card['class'].append('local')
                update_count += 1
            
            # START: MODIFIED SECTION - إضافة معلومات الفيديو إلى القائمة
            # استخراج اسم المستخدم من القسم الأب لتوفير سياق أفضل
            username = "unknown_user"
            user_section = card.find_parent('div', class_='user-section')
            if user_section and user_section.get('id'):
                # استخراج الاسم من 'user-username'
                username = user_section['id'].replace('user-', '')
            
            found_videos_log.append(f"User: {username.ljust(20)} | Video ID: {video_id}")
            # END: MODIFIED SECTION
    
    # START: MODIFIED SECTION - كتابة القائمة إلى الملف النصي بعد انتهاء الحلقة
    if found_videos_log:
        try:
            with open(OUTPUT_TEXT_FILE, 'w', encoding='utf-8') as f:
                f.write(f"# قائمة بالفيديوهات التي تم العثور عليها محلياً ({len(found_videos_log)} فيديو)\n")
                f.write(f"# تاريخ الإنشاء: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60 + "\n")
                # فرز القائمة أبجدياً حسب اسم المستخدم لتكون منظمة
                for line in sorted(found_videos_log):
                    f.write(line + "\n")
            print(f"   • 📝 تم العثور على {len(found_videos_log)} فيديو محلي، وتم حفظ القائمة في ملف '{OUTPUT_TEXT_FILE}'.")
        except Exception as e:
            print(f"   • ❌ خطأ أثناء كتابة ملف السجل النصي: {e}")
    # END: MODIFIED SECTION

    if update_count > 0:
        print(f"   • سيتم تحديث {update_count} فيديو في ملف HTML كـ 'موجود محلياً'.")
        print("   • حفظ التغييرات...")
        try:
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            print("   • ✅ تم حفظ الملف بنجاح!")
        except Exception as e:
            print(f"   • ❌ خطأ أثناء حفظ ملف HTML: {e}")
    else:
        print("   • ✅ لا توجد تحديثات جديدة لملف HTML. كل شيء على ما يرام.")

    print("="*70)

def main():
    """الدالة الرئيسية لتشغيل السكربت."""
    script_start_time = time.time()
    print("\n*** أداة تحديث حالة الفيديوهات المحلية في ملف HTML ***")

    local_video_ids = scan_local_videos(LOCAL_VIDEOS_PATH)

    if local_video_ids:
        update_html_file(HTML_FILE, local_video_ids)
    else:
        print("\nلم يتم العثور على أي أرقام تعريف محلية، لذا سيتم تخطي تحديث HTML.")
    
    script_end_time = time.time()
    print("\n✨ اكتملت العملية كلها بنجاح!")
    print(f"   - الزمن الكلي: {script_end_time - script_start_time:.2f} ثانية.\n")


if __name__ == "__main__":
    main()

# END: ENTIRE FILE "update_local_status.py"