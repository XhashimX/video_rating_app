import os
import subprocess
import json
import tkinter as tk
from tkinter import simpledialog, messagebox
from tkinter import filedialog


# وظيفة تنفيذ أوامر bash داخل السكربت
def run_command(command):
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("خطأ", f"فشل تنفيذ الأمر: {e}")
        return False
    return True

# وظيفة لاستخراج الاطارات من الفيديو
def extract_frames(video_path, output_dir):
    command = f"ffmpeg -i {video_path} {output_dir}/frame_%05d.png"
    return run_command(command)

# وظيفة لمعالجة الصور باستخدام Real-ESRGAN
def process_images(input_folder, output_folder, tile=128, outscale=1.2, model="RealESRGAN_x2plus", suffix="", fp32=True):
    command = f"python inference_realesrgan.py -n {model} -i {input_folder} -o {output_folder} --fp32 --tile {tile} --outscale {outscale} {f'--suffix {suffix}' if suffix else ''}"
    return run_command(command)

# وظيفة لاستخراج معلومات الفيديوهات من قاعدة البيانات
def update_json_with_new_size(new_size, json_paths):
    for path in json_paths:
        with open(path, 'r') as f:
            data = json.load(f)
        
        for file_name, data_entry in data.items():
            if file_name in new_size:
                data_entry["file_size"] = new_size[file_name]
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

# وظيفة لنقل الملفات بين المجلدات
def move_files(source_folder, target_folder):
    for filename in os.listdir(source_folder):
        source_file = os.path.join(source_folder, filename)
        target_file = os.path.join(target_folder, filename)
        
        if os.path.exists(target_file):
            os.replace(source_file, target_file)

# الوظيفة التفاعلية
def interactive_gui():
    root = tk.Tk()
    root.withdraw()  # لإخفاء النافذة الرئيسية

    # سؤال للمستخدم عن الخيار الذي يريد اختياره
    choice = simpledialog.askstring("اختيار", "هل تريد رفع جودة صور أو فيديوهات؟ اختر (صور / فيديوات)")
    
    # تحديد مجلدات الإدخال والإخراج
    input_folder = "C:/Users/Stark/Download/myhome/video_rating_app/ESRGAN/Real-ESRGAN/inputs"
    output_folder = "C:/Users/Stark/Download/myhome/video_rating_app/ESRGAN/Real-ESRGAN/output"
    
    # إذا اختار المستخدم رفع جودة الصور
    if choice.lower() == "صور":
        tile = simpledialog.askinteger("إدخال الحجم", "ادخل قيمة tile (الافتراضي 128):", minvalue=1, maxvalue=256, initialvalue=128)
        outscale = simpledialog.askfloat("مقياس الصورة", "ادخل قيمة outscale (الافتراضي 1.2):", minvalue=1.0, maxvalue=3.0, initialvalue=1.2)
        suffix = simpledialog.askstring("اللاحقة", "ادخل اللاحقة (إن وجدت، الافتراضي لا شيء):")
        
        model_choice = simpledialog.askstring("اختر الموديل", "اختر الموديل:\n1. RealESRGAN_x2plus\n2. RealESRGAN_x4plus\n3. realesr-general-x4v3\n4. RealESRGAN_x4plus_anime_6B\n5. realesr-animevideov3", initialvalue="RealESRGAN_x2plus")
        
        model_dict = {
            "1": "RealESRGAN_x2plus",
            "2": "RealESRGAN_x4plus",
            "3": "realesr-general-x4v3",
            "4": "RealESRGAN_x4plus_anime_6B",
            "5": "realesr-animevideov3"
        }
        model = model_dict.get(model_choice, "RealESRGAN_x2plus")
        
        # تنفيذ معالجة الصور
        if process_images(input_folder, output_folder, tile, outscale, model, suffix):
            messagebox.showinfo("نجاح", "تم رفع جودة الصور بنجاح!")
    
    # إذا اختار المستخدم معالجة الفيديوهات
    elif choice.lower() == "فيديوات":
        video_files = [f for f in os.listdir(input_folder) if f.endswith(".mp4")]
        for video in video_files:
            video_path = os.path.join(input_folder, video)
            frame_output_dir = os.path.join(output_folder, video.split(".")[0])
            if not os.path.exists(frame_output_dir):
                os.makedirs(frame_output_dir)
            
            # استخراج الإطارات من الفيديو
            if extract_frames(video_path, frame_output_dir):
                messagebox.showinfo("نجاح", f"تم استخراج الإطارات من {video} بنجاح!")
            
            # معالجة الإطارات باستخدام Real-ESRGAN
            if process_images(frame_output_dir, frame_output_dir, tile=128, outscale=1.2):
                messagebox.showinfo("نجاح", f"تم رفع جودة الإطارات في {video} بنجاح!")
                
                # تجميع الإطارات إلى فيديو
                output_video = f"{frame_output_dir}_without_voice.mp4"
                command = f"ffmpeg -framerate 24 -i {frame_output_dir}/frame_%05d_out.png -c:v libx264 -pix_fmt yuv420p {output_video}"
                if run_command(command):
                    messagebox.showinfo("نجاح", f"تم تجميع الفيديو بدون الصوت {output_video} بنجاح!")
                
                # إضافة الصوت للفيديو
                original_video = os.path.join(input_folder, video)
                final_output = f"{frame_output_dir}_output_video.mp4"
                command = f"ffmpeg -i {output_video} -i {original_video} -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -y {final_output}"
                if run_command(command):
                    messagebox.showinfo("نجاح", f"تم تجميع الفيديو النهائي {final_output} بنجاح!")
    else:
        messagebox.showerror("خطأ", "لم يتم التعرف على الخيار!")

    root.mainloop()


# تشغيل واجهة المستخدم التفاعلية
interactive_gui()
