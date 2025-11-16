import subprocess
import json
import os

images_folder = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo pic"
exiftool_exe = r"C:\Windows\exiftool.exe"
output_file = "image_names_detailed.txt"

print("جاري استخراج الأسماء...")

# إضافة FileName للحقول المطلوبة
cmd = [exiftool_exe, "-j", "-r", "-RegionName", "-FileSize#", "-FileName", images_folder]
result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')

if result.returncode != 0:
    print("خطأ: تأكد من أن exiftool.exe موجود!")
    exit(1)

images_data = json.loads(result.stdout)
results = []

for img in images_data:
    region_name = img.get('RegionName')
    file_size = img.get('FileSize')
    file_name = img.get('FileName')  # ← إضافة اسم الملف
    
    if region_name and file_size and file_name:
        name = region_name[0] if isinstance(region_name, list) else region_name
        if name:
            # الصيغة الجديدة: اسم_الملف : حجم_الملف : اسم_الصاحب
            results.append(f"{file_name} : {file_size} : {name}")

with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print(f"تم! عدد الصور بأسماء: {len(results)}")
print(f"تم الحفظ في: {output_file}")

# عرض أول 5 أمثلة
if results:
    print("\nأمثلة من النتائج:")
    for line in results[:5]:
        print(f"  {line}")
