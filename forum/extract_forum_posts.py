import os
from bs4 import BeautifulSoup
from datetime import datetime

# --- الإعدادات ---
# اسم الملف النصي الذي سيتم حفظ النقاشات فيه
OUTPUT_FILENAME = "discussion_archive.txt"
# --- نهاية الإعدادات ---

def parse_post(post_element):
    """
    يستخرج المعلومات من عنصر منشور واحد (اسم المستخدم، التاريخ، والمحتوى).
    """
    try:
        # استخراج اسم المستخدم
        username_tag = post_element.find('h4', class_='message-name').find('span', itemprop='name')
        username = username_tag.text.strip() if username_tag else "Unknown User"

        # استخراج التاريخ والوقت
        time_tag = post_element.find('time', class_='u-dt')
        timestamp_str = time_tag['data-timestamp']
        # تحويل التاريخ من timestamp إلى كائن datetime لسهولة الترتيب
        post_datetime = datetime.fromtimestamp(int(timestamp_str))

        # استخراج محتوى المنشور (النص)
        # يستهدف bbWrapper الذي يحتوي على النص الفعلي للمنشور
        content_wrapper = post_element.find('div', class_='bbWrapper')
        if content_wrapper:
            # إزالة الاقتباسات لتجنب التكرار والحصول على النص الأصلي فقط
            for quote in content_wrapper.find_all('blockquote'):
                quote.decompose()
            content_text = content_wrapper.get_text(separator='\n', strip=True)
        else:
            content_text = "No content found."

        return {
            'username': username,
            'datetime': post_datetime,
            'content': content_text
        }

    except Exception as e:
        print(f"[!] حدث خطأ أثناء تحليل منشور: {e}")
        return None

def main():
    """
    الدالة الرئيسية التي تمسح الملفات، تستخرج، ترتب، وتحفظ المنشورات.
    """
    all_posts = []
    current_directory = '.' # يعني المجلد الحالي

    print("[*] بدء البحث عن ملفات HTML في المجلد الحالي...")

    # البحث عن كل ملفات .html في المجلد الحالي
    html_files = [f for f in os.listdir(current_directory) if f.lower().endswith(('.html', '.htm'))]

    if not html_files:
        print("[!] لم يتم العثور على أي ملفات HTML. تأكد من تشغيل السكريبت في المجلد الصحيح.")
        return

    print(f"[+] تم العثور على {len(html_files)} ملف HTML. بدء عملية الاستخراج...")

    for filename in html_files:
        print(f"    - جاري تحليل الملف: {filename}")
        with open(filename, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml')
            
            # العثور على جميع عناصر المنشورات (posts) في الصفحة
            # الهيكل يعتمد على أن كل منشور هو <article class="message--post">
            post_elements = soup.find_all('article', class_='message--post')
            
            for post_elem in post_elements:
                parsed_data = parse_post(post_elem)
                if parsed_data:
                    all_posts.append(parsed_data)

    if not all_posts:
        print("[!] لم يتم العثور على أي منشورات في الملفات. قد يكون هيكل HTML مختلفًا.")
        return
        
    print(f"\n[+] تم استخراج ما مجموعه {len(all_posts)} منشور بنجاح.")
    
    # الخطوة الحاسمة: ترتيب جميع المنشورات حسب التاريخ والوقت
    print("[*] جاري ترتيب المنشورات زمنيًا...")
    all_posts.sort(key=lambda x: x['datetime'])
    
    # كتابة المنشورات المرتبة إلى ملف نصي
    print(f"[*] جاري كتابة النقاش المرتب في الملف: {OUTPUT_FILENAME}")
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        for post in all_posts:
            # تنسيق التاريخ ليكون سهل القراءة
            formatted_date = post['datetime'].strftime('%Y-%m-%d %H:%M:%S')
            
            f.write("=" * 60 + "\n")
            f.write(f"المستخدم: {post['username']}\n")
            f.write(f"التاريخ:  {formatted_date}\n")
            f.write("-" * 60 + "\n")
            f.write(post['content'] + "\n\n")

    print(f"\n[+] اكتملت العملية! تم حفظ النقاش بالكامل في ملف '{OUTPUT_FILENAME}'.")

if __name__ == "__main__":
    main()