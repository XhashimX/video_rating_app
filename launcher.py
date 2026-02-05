import webview
import threading
import time
import os
import signal
import sys
import subprocess # تمت إضافته لضمان عمل taskkill
from app import app

window = None
my_pid = os.getpid()
exit_flag = False

# ═══════════════════════════════════════════════════════
# 🔥 ULTRA KILL - الإغلاق القوي
# ═══════════════════════════════════════════════════════

def ultra_kill():
    """قتل كل شيء بالقوة وبدون رحمة لمنع رسائل الخطأ"""
    global exit_flag
    
    # إذا كنا قد بدأنا عملية القتل بالفعل، لا تكررها (منعاً للتكرار)
    if exit_flag:
        return
    exit_flag = True
    
    print("\n💀 إغلاق قوي فوري...")
    
    # ---------------------------------------------------------
    # التغيير الجذري هنا:
    # تم حذف window.destroy() لأنها تسبب StackOverflow
    # بدلاً منها سنستخدم القتل المباشر للعملية من نظام التشغيل
    # ---------------------------------------------------------

    # 1. القتل باستخدام Taskkill (الأقوى في ويندوز)
    try:
        if sys.platform == 'win32':
            # /F = إجبار، /T = شجرة العمليات، /PID = رقم العملية
            subprocess.Popen(['taskkill', '/F', '/T', '/PID', str(my_pid)],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           shell=True) # shell=True يخفي النافذة السوداء أحياناً
    except:
        pass

    # 2. محاولة استخدام psutil (احتياطي كما كان في كودك الأصلي)
    try:
        import psutil
        parent = psutil.Process(my_pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except:
                pass
        try:
            parent.kill()
        except:
            pass
    except:
        pass
    
    # 3. القتل التقليدي (احتياطي ثالث)
    try:
        if sys.platform != 'win32':
            os.killpg(os.getpgid(my_pid), signal.SIGKILL)
    except:
        pass
    
    # النهاية الحاسمة
    try:
        time.sleep(0.1)
        os._exit(0) # خروج فوري من بايثون
    except:
        pass

# ═══════════════════════════════════════════════════════
# Signal Handlers
# ═══════════════════════════════════════════════════════

def handle_signals(sig, frame):
    print("\n⚠️ إشارة إيقاف - جاري الإغلاق...")
    ultra_kill()

try:
    signal.signal(signal.SIGINT, handle_signals)
    signal.signal(signal.SIGTERM, handle_signals)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, handle_signals)
except:
    pass

# ═══════════════════════════════════════════════════════
# Keyboard Hooks (اختياري)
# ═══════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════
# Exception Handler
# ═══════════════════════════════════════════════════════

def exception_handler(exc_type, exc_value, exc_tb):
    # أي خطأ يحدث أثناء الإغلاق نتجاهله ونقتل البرنامج
    if exit_flag:
        return
    ultra_kill()

sys.excepthook = exception_handler

# ═══════════════════════════════════════════════════════
# Flask Server
# ═══════════════════════════════════════════════════════

def start_server():
    try:
        import logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        # تم تعطيل use_reloader لأنه يسبب تكرار العمليات ومشاكل في الإغلاق
        app.run(host='127.0.0.1', port=5000, threaded=True, debug=False, use_reloader=False)
    except:
        pass

# ═══════════════════════════════════════════════════════
# Python API
# ═══════════════════════════════════════════════════════

class Api:
    def toggle_fullscreen(self):
        if window and not exit_flag:
            try:
                window.toggle_fullscreen()
            except:
                pass
    
    def go_back(self):
        if window and not exit_flag:
            try:
                window.evaluate_js('window.history.back();')
            except:
                pass
    
    def exit_app(self):
        ultra_kill()
    
    def zoom(self, factor):
        if window and not exit_flag:
            try:
                window.evaluate_js(f"""
                    document.body.style.zoom = {factor};
                    localStorage.setItem('appZoom', {factor});
                """)
            except:
                pass

# ═══════════════════════════════════════════════════════
# JavaScript الذكي - النسخة الكاملة من observer
# ═══════════════════════════════════════════════════════

