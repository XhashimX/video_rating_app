#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime
import time

def generate_html_page(data: dict, html_file: str):
    """إنشاء صفحة HTML لعرض البيانات"""
    print("\n🎨 Starting HTML generation...")
    start_time = time.time()
    
    # عد الإحصائيات
    total_users = len(data.get("users", {}))
    total_videos = sum(len(user_data.get("videos", {})) for user_data in data.get("users", {}).values() if user_data)
    total_new = sum(
        sum(1 for v in user_data.get("videos", {}).values() if v.get("is_new", False))
        for user_data in data.get("users", {}).values() if user_data
    )
    total_local = sum(
        sum(1 for v in user_data.get("videos", {}).values() if v.get("is_local", False))
        for user_data in data.get("users", {}).values() if user_data
    )
    
    print(f"   • Processing {total_users} users")
    print(f"   • Total videos: {total_videos}")
    print(f"   • New videos: {total_new}")
    print(f"   • Local videos: {total_local}")
    
    html_content = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>متتبع فيديوهات TikTok</title>
    <style>
        :root {
            --bg-dark-primary: #121212;
            --bg-dark-secondary: #1e1e1e;
            --bg-dark-tertiary: #2a2a2a;
            --text-primary: #e0e0e0;
            --text-secondary: #a0a0a0;
            --accent-primary: #bb86fc;
            --accent-secondary: #03dac6;
            --success-color: #4CAF50;
            --warning-color: #ff9800;
            --local-color: #2196F3;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-dark-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            margin-bottom: 20px;
            font-size: 2.8em;
            color: var(--accent-primary);
            text-shadow: 0 0 10px rgba(187, 134, 252, 0.3);
        }
        
        .global-stats {
            background: var(--bg-dark-secondary);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            text-align: center;
            border: 1px solid #333;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }
        
        .global-stats .stat {
            display: inline-block;
            margin: 0 20px;
            padding: 10px 20px;
            background: var(--bg-dark-tertiary);
            border-radius: 8px;
        }
        
        .global-stats .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            color: var(--accent-secondary);
        }
        
        .global-stats .stat-label {
            font-size: 0.9em;
            color: var(--text-secondary);
            margin-top: 5px;
        }
        
        .user-section {
            background: var(--bg-dark-secondary);
            border-radius: 12px;
            margin-bottom: 25px;
            overflow: hidden;
            border: 1px solid #333;
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }
        
        .user-header {
            background: linear-gradient(90deg, #3a3a3a 0%, #2a2a2a 100%);
            padding: 18px 25px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.3s ease;
        }
        
        .user-header:hover {
            background: linear-gradient(90deg, #4a4a4a 0%, #3a3a3a 100%);
        }
        
        .user-header h2 {
            font-size: 1.6em;
            color: var(--accent-secondary);
        }
        
        .toggle-icon {
            transition: transform 0.3s ease;
            font-size: 1.5em;
            color: var(--text-secondary);
        }
        
        .user-section.active .toggle-icon {
            transform: rotate(180deg);
        }
        
        .user-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.7s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .user-section.active .user-content {
            max-height: 50000px; /* Set a very large max-height to allow content to expand */
        }
        
        .stats {
            padding: 15px 25px;
            background: var(--bg-dark-tertiary);
            border-bottom: 1px solid #333;
            color: var(--text-secondary);
        }
        
        .stats strong {
            color: var(--text-primary);
        }
        
        .videos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 25px;
            padding: 25px;
        }
        
        .video-card {
            background: var(--bg-dark-tertiary);
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #444;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            position: relative;
        }
        
        .video-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 12px 30px rgba(0,0,0,0.5);
        }
        
        .video-card.new::before {
            content: "جديد";
            position: absolute;
            top: 12px;
            right: 12px;
            background: var(--success-color);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            z-index: 1;
            animation: pulse 1.5s infinite;
        }
        
        .video-card.local::after {
            content: "💾";
            position: absolute;
            top: 12px;
            left: 12px;
            background: var(--local-color);
            color: white;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 1.2em;
            z-index: 1;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(76, 175, 80, 0); }
            100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); }
        }
        
        .video-thumbnail {
            width: 100%;
            height: 400px;
            object-fit: cover;
            display: block;
            border-bottom: 1px solid #444;
        }
        
        .video-thumbnail.lazy {
            background: #222;
            position: relative;
        }
        
        .video-thumbnail.lazy::before {
            content: "⏳";
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 3em;
            color: #555;
        }
        
        .video-info {
            padding: 15px;
        }
        
        .video-link {
            display: inline-block;
            background: var(--accent-primary);
            color: #121212;
            font-weight: bold;
            padding: 10px 18px;
            border-radius: 8px;
            text-decoration: none;
            transition: all 0.3s ease;
            margin-top: 10px;
        }
        
        .video-link:hover {
            background: var(--accent-secondary);
            transform: scale(1.05);
        }
        
        .video-date {
            color: var(--text-secondary);
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        
        .no-thumbnail {
            width: 100%;
            height: 400px;
            background: #222;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #555;
            font-size: 4em;
            border-bottom: 1px solid #444;
        }
        
        .last-update {
            text-align: center;
            color: var(--text-secondary);
            margin-top: 30px;
            padding: 20px;
            background: var(--bg-dark-secondary);
            border-radius: 12px;
            border: 1px solid #333;
        }
        
        .new-badge {
            display: inline-block;
            background: var(--warning-color);
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-left: 10px;
            font-weight: bold;
        }
        
        .local-badge {
            display: inline-block;
            background: var(--local-color);
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-left: 10px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 متتبع فيديوهات TikTok</h1>
        
        <div class="global-stats">
            <div class="stat">
                <div class="stat-value">""" + str(total_users) + """</div>
                <div class="stat-label">المستخدمون</div>
            </div>
            <div class="stat">
                <div class="stat-value">""" + str(total_videos) + """</div>
                <div class="stat-label">إجمالي الفيديوهات</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: var(--success-color);">""" + str(total_new) + """</div>
                <div class="stat-label">فيديوهات جديدة</div>
            </div>
            <div class="stat">
                <div class="stat-value" style="color: var(--local-color);">""" + str(total_local) + """</div>
                <div class="stat-label">محفوظة محلياً</div>
            </div>
        </div>
"""
    
    print("   • Building HTML structure...")
    
    # فرز المستخدمين لإظهار من لديهم فيديوهات جديدة أولاً
    sorted_users = sorted(
        data["users"].items(),
        key=lambda item: sum(1 for v in item[1].get("videos", {}).values() if v and v.get("is_new")),
        reverse=True
    )

    for username, user_data in sorted_users:
        if not user_data: continue
        
        videos = user_data.get("videos", {})
        new_count = sum(1 for v in videos.values() if v and v.get("is_new", False))
        local_count = sum(1 for v in videos.values() if v and v.get("is_local", False))
        total_count = len(videos)
        
        last_update_val = user_data.get('last_update')
        formatted_last_update = last_update_val[:10] if last_update_val else 'غير محدد'
        
        new_badge = f'<span class="new-badge">{new_count} جديد</span>' if new_count > 0 else ''
        local_badge = f'<span class="local-badge">{local_count} محلي</span>' if local_count > 0 else ''
        
        html_content += f"""
        <div class="user-section" id="user-{username}" data-has-new="{str(new_count > 0).lower()}">
            <div class="user-header" onclick="toggleUser('{username}')">
                <h2>@{username} {new_badge} {local_badge}</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="user-content">
                <div class="stats">
                    <strong>إجمالي الفيديوهات:</strong> {total_count} | 
                    <strong style="color: var(--success-color);">الجديدة:</strong> {new_count} | 
                    <strong style="color: var(--local-color);">المحلية:</strong> {local_count} | 
                    <strong>آخر تحديث:</strong> {formatted_last_update}
                </div>
                <div class="videos-grid" id="grid-{username}">
"""
        
        # START: MODIFIED SECTION - عكس ترتيب عرض الفيديوهات
        # الآن يتم الفرز حسب تاريخ الإضافة فقط (من الأقدم إلى الأحدث)
        sorted_videos = sorted(
            videos.items(),
            key=lambda x: x[1].get("added_date", "")
        )
        # END: MODIFIED SECTION
        
        for video_id, video_data in sorted_videos:
            if not video_data: continue
                
            is_new = "new" if video_data.get("is_new", False) else ""
            is_local = "local" if video_data.get("is_local", False) else ""
            thumbnail = video_data.get("thumbnail")
            url = video_data.get("url", "#")
            added_date = video_data.get("added_date", "")
            
            if added_date:
                try:
                    date_obj = datetime.fromisoformat(added_date)
                    formatted_date = date_obj.strftime("%Y/%m/%d %H:%M")
                except:
                    formatted_date = added_date
            else:
                formatted_date = "غير محدد"
            
            html_content += f"""
                    <div class="video-card {is_new} {is_local}">
"""
            
            if thumbnail and os.path.exists(thumbnail):
                relative_thumb = os.path.relpath(thumbnail).replace('\\', '/')
                html_content += f"""
                        <img data-src="{relative_thumb}" alt="Video thumbnail" class="video-thumbnail lazy">
"""
            else:
                html_content += """
                        <div class="no-thumbnail">📷</div>
"""
            
            html_content += f"""
                        <div class="video-info">
                            <div class="video-date">📅 {formatted_date}</div>
                            <div style="font-size: 0.8em; color: #666;">ID: {video_id}</div>
                            <a href="{url}" target="_blank" class="video-link">مشاهدة الفيديو ←</a>
                        </div>
                    </div>
"""
        
        html_content += """
                </div>
            </div>
        </div>
"""
    
    # إضافة تاريخ آخر تحديث
    html_content += f"""
        <div class="last-update">
            <strong>آخر تحديث:</strong> {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}<br>
            <small>تم إنشاء هذا التقرير تلقائياً بواسطة TikTok Tracker v2.0</small>
        </div>
    </div>
    
    <script>
        let activeSection = null;
        let imageObserver = null;
        
        function setupLazyLoading() {{
            if ('IntersectionObserver' in window) {{
                // START: MODIFIED SECTION - تحسين التحميل الكسول للصور
                // زيادة الهامش لجعل الصور تبدأ بالتحميل مبكراً جداً قبل الوصول إليها
                imageObserver = new IntersectionObserver((entries, observer) => {{
                    entries.forEach(entry => {{
                        if (entry.isIntersecting) {{
                            const img = entry.target;
                            if (img.dataset.src) {{
                                img.src = img.dataset.src;
                                img.classList.remove('lazy');
                                img.removeAttribute('data-src');
                                observer.unobserve(img);
                            }}
                        }}
                    }});
                }}, {{
                    // هذا الهامش يخبر المتصفح أن يبدأ تحميل أي صورة
                    // تدخل في نطاق 800 بكسل أعلى أو أسفل الشاشة
                    rootMargin: '800px 0px'
                }});
                // END: MODIFIED SECTION
            }}
        }}
        
        function loadImagesForSection(username) {{
            const grid = document.getElementById('grid-' + username);
            if (!grid) return;
            
            const images = grid.querySelectorAll('img.lazy[data-src]');
            
            if (imageObserver) {{
                images.forEach(img => imageObserver.observe(img));
            }} else {{
                // Fallback للمتصفحات القديمة
                images.forEach(img => {{
                    if (img.dataset.src) {{
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        img.removeAttribute('data-src');
                    }}
                }});
            }}
        }}
        
        function toggleUser(username) {{
            const section = document.getElementById('user-' + username);
            if (!section) return;

            const wasActive = section.classList.contains('active');
            
            if (activeSection && activeSection !== section) {{
                activeSection.classList.remove('active');
            }}
            
            section.classList.toggle('active');
            
            if (!wasActive) {{
                activeSection = section;
                setTimeout(() => loadImagesForSection(username), 50);
            }} else {{
                activeSection = null;
            }}
        }}
        
        document.addEventListener('DOMContentLoaded', function() {{
            setupLazyLoading();
            
            const sections = document.querySelectorAll('.user-section');
            let openedInitialSection = false;

            for (const section of sections) {{
                if (section.dataset.hasNew === 'true') {{
                    const username = section.id.replace('user-', '');
                    toggleUser(username);
                    openedInitialSection = true;
                    break;
                }}
            }}
            
            if (!openedInitialSection && sections.length > 0) {{
                const firstSection = sections[0];
                const username = firstSection.id.replace('user-', '');
                toggleUser(username);
            }}
        }});
    </script>
</body>
</html>
"""
    
    print("   • Writing HTML file...")
    
    # حفظ ملف HTML
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    elapsed = time.time() - start_time
    print(f"✅ HTML page created: {html_file} ({elapsed:.2f}s)")
    print(f"   • File size: {os.path.getsize(html_file) / 1024:.2f} KB")