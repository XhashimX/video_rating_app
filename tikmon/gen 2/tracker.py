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

# START: MODIFIED SECTION
        # --- إعدادات قاطع الدائرة (Circuit Breaker) ---
        self.consecutive_timeouts = 0
        self.timeout_lock = threading.Lock() # Lock لضمان تحديث العداد بأمان
        self.TIMEOUT_THRESHOLD = 10  # عدد مرات الفشل المتتالية لتفعيل القاطع
        self.COOLDOWN_PERIOD = 60    # مدة التوقف بالثواني
# END: MODIFIED SECTION
    
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
    
# START: MODIFIED SECTION
    def download_thumbnail_single(self, video_url: str, username: str, video_num: int = 0) -> str:
        """تحميل صورة مصغرة واحدة مع نظام إعادة محاولة وقاطع دائرة ذكي."""
        MAX_RETRIES = 3
        BACKOFF_FACTOR = 2

        video_id = self.extract_video_id(video_url)
        base_filename = f"{username}_{video_id}"
        
        for ext in ['.jpg', '.jpeg', '.webp', '.png', '.image']:
            existing_path = os.path.join(self.thumbnails_dir, base_filename + ext)
            if os.path.exists(existing_path):
                self.safe_print(f"      ✓ Thumbnail already exists for video {video_num}: {video_id}")
                return existing_path
        
        self.safe_print(f"      📷 Downloading thumbnail for video {video_num}: {video_id}")
        
        for attempt in range(MAX_RETRIES):
            try:
                output_template = os.path.join(self.thumbnails_dir, base_filename)
                cmd = ["yt-dlp", "--write-thumbnail", "--skip-download", "--convert-thumbnails", "jpg", "-o", output_template, "--quiet", video_url]
                subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True, timeout=30)
                
                # --- عند النجاح، أعد ضبط عداد الفشل ---
                with self.timeout_lock:
                    self.consecutive_timeouts = 0

                final_path = output_template + '.jpg'
                if os.path.exists(final_path):
                    return final_path
                for ext in ['.jpeg', '.webp', '.png', '.image']:
                    fallback_path = output_template + ext
                    if os.path.exists(fallback_path):
                        return fallback_path
                
                return None

            except subprocess.TimeoutExpired:
                if attempt < MAX_RETRIES - 1:
                    delay = BACKOFF_FACTOR ** attempt
                    self.safe_print(f"      ⚠️ Timeout for video {video_num}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    self.safe_print(f"      ❌ Final Timeout for video {video_num}. Registering failure.")
                    # --- هنا يتم تفعيل منطق قاطع الدائرة ---
                    with self.timeout_lock:
                        self.consecutive_timeouts += 1
                        if self.consecutive_timeouts >= self.TIMEOUT_THRESHOLD:
                            self.safe_print("\n" + "="*70)
                            self.safe_print(f"🚨 CIRCUIT BREAKER TRIPPED! Too many consecutive timeouts ({self.consecutive_timeouts}).")
                            self.safe_print("   - Simulating restart to reset connection state...")
                            
                            # الخطوة 1: محاكاة إعادة التشغيل بحذف cache الخاص بـ yt-dlp
                            self.safe_print(f"   - Clearing yt-dlp cache to start fresh sessions...")
                            subprocess.run(["yt-dlp", "--rm-cache-dir"], capture_output=True)

                            # الخطوة 2: الدخول في فترة تبريد طويلة
                            self.safe_print(f"   - Entering {self.COOLDOWN_PERIOD}s cooldown period. All downloads paused.")
                            time.sleep(self.COOLDOWN_PERIOD)
                            
                            self.consecutive_timeouts = 0 # إعادة ضبط العداد بعد التبريد
                            self.safe_print("   - Cooldown finished. Resuming operations.")
                            self.safe_print("="*70 + "\n")
                    return None
            except Exception as e:
                self.safe_print(f"      ❌ Failed to download thumbnail for video {video_num}: {video_id} - {str(e)[:50]}")
                return None
        return None
# END: MODIFIED SECTION
    
    def download_thumbnails_batch(self, videos_data: List[Tuple[str, str, int]], username: str):
        """تحميل مجموعة من الصور بشكل متوازي"""
        self.safe_print(f"\n    📸 Starting parallel download of {len(videos_data)} thumbnails (8 concurrent)...")
        
        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(self.download_thumbnail_single, url, username, num): (url, num) 
                for url, _, num in videos_data
            }
            
            for future in as_completed(futures):
                url, num = futures[future]
                try:
                    thumbnail_path = future.result()
                    results.append((url, thumbnail_path))
                except Exception as e:
                    self.safe_print(f"      ❌ Error in thumbnail download thread: {e}")
                    results.append((url, None))
        
        return results
    
    def process_user(self, username: str, user_number: int, total_users: int):
        """معالجة مستخدم واحد بطريقة ذكية وتفاعلية"""
        self.safe_print(f"\n{'='*60}")
        self.safe_print(f"🔄 Processing user [{user_number}/{total_users}]: @{username}")
        self.safe_print(f"{'='*60}")
        
        process_start_time = time.time()

        # تهيئة بيانات المستخدم
        with self.data_lock:
            if username not in self.data["users"]:
                self.data["users"][username] = {
                    "videos": {},
                    "last_update": None
                }
            user_data = self.data["users"][username]
            existing_ids = set(user_data.get("videos", {}).keys())
            existing_count = len(existing_ids)
        
        self.safe_print(f"📊 Current videos in database: {existing_count}")
        
        new_links_to_process = []
        duplicate_count = 0
        video_counter = 0
        
        self.safe_print(f"📥 Starting to fetch videos for @{username}...")
        fetch_start_time = time.time()
        
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
                    self.safe_print(f"    - Checking video {video_counter}: ID {video_id} (DUPLICATE #{duplicate_count})")
                    
                    if duplicate_count >= 3:
                        self.safe_print(f"    ✅ Found 3 consecutive duplicates. Stopping fetch for @{username}")
                        break
                else:
                    duplicate_count = 0
                    self.safe_print(f"    - Checking video {video_counter}: ID {video_id} (NEW)")
                    new_links_to_process.append((link, video_id, video_counter))

            process.terminate()
            process.wait(timeout=5)
            
            fetch_elapsed = time.time() - fetch_start_time
            self.safe_print(f"📊 Fetch completed in {fetch_elapsed:.2f} seconds")

        except Exception as e:
            self.safe_print(f"❌ Error processing @{username}: {e}")
            if process:
                process.kill()
            return

        # معالجة الروابط الجديدة
        if not new_links_to_process:
            self.safe_print(f"✅ No new videos found for @{username}")
        else:
            self.safe_print(f"🆕 Found {len(new_links_to_process)} new videos to process")
            
            # تحميل الصور المصغرة بشكل متوازي
            thumbnail_results = self.download_thumbnails_batch(new_links_to_process, username)
            
            # حفظ البيانات الجديدة
            with self.data_lock:
                save_counter = 0
                for (link, thumbnail_path), (_, video_id, _) in zip(thumbnail_results, new_links_to_process):
                    user_data["videos"][video_id] = {
                        "url": link,
                        "thumbnail": thumbnail_path,
                        "added_date": datetime.now().isoformat(),
                        "is_new": True
                    }
                    save_counter += 1
                    
                    # حفظ تدريجي كل 50 فيديو
                    if save_counter % 50 == 0:
                        self.safe_print(f"    💾 Auto-saving progress ({save_counter} videos processed)...")
                        self.save_data(is_temp=True)
                
                # تحديث الفيديوهات القديمة
                newly_added_ids = {video_id for _, video_id, _ in new_links_to_process}
                for video_id, video_data in user_data["videos"].items():
                    if video_id not in newly_added_ids:
                        video_data["is_new"] = False
                
                user_data["last_update"] = datetime.now().isoformat()
                
                # حفظ نهائي للمستخدم
                self.save_data(is_temp=True)
                self.total_new_videos += len(new_links_to_process)
        
        total_elapsed = time.time() - process_start_time
        self.safe_print(f"✅ Completed @{username} in {total_elapsed:.2f} seconds")
        self.safe_print(f"📊 Total videos for @{username}: {len(user_data['videos'])}")
    
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