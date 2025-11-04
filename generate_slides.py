# Directness_and_Efficiency: Providing the complete script first.

import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

# --- الإعدادات ---
HTML_FILE_PATH = '1.html' # اسم ملف HTML الذي تريد تحليله
OUTPUT_DIR = 'atomic_elements_output_v2' # اسم مجلد جديد للمخرجات

# الحد الأدنى لأبعاد العنصر ليتم تصويره
MIN_WIDTH = 2
MIN_HEIGHT = 2

# START: MODIFIED SECTION
# --- الإضافة الجديدة: قائمة بالكلاسات التي يجب تجاهلها ---
# هذه هي العناصر الهيكلية أو الخلفيات التي لا نريد تصويرها بشكل منفصل
CLASSES_TO_EXCLUDE = [
    'bg-overlay', 
    'bg-accent',
    'slide-container', # تجاهل الحاوية الرئيسية نفسها
    'icon-container'   # هذه حاوية للعنصر الجزيئي، نريد الأجزاء الداخلية فقط
]
# END: MODIFIED SECTION

def sanitize_filename(text):
    """
    يزيل الرموز غير الصالحة من النص لإنشاء اسم ملف آمن.
    """
    if not text:
        return "notext"
    text = re.sub(r'\s+', ' ', text)
    return re.sub(r'[\\/*?:"<>|]', "", text)

# --- إعداد متصفح Chrome ---
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--window-size=1920,1200") 

# إنشاء مجلد المخرجات
os.makedirs(OUTPUT_DIR, exist_ok=True)
html_full_path = 'file://' + os.path.abspath(HTML_FILE_PATH)

# --- بدء التحكم بالمتصفح ---
print("🚀 بدء تشغيل Selenium والتحكم في متصفح Chrome...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # 1. افتح ملف HTML
    driver.get(html_full_path)
    time.sleep(2) 
    print(f"📄 تم تحميل الملف: {HTML_FILE_PATH}")

    # 2. إيجاد كل عنصر في الصفحة
    all_elements = driver.find_elements(By.CSS_SELECTOR, '*')
    print(f"🔍 تم العثور على {len(all_elements)} عنصر بشكل إجمالي. جارٍ الفلترة...")
    
    atomic_elements_to_capture = []
    
    # 3. الفلترة الذكية لتحديد "أصغر الأجزاء"
    for element in all_elements:
        # القاعدة 1: هل هو عنصر طرفي (لا يحتوي على عناصر أخرى)؟
        children = element.find_elements(By.XPATH, "./*")
        if children:
            continue

        # START: MODIFIED SECTION
        # --- القاعدة الجديدة: هل ينتمي هذا العنصر إلى قائمة التجاهل؟ ---
        class_attr = element.get_attribute('class')
        if class_attr:
            element_classes = class_attr.split()
            if any(cls in element_classes for cls in CLASSES_TO_EXCLUDE):
                continue # تخطى هذا العنصر لأنه في قائمة التجاهل
        # END: MODIFIED SECTION

        # القاعدة 2: هل هو مرئي على الصفحة؟
        if not element.is_displayed():
            continue

        # القاعدة 3: هل له حجم فعلي؟
        size = element.size
        if size['width'] < MIN_WIDTH or size['height'] < MIN_HEIGHT:
            continue
            
        atomic_elements_to_capture.append(element)
    
    print(f"🖼️ تم العثور على {len(atomic_elements_to_capture)} جزء صغير وقابل للتصوير...")

    # 4. قم بالمرور على كل جزء صغير وتصويره
    for i, element in enumerate(atomic_elements_to_capture):
        try:
            # إنشاء اسم ملف وصفي
            tag_name = element.tag_name
            class_name = element.get_attribute('class').split(' ')[0] if element.get_attribute('class') else ''
            text_content = sanitize_filename(element.text[:25].strip())
            
            # اجعل اسم الملف أكثر تميزاً
            filename = f"{i+1:04d}_{tag_name}_{class_name}_{text_content}.png"
            output_path = os.path.join(OUTPUT_DIR, filename)
            
            element.screenshot(output_path)
            
            print(f"  ✅ ({i+1}/{len(atomic_elements_to_capture)}) تم حفظ: {output_path}")
        except Exception as e:
            print(f"  ❌ ({i+1}/{len(atomic_elements_to_capture)}) فشل في تصوير عنصر. الخطأ: {e}")

    print(f"\n🎉 اكتملت العملية بنجاح! تم حفظ الصور في مجلد '{OUTPUT_DIR}'.")

finally:
    # 5. أغلق المتصفح دائماً في النهاية
    driver.quit()
    print("🛑 تم إغلاق المتصفح.")