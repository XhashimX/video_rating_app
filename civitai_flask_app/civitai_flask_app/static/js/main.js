// START: MODIFIED SECTION
document.addEventListener('DOMContentLoaded', () => {
    // --- 1. تحديد عناصر الواجهة ---
    const form = document.getElementById('generation-form');
    const generateBtn = document.getElementById('generate-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');
    
    const statusMessage = document.getElementById('status-message');
    const imageContainer = document.getElementById('image-container');
    const resultImage = document.getElementById('result-image');
    
    const stepsInput = document.getElementById('steps-input');
    const stepsValue = document.getElementById('steps-value');
    const cfgScaleInput = document.getElementById('cfg-scale-input');
    const cfgScaleValue = document.getElementById('cfg-scale-value');

    // --- 2. ربط الأحداث (Event Listeners) ---
    stepsInput.addEventListener('input', () => {
        stepsValue.textContent = stepsInput.value;
    });

    cfgScaleInput.addEventListener('input', () => {
        cfgScaleValue.textContent = cfgScaleInput.value;
    });

    form.addEventListener('submit', async (event) => {
        event.preventDefault(); 
        
        const formData = new FormData(form);
        const payload = {
            model: formData.get('model'),
            prompt: formData.get('prompt'),
            negativePrompt: formData.get('negativePrompt'),
            steps: parseInt(formData.get('steps'), 10),
            cfgScale: parseFloat(formData.get('cfgScale')),
            width: parseInt(formData.get('width'), 10),
            height: parseInt(formData.get('height'), 10),
            scheduler: formData.get('scheduler'),
            seed: formData.get('seed') ? parseInt(formData.get('seed'), 10) : -1
        };

        setLoadingState(true);
        resultImage.style.display = 'none';
        statusMessage.textContent = 'يتم إرسال الطلب...';

        try {
            const generateResponse = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!generateResponse.ok) {
                const errorData = await generateResponse.json();
                throw new Error(errorData.error || 'فشل في بدء عملية التوليد');
            }

            const jobData = await generateResponse.json();
            statusMessage.textContent = 'تم استلام المهمة! جارٍ التحقق من الحالة...';
            
            // --- التعديل الرئيسي هنا ---
            // نستخدم jobData.jobId الذي أرسلته الواجهة الخلفية
            checkJobStatus(jobData.jobId);

        } catch (error) {
            statusMessage.textContent = `خطأ: ${error.message}`;
            setLoadingState(false);
        }
    });

    // --- 5. وظيفة التحقق من حالة المهمة (Polling) ---
    const checkJobStatus = async (jobId) => { // تم تغيير اسم المتغير من token إلى jobId للوضوح
        try {
            // --- التعديل الرئيسي هنا ---
            // بناء الرابط باستخدام jobId
            const statusResponse = await fetch(`/status/${jobId}`);
            if (!statusResponse.ok) {
                throw new Error('فشل في الحصول على حالة المهمة.');
            }

            const jobStatus = await statusResponse.json();
            
            if (jobStatus.result && jobStatus.result.available) {
                statusMessage.textContent = 'اكتمل التوليد!';
                if (jobStatus.result.images && jobStatus.result.images.length > 0) {
                    const imageUrl = jobStatus.result.images[0].url;
                    resultImage.src = imageUrl;
                    resultImage.style.display = 'block';
                } else {
                    statusMessage.textContent = 'اكتمل التوليد ولكن لم يتم العثور على صور.';
                }
                setLoadingState(false);
            } else if (jobStatus.status === 'Processing' || jobStatus.status === 'Submitted') {
                let progress = jobStatus.progress ? `${(jobStatus.progress * 100).toFixed(0)}%` : '';
                statusMessage.textContent = `قيد المعالجة... ${progress}`;
                // إعادة التحقق بعد 3 ثوانٍ
                setTimeout(() => checkJobStatus(jobId), 3000);
            } else {
                 statusMessage.textContent = `حالة المهمة: ${jobStatus.status}. سأتوقف عن التحقق.`;
                 setLoadingState(false);
            }

        } catch (error) {
            statusMessage.textContent = `خطأ أثناء التحقق: ${error.message}`;
            setLoadingState(false);
        }
    };
    
    function setLoadingState(isLoading) {
        generateBtn.disabled = isLoading;
        if (isLoading) {
            btnText.style.display = 'none';
            btnSpinner.style.display = 'block';
        } else {
            btnText.style.display = 'block';
            btnSpinner.style.display = 'none';
        }
    }
});
// END: MODIFIED SECTION