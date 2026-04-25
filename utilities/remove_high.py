import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import re
import glob
import threading

# ================= إعدادات المسارات =================
BASE_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities"
ELO_TIK_PATH = os.path.join(BASE_DIR, "elo_videos_A1000 elo tik.json")
ELO_PIC_PATH = os.path.join(BASE_DIR, "elo_videos_A1000 elo pic.json")
# ====================================================

class TopCutCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TopCut Elo Cleaner Tool")
        self.root.geometry("700x550")
        
        # متغيرات البيانات
        self.found_files = []
        
        # --- التصميم (Layout) ---
        
        # 1. العنوان العلوي
        lbl_title = tk.Label(root, text="TopCut Cleaner & Merger", font=("Arial", 16, "bold"))
        lbl_title.pack(pady=10)

        # 2. إطار قائمة الملفات
        frame_list = tk.LabelFrame(root, text="Select Files to Process (Ends with 4 Digits)", padx=10, pady=10)
        frame_list.pack(fill="both", expand=True, padx=10)
        
        # القائمة (Listbox) مع شريط تمرير
        self.listbox = tk.Listbox(frame_list, selectmode=tk.MULTIPLE, font=("Consolas", 10))
        scrollbar = tk.Scrollbar(frame_list, orient="vertical", command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # أزرار التحكم بالقائمة
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(btn_frame, text="Scan Directory", command=self.scan_files, bg="#dddddd").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Select All", command=self.select_all).pack(side="left", padx=5)
        
        # زر التشغيل الرئيسي
        self.btn_run = tk.Button(btn_frame, text="START PROCESSING", command=self.run_process_thread, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.btn_run.pack(side="right", padx=5)

        # 3. سجل العمليات (Log Area)
        log_frame = tk.LabelFrame(root, text="Execution Log", padx=5, pady=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=10, state='disabled', bg="black", fg="#00ff00", font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True)

        # تشغيل الفحص التلقائي عند الفتح
        self.scan_files()

    def log(self, message):
        """كتابة النصوص في شاشة السجل"""
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def scan_files(self):
        """فحص المجلد والبحث عن الملفات المطابقة للنمط"""
        self.listbox.delete(0, tk.END)
        self.found_files = []
        
        if not os.path.exists(BASE_DIR):
            self.log(f"Error: Directory not found: {BASE_DIR}")
            return

        # النمط: يبدأ بـ topcut وينتهي بـ 4 أرقام بالضبط
        # pattern matches: topcut..._1234.json
        pattern = re.compile(r"topcut.*_(\d{4})\.json$")
        
        all_files = glob.glob(os.path.join(BASE_DIR, "*.json"))
        count = 0
        
        for f in all_files:
            filename = os.path.basename(f)
            match = pattern.search(filename)
            if match:
                self.found_files.append(f)
                self.listbox.insert(tk.END, filename)
                count += 1
        
        self.log(f"Scanned directory. Found {count} matching files.")

    def select_all(self):
        self.listbox.select_set(0, tk.END)

    def get_blacklist(self):
        """تحليل ملفات Elo لاستخراج أعلى 25"""
        banned_names = set()
        banned_sizes = set()
        
        paths = [ELO_TIK_PATH, ELO_PIC_PATH]
        
        for path in paths:
            if not os.path.exists(path):
                self.log(f"Warning: Elo file not found: {os.path.basename(path)}")
                continue
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                items_list = []
                for name, info in data.items():
                    if isinstance(info, dict) and 'rating' in info:
                        items_list.append({
                            'name': name,
                            'rating': info['rating'],
                            'file_size': info.get('file_size', 0)
                        })
                
                # ترتيب تنازلي وأخذ أعلى 25
                top_25 = sorted(items_list, key=lambda x: x['rating'], reverse=True)[:25]
                
                for item in top_25:
                    banned_names.add(item['name'])
                    banned_sizes.add(item['file_size'])
                    
                self.log(f"Loaded Top 25 from: {os.path.basename(path)}")
                
            except Exception as e:
                self.log(f"Error reading {os.path.basename(path)}: {e}")
                
        return banned_names, banned_sizes

    def run_process_thread(self):
        """تشغيل العملية في خيط منفصل لعدم تجميد الواجهة"""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select at least one file.")
            return
        
        files_to_process = [self.found_files[i] for i in selection]
        
        # تعطيل الزر أثناء العمل
        self.btn_run.config(state="disabled", text="Processing...")
        
        # بدء المعالجة في Thread جديد
        t = threading.Thread(target=self.process_logic, args=(files_to_process,))
        t.start()

    def process_logic(self, files):
        self.log("--- Starting Batch Process ---")
        
        # 1. جلب القائمة السوداء
        banned_names, banned_sizes = self.get_blacklist()
        
        if not banned_names and not banned_sizes:
            self.log("Critical Error: No blacklist data found.")
            self.btn_run.config(state="normal", text="START PROCESSING")
            return

        # 2. معالجة الملفات المختارة
        for filepath in files:
            filename = os.path.basename(filepath)
            self.log(f"\nProcessing: {filename}...")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    competitions = json.load(f)
                
                cleaned_competitions = []
                removed_count = 0
                merged_count = 0
                
                for comp in competitions:
                    videos = comp.get('videos', [])
                    ratings = comp.get('rating', [])
                    sizes = comp.get('file_size', [])
                    
                    if not (len(videos) == len(ratings) == len(sizes)):
                        continue
                    
                    new_videos, new_ratings, new_sizes = [], [], []
                    
                    # خطوة الحذف
                    for v, r, s in zip(videos, ratings, sizes):
                        if (v in banned_names) or (s in banned_sizes):
                            removed_count += 1 # تم الحذف لأنه من التوب 25
                        else:
                            new_videos.append(v)
                            new_ratings.append(r)
                            new_sizes.append(s)
                    
                    remaining_count = len(new_videos)
                    
                    # خطوة الدمج (اللوجيك)
                    if remaining_count >= 2:
                        comp['videos'] = new_videos
                        comp['rating'] = new_ratings
                        comp['file_size'] = new_sizes
                        comp['num_videos'] = remaining_count
                        cleaned_competitions.append(comp)
                        
                    elif remaining_count == 1:
                        # بقي واحد فقط، ندمجه مع السابق
                        if len(cleaned_competitions) > 0:
                            prev_comp = cleaned_competitions[-1]
                            prev_comp['videos'].append(new_videos[0])
                            prev_comp['rating'].append(new_ratings[0])
                            prev_comp['file_size'].append(new_sizes[0])
                            prev_comp['num_videos'] += 1
                            merged_count += 1
                        else:
                            # لا يوجد سابق، يتم حذفه للأسف
                            pass
                
                # حفظ الملف
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_competitions, f, indent=4)
                    
                self.log(f" -> Success. Removed: {removed_count}, Merged Orphans: {merged_count}")

            except Exception as e:
                self.log(f" -> Error processing file: {e}")

        self.log("\n--- All Done! ---")
        messagebox.showinfo("Done", "Processing Completed Successfully!")
        self.btn_run.config(state="normal", text="START PROCESSING")

# تشغيل التطبيق
if __name__ == "__main__":
    root = tk.Tk()
    app = TopCutCleanerApp(root)
    root.mainloop()