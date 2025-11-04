# --- استيراد المكتبات اللازمة ---
import os
import glob
import cv2
import numpy as np

# --- 1. الإعدادات ---
# تحديد أسماء المجلدات. يمكنك تغييرها بسهولة من هنا.
INPUT_FOLDER = 'options\m'
ESRGAN_FOLDER = 'output'
COMPARISON_FOLDER = 'results_comparison' # مجلد لحفظ النتائج النهائية

# --- 2. المنطق الرئيسي للسكريبت ---
def main():
    """
    الدالة الرئيسية التي تنفذ كل شيء.
    """
    print("🚀 بدء عملية دمج الصور (بتكبير الصورة الأصغر ارتفاعًا)...")

    # التأكد من وجود مجلد النتائج، وإنشائه إذا لم يكن موجودًا
    if not os.path.exists(COMPARISON_FOLDER):
        os.makedirs(COMPARISON_FOLDER)
        print(f"📁 تم إنشاء مجلد النتائج: {COMPARISON_FOLDER}")

    # الحصول على قائمة مسارات الملفات من كلا المجلدين وترتيبها لضمان التطابق
    input_list = sorted(glob.glob(os.path.join(INPUT_FOLDER, '*')))
    esrgan_list = sorted(glob.glob(os.path.join(ESRGAN_FOLDER, '*')))

    # التحقق من أن المجلدات ليست فارغة
    if not input_list or not esrgan_list:
        print(f"❌ خطأ: أحد المجلدين '{INPUT_FOLDER}' أو '{ESRGAN_FOLDER}' فارغ. يرجى وضع الصور في المجلدين.")
        return

    # التحقق من تطابق عدد الملفات
    if len(input_list) != len(esrgan_list):
        print(f"⚠️ تحذير: عدد الملفات غير متطابق. مجلد الإدخال: {len(input_list)}, مجلد الإخراج: {len(esrgan_list)}")

    # المرور على كل زوج من الصور ودمجها
    for input_path, esrgan_path in zip(input_list, esrgan_list):
        print(f"\n- جاري معالجة: {os.path.basename(input_path)}")
        
        # قراءة الصورتين
        img_input = cv2.imread(input_path)
        img_esrgan = cv2.imread(esrgan_path)

        # التحقق من تحميل الصور بنجاح
        if img_input is None or img_esrgan is None:
            print(f"   ...❌ خطأ في قراءة أحد الملفين، تم التخطي.")
            continue
            
        # # START: MODIFIED SECTION
        # --- توحيد ارتفاع الصورتين عن طريق تكبير الصورة الأصغر ---
        h_input, w_input, _ = img_input.shape
        h_esrgan, w_esrgan, _ = img_esrgan.shape

        # مقارنة الارتفاعات لتحديد أي صورة سيتم تكبيرها
        if h_input < h_esrgan:
            print(f"   - الصورة الأصلية أصغر ({h_input}px). سيتم تكبيرها لتطابق ارتفاع المحسنة ({h_esrgan}px).")
            # حساب العرض الجديد للحفاظ على نسبة الأبعاد
            new_w = int(w_input * (h_esrgan / h_input))
            # تكبير الصورة الأصلية. INTER_CUBIC هي خوارزمية تكبير جيدة.
            img_input = cv2.resize(img_input, (new_w, h_esrgan), interpolation=cv2.INTER_CUBIC)
        
        elif h_esrgan < h_input:
            print(f"   - الصورة المحسنة أصغر ({h_esrgan}px). سيتم تكبيرها لتطابق ارتفاع الأصلية ({h_input}px).")
            # حساب العرض الجديد للحفاظ على نسبة الأبعاد
            new_w = int(w_esrgan * (h_input / h_esrgan))
            # تكبير الصورة المحسنة
            img_esrgan = cv2.resize(img_esrgan, (new_w, h_input), interpolation=cv2.INTER_CUBIC)
        
        # إذا كان الارتفاع متطابقًا بالفعل، لن يتم فعل أي شيء
        # # END: MODIFIED SECTION

        # --- دمج الصورتين أفقيًا ---
        # بما أن الارتفاع أصبح متطابقًا، يمكن استخدام hstack مباشرة
        try:
            combined_image = np.hstack((img_input, img_esrgan))
        except cv2.error as e:
            print(f"   ...❌ خطأ أثناء الدمج. التفاصيل: {e}")
            continue

        # --- حفظ الصورة المدمجة ---
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_filename = f"{base_name}_comparison.jpg"
        output_path = os.path.join(COMPARISON_FOLDER, output_filename)

        cv2.imwrite(output_path, combined_image)
        print(f"   ✅ تم حفظ الصورة المدمجة في: {output_path}")

    print("\n🎉 اكتملت عملية دمج جميع الصور بنججاح.")

# هذا السطر يضمن أن الدالة main() تعمل فقط عندما يتم تشغيل الملف مباشرة
if __name__ == "__main__":
    main()