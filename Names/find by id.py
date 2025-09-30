# START: MODIFIED SECTION
# -*- coding: utf-8 -*-
import sys
import re
import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed # لاستخدام المعالجة المتزامنة

# اسم ملف المعرفات المحذوفة
DELETED_IDS_FILE = "deleted_ids.txt"
# اسم ملف الإدخال الثابت
INPUT_FILE = "video_ids.txt"

def load_deleted_ids():
    """
    يحمل المعرفات المخزنة في ملف المعرفات المحذوفة.

    Returns:
        set: مجموعة من المعرفات التي لا يمكن العثور على أسماء مستخدمين لها.
    """
    deleted_ids = set()
    if os.path.exists(DELETED_IDS_FILE):
        try:
            with open(DELETED_IDS_FILE, 'r') as f:
                for line in f:
                    deleted_ids.add(line.strip())
        except IOError as e:
            print(f"تحذير: لا يمكن قراءة ملف المعرفات المحذوفة {DELETED_IDS_FILE}: {e}", file=sys.stderr)
    return deleted_ids

def save_deleted_id(video_id):
    """
    يضيف معرف الفيديو إلى ملف المعرفات المحذوفة.
    """
    try:
        with open(DELETED_IDS_FILE, 'a') as f: # 'a' لفتح الملف للكتابة في نهايته (append)
            f.write(f"{video_id}\n")
    except IOError as e:
        print(f"خطأ: لا يمكن الكتابة إلى ملف المعرفات المحذوفة {DELETED_IDS_FILE}: {e}", file=sys.stderr)

def get_tiktok_username(video_id):
    """
    يستخرج اسم المستخدم (username) من فيديو تيك توك باستخدام Video ID.

    Args:
        video_id (str): معرف الفيديو (Video ID) لتيك توك.

    Returns:
        tuple: (video_id, username) إذا تم العثور عليه، أو (video_id, None) إذا لم يتم العثور عليه.
    """
    embed_url = f"https://www.tiktok.com/embed/{video_id}"
    try:
        # زيادة المهلة الزمنية قليلاً لتجنب الأخطاء العشوائية في المهلة
        response = requests.get(embed_url, timeout=15) 
        response.raise_for_status()

        match = re.search(r'https://www\.tiktok\.com/@([a-zA-Z0-9_\.]+)', response.text)

        if match:
            username = match.group(1)
            return (video_id, username)
        else:
            return (video_id, None)
    except requests.exceptions.Timeout:
        return (video_id, None)
    except requests.exceptions.RequestException: # يمكن جمع جميع RequestExceptions هنا
        return (video_id, None)
    except Exception: # أي أخطاء أخرى غير متوقعة
        return (video_id, None)

if __name__ == "__main__":
    # تم تبسيط هذا الجزء بالكامل
    # الآن السكريبت يبحث تلقائياً عن ملف video_ids.txt
    
    if not os.path.isfile(INPUT_FILE):
        print(f"خطأ: ملف الإدخال '{INPUT_FILE}' غير موجود.", file=sys.stderr)
        print("يرجى التأكد من وجود الملف في نفس المجلد الذي يوجد به السكريبت.", file=sys.stderr)
        sys.exit(1)

    # تحميل المعرفات المحذوفة في بداية التشغيل
    deleted_ids = load_deleted_ids()
    print(f"تم تحميل {len(deleted_ids)} معرفات محذوفة/غير صالحة من {DELETED_IDS_FILE}.")
    
    input_file_path = INPUT_FILE
    base_name = os.path.splitext(os.path.basename(input_file_path))[0]
    output_file_name = f"{base_name}_output.txt"

    print(f"جاري معالجة معرفات الفيديو من الملف: {input_file_path} باستخدام 70 عاملاً متزامناً.")
    print(f"سيتم حفظ النتائج الصالحة في الملف: {output_file_name}")
    print(f"سيتم تسجيل المعرفات التي لا يمكن العثور على اسم مستخدم لها في: {DELETED_IDS_FILE}\n")

    # قائمة لتخزين المعرفات التي تحتاج للمعالجة (ليست في deleted_ids)
    ids_to_process = []
    skipped_count = 0

    # قراءة المعرفات من الملف وتصفيتها
    try:
        with open(input_file_path, 'r') as infile:
            for line_num, line in enumerate(infile, 1):
                video_id = line.strip()
                if not video_id:
                    continue
                if video_id in deleted_ids:
                    skipped_count += 1
                else:
                    ids_to_process.append(video_id)
    except IOError as e:
        print(f"خطأ: لا يمكن قراءة ملف الإدخال {input_file_path}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"تم العثور على {len(ids_to_process)} معرفات جديدة للمعالجة، وتجاوز {skipped_count} معرفة سابقة.")
    if not ids_to_process:
        print("لا توجد معرفات جديدة للمعالجة. تم الانتهاء.")
        sys.exit(0)

    # المتغيرات الإحصائية
    processed_count = 0
    found_count = 0
    added_to_deleted_count = 0

    # استخدام ThreadPoolExecutor لمعالجة متزامنة
    # max_workers=70 ليعالج 70 فيديوهات في نفس الوقت
    with ThreadPoolExecutor(max_workers=70) as executor:
        future_to_id = {executor.submit(get_tiktok_username, vid_id): vid_id for vid_id in ids_to_process}

        with open(output_file_name, 'w') as outfile:
            for future in as_completed(future_to_id):
                processed_count += 1
                sys.stdout.write(f"\rجاري معالجة: {processed_count}/{len(ids_to_process)} ID (تم العثور: {found_count}, تم الإضافة للمحذوف: {added_to_deleted_count})")
                sys.stdout.flush()

                video_id, username = future.result()

                if username:
                    outfile.write(f"{video_id} : {username}\n")
                    found_count += 1
                else:
                    if video_id not in deleted_ids:
                        deleted_ids.add(video_id)
                        save_deleted_id(video_id)
                        added_to_deleted_count += 1

    print("\n\nتمت المعالجة بنجاح.")
    print(f"إجمالي معرفات الفيديو التي تم العثور عليها في الملف: {len(ids_to_process) + skipped_count}")
    print(f"معرفات الفيديو التي تم تجاهلها (موجودة في {DELETED_IDS_FILE}): {skipped_count}")
    print(f"معرفات الفيديو التي تم معالجتها فعلياً: {processed_count}")
    print(f"معرفات الفيديو التي تم العثور على أسماء مستخدمين لها: {found_count}")
    print(f"معرفات الفيديو الجديدة التي لم يتم العثور على أسماء مستخدمين لها وتمت إضافتها إلى {DELETED_IDS_FILE}: {added_to_deleted_count}")
    print(f"النتائج الصالحة محفوظة في الملف: {output_file_name}")
    print(f"المعرفات غير الصالحة/المحذوفة موجودة في: {DELETED_IDS_FILE}")
# END: MODIFIED SECTION