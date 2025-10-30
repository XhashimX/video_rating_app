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
    total_videos = sum(len(user_data.get("videos", {})) for user_data in data.get("users", {}).values())
    total_new = sum(
        sum(1 for v in user_data.get("videos", {}).values() if v.get("is_new", False))
        for user_data in data.get("users", {}).values()
    )
    
    print(f"   • Processing {total_users} users")
    print(f"   • Total videos: {total_videos}")
    print(f"   • New videos: {total_new}")
    
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
            max-height: 10000px;
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
        </div>
"""
    
    print("   • Building HTML structure...")
    
    # إضافة بيانات كل مستخدم
    for username, user_data in data["users"].items():
        videos = user_data.get("videos", {})
        new_count = sum(1 for v in videos.values() if v.get("is_new", False))
        total_count = len(videos)
        
        new_badge = f'<span class="new-badge">{new_count} جديد</span>' if new_count > 0 else ''
        
        html_content += f"""
        <div class="user-section" id="user-{username}" data-has-new="{str(new_count > 0).lower()}">
            <div class="user-header" onclick="toggleUser('{username}')">
                <h2>@{username} {new_badge}</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="user-content">
                <div class="stats">
                    <strong>إجمالي الفيديوهات:</strong> {total_count} | 
                    <strong style="color: var(--success-color);">الجديدة:</strong> {new_count} | 
                    <strong>آخر تحديث:</strong> {user_data.get('last_update', 'غير محدد')[:10]}
                </div>
                <div class="videos-grid">
"""
        
        # ترتيب الفيديوهات
        sorted_videos = sorted(
            videos.items(),
            key=lambda x: (not x[1].get("is_new", False), x[1].get("added_date", "")),
            reverse=True
        )
        
        for video_id, video_data in sorted_videos:
            is_new = "new" if video_data.get("is_new", False) else ""
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
                    <div class="video-card {is_new}">
"""
            
            if thumbnail and os.path.exists(thumbnail):
                relative_thumb = os.path.relpath(thumbnail).replace('\\', '/')
                html_content += f"""
                        <img src="{relative_thumb}" alt="Video thumbnail" class="video-thumbnail" loading="lazy">
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
        function toggleUser(username) {{
            const section = document.getElementById('user-' + username);
            section.classList.toggle('active');
        }}
        
        document.addEventListener('DOMContentLoaded', function() {{
            const sections = document.querySelectorAll('.user-section');
            let openedASection = false;
            
            // فتح الأقسام التي بها فيديوهات جديدة
            sections.forEach(section => {{
                if (section.dataset.hasNew === 'true') {{
                    section.classList.add('active');
                    openedASection = true;
                }}
            }});
            
            // إذا لم يكن هناك فيديوهات جديدة، افتح القسم الأول
            if (!openedASection && sections.length > 0) {{
                sections[0].classList.add('active');
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
