
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
import sys

class TikTokTracker:
    def __init__(self):
        self.users_file = "users.txt"
        self.data_file = "tiktok_data.json"
        self.thumbnails_dir = "thumbnails"
        self.html_file = "index.html"
        self.temp_data_file = "tiktok_data_temp.json"
        self.url_cache_file = "url_cache.json"
        
        Path(self.thumbnails_dir).mkdir(exist_ok=True)
        
        self.data_lock = threading.Lock()
        self.save_lock = threading.Lock()
        self.print_lock = threading.Lock()
        
        self.data = self.load_data()
        self.url_cache = self.load_url_cache()
        
        # تشغيل المزامنة فوراً عند البدء
        self.sync_cache_with_db()
        
        self.processed_videos_count = 0
        self.total_new_videos = 0

        self.consecutive_timeouts = 0
        self.timeout_lock = threading.Lock()
        self.TIMEOUT_THRESHOLD = 10
        self.COOLDOWN_PERIOD = 60
    
    def safe_print(self, message: str):
        with self.print_lock:
            print(message)
    
    def load_data(self) -> Dict:
        if os.path.exists(self.temp_data_file):
            try:
                with open(self.temp_data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.safe_print(f"⚠️ Found temporary data file. Recovering from previous session...")
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
        return {"users": {}}

    def load_url_cache(self) -> Dict:
        if os.path.exists(self.url_cache_file):
            try:
                with open(self.url_cache_file, 'r', encoding='utf-8') as f:
                    self.safe_print(f"✅ URL Cache file found and loaded.")
                    return json.load(f)
            except Exception as e:
                self.safe_print(f"⚠️ Warning: Could not load URL cache file '{self.url_cache_file}': {e}")
        return {}

    def sync_cache_with_db(self):
        """
        تقوم هذه الدالة بنقل الروابط الموجودة في قاعدة البيانات (tiktok_data.json)
        إلى الكاش (url_cache.json) لتجنب إعادة تحميلها مرة أخرى.
        """
        self.safe_print("    🔄 Syncing database with cache...")
        updates_count = 0
        
        for username, user_data in self.data.get("users", {}).items():
            if not user_data or "videos" not in user_data:
                continue
            
            db_urls = {v.get("url") for v in user_data["videos"].values() if v.get("url")}
            
            if not db_urls:
                continue

            current_cache_list = self.url_cache.get(username, [])
            current_cache_set = set(current_cache_list)
            
            if not db_urls.issubset(current_cache_set):
                combined_set = current_cache_set.union(db_urls)
                self.url_cache[username] = list(combined_set)
                updates_count += 1
        
        if updates_count > 0:
            self.safe_print(f"    ✅ Synced cache for {updates_count} users from existing database.")
            self.save_url_cache()
        else:
            self.safe_print("    ✅ Cache is already in sync with database.")

    def save_url_cache(self):
        with self.save_lock:
            try:
                with open(self.url_cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.url_cache, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.safe_print(f"❌ Error saving URL Cache: {e}")

    def save_data(self, is_temp=False):
        with self.save_lock:
            filename = self.temp_data_file if is_temp else self.data_file
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                
                if not is_temp and os.path.exists(self.temp_data_file):
                    os.remove(self.temp_data_file)
            except Exception as e:
                self.safe_print(f"❌ Error saving data to {filename}: {e}")
    
    def get_users(self) -> List[str]:
        if not os.path.exists(self.users_file):
            return []
        with open(self.users_file, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    def extract_video_id(self, url: str) -> str:
        match = re.search(r'/video/(\d+)', url)
        return match.group(1) if match else url.split('/')[-1]
    
    def download_thumbnail_single(self, video_url: str, username: str, video_num: int = 0) -> Tuple[str, str]:
        MAX_RETRIES = 2
        BACKOFF_FACTOR = 2
        video_id = self.extract_video_id(video_url)
        base_filename = f"{username}_{video_id}"
        
        self.safe_print(f"      📷 Downloading thumbnail for video {video_num}: {video_id}")
        
        for attempt in range(MAX_RETRIES):
            try:
                output_template = os.path.join(self.thumbnails_dir, base_filename)
                cmd = [
                    "yt-dlp", 
                    "--write-thumbnail", 
                    "--skip-download", 
                    "--convert-thumbnails", "jpg", 
                    "-o", output_template, 
                    "--quiet", 
                    "--socket-timeout", "10", 
                    video_url
                ]
                subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True, timeout=20)
                
                with self.timeout_lock:
                    self.consecutive_timeouts = 0

                final_path = output_template + '.jpg'
                if os.path.exists(final_path):
                    return (video_url, final_path)
                for ext in ['.jpeg', '.webp', '.png', '.image']:
                    fallback_path = output_template + ext
                    if os.path.exists(fallback_path):
                        return (video_url, fallback_path)
                return (video_url, None)

            except subprocess.TimeoutExpired:
                if attempt < MAX_RETRIES - 1:
                    self.safe_print(f"      ⚠️ Timeout for video {video_num}. Retrying...")
                else:
                    self.safe_print(f"      ❌ Final Timeout for video {video_num}.")
                    return (video_url, None)
            except Exception as e:
                self.safe_print(f"      ❌ Failed: {video_id} - {str(e)[:50]}")
                return (video_url, None)
        return (video_url, None)

    def download_thumbnails_batch(self, videos_data: List[Tuple[str, str, int]], username: str):
        self.safe_print(f"\n    🔍 Pre-filtering: Checking for {len(videos_data)} videos...")
        
        try:
            existing_files_on_disk = set(os.listdir(self.thumbnails_dir))
        except FileNotFoundError:
            existing_files_on_disk = set()

        links_to_download = []
        final_results = []
        
        for url, video_id, num in videos_data:
            base_filename = f"{username}_{video_id}"
            found_path = None
            for ext in ['.jpg', '.jpeg', '.webp', '.png', '.image']:
                if (base_filename + ext) in existing_files_on_disk:
                    found_path = os.path.join(self.thumbnails_dir, base_filename + ext)
                    break
            
            if found_path:
                final_results.append((url, found_path))
            else:
                links_to_download.append((url, video_id, num))
        
        existing_count = len(videos_data) - len(links_to_download)
        self.safe_print(f"    👍 Found {existing_count} thumbnails already on disk.")

        if not links_to_download:
            self.safe_print("    ✅ No new thumbnails to download.")
            return final_results
            
        self.safe_print(f"    📸 Starting parallel download of {len(links_to_download)} new thumbnails (5 concurrent)...")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.download_thumbnail_single, url, username, num): (url, num) 
                for url, _, num in links_to_download
            }
            
            for future in as_completed(futures):
                try:
                    url, thumbnail_path = future.result()
                    final_results.append((url, thumbnail_path))
                except Exception as e:
                    self.safe_print(f"      ❌ Error in thumbnail download thread: {e}")
        return final_results

    def process_user(self, username: str, user_number: int, total_users: int):
        self.safe_print(f"\n{'='*60}")
        self.safe_print(f"🔄 Processing user [{user_number}/{total_users}]: @{username}")
        self.safe_print(f"{'='*60}")
        
        process_start_time = time.time()

        with self.data_lock:
            if username not in self.data["users"]:
                self.data["users"][username] = {"videos": {}, "last_update": None}
            user_data = self.data["users"][username]
            existing_ids_in_db = set(user_data.get("videos", {}).keys())
        
        self.safe_print(f"📊 Current videos in database: {len(existing_ids_in_db)}")
        self.safe_print(f"📥 Starting smart fetch for @{username} (Timeout set to 15s)...")
        
        fetch_start_time = time.time()
        
        cached_urls = self.url_cache.get(username, [])
        cached_urls_set = set(cached_urls)
        
        newly_fetched_urls = []
        fetch_successful = True
        
        url = f"https://www.tiktok.com/@{username}"
        cmd = [
            "yt-dlp", 
            "--simulate", 
            "--print", "%(webpage_url)s", 
            "--socket-timeout", "15", 
            "--retries", "3", 
            url
        ]
        
        process = None
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=None, 
                                     text=True, encoding='utf-8')

            count = 0
            for line in process.stdout:
                link = line.strip()
                if not link:
                    continue

                count += 1
                if count % 5 == 0:
                    sys.stdout.write(".")
                    sys.stdout.flush()

                if link not in cached_urls_set:
                    newly_fetched_urls.append(link)
                else:
                    self.safe_print(f"\n    🧠 Hit cached URL at #{count}. Stopping fetch.")
                    process.terminate()
                    break

            if count > 0: print() 

            process.wait(timeout=15)
            if process.returncode != 0 and process.returncode != -15:
                self.safe_print(f"    ⚠️ Warning: yt-dlp finished with non-zero code.")
                
                # START: MODIFIED SECTION - إنقاذ البيانات حتى في حالة وجود خطأ
                if len(newly_fetched_urls) > 0:
                    self.safe_print(f"    ℹ️ However, we found {len(newly_fetched_urls)} valid URLs. Saving them despite errors.")
                    fetch_successful = True
                else:
                    fetch_successful = False
                # END: MODIFIED SECTION
        
        except subprocess.TimeoutExpired:
            self.safe_print(f"\n    ❌ FETCH TIMED OUT for @{username}! Checking results...")
            if process: process.kill()
            # إنقاذ البيانات في حالة انتهاء الوقت أيضاً
            if len(newly_fetched_urls) > 0:
                self.safe_print(f"    ℹ️ Saving {len(newly_fetched_urls)} valid URLs fetched before timeout.")
                fetch_successful = True
            else:
                fetch_successful = False

        except Exception as e:
            self.safe_print(f"\n    ❌ Error fetching @{username}: {e}")
            if process: process.kill()
            fetch_successful = False

        fetch_elapsed = time.time() - fetch_start_time

        if fetch_successful:
            final_urls = newly_fetched_urls + cached_urls
            self.safe_print(f"    ✅ Smart fetch completed in {fetch_elapsed:.2f} seconds.")
            self.safe_print(f"    📊 Fetched {len(newly_fetched_urls)} new URLs. Total: {len(final_urls)}.")
            
            self.url_cache[username] = final_urls
            self.save_url_cache()
            
        else:
            final_urls = cached_urls
            self.safe_print(f"    ⚠️ Fetch failed or timed out. Using {len(final_urls)} cached URLs only.")

        # --- معالجة الفيديوهات ---
        new_links_to_process = []
        for i, link in enumerate(final_urls):
            video_id = self.extract_video_id(link)
            if video_id not in existing_ids_in_db:
                new_links_to_process.append((link, video_id, i + 1))

        if not new_links_to_process:
            self.safe_print(f"\n✅ No new videos found for @{username}")
        else:
            self.safe_print(f"\n🆕 Found {len(new_links_to_process)} new videos to process.")
            
            thumbnail_results = self.download_thumbnails_batch(new_links_to_process, username)
            
            with self.data_lock:
                save_counter = 0
                thumbnail_map = {url: path for url, path in thumbnail_results}

                for (link, video_id, _) in new_links_to_process:
                    if link in thumbnail_map:
                        thumbnail_path = thumbnail_map.get(link)
                        user_data["videos"][video_id] = {
                            "url": link, "thumbnail": thumbnail_path,
                            "added_date": datetime.now().isoformat(), "is_new": True
                        }
                        save_counter += 1
                
                self.safe_print(f"\n    💾 Saved {save_counter} new items.")
                
                newly_added_ids = {video_id for _, video_id, _ in new_links_to_process}
                for video_id, video_data in user_data["videos"].items():
                    if video_id not in newly_added_ids:
                        video_data["is_new"] = False
                
                user_data["last_update"] = datetime.now().isoformat()
                
                self.save_data(is_temp=True)
                self.total_new_videos += save_counter
        
        total_elapsed = time.time() - process_start_time
        self.safe_print(f"\n✅ Completed @{username} in {total_elapsed:.2f} seconds")

    def process_users_parallel(self, users: List[str]):
        total_users = len(users)
        self.safe_print(f"\n🚀 Starting parallel processing of {total_users} users (2 concurrent)...")
        
        with ThreadPoolExecutor(max_workers=2) as executor:
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
                    self.safe_print(f"\n✅ [{completed_count}/{total_users}] Completed thread for @{username}")
                except Exception as e:
                    self.safe_print(f"\n❌ [{completed_count}/{total_users}] Error in thread for @{username}: {e}")

# END: ENTIRE FILE "tracker.py"