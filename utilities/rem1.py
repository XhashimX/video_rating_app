
import json
import argparse
import os
import sys

# --- إعداد استقبال اسم الملف من سطر الأوامر ---
parser = argparse.ArgumentParser(description="استخراج العناوين (المفاتيح) من ملف JSON إلى ملف نصي.")
# إضافة حجة إجبارية لاسم ملف الإدخال
parser.add_argument("json_file", help="المسار إلى ملف الإدخال JSON.")
# تحليل الحجج التي تم تمريرها
args = parser.parse_args()
input_filename = args.json_file

# --- تحديد اسم ملف الإخراج ---
# أخذ اسم الملف الأساسي بدون الامتداد
base_name = os.path.splitext(os.path.basename(input_filename))[0]
# إنشاء اسم ملف الإخراج بإضافة "_titles.txt"
output_filename = f"{base_name}_titles.txt"

print(f"جاري معالجة ملف JSON: {input_filename}")
print(f"سيتم كتابة المخرجات إلى: {output_filename}")

try:
    # --- فتح وقراءة ملف JSON ---
    # استخدم 'utf-8' لضمان قراءة الأحرف العربية والرموز بشكل صحيح
    with open(input_filename, 'r', encoding='utf-8') as f_in:
        # --- تحليل بيانات JSON ---
        data = json.load(f_in)

    # التأكد من أن البيانات المحملة هي قاموس (الشكل المتوقع)
    if not isinstance(data, dict):
        print(f"خطأ: ملف JSON '{input_filename}' لا يحتوي على كائن (قاموس) في المستوى الأعلى.", file=sys.stderr)
        sys.exit(1) # الخروج مع رمز خطأ

    # --- استخراج المفاتيح (العناوين) ---
    titles = list(data.keys())

    if not titles:
        print("تحذير: ملف JSON فارغ أو يحتوي على كائن فارغ. لم يتم العثور على عناوين.")
        # يمكنك اختيار إنشاء ملف فارغ أو الخروج هنا

    # --- فتح ملف الإخراج للكتابة ---
    with open(output_filename, 'w', encoding='utf-8') as f_out:
        # --- كتابة العناوين في الملف النصي ---
        # كل عنوان في سطر جديد
        for title in titles:
            f_out.write(title + '\n')

    print(f"تم بنجاح استخراج {len(titles)} عنوان إلى الملف {output_filename}")

# --- معالجة الأخطاء المحتملة ---
except FileNotFoundError:
    print(f"خطأ: ملف الإدخال غير موجود: {input_filename}", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError:
    print(f"خطأ: تعذر فك ترميز JSON من الملف: {input_filename}. يرجى التأكد من أنه ملف JSON صالح.", file=sys.stderr)
    sys.exit(1)
except PermissionError:
    print(f"خطأ: صلاحيات مرفوضة. لا يمكن قراءة '{input_filename}' أو الكتابة إلى '{output_filename}'.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"حدث خطأ غير متوقع: {e}", file=sys.stderr)
    sys.exit(1)
