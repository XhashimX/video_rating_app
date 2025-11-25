# START: ENTIRE FILE "generate_pc_data.py"
import os
import json

# =========================================================
# ضع هنا المسار الكامل لمجلد الفيديوهات على كمبيوترك
# =========================================================
LOCAL_VIDEOS_PATH = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok"

# اسم الملف الذي سينتجه السكربت
OUTPUT_FILE = "pc_video_sizes.json"

def main():
    print(f"🚀 جاري مسح الفيديوهات في: {LOCAL_VIDEOS_PATH}")
    
    if not os.path.exists(LOCAL_VIDEOS_PATH):
        print("❌ خطأ: المسار غير موجود. تأكد من كتابته بشكل صحيح.")
        return

    # القاموس الذي سنحفظ فيه البيانات: المفتاح هو الحجم، والقيمة هي الاسم
    video_data = {}
    count = 0

    # os.walk يمر على المجلد وكل المجلدات الفرعية
    for root, _, files in os.walk(LOCAL_VIDEOS_PATH):
        for filename in files:
            # نركز فقط على ملفات الفيديو لتسريع العملية
            if filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                full_path = os.path.join(root, filename)
                try:
                    # الحصول على حجم الملف بالبايت
                    file_size = os.path.getsize(full_path)
                    
                    # نخزن الحجم كمفتاح (string)
                    video_data[str(file_size)] = filename
                    count += 1
                except Exception as e:
                    print(f"⚠️ خطأ في قراءة ملف: {filename}")

    # حفظ البيانات في ملف JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(video_data, f)

    print("-" * 50)
    print(f"✅ تم الانتهاء! تم مسح {count} فيديو.")
    print(f"📄 تم إنشاء الملف: {OUTPUT_FILE}")
    print("👉 الآن: ارفع هذا الملف إلى Google Colab بجانب السكربت الآخر.")

if __name__ == "__main__":
    main()
# END: ENTIRE FILE "generate_pc_data.py"