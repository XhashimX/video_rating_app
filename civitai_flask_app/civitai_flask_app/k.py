from dotenv import load_dotenv
import civitai
import time

load_dotenv()

print("🚀 بدء إنشاء صورة باستخدام Civitai...")

input_data = {
    "model": "urn:air:sd1:checkpoint:civitai:4201@130072",
    "params": {
        "prompt": "a beautiful landscape with mountains and a lake, sunset, realistic",
        "negativePrompt": "blurry, low quality, distorted",
        "scheduler": "EulerA",
        "steps": 20,
        "cfgScale": 7,
        "width": 512,
        "height": 512,
        "clipSkip": 2
    }
}

try:
    print("\n📤 إرسال الطلب...")
    response = civitai.image.create(input_data)
    
    print(f"✅ تم إنشاء المهمة بنجاح!")
    job_token = response['token']
    
    print(f"Token: {job_token}")
    
    # انتظر قليلاً قبل البدء بالتحقق (لإعطاء وقت لبدء المعالجة)
    print("\n⏳ انتظار بدء معالجة الصورة...")
    time.sleep(15)
    
    max_attempts = 20
    attempt = 0
    
    while attempt < max_attempts:
        try:
            print(f"\n📊 محاولة {attempt + 1}/{max_attempts}...")
            
            # استخدام token للاستعلام
            job_status = civitai.jobs.get(token=job_token)
            
            print(f"البيانات المُرجعة: {job_status}")
            
            # التحقق من البنية
            if isinstance(job_status, dict):
                jobs = job_status.get('jobs', [])
                if jobs:
                    job = jobs[0]
                    result = job.get('result', [])
                    
                    if result and isinstance(result, list) and len(result) > 0:
                        if result[0].get('available', False):
                            blob_key = result[0].get('blobKey')
                            image_url = f"https://image.civitai.com/{blob_key}"
                            print(f"\n🎉 تم توليد الصورة بنجاح!")
                            print(f"رابط الصورة: {image_url}")
                            break
                        else:
                            print(f"⏳ الصورة قيد المعالجة...")
                    else:
                        print(f"⏳ في انتظار النتائج...")
            
            attempt += 1
            if attempt < max_attempts:
                print("⏱️ انتظار 15 ثانية...")
                time.sleep(15)
            
        except TimeoutError:
            print(f"⚠️ انتهى وقت الانتظار في محاولة {attempt + 1}")
            attempt += 1
            time.sleep(15)
        except Exception as e:
            print(f"⚠️ خطأ في محاولة {attempt + 1}: {type(e).__name__}: {e}")
            attempt += 1
            if attempt < max_attempts:
                time.sleep(15)
    
    if attempt >= max_attempts:
        print(f"\n⏰ تم الوصول للحد الأقصى من المحاولات!")
        print(f"يمكنك التحقق يدوياً من حالة المهمة باستخدام Token: {job_token}")
            
except Exception as e:
    print(f"\n❌ حدث خطأ رئيسي: {e}")
    import traceback
    traceback.print_exc()
