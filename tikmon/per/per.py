# -*- coding: utf-8 -*-
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

# START: MODIFIED SECTION
# الإعدادات
USERS_FILE = "users.txt"
OUTPUT_DIR = "output"
VIDEO_LINKS_SUFFIX = "_links.txt"
THUMBNAIL_SUFFIX = "_thumbs"
HTML_FILE = "index.html"
NEW_MARKER = " (جديد)"

# عدد الروابط المكررة قبل التوقف
REPEAT_THRESHOLD = 3

# --------------------------------------------------------
def read_users():
    """يقرأ أسماء المستخدمين من users.txt"""
    if not os.path.exists(USERS_FILE):
        print(f"الملف {USERS_FILE} غير موجود.")
        return []
    with open(USERS_FILE, encoding="utf-8") as f:
        users = [line.strip() for line in f if line.strip()]
    return users

# --------------------------------------------------------
def fetch_tiktok_links(user):
    """استخدام yt-dlp لجلب روابط فيديوهات للمستخدم بدون تحميل الفيديوهات"""
    links_file = os.path.join(OUTPUT_DIR, f"{user}{VIDEO_LINKS_SUFFIX}")
    user_url = f"https://www.tiktok.com/@{user}"
    cmd = [
        "yt-dlp", "--simulate",
        "--print-to-file", "%(webpage_url)s",
        links_file, user_url
    ]
    subprocess.run(cmd, capture_output=True)
    # إزالة الفراغات والأسطر غير الروابط
    with open(links_file, encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip().startswith("https://")]
    # إزالة التكرار والحفاظ على الترتيب من الأحدث للأقدم
    seen = set()
    urls_unique = []
    for url in urls:
        if url not in seen:
            urls_unique.append(url)
            seen.add(url)
    return urls_unique

# --------------------------------------------------------
def load_existing_links(user):
    """يقرأ الروابط الموجودة مسبقًا من ملف المستخدم"""
    links_file = os.path.join(OUTPUT_DIR, f"{user}{VIDEO_LINKS_SUFFIX}")
    if not os.path.exists(links_file):
        return []
    with open(links_file, encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip().startswith("https://")]
    return urls

# --------------------------------------------------------
def update_links_file(user, all_links, new_links):
    """تحديث ملف الروابط بذكاء، مع تمييز الجديد"""
    links_file = os.path.join(OUTPUT_DIR, f"{user}{VIDEO_LINKS_SUFFIX}")
    # توضيح: سنميز الجديد بإضافة NEW_MARKER بجواره
    with open(links_file, "w", encoding="utf-8") as f:
        for url in all_links:
            if url in new_links:
                f.write(f"{url}{NEW_MARKER}\n")
            else:
                f.write(f"{url}\n")

# --------------------------------------------------------
def find_new_links(fetched, existing):
    """
    إيجاد الروابط الجديدة بمقارنة القائمة الحالية بالسابقة.
    الشرط الذكي: إذا وجدنا REPEAT_THRESHOLD روابط مكررة (بنفس الترتيب)، نتوقف.
    """
    new_links = []
    repeat_count = 0
    for url in fetched:
        if url in existing:
            repeat_count += 1
            if repeat_count >= REPEAT_THRESHOLD:
                break
        else:
            repeat_count = 0
            new_links.append(url)
    return new_links

# --------------------------------------------------------
def fetch_thumbnails(user, links, thumbs_dir):
    """استخراج صور الفيديوهات فقط للروابط التي لا يوجد لها صورة بالفعل"""
    # أنشئ مجلد الصور إن لم يكن موجودًا
    Path(thumbs_dir).mkdir(parents=True, exist_ok=True)
    new_thumb_paths = []
    for url in links:
        vid = url.split("/")[-1]
        out_img = os.path.join(thumbs_dir, f"{vid}.jpg")
        if not os.path.exists(out_img):
            # أمر yt-dlp لاستخراج الصورة المصغرة فقط
            cmd = [
                "yt-dlp", "--write-thumbnail", "--skip-download",
                "--convert-thumbnails", "jpg", "-o", f"{thumbs_dir}/{vid}.%(ext)s", url
            ]
            subprocess.run(cmd, capture_output=True)
            if os.path.exists(out_img):
                new_thumb_paths.append(out_img)
    return new_thumb_paths

# --------------------------------------------------------
def generate_html(users, user_links, user_thumbs, new_links_set):
    """ينشئ صفحة HTML تعرض كل مستخدم وروابطه و صوره مع تمييز الجديد"""
    with open(os.path.join(OUTPUT_DIR, HTML_FILE), "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'><title>TikTok Gallery</title></head><body style='font-family:Tahoma'>\n")
        f.write("<h1>فهرس المستخدمين والفيديوهات من TikTok</h1>\n")
        for user in users:
            f.write(f"<details><summary><b>{user}</b></summary>\n")
            # صور وروابط
            for url in user_links[user]:
                vid = url.split("/")[-1].replace(NEW_MARKER, "")
                thumb = user_thumbs[user].get(vid)
                marker = " <b style='color:red'>جديد</b>" if url in new_links_set[user] else ""
                link_visible = url.replace(NEW_MARKER, "")
                f.write("<div style='margin:5px'>\n")
                if thumb and os.path.exists(thumb):
                    f.write(f"<a href='{link_visible}' target='_blank'><img src='{thumb}' style='width:120px;vertical-align:middle'></a>\n")
                else:
                    f.write(f"<a href='{link_visible}' target='_blank'>[رابط]</a>\n")
                f.write(f"<span style='margin-right:8px'><a href='{link_visible}' target='_blank'>{link_visible}</a>{marker}</span></div>\n")
            f.write("</details><hr>\n")
        f.write("</body></html>\n")

# --------------------------------------------------------
def main():
    # التأكد من وجود مجلد الإخراج
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    users = read_users()
    user_links = {}
    user_thumbs = {}
    new_links_set = {}
    for user in users:
        # قراءة الروابط المخزنة (قديمة)
        existing_links = load_existing_links(user)
        
        # جلب الروابط الحالية عبر yt-dlp (أحدث فيديوهات)
        fetched_links = fetch_tiktok_links(user)
        
        # العثور على الروابط الجديدة:
        new_links = find_new_links(fetched_links, existing_links)
        print(f"{user}: وجدت {len(new_links)} رابط جديد.")
        # دمج الروابط؛ الأحدث أولًا
        all_links = new_links + [url for url in existing_links if url not in new_links]
        update_links_file(user, all_links, new_links)
        user_links[user] = all_links
        new_links_set[user] = set(new_links)
        # استخراج الصور فقط للروابط الجديدة
        thumbs_dir = os.path.join(OUTPUT_DIR, f"{user}{THUMBNAIL_SUFFIX}")
        fetch_thumbnails(user, new_links, thumbs_dir)
        # ربط كل فيديو بالثامبـنيل
        vid2thumb = {}
        for url in all_links:
            vid = url.split("/")[-1].replace(NEW_MARKER, "")
            thumb_path = os.path.join(thumbs_dir, f"{vid}.jpg")
            if os.path.exists(thumb_path):
                vid2thumb[vid] = thumb_path
        user_thumbs[user] = vid2thumb
    generate_html(users, user_links, user_thumbs, new_links_set)

if __name__ == "__main__":
    main()
# END: MODIFIED SECTION
