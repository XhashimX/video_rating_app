# --- START OF FILE tracker.py ---
# START: MODIFIED SECTION
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
import re
from typing import List, Dict, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from queue import Queue

class TikTokTracker:
    def __init__(self):
        self.users_file = "users.txt"
        self.data_file = "tiktok_data.json"
        self.thumbnails_dir = "thumbnails"
        self.html_file = "index.html"
        self.temp_data_file = "tiktok_data_temp.json"  # ملف مؤقت للحفظ التدريجي
        
        # إنشاء مجلد الصور إذا لم يكن موجوداً
        Path(self.thumbnails_dir).mkdir(exist_ok=True)
        
        # تحميل البيانات السابقة إن وجدت
        self.data = self.load_data()
        
        # Lock للوصول الآمن للبيانات من عدة threads
        self.data_lock = threading.Lock()
        self.save_lock = threading.Lock()
        self.print_lock = threading.Lock()
        
        # عداد للفيديوهات المعالجة
        self.processed_videos_count = 0
        self.total_new_videos = 0
    
    def safe_print(self, message: str):
        """طباعة آمنة من عدة threads"""
        with self.print_lock:
            print(message)
    
    def load_data(self) -> Dict:
        """تحميل البيانات المحفوظة من الملف"""
        # محاولة تحميل الملف المؤقت أولاً (في حالة توقف مفاجئ)
        if os.path.exists(self.temp_data_file):
            try:
                with open(self.temp_data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.safe_print(f"⚠️ Found temporary data file. Recovering from previous session...")
                # نقل الملف المؤقت ليصبح الرئيسي
                os.rename(self.temp_data_file, self.data_file)
                return data
            except:
                pass
        
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                self.safe_print(f"⚠️ Warning: Data file {self.data_file} is corrupted. Starting fresh.")
                return {"users": {}}
            except Exception as e:
                self.safe_print(f"❌ Unexpected error while reading {self.data_file}: {e}")
                return {"users": {}}
        return {"users": {}}
    
    def save_data(self, is_temp=False):
        """حفظ البيانات في ملف JSON"""
        with self.save_lock:
            filename = self.temp_data_file if is_temp else self.data_file
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                
                # إذا كان الحفظ النهائي، احذف الملف المؤقت
                if not is_temp and os.path.exists(self.temp_data_file):
                    os.remove(self.temp_data_file)
            except Exception as e:
                self.safe_print(f"❌ Error saving data to {filename}: {e}")
    
    def get_users(self) -> List[str]:
        """قراءة قائمة المستخدمين من الملف"""
        if not os.path.exists(self.users_file):
            self.safe_print(f"❌ File not found: {self.users_file}")
            return []
        
        with open(self.users_file, 'r', encoding='utf-8') as f:
            users = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        return users
    
    def extract_video_id(self, url: str) -> str:
        """استخراج معرف الفيديو من الرابط"""
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
        return url.split('/')[-1]
    
    def download_thumbnail_single(self, video_url: str, username: str, video_num: int = 0) -> str:
        """تحميل صورة مصغرة واحدة للفيديو"""
        video_id = self.extract_video_id(video_url)
        base_filename = f"{username}_{video_id}"
        
        # التحقق من وجود الصورة بالفعل
        for ext in ['.jpg', '.jpeg', '.webp', '.png', '.image']:
            existing_path = os.path.join(self.thumbnails_dir, base_filename + ext)
            if os.path.exists(existing_path):
                # NOTE: تم تعديل الطباعة لتكون أقل إزعاجًا
                # self.safe_print(f"      ✓ Thumbnail already exists for video {video_num}: {video_id}")
                return existing_path
        
        # NOTE: تم تعديل الطباعة لتكون أقل إزعاجًا
        # self.safe_print(f"      📷 Downloading thumbnail for video {video_num}: {video_id}")
        start_time = time.time()
        
        try:
            output_template = os.path.join(self.thumbnails_dir, base_filename)
            cmd = [
                "yt-dlp",
                "--write-thumbnail", "--skip-download", "--convert-thumbnails", "jpg",
                "-o", output_template,
                "--quiet",  # تقليل المخرجات
                video_url
            ]
            subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True, timeout=30)
            
            elapsed = time.time() - start_time
            
            final_path = output_template + '.jpg'
            if os.path.exists(final_path):
                # self.safe_print(f"      ✅ Thumbnail downloaded for video {video_num}: {video_id} ({elapsed:.2f}s)")
                return final_path

            for ext in ['.jpeg', '.webp', '.png', '.image']:
                fallback_path = output_template + ext
                if os.path.exists(fallback_path):
                    # self.safe_print(f"      ✅ Thumbnail downloaded for video {video_num}: {video_id} ({elapsed:.2f}s)")
                    return fallback_path
            
            self.safe_print(f"      ⚠️ Could not find thumbnail for video {video_num}: {video_id}")
            return None

        except subprocess.TimeoutExpired:
            self.safe_print(f"      ⚠️ Timeout downloading thumbnail for video {video_num}: {video_id}")
            return None
        except Exception as e:
            self.safe_print(f"      ⚠️ Failed to download thumbnail for video {video_num}: {video_id} - {str(e)[:50]}")
            return None
    
    # --- START: NEW/MODIFIED FUNCTIONS FOR SPEED ---

    def _producer_fetch_links(self, username: str, existing_ids: set, link_queue: Queue):
        """
        [Producer] وظيفة المُنتِج: تجلب الروابط بسرعة وتضعها في الطابور.
        """
        self.safe_print(f"📥 Starting to fetch video links for @{username}...")
        fetch_start_time = time.time()
        video_counter = 0
        duplicate_count = 0
        
        url = f"https://www.tiktok.com/@{username}"
        cmd = ["yt-dlp", "--simulate", "--print", "%(webpage_url)s", url]
        
        process = None
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     text=True, encoding='utf-8')

            for line in process.stdout:
                link = line.strip()
                if not link:
                    continue

                video_counter += 1
                video_id = self.extract_video_id(link)
                
                if video_id in existing_ids:
                    duplicate_count += 1
                    # self.safe_print(f"    - Checking video {video_counter}: ID {video_id} (DUPLICATE #{duplicate_count})")
                    if duplicate_count >= 10: # تم زيادة حد التكرار لتحسين الدقة
                        self.safe_print(f"    ✅ Found 10 consecutive duplicates. Stopping link fetch for @{username}")
                        break
                else:
                    duplicate_count = 0
                    # self.safe_print(f"    - Checking video {video_counter}: ID {video_id} (NEW)")
                    link_queue.put((link, video_id, video_counter))

            fetch_elapsed = time.time() - fetch_start_time
            self.safe_print(f"📊 Link fetch completed in {fetch_elapsed:.2f} seconds. Found {link_queue.qsize()} new videos to process.")
        except Exception as e:
            self.safe_print(f"❌ Error during link fetching for @{username}: {e}")
        finally:
            if process:
                process.terminate()
                process.wait(timeout=5)
            # وضع علامة خاصة في نهاية الطابور لإخبار المستهلكين بالتوقف
            link_queue.put(None)

    def _consumer_process_videos(self, username: str, link_queue: Queue, user_data: dict):
        """
        [Consumer] وظيفة المستهِلِك: تسحب رابطًا من الطابور، تحمل صورته، وتحدث البيانات.
        """
        processed_count = 0
        while True:
            item = link_queue.get()
            if item is None: # علامة النهاية
                link_queue.put(None) # إعادة العلامة للعمال الآخرين
                break

            link, video_id, video_num = item
            
            thumbnail_path = self.download_thumbnail_single(link, username, video_num)
            
            with self.data_lock:
                user_data["videos"][video_id] = {
                    "url": link,
                    "thumbnail": thumbnail_path,
                    "added_date": datetime.now().isoformat(),
                    "is_new": True
                }
            
            processed_count += 1
            # تحديث عداد الفيديوهات الجديدة بشكل آمن
            with self.data_lock:
                 self.total_new_videos += 1

            # حفظ تدريجي
            if processed_count % 50 == 0:
                self.safe_print(f"    💾 Auto-saving progress ({processed_count} new videos processed for @{username})...")
                self.save_data(is_temp=True)
            
            link_queue.task_done()

    def process_user(self, username: str, user_number: int, total_users: int):
        """
        [MODIFIED] تم إعادة هيكلة هذه الدالة لتستخدم منطق المُنتِج/المستهلِك.
        """
        self.safe_print(f"\n{'='*60}")
        self.safe_print(f"🔄 Processing user [{user_number}/{total_users}]: @{username}")
        self.safe_print(f"{'='*60}")
        
        process_start_time = time.time()

        with self.data_lock:
            if username not in self.data["users"]:
                self.data["users"][username] = {"videos": {}, "last_update": None}
            user_data = self.data["users"][username]
            existing_ids = set(user_data.get("videos", {}).keys())
        
        self.safe_print(f"📊 Current videos in database: {len(existing_ids)}")
        
        link_queue = Queue()
        
        # --- تشغيل المُنتِج والمستهلكين في threads منفصلة ---
        producer_thread = threading.Thread(target=self._producer_fetch_links, args=(username, existing_ids, link_queue))
        producer_thread.start()
        
        # تحديد عدد عمال تحميل الصور (المستهلكين)
        # 🚀🚀🚀 تم زيادة العدد إلى 64 كما طلبت 🚀🚀🚀
        num_consumers = 64
        self.safe_print(f"    🚀 Starting {num_consumers} parallel thumbnail downloaders...")
        
        consumer_threads = []
        for _ in range(num_consumers):
            thread = threading.Thread(target=self._consumer_process_videos, args=(username, link_queue, user_data))
            thread.start()
            consumer_threads.append(thread)
            
        # الانتظار حتى ينتهي المُنتِج من جلب كل الروابط
        producer_thread.join()
        
        # الانتظار حتى يفرغ الطابور (حتى يعالج المستهلكون كل الروابط)
        link_queue.join()
        
        # الانتظار حتى تنتهي جميع threads المستهلكة
        for thread in consumer_threads:
            thread.join()

        self.safe_print(f"    ✅ All new videos for @{username} have been processed.")

        # --- تحديث البيانات النهائية ---
        with self.data_lock:
            # تحديث علامة "is_new" للفيديوهات القديمة
            for video_data in user_data["videos"].values():
                if "is_new" in video_data: # تحقق لتجنب خطأ في البيانات القديمة جداً
                     video_data["is_new"] = False
            
            user_data["last_update"] = datetime.now().isoformat()
            self.save_data(is_temp=True)
        
        total_elapsed = time.time() - process_start_time
        self.safe_print(f"✅ Completed @{username} in {total_elapsed:.2f} seconds")
        self.safe_print(f"📊 Total videos for @{username}: {len(user_data['videos'])}")

    # --- END: NEW/MODIFIED FUNCTIONS FOR SPEED ---
    
    def process_users_parallel(self, users: List[str]):
        """معالجة المستخدمين بشكل متوازي (3 في نفس الوقت)"""
        total_users = len(users)
        self.safe_print(f"\n🚀 Starting parallel processing of {total_users} users (3 concurrent)...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.process_user, username, idx+1, total_users): username 
                for idx, username in enumerate(users)
            }
            
            completed_count = 0
            for future in as_completed(futures):
                username = futures[future]
                completed_count += 1
                try:
                    future.result()
                    self.safe_print(f"\n✅ [{completed_count}/{total_users}] Completed processing @{username}")
                except Exception as e:
                    self.safe_print(f"\n❌ [{completed_count}/{total_users}] Error processing @{username}: {e}")
# END: MODIFIED SECTION