import os
import subprocess
import json
import sys

# --- الإعدادات الرئيسية ---
USERS_FILE = 'users.txt'
DATA_FILE = 'tiktok_data.json'
THUMBNAILS_DIR = 'thumbnails'
HTML_REPORT_FILE = 'report.html'
HTML_TEMPLATE_FILE = 'report_template.html'
CONSECUTIVE_LIMIT = 3 # عدد الروابط المكررة التي يتوقف عندها البحث

# --- الدوال المساعدة ---

def load_data():
    """تحميل البيانات القديمة من ملف JSON."""
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # تعيين كل الفيديوهات القديمة على أنها ليست جديدة
            for user in data:
                for video in data[user]['videos']:
                    video['is_new'] = False
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_data(data):
    """حفظ البيانات في ملف JSON."""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_users():
    """قراءة أسماء المستخدمين من ملف users.txt."""
    if not os.path.exists(USERS_FILE):
        print(f"خطأ: لم يتم العثور على ملف '{USERS_FILE}'. قم بإنشائه وأضف أسماء المستخدمين.")
        return []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        users = [line.strip() for line in f if line.strip()]
    return users

def fetch_video_urls(username, existing_urls_set):
    """استخراج روابط الفيديوهات الجديدة للمستخدم."""
    print(f"🔍 جارِ البحث عن فيديوهات جديدة للمستخدم: {username}...")
    command = [
        'yt-dlp',
        '--simulate',
        '--print', '%(webpage_url)s',
        f'https://www.tiktok.com/@{username}'
    ]
    
    try:
        # تأكد من أن إصدار yt-dlp والإضافات متوافقة
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        
        all_urls = result.stdout.strip().split('\n')
        new_urls = []
        consecutive_found = 0

        for url in all_urls:
            if url in existing_urls_set:
                consecutive_found += 1
                if consecutive_found >= CONSECUTIVE_LIMIT:
                    print(f"✅ تم العثور على {CONSECUTIVE_LIMIT} فيديوهات قديمة متتالية. تم إيقاف البحث للمستخدم {username}.")
                    break
            else:
                consecutive_found = 0
                new_urls.append(url)
        
        # الفيديوهات الجديدة تكون في بداية القائمة، لذا نعكسها
        new_urls.reverse()
        return new_urls

    except subprocess.CalledProcessError as e:
        print(f"⚠️ حدث خطأ أثناء استخراج الروابط للمستخدم {username}. قد يكون الحساب خاصًا أو غير موجود.")
        print(f"   رسالة الخطأ: {e.stderr}")
        return []
    except FileNotFoundError:
        print("❌ خطأ: لم يتم العثور على أمر 'yt-dlp'. تأكد من أنه مثبت وفي مسار النظام (PATH).")
        sys.exit(1)


def download_thumbnail(video_url, user_thumbnails_dir):
    """تحميل الصورة المصغرة لفيديو واحد وحفظها."""
    video_id = video_url.strip().split('/')[-1]
    # تجنب الأسماء الطويلة للملفات عن طريق استخدام معرف الفيديو فقط
    output_template = os.path.join(user_thumbnails_dir, f'{video_id}.%(ext)s')
    
    # التحقق مما إذا كانت الصورة موجودة بالفعل
    # نحن نتحقق من وجود jpg أو webp لتجنب إعادة التحميل
    if os.path.exists(output_template.replace('%(ext)s', 'jpg')) or \
       os.path.exists(output_template.replace('%(ext)s', 'webp')):
        # print(f"  الصورة المصغرة لـ {video_id} موجودة بالفعل. تم التخطي.")
        # نرجع المسار المتوقع
        return output_template.replace('%(ext)s', 'jpg')

    command = [
        'yt-dlp',
        '--write-thumbnail',
        '--skip-download',
        '--convert-thumbnails', 'jpg',
        '-o', output_template,
        video_url
    ]
    
    try:
        subprocess.run(command, check=True, capture_output=True)
        thumbnail_path = output_template.replace('%(ext)s', 'jpg')
        print(f"  🖼️ تم تحميل الصورة المصغرة: {thumbnail_path}")
        return thumbnail_path
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️ فشل تحميل الصورة المصغرة للرابط: {video_url}")
        print(f"     الخطأ: {e.stderr}")
        return None

def generate_html_report(data):
    """إنشاء تقرير HTML لعرض النتائج."""
    if not os.path.exists(HTML_TEMPLATE_FILE):
        print(f"❌ خطأ: لم يتم العثور على قالب HTML '{HTML_TEMPLATE_FILE}'.")
        return

    with open(HTML_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template = f.read()

    user_sections_html = ""
    for username, user_data in data.items():
        new_videos_count = sum(1 for v in user_data['videos'] if v.get('is_new', False))
        
        # إنشاء شارة "جديد" إذا كان هناك فيديوهات جديدة
        new_badge = f'<span class="new-badge">{new_videos_count} جديد</span>' if new_videos_count > 0 else ''

        video_cards_html = ""
        # عرض الفيديوهات من الأحدث إلى الأقدم
        for video in reversed(user_data['videos']):
            is_new_class = "new-item" if video.get('is_new') else ""
            thumb_path = video.get('thumbnail_path', 'placeholder.png') # مسار احتياطي
            
            video_cards_html += f"""
            <div class="video-card {is_new_class}">
                <img src="{thumb_path}" alt="صورة مصغرة">
                <a href="{video['url']}" target="_blank">فتح الفيديو</a>
            </div>
            """
        
        user_sections_html += f"""
        <details class="user-section" open>
            <summary class="user-summary">{username} {new_badge}</summary>
            <div class="video-grid">
                {video_cards_html}
            </div>
        </details>
        """

    final_html = template.replace('{user_sections}', user_sections_html)
    with open(HTML_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(final_html)
    print(f"\n🎉 تم إنشاء التقرير بنجاح! افتح الملف: {HTML_REPORT_FILE}")

# --- الدالة الرئيسية ---

def main():
    """الدالة الرئيسية لتشغيل السكربت."""
    print("--- بدء تشغيل سكربت تيك توك ---")
    
    # إنشاء المجلدات اللازمة
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)
    
    data = load_data()
    users = get_users()
    
    if not users:
        print("لا يوجد مستخدمين للمعالجة. الرجاء إضافة أسماء في ملف users.txt.")
        return

    total_new_videos = 0
    for username in users:
        user_thumbnails_dir = os.path.join(THUMBNAILS_DIR, username)
        os.makedirs(user_thumbnails_dir, exist_ok=True)
        
        if username not in data:
            data[username] = {'videos': []}
        
        existing_urls_set = {video['url'] for video in data[username]['videos']}
        new_urls = fetch_video_urls(username, existing_urls_set)
        
        if new_urls:
            print(f"✨ تم العثور على {len(new_urls)} فيديو جديد للمستخدم {username}.")
            total_new_videos += len(new_urls)
            for url in new_urls:
                thumbnail_path = download_thumbnail(url, user_thumbnails_dir)
                if thumbnail_path:
                    data[username]['videos'].append({
                        'url': url,
                        'thumbnail_path': thumbnail_path,
                        'is_new': True
                    })
        else:
            print(f"👍 المستخدم {username} محدّث بالفعل.")
            
    if total_new_videos > 0:
        print(f"\n💾 جارِ حفظ البيانات المحدثة...")
        save_data(data)
    
    print("📄 جارِ إنشاء التقرير...")
    generate_html_report(data)
    print("\n--- انتهت العملية ---")

if __name__ == "__main__":
    main()