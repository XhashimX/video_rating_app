# START: ENTIRE FILE
# FILE: patcher.py

import requests
import re
import os

# --- الإعدادات ---
# اسم ملف السكربت الأصلي الذي يحتوي على الرابط
SOURCE_FILE_NAME = "s.txt"
# اسم الملف الجديد الذي سيتم إنشاؤه بعد التعديل
OUTPUT_FILE_NAME = "s_modified.js"

# هذا هو الكود الجديد الكامل لدالة loadTagsFromCSV
# سيتم استخدامه لاستبدال الدالة القديمة في السكربت
NEW_FUNCTION_CODE = r"""
async function loadTagsFromCSV() {
    debug('Attempting to load tags from inline data...');
    return new Promise((resolve, reject) => {
        try {
            // نقرأ من المتغير مباشرة بدلاً من طلب الويب
            const lines = LOCAL_CSV_DATA.split('\n');
            const parsedTags = lines.map(line => {
                const parts = line.split(',');
                if (parts.length === 2) {
                    const label = parts[0].trim();
                    const post_count = parseInt(parts[1].trim(), 10);
                    if (label && !isNaN(post_count)) {
                        return { label: label, count: post_count };
                    }
                }
                return null;
            }).filter(tag => tag !== null);

            allLocalTags = parsedTags;
            debug(`Successfully loaded and parsed ${allLocalTags.length} tags from inline data.`);
            resolve();
        } catch (e) {
            console.error("Error parsing local tags from inline data:", e);
            reject(e);
        }
    });
}
"""

def patch_script():
    """
    الدالة الرئيسية التي تقوم بقراءة السكربت الأصلي، تحميل البيانات،
    تعديل الكود، وحفظ الملف الجديد.
    """
    print(f"🚀 بدء معالجة الملف: {SOURCE_FILE_NAME}")

    # 1. قراءة محتوى السكربت الأصلي
    try:
        with open(SOURCE_FILE_NAME, 'r', encoding='utf-8') as f:
            script_content = f.read()
    except FileNotFoundError:
        print(f"❌ خطأ: لم يتم العثور على الملف '{SOURCE_FILE_NAME}'. تأكد من أنه في نفس المجلد.")
        return

    # 2. إيجاد الرابط باستخدام Regular Expressions
    match = re.search(r"const LOCAL_TAGS_CSV_URL = '(.*?)';", script_content)
    if not match:
        print("❌ خطأ: لم يتم العثور على سطر الرابط (LOCAL_TAGS_CSV_URL) في السكربت.")
        return
    
    tags_url = match.group(1)
    url_line_to_replace = match.group(0) # السطر الكامل الذي يحتوي على الرابط
    print(f"    ✓ تم العثور على الرابط: {tags_url[:50]}...")

    # 3. تحميل محتوى ملف الـ tags
    try:
        print("    📥 جاري تحميل محتوى الـ tags من الرابط...")
        response = requests.get(tags_url)
        response.raise_for_status()  # التأكد من أن الطلب نجح
        tags_data = response.text
        print(f"    ✓ تم تحميل {len(tags_data.splitlines())} سطر من الـ tags.")
    except requests.exceptions.RequestException as e:
        print(f"❌ خطأ: فشل تحميل البيانات من الرابط. {e}")
        return
        
    # 4. تجهيز الكود الجديد الذي سيتم إضافته
    # سيتم تعليق السطر الأصلي وإضافة المتغير الجديد بعده
    new_code_block = f"""
// {url_line_to_replace}
const LOCAL_CSV_DATA = `
{tags_data.strip()}
`;
"""

    # 5. القيام بعمليات الاستبدال
    print("    🛠️  جاري تعديل السكربت...")
    # أولاً: استبدال سطر الرابط بالكتلة الجديدة
    modified_content = script_content.replace(url_line_to_replace, new_code_block)
    
    # ثانياً: استبدال الدالة القديمة بالجديدة باستخدام re.sub
    # re.DOTALL تجعل . تطابق أي حرف بما في ذلك الأسطر الجديدة
    final_content = re.sub(
        r"async function loadTagsFromCSV\(\) \{.*?\n\s*\}\);",
        NEW_FUNCTION_CODE,
        modified_content,
        flags=re.DOTALL
    )
    print("    ✓ تمت عمليات التعديل بنجاح.")

    # 6. حفظ الملف الجديد
    try:
        with open(OUTPUT_FILE_NAME, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print(f"\n✅ نجحت العملية! تم حفظ السكربت المعدل في ملف: {OUTPUT_FILE_NAME}")
    except IOError as e:
        print(f"❌ خطأ: فشل حفظ الملف الجديد. {e}")

# --- نقطة بداية تشغيل السكربت ---
if __name__ == "__main__":
    patch_script()

# END: ENTIRE FILE