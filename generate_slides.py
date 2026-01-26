# START: MODIFIED SECTION
import socket
import ssl

# قائمة النطاقات التي أعطت نتيجة إيجابية (301 أو 200) في الفحص السابق
hosts_to_test = [
    "m.facebook.com",
    "graph.facebook.com",
    "api.facebook.com",
    "zero.facebook.com",
    "static.xx.fbcdn.net",
    "connect.facebook.net",
    "developers.facebook.com"
]

def check_sni(host, port=443):
    """
    يحاول هذا التابع إنشاء اتصال SSL حقيقي (Handshake)
    لمعرفة ما إذا كان الـ SNI مسموحاً به.
    """
    # إنشاء سياق SSL آمن
    context = ssl.create_default_context()
    
    try:
        # إنشاء اتصال TCP عادي أولاً
        with socket.create_connection((host, port), timeout=5) as sock:
            # محاولة "تغليف" الاتصال بطبقة تشفير SSL
            # server_hostname هو ما يرسل كـ SNI
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                # إذا وصلنا هنا، يعني أن الاتصال المشفر نجح!
                return True, ssock.version()
                
    except ConnectionRefusedError:
        return False, "Connection Refused (Port Closed)"
    except socket.timeout:
        return False, "Timeout (Blocked by Firewall)"
    except ssl.SSLError as e:
        return False, f"SSL Error: {e}"
    except Exception as e:
        return False, str(e)

print("--- بدء فحص الـ SSL/SNI (المنفذ 443) ---")
print("هذا الفحص هو الأهم لتطبيقات V2Ray و Tunneling")
print("==========================================")

for host in hosts_to_test:
    print(f"جاري فحص SNI: {host} ...", end=" ")
    
    success, message = check_sni(host)
    
    if success:
        # إذا نجح الاتصال، فهذا هو الـ SNI الذي ستضعه في البرنامج!
        print(f"[✅ شغال 100%] بروتوكول: {message}")
    else:
        print(f"[❌ فشل] السبب: {message}")

print("==========================================")
# END: MODIFIED SECTION