SMART_INJECTION = """
(function() {
    'use strict';
    
    // منع التنفيذ المتكرر
    if (window.__SMART_FEATURES_LOADED__) return;
    window.__SMART_FEATURES_LOADED__ = true;
    
    console.log('🔧 تفعيل الميزات الذكية...');
    
    // ═══════════════════════════════════════════════════════
    // 1. إخفاء السكرول بار - مع إعادة حقن تلقائية
    // ═══════════════════════════════════════════════════════
    
    function injectNoScrollbarCSS() {
        // حذف القديم
        const old = document.getElementById('smart-no-scrollbar');
        if (old) old.remove();
        
        // إنشاء جديد
        const style = document.createElement('style');
        style.id = 'smart-no-scrollbar';
        style.innerHTML = `
            *, *::before, *::after {
                scrollbar-width: none !important;
                -ms-overflow-style: none !important;
            }
            *::-webkit-scrollbar {
                display: none !important;
                width: 0 !important;
                height: 0 !important;
            }
            html, body {
                overflow-y: auto !important;
                overflow-x: hidden !important;
            }
        `;
        document.head.appendChild(style);
    }
    
    // حقن أولي
    injectNoScrollbarCSS();
    
    // إعادة الحقن عند أي تغيير في <head>
    const headObserver = new MutationObserver(function(mutations) {
        if (!document.getElementById('smart-no-scrollbar')) {
            injectNoScrollbarCSS();
        }
    });
    
    headObserver.observe(document.head, {
        childList: true,
        subtree: true
    });
    
    // ═══════════════════════════════════════════════════════
    // 2. إدارة الزوم
    // ═══════════════════════════════════════════════════════
    
    let currentZoom = parseFloat(localStorage.getItem('appZoom')) || 1.0;
    
    function setZoom(zoom) {
        currentZoom = zoom;
        document.body.style.zoom = currentZoom;
        localStorage.setItem('appZoom', currentZoom);
    }
    
    // تطبيق الزوم المحفوظ
    setZoom(currentZoom);
    
    // إعادة تطبيق الزوم عند تغيير body.style
    const bodyObserver = new MutationObserver(function(mutations) {
        const currentBodyZoom = parseFloat(document.body.style.zoom) || 1.0;
        if (Math.abs(currentBodyZoom - currentZoom) > 0.01) {
            document.body.style.zoom = currentZoom;
        }
    });
    
    bodyObserver.observe(document.body, {
        attributes: true,
        attributeFilter: ['style']
    });
    
    // ═══════════════════════════════════════════════════════
    // 3. اختصارات لوحة المفاتيح
    // ═══════════════════════════════════════════════════════
    
    function handleKeyboard(e) {
        // ] للرجوع
        if (e.key === ']') {
            e.preventDefault();
            e.stopPropagation();
            window.history.back();
            return false;
        }
        
        // F11 لملء الشاشة
        if (e.key === 'F11') {
            e.preventDefault();
            e.stopPropagation();
            if (window.pywebview?.api?.toggle_fullscreen) {
                window.pywebview.api.toggle_fullscreen();
            }
            return false;
        }
        
        // Ctrl+Escape للإغلاق
        if (e.key === 'Escape' && e.ctrlKey) {
            e.preventDefault();
            e.stopPropagation();
            if (window.pywebview?.api?.exit_app) {
                window.pywebview.api.exit_app();
            }
            return false;
        }
        
        // اختصارات الزوم
        if (e.ctrlKey || e.metaKey) {
            // تكبير
            if (e.key === '+' || e.key === '=') {
                e.preventDefault();
                e.stopPropagation();
                setZoom(Math.min(currentZoom + 0.1, 3.0));
                return false;
            }
            // تصغير
            if (e.key === '-') {
                e.preventDefault();
                e.stopPropagation();
                setZoom(Math.max(currentZoom - 0.1, 0.3));
                return false;
            }
            // إعادة ضبط
            if (e.key === '0') {
                e.preventDefault();
                e.stopPropagation();
                setZoom(1.0);
                return false;
            }
        }
    }
    
    // إضافة المستمعات
    document.addEventListener('keydown', handleKeyboard, true);
    window.addEventListener('keydown', handleKeyboard, true);
    
    // منع الزوم الافتراضي
    window.addEventListener('wheel', function(e) {
        if (e.ctrlKey) {
            e.preventDefault();
        }
    }, { passive: false });
    
    // ═══════════════════════════════════════════════════════
    // 4. مراقبة تحميل الصفحات الجديدة
    // ═══════════════════════════════════════════════════════
    
    // عند تغيير الـ URL (navigation)
    let lastUrl = location.href;
    new MutationObserver(function() {
        const currentUrl = location.href;
        if (currentUrl !== lastUrl) {
            lastUrl = currentUrl;
            console.log('🔄 صفحة جديدة - إعادة تطبيق الميزات...');
            
            // إعادة حقن CSS
            setTimeout(injectNoScrollbarCSS, 100);
            
            // إعادة تطبيق الزوم
            setTimeout(() => setZoom(currentZoom), 100);
        }
    }).observe(document.body, {
        childList: true,
        subtree: true
    });
    
    console.log('✅ الميزات الذكية مفعّلة');
    console.log('📊 الزوم الحالي:', currentZoom);
    
})();
"""

