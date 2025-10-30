#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from datetime import datetime
import time

from tracker import TikTokTracker
from html_generator import generate_html_page

def main():
    """نقطة البداية للبرنامج"""
    start_time = time.time()
    
    print("\n" + "="*70)
    print("                    🎬 TikTok Video Tracker v2.0")
    print("="*70)
    print(f"📅 Started at: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
    print("="*70)
    
    # التحقق من وجود yt-dlp
    print("\n🔍 Checking dependencies...")
    try:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True, text=True)
        version = result.stdout.strip()
        print(f"✅ yt-dlp found (version: {version})")
    except:
        print("❌ Error: yt-dlp is not installed.")
        print("📦 Please install it using: pip install yt-dlp")
        sys.exit(1)
    
    # إنشاء ملف users.txt إذا لم يكن موجوداً
    if not os.path.exists("users.txt"):
        print("\n📝 Creating users.txt file...")
        with open("users.txt", "w", encoding="utf-8") as f:
            f.write("# ضع أسماء المستخدمين هنا، كل اسم في سطر منفصل\n")
            f.write("# مثال:\n")
            f.write("# hajar0220\n")
            f.write("# username2\n")
        print("✅ users.txt created. Please add usernames to it and run again.")
        sys.exit(0)
    
    # تشغيل البرنامج
    print("\n🚀 Initializing TikTok Tracker...")
    tracker = TikTokTracker()
    
    # الحصول على قائمة المستخدمين
    print("📖 Reading users list...")
    users = tracker.get_users()
    
    if not users:
        print("❌ No usernames found in users.txt.")
        print("📝 Please add at least one username to the file.")
        return
    
    print(f"✅ Found {len(users)} user(s) to process:")
    for idx, user in enumerate(users, 1):
        print(f"   {idx}. @{user}")
    
    # معالجة المستخدمين بشكل متوازي
    print("\n" + "="*70)
    print("                    🔄 STARTING PARALLEL PROCESSING")
    print("="*70)
    
    processing_start = time.time()
    tracker.process_users_parallel(users)
    processing_time = time.time() - processing_start
    
    # حفظ البيانات النهائية
    print("\n" + "="*70)
    print("💾 Saving final data...")
    tracker.save_data()
    print(f"✅ Data saved to {tracker.data_file}")
    
    # إنشاء صفحة HTML
    print("\n🎨 Generating HTML report...")
    generate_html_page(tracker.data, tracker.html_file)
    
    # إحصائيات نهائية
    total_time = time.time() - start_time
    print("\n" + "="*70)
    print("                    ✨ PROCESS COMPLETED SUCCESSFULLY!")
    print("="*70)
    print(f"📊 Statistics:")
    print(f"   • Total users processed: {len(users)}")
    print(f"   • Total new videos found: {tracker.total_new_videos}")
    print(f"   • Processing time: {processing_time:.2f} seconds")
    print(f"   • Total execution time: {total_time:.2f} seconds")
    print(f"   • Average time per user: {processing_time/len(users):.2f} seconds")
    print(f"\n🌐 Open {tracker.html_file} to view the results")
    print("="*70)
    print(f"📅 Finished at: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user!")
        print("💾 Data has been auto-saved periodically.")
        print("🔄 You can safely restart the script to continue.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        print("💾 Check tiktok_data_temp.json for any saved progress.\n")
        sys.exit(1)
