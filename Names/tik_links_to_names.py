# -*- coding: utf-8 -*-
import os
import re

# ==============================================================================
# 1. الإعدادات - أسماء الملفات المستخدمة
# ==============================================================================

# اسم ملف الإدخال الذي يحتوي على روابط تيك توك الكاملة
INPUT_FILE = "unique_links_to_download.txt"

# اسم ملف المخرجات الذي سيتم إضافة البيانات إليه
OUTPUT_FILE = "video_ids_output.txt"


# ==============================================================================
# 2. الدوال المساعدة
# ==============================================================================

def extract_info_from_url(url: str) -> tuple[str, str] | None:
    """
    يستخرج اسم المستخدم ورقم الفيديو من رابط تيك توك كامل.
    مثال: '.../@username/video/12345' -> ('12345', 'username')
    """
    # التعبير النمطي (Regex) للبحث عن النمط المحدد في الرابط
    # /@([^/]+) : يجد علامة @ ثم يلتقط كل الحروف التالية حتى يصل إلى علامة / (هذا هو اسم المستخدم)
    # /video/(\d+) : يجد كلمة video/ ثم يلتقط كل الأرقام التالية (هذا هو رقم الفيديو)
    match = re.search(r'/@([^/]+)/video/(\d+)', url)
    
    if match:
        username = match.group(1)
        video_id = match.group(2)
        return (video_id, username)
    
    return None

def load_existing_output_ids(output_file: str) -> set:
    """
    يقرأ ملف المخرجات الحالي ويجمع كل أرقام الـ ID الموجودة فيه بالفعل
    لتجنب إضافتها مرة أخرى.
    """
    existing_ids = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if ' : ' in line:
                        video_id = line.split(' : ', 1)[0].strip()
                        if video_id:
                            existing_ids.add(video_id)
        except Exception as e:
            print(f"تحذير: حدث خطأ أثناء قراءة ملف المخرجات الحالي: {e}")
    return existing_ids

# ==============================================================================
# 3. السكربت الرئيسي
# ==============================================================================

def main():
    """الوظيفة الرئيسية لتشغيل السكربت"""
    print("=" * 60)
    print("🚀 بدء عملية استخراج ID واسم المستخدم من الروابط")
    print("=" * 60)

    # --- الخطوة 1: التحقق من وجود ملف الإدخال ---
    if not os.path.isfile(INPUT_FILE):
        print(f"❌ خطأ: لم يتم العثور على ملف الإدخال '{INPUT_FILE}'.")
        print("يرجى التأكد من وجود الملف في نفس المجلد.")
        return

    # --- الخطوة 2: تحميل الـ IDs الموجودة بالفعل في ملف المخرجات لتجنب التكرار ---
    existing_ids = load_existing_output_ids(OUTPUT_FILE)
    print(f"🔍 تم العثور على {len(existing_ids)} مدخل موجود بالفعل في '{OUTPUT_FILE}'. سيتم تجاهلها إذا تكررت.")

    # --- الخطوة 3: قراءة ملف الروابط ومعالجته ---
    print(f"\n🔄 جاري قراءة الروابط من '{INPUT_FILE}'...")
    
    new_entries_found = []
    links_processed = 0
    links_skipped = 0
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                links_processed += 1
                url = line.strip()
                if not url:
                    continue

                info = extract_info_from_url(url)
                
                if info:
                    video_id, username = info
                    # التحقق من أن هذا الـ ID ليس موجوداً بالفعل
                    if video_id not in existing_ids:
                        new_entries_found.append((video_id, username))
                        # نضيفه إلى القائمة الحالية أيضاً لنتجنب تكراره لو كان موجوداً مرتين في ملف الإدخال
                        existing_ids.add(video_id) 
                    else:
                        links_skipped += 1
                else:
                    print(f"   ⚠️ تحذير: تم تجاهل السطر '{url}' لأنه لا يطابق الصيغة المتوقعة.")

    except Exception as e:
        print(f"❌ حدث خطأ أثناء قراءة ملف الإدخال: {e}")
        return

    print(f"✔️ انتهت القراءة. تم معالجة {links_processed} رابط.")
    if links_skipped > 0:
        print(f"   - تم تجاهل {links_skipped} رابط لأنها موجودة بالفعل في المخرجات.")
    
    # --- الخطوة 4: كتابة النتائج الجديدة في ملف المخرجات ---
    if not new_entries_found:
        print("\n✅ لا توجد بيانات جديدة لإضافتها. الملف محدث بالفعل!")
    else:
        print(f"\n💾 جاري إضافة {len(new_entries_found)} مدخل جديد إلى '{OUTPUT_FILE}'...")
        try:
            # نفتح الملف في وضع الإضافة 'a' (append)
            with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                for video_id, username in new_entries_found:
                    f.write(f"{video_id} : {username}\n")
            print(f"✔️ تمت إضافة {len(new_entries_found)} مدخل جديد بنجاح.")
        except Exception as e:
            print(f"❌ حدث خطأ أثناء الكتابة إلى ملف المخرجات: {e}")

    print("\n" + "=" * 60)
    print("🎉 اكتملت العملية بنجاح!")
    print("=" * 60)


if __name__ == "__main__":
    main()