def inject_smart_features():
    """حقن الميزات الذكية"""
    if window and not exit_flag:
        try:
            window.evaluate_js(SMART_INJECTION)
            print("✅ تم حقن الميزات الذكية")
        except Exception as e:
            print(f"⚠️ خطأ في الحقن: {e}")

def on_loaded():
    """عند تحميل الصفحة"""
    if not exit_flag:
        print("📄 صفحة محملة")
        time.sleep(0.1)
        inject_smart_features()

def on_closing():
    """عند إغلاق النافذة"""
    print("🔄 إغلاق النافذة...")
    ultra_kill()
    return False  # إضافة مهمة: تمنع النافذة من الاستمرار في محاولة الإغلاق بنفسها

# ═══════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════

def wait_for_server():
    import socket
    for _ in range(50):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            if sock.connect_ex(('127.0.0.1', 5000)) == 0:
                sock.close()
                print("✅ السيرفر جاهز")
                return True
            sock.close()
        except:
            pass
        time.sleep(0.1)
    return False

def start_gui():
    global window
    
    if not wait_for_server():
        print("❌ فشل تشغيل السيرفر")
        os._exit(1)
    
    api = Api()
    
    # START: MODIFIED SECTION - تحديد مسار التخزين
    # نحدد مجلد للكاش بجوار ملف التشغيل ليحفظ البيانات فيه
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir = os.path.join(base_dir, '.webview_cache')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
    # END: MODIFIED SECTION
    
    try:
        window = webview.create_window(
            title='مدير مسابقات الفيديو',
            url='http://127.0.0.1:5000',
            width=1200,
            height=800,
            resizable=True,
            fullscreen=True,
            confirm_close=False,
            text_select=True,
            js_api=api
        )
        
        # ربط الأحداث
        window.events.loaded += on_loaded
        window.events.closing += on_closing
        
        print("✅ النافذة جاهزة")
        
        # START: MODIFIED SECTION - تفعيل الحفظ
        # storage_path: يحدد أين يحفظ الكوكيز والكاش
        # private_mode=False: يمنع مسح البيانات عند الخروج
        webview.start(debug=False, private_mode=False, storage_path=cache_dir)
        # END: MODIFIED SECTION
        
    except Exception as e:
        print(f"❌ خطأ في النافذة: {e}")
    finally:
        ultra_kill()

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 مدير مسابقات الفيديو")
    print("=" * 60)
    print("💡 للإغلاق:")
    print("   - Ctrl+C (في Terminal)")
    print("   - Ctrl+Escape (في التطبيق)")
    print("   - Alt+F4 أو زر X")
    print("=" * 60)
    
    # تشغيل السيرفر
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)
    
    # تشغيل GUI
    try:
        start_gui()
    except KeyboardInterrupt:
        print("\n⚠️ Ctrl+C")
        ultra_kill()
    except Exception as e:
        print(f"❌ خطأ: {e}")
        ultra_kill()