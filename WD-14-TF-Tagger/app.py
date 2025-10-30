import gradio as gr
import subprocess
import os
import threading
import time
import sys
import shutil
import tempfile
from pathlib import Path
import json

# --- الإعدادات ---
DEFAULT_MODEL = "ConvNextV2"
TEMP_UPLOAD_DIR = "temp_uploads"
RESULTS_CACHE = {}

# إنشاء مجلد مؤقت للرفع إذا لم يكن موجوداً
if not os.path.exists(TEMP_UPLOAD_DIR):
    os.makedirs(TEMP_UPLOAD_DIR)

def clean_temp_folder():
    """تنظيف المجلد المؤقت من الملفات القديمة"""
    if os.path.exists(TEMP_UPLOAD_DIR):
        for file in os.listdir(TEMP_UPLOAD_DIR):
            file_path = os.path.join(TEMP_UPLOAD_DIR, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except:
                pass

def process_single_image(image_path, model_name, general_score, character_score, add_initial):
    """معالجة صورة واحدة وإرجاع التاجات"""
    # إنشاء مجلد مؤقت للصورة
    temp_dir = tempfile.mkdtemp(prefix="single_image_", dir=TEMP_UPLOAD_DIR)
    
    try:
        # نسخ الصورة إلى المجلد المؤقت
        image_name = os.path.basename(image_path)
        new_image_path = os.path.join(temp_dir, image_name)
        shutil.copy2(image_path, new_image_path)
        
        # تشغيل السكربت على هذه الصورة
        command = [
            sys.executable,
            "tagger.py",
            "--input", temp_dir,
            "--model", model_name,
            "--general_score", str(general_score)
        ]
        
        if character_score > 0:
            command.extend(["--character_score", str(character_score)])
        if add_initial:
            command.extend(["--add_initial_keyword", add_initial])
        
        # تشغيل الأمر
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            return f"❌ خطأ في معالجة الصورة:\n{stderr}", None
        
        # قراءة ملف التاجات
        txt_file = os.path.join(temp_dir, os.path.splitext(image_name)[0] + ".txt")
        if os.path.exists(txt_file):
            with open(txt_file, 'r', encoding='utf-8') as f:
                tags = f.read()
            return f"✅ تمت معالجة الصورة بنجاح!", tags
        else:
            return "⚠️ لم يتم العثور على ملف التاجات", None
            
    finally:
        # تنظيف المجلد المؤقت
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def run_tagging_process(input_folder, output_folder, model_name, general_score, character_score, add_initial):
    """معالجة مجلد كامل من الصور"""
    if not input_folder:
        return "❌ يرجى تحديد مجلد الإدخال", ""
    
    if not os.path.exists(input_folder):
        return "❌ مجلد الإدخال غير موجود", ""
    
    # التأكد من أن مجلد المخرجات موجود
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # استخدام مجلد الإدخال كمجلد إخراج إذا لم يتم تحديد مجلد إخراج
    final_output = output_folder if output_folder else input_folder
        
    # بناء الأمر
    command = [
        sys.executable,
        "tagger.py",
        "--input", input_folder,
        "--model", model_name,
        "--general_score", str(general_score)
    ]
    
    if output_folder:
        command.extend(["--output", output_folder])
    if character_score > 0:
        command.extend(["--character_score", str(character_score)])
    if add_initial:
        command.extend(["--add_initial_keyword", add_initial])
        
    print(f"🚀 Running command: {' '.join(command)}")
    
    # تشغيل الأمر
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    
    stdout_output = ""
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
            stdout_output += output
    
    stderr_output = process.stderr.read()
    if process.returncode != 0:
        return f"❌ حدث خطأ:\n{stderr_output}", ""
    
    # قراءة جميع ملفات التاجات من مجلد المخرجات
    all_tags = []
    txt_files = list(Path(final_output).glob("*.txt"))
    
    for txt_file in txt_files[:10]:  # عرض أول 10 ملفات كمثال
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()
            all_tags.append(f"📄 {txt_file.name}:\n{content}\n")
    
    if len(txt_files) > 10:
        all_tags.append(f"\n... و {len(txt_files) - 10} ملف آخر")
    
    tags_display = "\n".join(all_tags) if all_tags else "لم يتم العثور على ملفات تاجات"
    
    log_message = f"✅ اكتملت العملية بنجاح!\n\nتم معالجة {len(txt_files)} صورة\nالنتائج في: {final_output}\n\n--- LOG ---\n{stdout_output}"
    
    return log_message, tags_display

def handle_single_image(image, model_name, general_score, character_score, add_initial):
    """معالج رفع صورة واحدة"""
    if image is None:
        return "❌ يرجى رفع صورة", ""
    
    log, tags = process_single_image(image, model_name, general_score, character_score, add_initial)
    return log, tags

def get_local_ip():
    """الحصول على عنوان IP المحلي"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

# --- بناء واجهة Gradio ---
with gr.Blocks(theme=gr.themes.Soft(), title="WD-14 Tagger") as app:
    gr.Markdown("# 🖼️ WD-14 Tagger Interface")
    gr.Markdown("واجهة رسومية لاستخراج التاجات من الصور باستخدام نماذج WD-14")
    
    # عرض عنوان IP المحلي
    local_ip = get_local_ip()
    gr.Markdown(f"📱 **للوصول من الأجهزة الأخرى على الشبكة المحلية:** `http://{local_ip}:7860`")
    
    with gr.Tabs():
        # تبويب معالجة صورة واحدة
        with gr.TabItem("🖼️ صورة واحدة"):
            with gr.Row():
                with gr.Column(scale=1):
                    single_image = gr.Image(
                        label="ارفع صورة أو اسحبها هنا",
                        type="filepath",
                        height=300
                    )
                    
                    single_model = gr.Dropdown(
                        ["ConvNextV2", "ConvNext", "SwinV2", "ViTv2"], 
                        label="🤖 النموذج", 
                        value=DEFAULT_MODEL
                    )
                    
                    single_initial = gr.Textbox(
                        label="🔑 وسم إضافي (اختياري)", 
                        placeholder="e.g., 1girl, anime"
                    )
                    
                    with gr.Accordion("⚙️ إعدادات متقدمة", open=False):
                        single_general = gr.Slider(0.1, 1.0, value=0.4, step=0.05, label="حد الثقة العام")
                        single_char = gr.Slider(0.1, 1.0, value=0.85, step=0.05, label="حد ثقة الشخصيات")
                    
                    single_run = gr.Button("🚀 استخرج التاجات", variant="primary")
                
                with gr.Column(scale=1):
                    single_log = gr.Textbox(label="📝 الحالة", lines=3)
                    single_tags = gr.Textbox(
                        label="🏷️ التاجات المستخرجة (يمكنك نسخها)",
                        lines=10,
                        placeholder="التاجات ستظهر هنا..."
                    )
                    copy_btn = gr.Button("📋 نسخ التاجات", size="sm")
        
        # تبويب معالجة مجلد كامل
        with gr.TabItem("📁 مجلد كامل"):
            with gr.Row():
                with gr.Column(scale=1):
                    input_dir = gr.Textbox(
                        label="📂 مسار مجلد الصور",
                        placeholder="e.g., C:\\MyDataset\\Images"
                    )
                    output_dir = gr.Textbox(
                        label="📁 مجلد الحفظ (اختياري)",
                        placeholder="اتركه فارغاً للحفظ في نفس المجلد"
                    )
                    
                    folder_model = gr.Dropdown(
                        ["ConvNextV2", "ConvNext", "SwinV2", "ViTv2"],
                        label="🤖 النموذج",
                        value=DEFAULT_MODEL
                    )
                    
                    folder_initial = gr.Textbox(
                        label="🔑 وسم إضافي (اختياري)",
                        placeholder="e.g., my_character, 1girl"
                    )
                    
                    with gr.Accordion("⚙️ إعدادات متقدمة", open=False):
                        folder_general = gr.Slider(0.1, 1.0, value=0.4, step=0.05, label="حد الثقة العام")
                        folder_char = gr.Slider(0.1, 1.0, value=0.85, step=0.05, label="حد ثقة الشخصيات")
                    
                    folder_run = gr.Button("🚀 ابدأ المعالجة", variant="primary")
                
                with gr.Column(scale=2):
                    folder_log = gr.Textbox(
                        label="📝 سجل العملية",
                        lines=10,
                    )
                    folder_results = gr.Textbox(
                        label="📄 نماذج من النتائج (أول 10 ملفات)",
                        lines=15,
                    )
    
    # ربط الأحداث
    single_run.click(
        fn=handle_single_image,
        inputs=[single_image, single_model, single_general, single_char, single_initial],
        outputs=[single_log, single_tags]
    )
    
    folder_run.click(
        fn=run_tagging_process,
        inputs=[input_dir, output_dir, folder_model, folder_general, folder_char, folder_initial],
        outputs=[folder_log, folder_results]
    )
    
    # JavaScript لنسخ النص
    copy_btn.click(
        None,
        [single_tags],
        None,
        js="""
        (text) => {
            navigator.clipboard.writeText(text);
            alert('تم نسخ التاجات!');
        }
        """
    )

# --- تشغيل التطبيق ---
if __name__ == "__main__":
    print(f"\n🌐 التطبيق سيعمل على:")
    print(f"   - المحلي: http://localhost:7860")
    print(f"   - الشبكة المحلية: http://{get_local_ip()}:7860\n")
    
    # تنظيف المجلد المؤقت عند البداية
    clean_temp_folder()
    
    # تشغيل التطبيق على جميع الواجهات (0.0.0.0) للسماح بالوصول من الشبكة المحلية
    app.launch(
        server_name="0.0.0.0",  # يسمح بالوصول من أي جهاز على الشبكة
        server_port=7860,        # المنفذ
        share=False,             # لا نحتاج رابط عام
        inbrowser=True          # فتح المتصفح تلقائياً
    )
