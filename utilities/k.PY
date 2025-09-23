# clean_links.py

# --- 1. تحديد مسارات الملفات ---
# المسار الكامل للملف الأصلي الذي يحتوي على البيانات
input_file_path = r"C:\Users\Stark\Download\myhome\results.txt"

# المسار الكامل للملف الجديد الذي سنحفظ فيه النتائج النظيفة
# سيتم إنشاؤه في نفس المجلد
output_file_path = r"C:\Users\Stark\Download\myhome\cleaned_results.txt"


# --- 2. بدء عملية المعالجة ---
print("Starting the cleaning process...")

try:
    # استخدام 'with' يضمن إغلاق الملفات تلقائياً حتى لو حدث خطأ
    # نستخدم encoding='utf-8' لضمان التعامل الصحيح مع أي رموز أو أحرف خاصة في الروابط
    with open(input_file_path, 'r', encoding='utf-8') as infile, \
         open(output_file_path, 'w', encoding='utf-8') as outfile:
        
        # متغيرات لتتبع عدد الأسطر التي تمت معالجتها
        lines_processed = 0
        links_kept = 0
        
        # قراءة الملف الأصلي سطراً بسطر
        for line in infile:
            lines_processed += 1
            
            # التحقق من وجود الفاصل ' -> ' في السطر لتجنب الأسطر الفارغة أو الخاطئة
            if ' -> ' not in line:
                print(f"  - Skipping malformed line {lines_processed}: {line.strip()}")
                continue # انتقل إلى السطر التالي

            # تقسيم السطر إلى جزأين عند الفاصل
            # نستخدم maxsplit=1 لضمان التقسيم مرة واحدة فقط حتى لو كان الرابط يحتوي على '->'
            part1, part2 = line.split(' -> ', 1)
            
            # تنظيف الجزأين من أي مسافات فارغة في البداية أو النهاية
            part1 = part1.strip()
            part2 = part2.strip()
            
            # تطبيق المنطق الذي طلبته
            if part2 == "ERROR":
                # إذا كان الجزء الثاني هو "ERROR"، احتفظ بالجزء الأول
                link_to_keep = part1
            else:
                # في كل الحالات الأخرى، احتفظ بالجزء الثاني (الرابط الصحيح)
                link_to_keep = part2
            
            # كتابة الرابط الذي تم اختياره في الملف الجديد، مع إضافة سطر جديد بعده
            outfile.write(link_to_keep + '\n')
            links_kept += 1

    # --- 3. عرض رسالة نجاح عند الانتهاء ---
    print("\n--- Process Complete! ---")
    print(f"Total lines read from input file: {lines_processed}")
    print(f"Total links saved to output file: {links_kept}")
    print(f"The cleaned links have been saved to: {output_file_path}")

except FileNotFoundError:
    print(f"\nERROR: The input file was not found at the specified path.")
    print(f"Please make sure this file exists: {input_file_path}")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")