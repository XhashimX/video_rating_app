import rotatescreen
import time

# START: MODIFIED SECTION
# هذا السكريبت يقوم بتبديل وضع الشاشة بين العرضي والطولي
# This script toggles the screen orientation between Landscape and Portrait

def toggle_orientation():
    try:
        # الحصول على الشاشة الأساسية
        # Get the primary display handle
        screen = rotatescreen.get_primary_display()
        
        # معرفة الوضع الحالي للشاشة
        # 0 = Landscape (الوضع الطبيعي)
        # 90 = Portrait (عمودي - مقلوب لليسار)
        # 180 = Landscape Flipped (مقلوب رأساً على عقب)
        # 270 = Portrait Flipped (عمودي - مقلوب لليمين)
        
        current_orientation = screen.current_orientation
        
        print(f"الوضع الحالي: {current_orientation}")
        
        # المنطق: إذا كان الوضع طبيعي (0)، اقلبه ليكون عمودياً (270 أو 90 حسب مسكتك للابتوب)
        # إذا كان أي شيء آخر، أعده للوضع الطبيعي (0)
        
        if current_orientation == 0:
            print("تحويل إلى الوضع العمودي (تيك توك)...")
            # اخترنا 270 لأن هذا عادة يناسب مسك اللابتوب ككتاب (البطارية تكون لليمين)
            # إذا كانت الصورة مقلوبة، جرب تغيير 270 إلى 90
            screen.set_portrait() 
        else:
            print("العودة للوضع الطبيعي...")
            screen.set_landscape()
            
        print("تم التدوير بنجاح! الفأرة يجب أن تعمل بشكل صحيح الآن.")

    except Exception as e:
        print(f"حدث خطأ: {e}")
        print("تأكد أن تعريف كرت الشاشة يدعم التدوير.")

if __name__ == "__main__":
    toggle_orientation()
    # إبقاء النافذة مفتوحة لثواني لقراءة الرسالة
    time.sleep(2)

# END: MODIFIED SECTION