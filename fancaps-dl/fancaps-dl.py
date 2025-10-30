import requests
from bs4 import BeautifulSoup

# --- الإعدادات ---
# هذا هو الرابط الذي سنختبره، كما طلبت تماماً
EPISODE_URL = "https://fancaps.net/anime/episodeimages.php?33035-World_s_End_Harem/Episode_10"

# نحتاج إلى ترويسة (Header) لنبدو كمتصفح حقيقي ونتجنب الحظر
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

print(f"[*] جارٍ فحص الرابط: {EPISODE_URL}")

# --- منطق استخراج روابط الصفحات ---
try:
    # 1. إرسال طلب للحصول على محتوى الصفحة
    response = requests.get(EPISODE_URL, headers=HEADERS)
    # هذا السطر سيطلق خطأ إذا فشل الطلب (مثل خطأ 404 أو 500)
    response.raise_for_status() 

    # 2. تحليل محتوى الصفحة باستخدام BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # 3. البحث عن الروابط وجمعها
    # نستخدم "set" بدلاً من "list" في البداية لتجنب التكرار تلقائياً
    # ونضيف الرابط الأصلي لأنه يمثل الصفحة الأولى (page=1)
    found_pages = {EPISODE_URL}

    # نبحث عن كل الوسوم <a> التي تحتوي على خاصية href
    for link in soup.find_all('a', href=True):
        href_value = link.get('href')
        
        # هذا هو الشرط الذي طلبته: هل الرابط يحتوي على النص المطلوب؟
        if '&page=' in href_value:
            # الروابط في الموقع تكون نسبية (لا تبدأ بـ https://)
            # لذلك نقوم ببناء الرابط الكامل
            full_url = 'https://fancaps.net/anime/' + href_value
            found_pages.add(full_url)
            
    # 4. عرض النتائج
    # نحول الـ set إلى list (قائمة) لنتمكن من ترتيبها
    sorted_pages = sorted(list(found_pages))
    
    print("\n--- النتائج ---")
    print(f"[+] تم العثور على {len(sorted_pages)} صفحة مختلفة.")
    print("قائمة الصفحات التي تم العثور عليها:")
    
    for page_url in sorted_pages:
        print(page_url)

except requests.RequestException as e:
    print(f"[!] حدث خطأ أثناء الاتصال بالموقع: {e}")
except Exception as e:
    print(f"[!] حدث خطأ غير متوقع: {e}")