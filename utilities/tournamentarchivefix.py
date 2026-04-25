import json
import os
import shutil
import random

# --- إعداد المسارات ---
archive_path = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\tournamentarchive.json"
bets_path = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\bets.json"
utilities_dir = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities"

reference_files =[
    r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json",
    r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo pic.json"
]

def load_json(filepath):
    """دالة مساعدة لقراءة ملفات JSON مع دعم الحروف العربية"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: الملف غير موجود: {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Error: ملف معطوب أو غير صالح: {filepath}")
        return None

def get_suffix(filename):
    """دالة مساعدة لاستخراج ما بعد أول شرطة سفلية في اسم الملف"""
    if filename and '_' in filename:
        return filename.split('_', 1)[1]
    return filename

def main():
    # 1. إنشاء نسخ احتياطية
    if os.path.exists(archive_path):
        shutil.copy(archive_path, archive_path + ".backup_v2")
        print(f"✅ تم إنشاء نسخة احتياطية لملف الأرشيف.")
    
    if os.path.exists(bets_path):
        shutil.copy(bets_path, bets_path + ".backup_v2")
        print(f"✅ تم إنشاء نسخة احتياطية لملف الرهانات (bets).")

    # 2. بناء خرائط (Maps) للبحث الذكي
    size_to_name_map = {}
    suffix_to_name_map = {}
    
    print("🔄 جاري قراءة الملفات المرجعية وبناء قواميس التطابق...")
    for ref_path in reference_files:
        data = load_json(ref_path)
        if data:
            for filename, details in data.items():
                if isinstance(details, dict) and 'file_size' in details:
                    # الخريطة القديمة المعتمدة على الحجم
                    f_size = details['file_size']
                    size_to_name_map[f_size] = filename
                
                # الخريطة الجديدة المعتمدة على "ما بعد أول شرطة سفلية"
                suffix = get_suffix(filename)
                suffix_to_name_map[suffix] = filename

    print(f"📊 تم فهرسة {len(size_to_name_map)} فيديو للحجم و {len(suffix_to_name_map)} للمقاطع اللاحقة.")

    # ==========================================
    # 3. تصحيح الأرشيف (بناءً على الحجم - الكود الأصلي)
    # ==========================================
    archive_data = load_json(archive_path)
    if archive_data:
        archive_updated_count = 0
        print("🔄 جاري فحص الأرشيف وتصحيح الأسماء...")
        
        for tournament_name, rankings in archive_data.items():
            if not isinstance(rankings, dict):
                continue
            for rank_key, video_details in rankings.items():
                if not isinstance(video_details, dict):
                    continue
                
                current_size = video_details.get('file_size')
                current_name = video_details.get('video')

                if current_size is not None and current_size in size_to_name_map:
                    correct_name = size_to_name_map[current_size]
                    if current_name != correct_name:
                        video_details['video'] = correct_name
                        archive_updated_count += 1
        
        if archive_updated_count > 0:
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(archive_data, f, indent=4, ensure_ascii=False)
            print(f"✅ تم تصحيح {archive_updated_count} اسم في الأرشيف.")
        else:
            print("ℹ️ لم يتم العثور على أسماء تحتاج لتصحيح في الأرشيف.")

    # ==========================================
    # 4. تصحيح ملف bets (بناءً على المقطع اللاحق الذكي)
    # ==========================================
    bets_data = load_json(bets_path)
    corrected_bets = {}
    if bets_data:
        bets_updated_count = 0
        print("🔄 جاري فحص الرهانات (bets) وتصحيح الأسماء بذكاء...")
        
        for key, details in bets_data.items():
            # تصحيح المفتاح الأساسي (اسم الفيديو المهاجم)
            key_suffix = get_suffix(key)
            new_key = suffix_to_name_map.get(key_suffix, key)
            
            if new_key != key:
                bets_updated_count += 1

            # تصحيح اسم الفيديو المدافع
            if isinstance(details, dict) and 'defender_video' in details:
                old_defender = details['defender_video']
                defender_suffix = get_suffix(old_defender)
                new_defender = suffix_to_name_map.get(defender_suffix, old_defender)
                
                if old_defender != new_defender:
                    details['defender_video'] = new_defender
                    bets_updated_count += 1
            
            # إضافة البيانات المصححة إلى القاموس الجديد
            corrected_bets[new_key] = details

        if bets_updated_count > 0 or len(corrected_bets) > 0:
            with open(bets_path, 'w', encoding='utf-8') as f:
                json.dump(corrected_bets, f, indent=4, ensure_ascii=False)
            print(f"✅ تم تصحيح {bets_updated_count} عنصر في ملف الرهانات.")

    # ==========================================
    # 5. التفاعل: إنشاء مسابقة (Tournament)
    # ==========================================
    if corrected_bets:
        print("\n" + "="*50)
        choice = input("🤔 هل تريد عمل مسابقة بينهم؟ (نعم/لا): ").strip().lower()
        if choice in ['نعم', 'yes', 'y', 'ن']:
            create_random_tournament(corrected_bets)
        else:
            print("👍 تم تخطي إنشاء المسابقة.")

def create_random_tournament(bets_data):
    """توليد مسابقة عشوائية بناءً على بيانات bets"""
    rand_id = f"{random.randint(1000, 9999)}"
    tournament_filename = f"topcut_elo_videos_A1000 elo tik_{rand_id}.json"
    out_path = os.path.join(utilities_dir, tournament_filename)
    
    matches =[]
    
    for attacker_vid, details in bets_data.items():
        if isinstance(details, dict) and 'defender_video' in details:
            defender_vid = details['defender_video']
            
            # توليد أرقام عشوائية لتقييم (rating) وحجم الملف (file_size)
            match = {
                "videos": [attacker_vid, defender_vid],
                "rating":[
                    round(random.uniform(1000.0, 1500.0), 10),
                    round(random.uniform(1000.0, 1500.0), 10)
                ],
                "file_size":[
                    random.randint(1000000, 20000000), 
                    random.randint(1000000, 20000000)
                ],
                "mode": 1,
                "num_videos": 2,
                "ranking_type": "winner_only",
                "competition_type": "random"
            }
            matches.append(match)
            
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(matches, f, indent=4, ensure_ascii=False)
        print(f"\n🎉 رائع! تم إنشاء ملف المسابقة الجديد بنجاح:\n📁 {out_path}")
        print(f"⚔️ عدد الجولات (المباريات) التي تم إنشاؤها: {len(matches)}")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء محاولة إنشاء المسابقة: {e}")

if __name__ == "__main__":
    main()