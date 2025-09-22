# START: MODIFIED SECTION
import sys
import ctypes
from scapy.all import ARP, Ether, srp
from mac_vendor_lookup import MacLookup, VendorNotFoundError

def is_admin():
    """
    تتحقق من صلاحيات المسؤول بطريقة صحيحة على ويندوز.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False

def scan_network(ip_range):
    """
    تقوم بمسح الشبكة للعثور على جميع الأجهزة المتصلة ومعلوماتها.
    """
    print(f"[*] جاري مسح الشبكة في النطاق: {ip_range}")
    print("[*] قد تستغرق هذه العملية دقيقة أو دقيقتين...")

    # 1. إنشاء حزمة ARP لسؤال "من يملك هذا الـ IP؟"
    arp_request = ARP(pdst=ip_range)
    
    # 2. إنشاء إطار Ethernet لإرسال الحزمة للجميع على الشبكة
    # ff:ff:ff:ff:ff:ff هو العنوان العام للبث (Broadcast)
    broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
    
    # 3. دمج الحزمتين معًا
    arp_request_broadcast = broadcast / arp_request
    
    # 4. إرسال الحزمة وانتظار الردود (srp = send and receive packets)
    # timeout=3 يعني أننا سننتظر 3 ثواني كحد أقصى للردود
    answered_list = srp(arp_request_broadcast, timeout=3, verbose=False)[0]
    
    clients_list = []
    mac_lookup = MacLookup()

    # 5. تحليل الردود التي وصلتنا
    for element in answered_list:
        ip_addr = element[1].psrc  # IP الخاص بالجهاز الذي رد
        mac_addr = element[1].hwsrc # MAC address الخاص به
        
        vendor = "غير معروف"
        try:
            # محاولة العثور على اسم الشركة المصنعة من الـ MAC
            vendor = mac_lookup.lookup(mac_addr)
        except VendorNotFoundError:
            pass # إذا لم نجد الشركة، سنتركه "غير معروف"
            
        clients_list.append({"ip": ip_addr, "mac": mac_addr, "vendor": vendor})
        
    return clients_list

def print_result(results_list):
    """
    تقوم بطباعة النتائج في جدول منظم وواضح.
    """
    print("\n------------------------------------------------------------------")
    print("الأجهزة التي تم العثور عليها في الشبكة:")
    print("------------------------------------------------------------------")
    print("IP Address\t\tMAC Address\t\tManufacturer")
    print("------------------\t-----------------\t--------------------------")
    for client in results_list:
        print(f"{client['ip']:<18}\t{client['mac']:<17}\t{client['vendor']}")
    print("------------------------------------------------------------------")


# --- الإعدادات ---
# !!! قم بتغيير هذا النطاق ليناسب شبكتك !!!
# /24 تعني مسح كل العناوين من 192.168.1.1 إلى 192.168.1.254
# تأكد من أن الجزء الأول يطابق عنوان الراوتر (Gateway) لديك
NETWORK_TO_SCAN = "192.168.254.175/24" # <--- عدّل هذا إذا كان الراوتر لديك مختلفًا

# --- التشغيل ---
if __name__ == "__main__":
    if not is_admin():
        print("[-] خطأ: يجب تشغيل هذا السكربت بصلاحيات المسؤول (Administrator).")
        sys.exit(1)
        
    found_devices = scan_network(NETWORK_TO_SCAN)
    if found_devices:
        print_result(found_devices)
    else:
        print("\n[!] لم يتم العثور على أي أجهزة. تأكد من أنك متصل بالشبكة الصحيحة.")

# END: MODIFIED SECTION