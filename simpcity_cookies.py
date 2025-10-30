import os
from pathlib import Path

# إعدادات البحث
search_dirs = [
    "C:\\Users\\Stark\\Download\\myhome\\video_rating_app",
    "C:\\Users\\Stark\\Downloads",
    "C:\\Users\\Stark\\.cache\\huggingface\\hub",
    "C:\\Users\\Stark\\AppData\\Local\\huggingface\\hub",
    "C:\\Users\\Stark",
    "C:\\",
]
exts = [".safetensors", ".onnx", ".pt", ".ckpt"]
min_size_mb = 50  # أقل حجم ملف 50 ميجابايت للموديلات

found_files = []

print("="*70)
for base in search_dirs:
    base_path = Path(base)
    if base_path.exists():
        print(f"\n🔍 البحث داخل: {base}")
        try:
            for root, dirs, files in os.walk(base, topdown=True):
                # عرض كل مجلد يتم الدخول عليه (يظهر المجلدات حتى لو مخفية)
                for file in files:
                    fpath = os.path.join(root, file)
                    try:
                        ext = os.path.splitext(fpath)[1].lower()
                        sz = os.path.getsize(fpath)
                        if ext in exts and sz > min_size_mb * 1024 * 1024:
                            found_files.append((fpath, sz))
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"⛔️ (تخطي) {base}: {e}")

if not found_files:
    print("\n❌ لم يتم العثور على أي موديلات كبيرة (سعت 50 ميجابايت أو أكثر)...")
else:
    print(f"\n✅ عدد ملفات الموديل الكبيرة التي تم إيجادها: {len(found_files)}\n")
    for fpath, sz in found_files:
        print(f" - {fpath}\n   ({round(sz/1024/1024, 2)} MB)")
print("="*70)
