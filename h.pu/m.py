# START: MODIFIED SECTION
# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import csv

# --- الإعدادات ---
INPUT_FILENAME = 'video_ids.txt'
OUTPUT_FILENAME = 'final_results.csv'

print("جاري تشغيل المتصفح في الخلفية...")
options = webdriver.ChromeOptions()
options.add_argument("--headless") 
options.add_argument("--log-level=3") 
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
print("تم تشغيل المتصفح.")

def get_username_with_selenium(video_id):
    """
    النسخة النهائية التي تبحث عن وصف الصورة (alt attribute) بدلاً من النص المرئي.
    """
    url = f"https://urlebird.com/video/{video_id}/"
    
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        
        # التعديل: أصبحنا نبحث مباشرة عن الصورة التي بداخل الرابط
        # العنوان الآن يعني: "ابحث عن صورة (img) لها كلاس (user) موجودة بداخل رابط (a) له كلاس (user-video)"
        image_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "a.user-video img.user")))
        
        # التعديل: بدلاً من قراءة النص، نقرأ محتوى خاصية 'alt'
        alt_text = image_element.get_attribute('alt')
        
        if alt_text and alt_text.startswith('@'):
            # نزيل علامة @ من بداية النص
            username = alt_text.lstrip('@')
            return username
        else:
            # في حال كانت خاصية alt فارغة أو لا تبدأ بـ @
            return "USERNAME_FORMAT_UNEXPECTED_IN_ALT"

    except TimeoutException:
        return "ELEMENT_NOT_FOUND_TIMEOUT"
    except Exception as e:
        return f"AN_ERROR_OCCURRED: {type(e).__name__}"

def main():
    try:
        with open(INPUT_FILENAME, 'r') as f:
            video_ids = [line.strip() for line in f if line.strip()]
        print(f"تم العثور على {len(video_ids)} فيديو لمعالجتها.")
    except FileNotFoundError:
        print(f"خطأ فادح: لم يتم العثور على الملف '{INPUT_FILENAME}'.")
        driver.quit()
        return

    results = []
    for index, video_id in enumerate(video_ids):
        print(f"({index + 1}/{len(video_ids)}) جاري معالجة ID: {video_id}")
        
        username = get_username_with_selenium(video_id)
        
        results.append({
            'video_id': video_id,
            'username': username
        })
        print(f"  -> اسم المستخدم: {username}")

    with open(OUTPUT_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['video_id', 'username']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nاكتملت العملية بنجاح! تم حفظ النتائج في ملف '{OUTPUT_FILENAME}'.")
    
    driver.quit()

if __name__ == "__main__":
    main()
# END: MODIFIED SECTION