# -*g: utf-8 -*-
from playwright.sync_api import sync_playwright
import time
import re
import requests
import os
from pathlib import Path
from datetime import datetime
# START: MODIFIED SECTION
import concurrent.futures
# END: MODIFIED SECTION

def download_image(url, filename):
    """تحميل صورة من URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"    ✗ فشل تحميل الصورة: {e}")
        return False

def read_users_file():
    """قراءة أسماء المستخدمين من ملف users.txt"""
    users_file = 'users.txt'
    
    if not os.path.exists(users_file):
        print(f"⚠ لم يتم العثور على ملف {users_file}")
        print(f"جاري إنشاء ملف تجريبي...")
        with open(users_file, 'w', encoding='utf-8') as f:
            f.write("maramramadan2\n")
        print(f"✓ تم إنشاء {users_file} - يرجى إضافة أسماء المستخدمين")
        return ['maramramadan2']
    
    with open(users_file, 'r', encoding='utf-8') as f:
        users = [line.strip().replace('@', '') for line in f if line.strip()]
    
    return users

def read_links_file():
    """قراءة محتوى ملف links_mon.txt"""
    links_file = 'links_mon.txt'
    
    if not os.path.exists(links_file):
        return {}
    
    users_data = {}
    current_user = None
    
    with open(links_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.endswith(':'):
                current_user = line[:-1]
                users_data[current_user] = []
            elif line and current_user and line != '---':
                users_data[current_user].append(line)
    
    return users_data

def write_links_file(all_users_data):
    """كتابة محتوى ملف links_mon.txt"""
    links_file = 'links_mon.txt'
    
    with open(links_file, 'w', encoding='utf-8') as f:
        for username, links in all_users_data.items():
            f.write(f"{username}:\n")
            for link in links:
                f.write(f"{link}\n")
            f.write("\n")

def create_unified_html_gallery(all_users_videos):
    """إنشاء صفحة HTML موحدة لجميع المستخدمين"""
    
    total_videos = sum(len(videos) for videos in all_users_videos.values())
    
    html_content = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مراقب فيديوهات TikTok</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }}
        
        .header h1 {{
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header .subtitle {{
            font-size: 1.3em;
            opacity: 0.9;
        }}
        
        .header .timestamp {{
            font-size: 1em;
            opacity: 0.8;
            margin-top: 10px;
        }}
        
        .user-section {{
            background: white;
            border-radius: 20px;
            padding: 0;
            margin-bottom: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .user-section.collapsed .gallery {{
            display: none;
        }}
        
        .user-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 30px;
            border-bottom: 3px solid #667eea;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }}
        
        .user-header:hover {{
            background-color: #f8f9fa;
        }}
        
        .user-info {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .user-avatar {{
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2em;
            color: white;
        }}
        
        .user-details h2 {{
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 5px;
        }}
        
        .user-details .video-count {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .user-actions {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        
        .user-link {{
            padding: 12px 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: bold;
            transition: transform 0.3s ease;
        }}
        
        .user-link:hover {{
            transform: scale(1.05);
        }}
        
        .collapse-icon {{
            font-size: 1.5em;
            color: #667eea;
            transition: transform 0.3s ease;
        }}
        
        .user-section.collapsed .collapse-icon {{
            transform: rotate(-90deg);
        }}
        
        .gallery-container {{
            padding: 30px;
        }}
        
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }}
        
        .video-card {{
            background: #f8f9fa;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
            display: block;
            position: relative;
        }}
        
        .video-card.hidden {{
            display: none;
        }}
        
        .video-card.selected {{
            outline: 4px solid #667eea;
            outline-offset: 2px;
        }}
        
        .video-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }}
        
        .thumbnail-container {{
            position: relative;
            width: 100%;
            padding-top: 177.78%;
            background: #e9ecef;
            overflow: hidden;
        }}
        
        .thumbnail {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        
        .no-thumbnail {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #adb5bd;
            font-size: 3em;
        }}
        
        .play-overlay {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 60px;
            height: 60px;
            background: rgba(255,255,255,0.95);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
        }}
        
        .video-card:hover .play-overlay {{
            opacity: 1;
        }}
        
        .play-icon {{
            width: 0;
            height: 0;
            border-left: 20px solid #667eea;
            border-top: 12px solid transparent;
            border-bottom: 12px solid transparent;
            margin-right: -5px;
        }}
        
        .video-info {{
            padding: 15px;
        }}
        
        .video-number {{
            color: #667eea;
            font-weight: bold;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        
        .video-id {{
            color: #6c757d;
            font-size: 0.8em;
            direction: ltr;
            text-align: left;
            font-family: monospace;
        }}
        
        .new-badge {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: #ff4757;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
            z-index: 10;
            animation: pulse 2s infinite;
        }}
        
        .video-actions {{
            position: absolute;
            top: 10px;
            left: 10px;
            display: flex;
            gap: 5px;
            z-index: 10;
        }}
        
        .action-btn {{
            width: 35px;
            height: 35px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2em;
            transition: transform 0.2s ease;
            background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        
        .action-btn:hover {{
            transform: scale(1.1);
        }}
        
        .hide-btn {{
            color: #ff4757;
        }}
        
        .select-btn {{
            color: #667eea;
        }}
        
        .video-card.selected .select-btn {{
            background: #667eea;
            color: white;
        }}
        
        @keyframes pulse {{
            0%, 100% {{
                transform: scale(1);
            }}
            50% {{
                transform: scale(1.05);
            }}
        }}
        
        .stats {{
            background: white;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            text-align: center;
        }}
        
        .stats h2 {{
            color: #667eea;
            margin-bottom: 25px;
            font-size: 2em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        
        .stat-item {{
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px;
            font-size: 1.1em;
        }}
        
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            display: block;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            opacity: 0.9;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #6c757d;
        }}
        
        .empty-state-icon {{
            font-size: 5em;
            margin-bottom: 20px;
        }}
        
        .empty-state h3 {{
            font-size: 1.5em;
            margin-bottom: 10px;
        }}
        
        .floating-toolbar {{
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            padding: 15px 30px;
            border-radius: 50px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            display: none;
            gap: 15px;
            align-items: center;
            z-index: 1000;
        }}
        
        .floating-toolbar.show {{
            display: flex;
        }}
        
        .toolbar-btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
            transition: transform 0.2s ease;
            font-size: 1em;
        }}
        
        .toolbar-btn:hover {{
            transform: scale(1.05);
        }}
        
        .copy-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        .deselect-btn {{
            background: #e9ecef;
            color: #666;
        }}
        
        .selection-count {{
            color: #667eea;
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .notification {{
            position: fixed;
            top: 30px;
            right: 30px;
            background: white;
            padding: 20px 30px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            display: none;
            align-items: center;
            gap: 15px;
            z-index: 1001;
            animation: slideIn 0.3s ease;
        }}
        
        .notification.show {{
            display: flex;
        }}
        
        @keyframes slideIn {{
            from {{
                transform: translateX(400px);
                opacity: 0;
            }}
            to {{
                transform: translateX(0);
                opacity: 1;
            }}
        }}
        
        .notification.success {{
            border-right: 4px solid #10b981;
        }}
        
        .notification.error {{
            border-right: 4px solid #ff4757;
        }}
        
        .notification-icon {{
            font-size: 2em;
        }}
        
        .notification-text {{
            color: #333;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 مراقب فيديوهات TikTok</h1>
            <p class="subtitle">مراقبة {len(all_users_videos)} حساب - {total_videos} فيديو</p>
            <p class="timestamp">آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <h2>📊 الإحصائيات العامة</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-number">{len(all_users_videos)}</span>
                    <span class="stat-label">عدد الحسابات</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{total_videos}</span>
                    <span class="stat-label">إجمالي الفيديوهات</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{sum(1 for videos in all_users_videos.values() for v in videos if v.get('is_new'))}</span>
                    <span class="stat-label">فيديوهات جديدة</span>
                </div>
            </div>
        </div>
"""
    
    for username, videos in all_users_videos.items():
        if not videos:
            continue
            
        new_count = sum(1 for v in videos if v.get('is_new'))
        
        html_content += f"""
        <div class="user-section" id="user-{username}">
            <div class="user-header" onclick="toggleUser('{username}')">
                <div class="user-info">
                    <div class="user-avatar">👤</div>
                    <div class="user-details">
                        <h2>@{username}</h2>
                        <p class="video-count">{len(videos)} فيديو"""
        
        if new_count > 0:
            html_content += f""" • <span style="color: #ff4757; font-weight: bold;">{new_count} جديد</span>"""
        
        html_content += f"""</p>
                    </div>
                </div>
                <div class="user-actions">
                    <a href="https://www.tiktok.com/@{username}" target="_blank" class="user-link" onclick="event.stopPropagation()">
                        زيارة الحساب 🔗
                    </a>
                    <span class="collapse-icon">▼</span>
                </div>
            </div>
            
            <div class="gallery-container">
                <div class="gallery">
"""
        
        for i, video in enumerate(videos, 1):
            thumbnail_html = ""
            if video.get('thumbnail_path') and os.path.exists(video['thumbnail_path']):
                thumbnail_html = f'<img src="{video["thumbnail_path"]}" alt="فيديو {i}" class="thumbnail">'
            else:
                thumbnail_html = '<div class="no-thumbnail">📹</div>'
            
            new_badge = '<div class="new-badge">جديد ✨</div>' if video.get('is_new') else ''
            
            html_content += f"""
                <div class="video-card" data-url="{video['url']}" data-video-id="{video['video_id']}" onclick="handleVideoClick(event, this)">
                    <div class="thumbnail-container">
                        {new_badge}
                        <div class="video-actions">
                            <button class="action-btn hide-btn" onclick="hideVideo(event, '{video['url']}')" title="إخفاء">👁️</button>
                            <button class="action-btn select-btn" onclick="toggleSelect(event, this)" title="تحديد">✓</button>
                        </div>
                        {thumbnail_html}
                        <div class="play-overlay">
                            <div class="play-icon"></div>
                        </div>
                    </div>
                    <div class="video-info">
                        <div class="video-number">فيديو #{i}</div>
                        <div class="video-id">{video['video_id']}</div>
                    </div>
                </div>
"""
        
        html_content += """
                </div>
            </div>
        </div>
"""
    
    html_content += """
    </div>
    
    <div class="floating-toolbar" id="floatingToolbar">
        <span class="selection-count" id="selectionCount">0 محدد</span>
        <button class="toolbar-btn copy-btn" onclick="copySelected()">نسخ الروابط 📋</button>
        <button class="toolbar-btn deselect-btn" onclick="deselectAll()">إلغاء التحديد ✕</button>
    </div>
    
    <div class="notification" id="notification">
        <span class="notification-icon" id="notificationIcon"></span>
        <span class="notification-text" id="notificationText"></span>
    </div>
    
    <script>
        // تحميل الفيديوهات المخفية من localStorage
        let hiddenVideos = JSON.parse(localStorage.getItem('hiddenVideos') || '[]');
        let selectedVideos = new Set();
        
        // إخفاء الفيديوهات المحفوظة عند تحميل الصفحة
        window.addEventListener('DOMContentLoaded', function() {
            hiddenVideos.forEach(url => {
                const card = document.querySelector(`[data-url="${url}"]`);
                if (card) {
                    card.classList.add('hidden');
                }
            });
        });
        
        // دالة لإخفاء الفيديو
        function hideVideo(event, url) {
            event.stopPropagation();
            event.preventDefault();
            
            const card = document.querySelector(`[data-url="${url}"]`);
            if (card) {
                card.classList.add('hidden');
                
                // حفظ في localStorage
                if (!hiddenVideos.includes(url)) {
                    hiddenVideos.push(url);
                    localStorage.setItem('hiddenVideos', JSON.stringify(hiddenVideos));
                }
                
                showNotification('تم إخفاء الفيديو بنجاح', 'success');
            }
        }
        
        // دالة لتحديد/إلغاء تحديد الفيديو
        function toggleSelect(event, btn) {
            event.stopPropagation();
            event.preventDefault();
            
            const card = btn.closest('.video-card');
            const url = card.dataset.url;
            
            if (selectedVideos.has(url)) {
                selectedVideos.delete(url);
                card.classList.remove('selected');
            } else {
                selectedVideos.add(url);
                card.classList.add('selected');
            }
            
            updateToolbar();
        }
        
        // دالة لمعالجة النقر على الفيديو
        function handleVideoClick(event, card) {
            // إذا كان هناك فيديوهات محددة، نضيف/نزيل هذا الفيديو
            if (selectedVideos.size > 0) {
                event.preventDefault();
                const selectBtn = card.querySelector('.select-btn');
                toggleSelect(event, selectBtn);
            } else {
                // إذا لم يكن هناك فيديوهات محددة، نفتح الرابط
                window.open(card.dataset.url, '_blank');
            }
        }
        
        // دالة لتحديث شريط الأدوات
        function updateToolbar() {
            const toolbar = document.getElementById('floatingToolbar');
            const count = document.getElementById('selectionCount');
            
            if (selectedVideos.size > 0) {
                toolbar.classList.add('show');
                count.textContent = selectedVideos.size + ' محدد';
            } else {
                toolbar.classList.remove('show');
            }
        }
        
        // دالة لنسخ الروابط المحددة
        function copySelected() {
            if (selectedVideos.size === 0) return;
            
            const urls = Array.from(selectedVideos).join('\\n');
            
            navigator.clipboard.writeText(urls).then(() => {
                showNotification(`تم نسخ ${selectedVideos.size} رابط`, 'success');
                deselectAll();
            }).catch(err => {
                showNotification('فشل النسخ', 'error');
            });
        }
        
        // دالة لإلغاء تحديد الكل
        function deselectAll() {
            selectedVideos.clear();
            document.querySelectorAll('.video-card.selected').forEach(card => {
                card.classList.remove('selected');
            });
            updateToolbar();
        }
        
        // دالة لإظهار/إخفاء قسم المستخدم
        function toggleUser(username) {
            const section = document.getElementById('user-' + username);
            section.classList.toggle('collapsed');
        }
        
        // دالة لإظهار الإشعارات
        function showNotification(text, type) {
            const notification = document.getElementById('notification');
            const icon = document.getElementById('notificationIcon');
            const textEl = document.getElementById('notificationText');
            
            notification.className = 'notification show ' + type;
            textEl.textContent = text;
            icon.textContent = type === 'success' ? '✓' : '✕';
            
            setTimeout(() => {
                notification.classList.remove('show');
            }, 3000);
        }
    </script>
</body>
</html>
"""
    
    with open('tiktok_monitor.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✓ تم إنشاء معرض HTML موحد: tiktok_monitor.html")

def wait_for_videos_smart(page, max_attempts=5):
    """انتظار ذكي لتحميل الفيديوهات مع محاولات متعددة"""
    selectors = [
        'div[data-e2e="user-post-item"]',
        'div[class*="DivItemContainer"]',
        'a[href*="/video/"]'
    ]
    
    for attempt in range(max_attempts):
        print(f"    محاولة {attempt + 1}/{max_attempts}...")
        
        for selector in selectors:
            try:
                page.wait_for_selector(selector, timeout=3000)
                print(f"    ✓ تم العثور على العناصر")
                return True
            except:
                continue
        
        page.evaluate("window.scrollBy(0, 500)")
        time.sleep(1)
    
    return False

def get_tiktok_videos_with_thumbnails(username, existing_links=None, is_first_run=False):
    """استخراج روابط الفيديوهات مع الصور المصغرة"""
    username = username.replace('@', '')
    profile_url = f"https://www.tiktok.com/@{username}"
    
    thumbnails_dir = f"thumbnails_{username}"
    Path(thumbnails_dir).mkdir(exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"معالجة الحساب: @{username}")
    print(f"{'='*80}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        try:
            print(f"[{username}] [1] جاري تحميل الصفحة...")
            
            for attempt in range(3):
                try:
                    page.goto(profile_url, wait_until='domcontentloaded', timeout=60000)
                    print(f"[{username}]     ✓ تم تحميل الصفحة")
                    break
                except Exception as e:
                    if attempt == 2:
                        raise e
                    print(f"[{username}]     ⚠ إعادة المحاولة...")
                    time.sleep(3)
            
            print(f"[{username}] [2] انتظار تحميل المحتوى...")
            time.sleep(5)
            
            print(f"[{username}] [3] البحث عن عناصر الفيديو...")
            wait_for_videos_smart(page)
            
            print(f"[{username}] [4] جاري التمرير...")
            
            if is_first_run:
                # في التشغيل الأول: نأخذ آخر 30 فيديو فقط
                print(f"[{username}]     (التشغيل الأول - سيتم جلب آخر 30 فيديو)")
                for i in range(5):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                    print(f"[{username}]     التمرير {i + 1}/5")
            else:
                # في التشغيلات اللاحقة: نتمرر حتى نجد رابط مكرر
                print(f"[{username}]     (البحث عن فيديوهات جديدة...)")
                found_duplicate = False
                scroll_count = 0
                max_scrolls = 20
                
                while not found_duplicate and scroll_count < max_scrolls:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                    scroll_count += 1
                    
                    # فحص الروابط الحالية
                    current_videos = page.evaluate("""
                        () => {
                            const items = [];
                            const videoElements = document.querySelectorAll('div[data-e2e="user-post-item"]');
                            videoElements.forEach((el) => {
                                const link = el.querySelector('a[href*="/video/"]');
                                if (link && link.href) {
                                    items.push(link.href);
                                }
                            });
                            return items;
                        }
                    """)
                    
                    # فحص إذا وجدنا رابط مكرر
                    for video_url in current_videos:
                        if existing_links and video_url in existing_links:
                            found_duplicate = True
                            print(f"[{username}]     ✓ تم العثور على رابط مكرر - التوقف عن البحث")
                            break
                    
                    if not found_duplicate:
                        print(f"[{username}]     التمرير {scroll_count}/{max_scrolls}")
            
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(2)
            
            print(f"[{username}] [5] جاري استخراج البيانات...")
            
            videos_data = page.evaluate("""
                () => {
                    const items = [];
                    let videoElements = document.querySelectorAll('div[data-e2e="user-post-item"]');
                    
                    if (videoElements.length === 0) {
                        videoElements = document.querySelectorAll('div[class*="DivItemContainer"]');
                    }
                    
                    videoElements.forEach((el) => {
                        const link = el.querySelector('a[href*="/video/"]') || el.querySelector('a');
                        const img = el.querySelector('img');
                        
                        if (link && link.href && link.href.includes('/video/')) {
                            items.push({
                                url: link.href,
                                thumbnail: img ? img.src : null
                            });
                        }
                    });
                    
                    return items;
                }
            """)
            
            print(f"[{username}] [6] تم العثور على {len(videos_data)} فيديو")
            
            results = []
            new_videos_count = 0
            
            # تحديد الفيديوهات للمعالجة
            videos_to_process = videos_data
            
            if is_first_run:
                # في التشغيل الأول: نأخذ آخر 30 فقط
                videos_to_process = videos_data[:30]
                print(f"[{username}] [7] معالجة آخر {len(videos_to_process)} فيديو...")
            else:
                # في التشغيلات اللاحقة: نأخذ الفيديوهات حتى نجد مكرر
                videos_to_process = []
                for video_data in videos_data:
                    if existing_links and video_data['url'] in existing_links:
                        break
                    videos_to_process.append(video_data)
                    new_videos_count += 1
                
                print(f"[{username}] [7] تم العثور على {new_videos_count} فيديو جديد")
            
            for i, video_data in enumerate(videos_to_process, 1):
                video_url = video_data['url']
                thumbnail_url = video_data['thumbnail']
                
                match = re.search(r'/video/(\d+)', video_url)
                video_id = match.group(1) if match else f"video_{i}"
                
                is_new = not is_first_run and (not existing_links or video_url not in existing_links)
                
                status = "جديد ✨" if is_new else ""
                print(f"[{username}]     [{i}/{len(videos_to_process)}] {video_id} {status}")
                
                thumbnail_path = None
                
                if thumbnail_url:
                    ext = '.webp' if '.webp' in thumbnail_url else '.jpg'
                    thumbnail_filename = os.path.join(thumbnails_dir, f"{video_id}{ext}")
                    
                    if not os.path.exists(thumbnail_filename):
                        if download_image(thumbnail_url, thumbnail_filename):
                            thumbnail_path = thumbnail_filename
                    else:
                        thumbnail_path = thumbnail_filename
                
                results.append({
                    'url': video_url,
                    'video_id': video_id,
                    'thumbnail_url': thumbnail_url,
                    'thumbnail_path': thumbnail_path,
                    'is_new': is_new
                })
            
            browser.close()
            return results
            
        except Exception as e:
            print(f"[{username}] [خطأ] حدث خطأ: {e}")
            import traceback
            traceback.print_exc()
            browser.close()
            return []

# START: MODIFIED SECTION
def process_user(args):
    """
    دالة وسيطة لمعالجة مستخدم واحد. مصممة للعمل مع ProcessPoolExecutor.
    """
    username, existing_data = args
    print(f"🚀 بدء العملية للمستخدم @{username}...")
    
    is_first_run = username not in existing_data
    existing_links = existing_data.get(username, [])
    
    videos = get_tiktok_videos_with_thumbnails(
        username, 
        existing_links=existing_links,
        is_first_run=is_first_run
    )
    
    print(f"🏁 انتهت العملية للمستخدم @{username}.")
    return username, videos, is_first_run, existing_links

def main():
    print("=" * 80)
    print("🎬 مراقب فيديوهات TikTok")
    print("=" * 80)
    print()
    
    # قراءة أسماء المستخدمين
    users = read_users_file()
    print(f"✓ تم العثور على {len(users)} مستخدم: {', '.join(users)}")
    print()
    
    # قراءة الروابط الموجودة
    existing_data = read_links_file()
    
    # تخزين جميع البيانات
    all_users_data = existing_data.copy()
    all_users_videos = {}
    
    # تحديد عدد العمليات المتوازية (العمال)
    MAX_WORKERS = 7
    
    # تهيئة قائمة المهام
    tasks = [(user, existing_data) for user in users]

    print(f"🔄 سيتم تشغيل {min(MAX_WORKERS, len(users))} عملية بشكل متوازي...")
    print("-" * 80)
    
    # استخدام ProcessPoolExecutor لتشغيل المهام بشكل متوازي
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # executor.map يقوم بتوزيع المهام على العمليات واستلام النتائج
        results = executor.map(process_user, tasks)
        
        # معالجة النتائج فور وصولها
        for username, videos, is_first_run, existing_links in results:
            if videos:
                # تحديث البيانات
                new_links = [v['url'] for v in videos]
                
                # فرز الفيديوهات لضمان أن الجديدة تظهر أولاً
                videos.sort(key=lambda v: not v['is_new'])
                
                current_links_in_file = [link for link in existing_links if link != '---']

                if is_first_run:
                    # التشغيل الأول: إضافة الروابط مباشرة
                    all_users_data[username] = new_links
                else:
                    # التشغيلات اللاحقة: إضافة الروابط الجديدة في الأعلى
                    combined_links = new_links + current_links_in_file
                    # إزالة المكرر مع الحفاظ على الترتيب
                    unique_links = list(dict.fromkeys(combined_links))
                    
                    if new_links and current_links_in_file:
                         all_users_data[username] = new_links + ['---'] + current_links_in_file
                    else:
                         all_users_data[username] = unique_links

                # دمج الفيديوهات الجديدة مع القديمة للعرض في HTML
                if not is_first_run:
                    old_videos = []
                    for link in current_links_in_file:
                        if link not in new_links:
                             match = re.search(r'/video/(\d+)', link)
                             video_id = match.group(1) if match else "unknown"
                             old_videos.append({'url': link, 'video_id': video_id, 'is_new': False})
                    all_users_videos[username] = videos + old_videos
                else:
                    all_users_videos[username] = videos

                print(f"✓ تمت معالجة النتائج لـ @{username}: {len(videos)} فيديو جديد")
            else:
                print(f"✗ لم يتم العثور على فيديوهات لـ @{username}")
                all_users_videos[username] = []
                if username not in all_users_data:
                    all_users_data[username] = []

    print("-" * 80)
    print("✓ اكتملت جميع عمليات المعالجة المتوازية.")

    # حفظ الملفات
    if all_users_data:
        write_links_file(all_users_data)
        print(f"\n✓ تم تحديث ملف: links_mon.txt")
    
    if all_users_videos:
        create_unified_html_gallery(all_users_videos)
    
    print("\n" + "=" * 80)
    print("✓ اكتمل التشغيل بنجاح!")
    print("=" * 80)
# END: MODIFIED SECTION

if __name__ == "__main__":
    main()