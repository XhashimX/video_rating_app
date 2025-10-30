# START: MODIFIED SECTION
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from datetime import datetime
import time
import signal
import threading  # <-- هذا هو السطر الذي تم نسيانه وإضافته الآن
from concurrent.futures import ThreadPoolExecutor

from tracker import TikTokTracker
from html_generator import generate_html_page

# --- بداية التعديلات الخاصة بالإيقاف الآمن ---

# متغير عام للإشارة إلى طلب الإيقاف
shutdown_event = threading.Event()

def graceful_shutdown(tracker):
    """دالة مخصصة لتنظيف الموارد قبل الخروج"""
    print("\n\n" + "="*70)
    print("                    🚦 SHUTDOWN SIGNAL RECEIVED 🚦")
    print("="*70)
    print("   • Stopping all active threads. Please wait...")
    # (المنفذ سيتم إيقافه تلقائيًا عند الخروج من
    #  `with` block بسبب الاستثناء)
    
    print("   • Performing a final save of all processed data...")
    tracker.save_data() # استدعاء الحفظ النهائي بدون is_temp
    print(f"   • ✅ Final data saved to {tracker.data_file}")
    
    # لا ننشئ HTML عند الإيقاف القسري
    print("   • Skipping HTML generation.")
    print("   • You can restart the script to continue and generate the report.")
    print("\n" + "="*70)
    print("                     GOODBYE!")
    print("="*70)
    sys.exit(0) # الخروج من البرنامج بنجاح

def main():
    """نقطة البداية للبرنامج"""
    start_time = time.time()
    
    print("\n" + "="*70)
    print("                    🎬 TikTok Video Tracker v2.0")
    print("="*70)
    print(f"📅 Started at: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
    print("="*70)
    
    print("\n🔍 Checking dependencies...")
    try:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True, text=True)
        version = result.stdout.strip()
        print(f"✅ yt-dlp found (version: {version})")
    except:
        print("❌ Error: yt-dlp is not installed.")
        print("📦 Please install it using: pip install yt-dlp")
        sys.exit(1)
    
    if not os.path.exists("users.txt"):
        print("\n📝 Creating users.txt file...")
        with open("users.txt", "w", encoding="utf-8") as f:
            f.write("# ضع أسماء المستخدمين هنا، كل اسم في سطر منفصل\n")
        print("✅ users.txt created. Please add usernames to it and run again.")
        sys.exit(0)
    
    print("\n🚀 Initializing TikTok Tracker...")
    tracker = TikTokTracker()

    # *** تسجيل معالج الإشارة (Signal Handler) ***
    # نستخدم lambda لتمرير كائن tracker إلى دالة الإيقاف
    # Frame and signal number are passed by default, so we ignore them with _
    signal.signal(signal.SIGINT, lambda signum, frame: graceful_shutdown(tracker))

    print("📖 Reading users list...")
    users = tracker.get_users()
    
    if not users:
        print("❌ No usernames found in users.txt.")
        return
    
    print(f"✅ Found {len(users)} user(s) to process.")
    
    print("\n" + "="*70)
    print("                    🔄 STARTING PARALLEL PROCESSING")
    print("                    (Press Ctrl+C to stop gracefully)")
    print("="*70)
    
    processing_start = time.time()
    
    try:
        # معالجة المستخدمين بشكل متوازي
        tracker.process_users_parallel(users)
    except KeyboardInterrupt:
        # هذا الاستثناء سيتم رفعه عندما نضغط Ctrl+C
        # ودالة signal handler الخاصة بنا قد تم تنفيذها بالفعل
        # لذلك لا نحتاج لفعل أي شيء هنا سوى المرور بهدوء
        pass
    
    processing_time = time.time() - processing_start
    
    print("\n" + "="*70)
    print("💾 Saving final data...")
    # الحفظ النهائي عند اكتمال العمل بشكل طبيعي
    tracker.save_data()
    print(f"✅ Data saved to {tracker.data_file}")
    
    print("\n🎨 Generating HTML report...")
    generate_html_page(tracker.data, tracker.html_file)
    
    total_time = time.time() - start_time
    print("\n" + "="*70)
    print("                    ✨ PROCESS COMPLETED SUCCESSFULLY!")
    print("="*70)
    print(f"📊 Statistics:")
    print(f"   • Total users processed: {len(users)}")
    print(f"   • Total new videos found: {tracker.total_new_videos}")
    print(f"   • Processing time: {processing_time:.2f} seconds")
    print(f"   • Total execution time: {total_time:.2f} seconds")
    print(f"\n🌐 Open {tracker.html_file} to view the results")
    print("="*70)
    print(f"📅 Finished at: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
# END: MODIFIED SECTION