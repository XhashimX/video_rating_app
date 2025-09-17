import os
import sys # قد تحتاجها، لكن os.path.basename(__file__) أفضل

output_file = "merged.txt"
# الحصول على اسم ملف السكريبت الحالي
script_filename = os.path.basename(__file__)

with open(output_file, "w", encoding="utf-8") as outfile:
    for filename in os.listdir():
        # التحقق مما إذا كان الملف ينتهي بـ .py أو .html
        # والتحقق أيضاً من أنه ليس ملف السكريبت الحالي نفسه
        if (filename.endswith(".py") or filename.endswith(".html")) and filename != script_filename:
            try: # إضافة try-except للتعامل مع أي مشاكل في قراءة ملف (مثل عدم وجود صلاحيات)
                with open(filename, "r", encoding="utf-8") as infile:
                    outfile.write(f":{filename}\n\n")
                    outfile.write(infile.read())
                    outfile.write("\n----\n")
            except Exception as e:
                # يمكنك طباعة رسالة هنا إذا لم يتمكن السكريبت من قراءة ملف معين
                print(f"لم يتمكن من قراءة الملف {filename}: {e}")


print(f"تم دمج الملفات في {output_file}")