import torch
from basicsr.archs.rrdbnet_arch import RRDBNet

model_path = r"C:\Users\Stark\Download\myhome\video_rating_app\ESRGAN\Real-ESRGAN\weights\4x-UltraSharp.pth"

# ✓ تحقق من محتوى الملف
checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)

print(f"نوع البيانات: {type(checkpoint)}")

if isinstance(checkpoint, dict):
    print("المفاتيح:")
    for key in checkpoint.keys():
        if isinstance(checkpoint[key], dict):
            print(f"  ✓ {key}: dict")
        else:
            print(f"  ✗ {key}: {type(checkpoint[key])}")

# ✓ إذا كانت الأوزان تحت مفتاح معين:
if 'params_ema' in checkpoint:
    new_checkpoint = checkpoint['params_ema']
elif 'params' in checkpoint:
    new_checkpoint = checkpoint['params']
else:
    new_checkpoint = checkpoint

# حفظ الملف المصحح
torch.save(new_checkpoint, model_path + '_fixed.pth')
print(f"✓ تم حفظ الملف المصحح: {model_path}_fixed.pth")

# ✓ جرب النموذج المصحح
from realesrgan import RealESRGANer
import cv2

upsampler = RealESRGANer(
    scale=4,
    model_path=model_path + '_fixed.pth',
    model='RRDBNet',
    tile=400,
    half=True
)

print("✓ النموذج محمّل!")
