# -*- coding: utf-8 -*-
import os
import json
from pathlib import Path

# ==============================================================================
# 1. الإعدادات - قم بتغيير هذه المسارات لتناسب جهازك
# ==============================================================================

# المسار الكامل لمجلد الفيديوهات الذي تريد حذف الملفات منه
VIDEOS_DIRECTORY_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik"

# المسار الكامل لملف JSON الذي يحتوي على بيانات الفيديوهات
JSON_FILE_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json"

# الوسم (Tag) الذي سيتم البحث عنه لحذف الفيديوهات
TAG_TO_DELETE = "L"


# ==============================================================================
# 2. السكربت الرئيسي - لا تحتاج لتعديل هذا الجزء
# ==============================================================================

def main():
    """الوظيفة الرئيسية لتشغيل السكربت"""
    print("=" * 70)
    print("🚀 بدء سكربت حذف الفيديوهات بناءً على بيانات JSON")
    print("=" * 70)

    # تحويل النصوص إلى كائنات Path للتعامل مع المسارات بشكل أفضل
    videos_dir = Path(VIDEOS_DIRECTORY_PATH)
    json_file = Path(JSON_FILE_PATH)

    # --- الخطوة 1: التحقق من وجود الملف والمجلد ---
    if not json_file.is_file():
        print(f"❌ خطأ: لم يتم العثور على ملف JSON في المسار:\n{json_file}")
        return
    
    if not videos_dir.is_dir():
        print(f"❌ خطأ: لم يتم العثور على مجلد الفيديوهات في المسار:\n{videos_dir}")
        return

    # --- الخطوة 2: قراءة ملف JSON وتحديد المرشحين للحذف ---
    print(f"\n[1/5] 🔍 جاري قراءة ملف البيانات: {json_file.name}")
    
    candidates_for_deletion = {}
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for filename, details in data.items():
            # التحقق من وجود مفتاح 'tags' وأن قيمته تساوي الوسم المطلوب
            if details.get("tags") == TAG_TO_DELETE:
                # التأكد من وجود حجم الملف في البيانات
                if "file_size" in details:
                    candidates_for_deletion[filename] = details["file_size"]
                else:
                    print(f"   ⚠️ تحذير: تم العثور على وسم '{TAG_TO_DELETE}' للملف '{filename}' ولكن لا يوجد حجم ملف مسجل له. سيتم تجاهله.")

    except json.JSONDecodeError:
        print(f"❌ خطأ: ملف JSON تالف أو غير صالح: {json_file}")
        return
    except Exception as e:
        print(f"❌ حدث خطأ غير متوقع أثناء قراءة ملف JSON: {e}")
        return
    
    if not candidates_for_deletion:
        print(f"\n✔️ لم يتم العثور على أي فيديوهات تحمل الوسم '{TAG_TO_DELETE}' في ملف JSON.")
        print("🎉 لا يوجد شيء لفعله. اكتملت العملية بنجاح!")
        return
        
    print(f"✔️ تم العثور على {len(candidates_for_deletion)} فيديو مرشح للحذف في ملف JSON.")

    # --- الخطوة 3: مسح مجلد الفيديوهات وجمع معلومات الملفات الموجودة ---
    print(f"\n[2/5] 📂 جاري مسح مجلد الفيديوهات: {videos_dir.name}")
    
    files_on_disk = {}
    try:
        for filename in os.listdir(videos_dir):
            full_path = videos_dir / filename
            if full_path.is_file():
                # تخزين المسار الكامل مع حجم الملف
                files_on_disk[filename] = {
                    "path": full_path,
                    "size": full_path.stat().st_size
                }
    except Exception as e:
        print(f"❌ حدث خطأ أثناء مسح المجلد: {e}")
        return

    print(f"✔️ تم العثور على {len(files_on_disk)} ملف في المجلد.")

    # --- الخطوة 4: تحديد قائمة الحذف النهائية بناءً على تطابق الاسم والحجم ---
    print("\n[3/5] 🔄 جاري مقارنة البيانات وتحديد الملفات المراد حذفها...")
    
    files_to_delete = []
    for filename, size_from_json in candidates_for_deletion.items():
        # التحقق مما إذا كان الملف موجوداً على القرص
        if filename in files_on_disk:
            disk_file_info = files_on_disk[filename]
            # التحقق من تطابق حجم الملف
            if disk_file_info["size"] == size_from_json:
                files_to_delete.append(disk_file_info["path"])
            else:
                 print(f"   ⚠️ تحذير: الملف '{filename}' موجود ولكن حجمه مختلف. JSON: {size_from_json}, Disk: {disk_file_info['size']}. لن يتم حذفه.")

    # --- الخطوة 5: عرض النتائج وطلب تأكيد المستخدم ---
    print("\n[4/5] 📝 مراجعة وتأكيد عملية الحذف")
    
    if not files_to_delete:
        print("✔️ لا توجد ملفات مطابقة ليتم حذفها.")
        print("🎉 اكتملت العملية بنجاح!")
        return

    print("=" * 70)
    print(f"🚨 تم العثور على {len(files_to_delete)} ملف جاهز للحذف:")
    for file_path in files_to_delete:
        print(f"   - {file_path.name}")
    print("=" * 70)
    
    # طلب تأكيد المستخدم
    try:
        while True:
            choice = input("❓ هل أنت متأكد من أنك تريد حذف هذه الملفات نهائياً؟ (y/n): ").lower().strip()
            if choice in ['y', 'yes', 'نعم', 'ن']:
                # بدء الحذف
                print("\n[5/5] 🗑️ جاري تنفيذ الحذف...")
                deleted_count = 0
                error_count = 0
                for file_path in files_to_delete:
                    try:
                        os.remove(file_path)
                        print(f"   ✔️ تم حذف: {file_path.name}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ❌ فشل حذف: {file_path.name} (السبب: {e})")
                        error_count += 1
                
                print("\n" + "="*70)
                print("✅ اكتملت عملية الحذف.")
                print(f"   - عدد الملفات التي تم حذفها بنجاح: {deleted_count}")
                if error_count > 0:
                    print(f"   - عدد الملفات التي فشل حذفها: {error_count}")
                print("=" * 70)
                break # الخروج من حلقة التأكيد
                
            elif choice in ['n', 'no', 'لا', 'ل']:
                print("\n🚫 تم إلغاء عملية الحذف. لم يتم تغيير أي شيء.")
                break # الخروج من حلقة التأكيد
            else:
                print("   إدخال غير صالح. الرجاء إدخال 'y' للتأكيد أو 'n' للإلغاء.")
    except KeyboardInterrupt:
        print("\n🚫 تم إلغاء العملية من قبل المستخدم.")

if __name__ == "__main__":
    main()