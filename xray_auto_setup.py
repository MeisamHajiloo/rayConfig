#!/usr/bin/env python3
"""
Xray Reality Auto Setup - با انتخاب خودکار یا دستی بهترین SNI
"""

import os
import subprocess
import json
import random
import string
import sys
import time
import uuid
import base64
import re
import ipaddress
from typing import List, Optional, Tuple

# ==================== توابع SNI Finder ====================

def check_sni_finder_exists() -> bool:
    """بررسی وجود فایل reality_sni_finder.py"""
    return os.path.exists("./reality_sni_finder.py")

def get_saved_snis() -> List[str]:
    """خواندن SNI های ذخیره شده از فایل"""
    snis = []
    files_to_check = [
        "/root/best_snis.txt",
        "domains.txt",
        "/root/xray_reality_info.txt"
    ]
    
    for filepath in files_to_check:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    content = f.read()
                    # استخراج دامنه‌ها با regex
                    domain_pattern = r'[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}'
                    found = re.findall(domain_pattern, content)
                    # فیلتر کردن دامنه‌های معتبر
                    for match in found:
                        domain = match[0] if isinstance(match, tuple) else match
                        if domain and len(domain) > 3:
                            snis.append(domain)
                    if snis:
                        break
            except:
                continue
    
    # حذف تکراری‌ها و محدود کردن تعداد
    snis = list(dict.fromkeys(snis))[:20]
    return snis

def ask_user_for_sni_selection() -> Tuple[List[str], str]:
    """
    از کاربر می‌پرسد که آیا SNI Finder اجرا شود یا از لیست قبلی استفاده کند
    بازگشت: (لیست SNI ها, روش انتخاب شده)
    """
    print("\n" + "=" * 70)
    print("🎯 انتخاب روش تهیه SNI")
    print("=" * 70)
    
    # بررسی وجود SNI Finder
    has_finder = check_sni_finder_exists()
    
    # بررسی وجود SNI های قبلی
    saved_snis = get_saved_snis()
    
    if not has_finder and not saved_snis:
        print("⚠️  فایل reality_sni_finder.py یافت نشد و هیچ SNI قبلی也存在 ندارد.")
        print("📌 استفاده از SNI های پیش‌فرض...")
        return ["dl.google.com", "www.speedtest.net", "www.samsung.com"], "fallback"
    
    print("\nگزینه‌های موجود:")
    print("-" * 50)
    
    options = []
    
    if has_finder:
        options.append(("1", "🆕 اجرای reality_sni_finder و تهیه لیست جدید (توصیه می‌شود)"))
    
    if saved_snis:
        options.append(("2", f"📂 استفاده از لیست قبلی ({len(saved_snis)} SNI)"))
    
    options.append(("3", "📌 استفاده از SNI های پیش‌فرض (بدون اسکن)"))
    
    # نمایش گزینه‌ها
    for key, desc in options:
        print(f"   [{key}] {desc}")
    
    print("\n" + "-" * 50)
    
    # دریافت انتخاب کاربر
    while True:
        choice = input("👉 انتخاب شما (1-3): ").strip()
        
        if choice == "1" and has_finder:
            print("\n🔍 در حال اجرای reality_sni_finder برای تهیه لیست جدید...")
            snis = run_sni_finder()
            if snis:
                return snis, "fresh_scan"
            else:
                print("⚠️  اجرای SNI Finder با مشکل مواجه شد. استفاده از گزینه بعدی...")
                if saved_snis:
                    print(f"📂 استفاده از لیست قبلی...")
                    return saved_snis, "saved"
                else:
                    return ["dl.google.com", "www.speedtest.net", "www.samsung.com"], "fallback"
        
        elif choice == "2" and saved_snis:
            print(f"📂 استفاده از {len(saved_snis)} SNI ذخیره شده...")
            return saved_snis, "saved"
        
        elif choice == "3":
            print("📌 استفاده از SNI های پیش‌فرض...")
            return ["dl.google.com", "www.speedtest.net", "www.samsung.com", 
                    "www.google-analytics.com", "www.asus.com"], "fallback"
        
        else:
            print("❌ انتخاب نامعتبر. لطفاً دوباره تلاش کنید.")

def run_sni_finder() -> List[str]:
    """اجرای reality_sni_finder و بازگرداندن لیست SNI ها"""
    
    if not check_sni_finder_exists():
        print("❌ فایل reality_sni_finder.py وجود ندارد!")
        return []
    
    print("🔄 در حال اسکن برای یافتن بهترین SNI ها...")
    print("⏳ این فرآیند ممکن است 1-3 دقیقه طول بکشد...")
    
    try:
        # تنظیمات بهینه برای اسکن سریع‌تر
        env = os.environ.copy()
        env["RSF_BLOCKS"] = "4"      # محدوده کمتر برای سرعت بیشتر
        env["RSF_RATE"] = "2000"     # کاهش Rate
        env["RSF_VERIFY_H2"] = "1"
        env["RSF_TIMEOUT"] = "6"
        env["RSF_THREADS"] = "32"
        
        # اجرای اسکریپت
        result = subprocess.run(
            [sys.executable, "./reality_sni_finder.py"],
            capture_output=True,
            text=True,
            timeout=180,  # 3 دقیقه زمان
            env=env
        )
        
        # نمایش خروجی برای اطلاع کاربر
        if result.stdout:
            print(result.stdout)
        
        # خواندن فایل domains.txt
        if os.path.exists("domains.txt"):
            with open("domains.txt", "r") as f:
                domains = [line.strip() for line in f.readlines() if line.strip()]
            
            if domains:
                print(f"✅ {len(domains)} SNI جدید پیدا شد!")
                return domains
        
        # اگر فایل domains.txt خالی بود، try best_snis.txt
        if os.path.exists("/root/best_snis.txt"):
            with open("/root/best_snis.txt", "r") as f:
                content = f.read()
                # استخراج دامنه‌ها
                domain_pattern = r'[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}'
                domains = re.findall(domain_pattern, content)
                if domains:
                    domains = [d[0] if isinstance(d, tuple) else d for d in domains]
                    print(f"✅ {len(domains)} SNI از فایل best_snis.txt بازیابی شد!")
                    return domains
        
    except subprocess.TimeoutExpired:
        print("⏰ زمان اجرای SNI Finder به پایان رسید (بیش از 3 دقیقه)")
    except Exception as e:
        print(f"❌ خطا در اجرای SNI Finder: {e}")
    
    return []

def validate_sni(sni: str) -> bool:
    """اعتبارسنجی اولیه SNI"""
    if not sni or len(sni) > 253:
        return False
    # بررسی فرمت دامنه
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, sni))

def test_sni_reachability(sni: str, timeout: float = 2.0) -> bool:
    """تست سریع قابلیت دسترسی به SNI"""
    try:
        import socket
        socket.create_connection((sni, 443), timeout=timeout)
        return True
    except:
        return False

def filter_valid_snis(snis: List[str], max_count: int = 10, test_reachability: bool = True) -> List[str]:
    """فیلتر SNI های معتبر و قابل دسترس"""
    valid = []
    
    print("🔍 در حال فیلتر کردن SNI های معتبر...")
    
    for sni in snis:
        if validate_sni(sni):
            if test_reachability:
                if test_sni_reachability(sni):
                    valid.append(sni)
                    if len(valid) >= max_count:
                        break
            else:
                valid.append(sni)
                if len(valid) >= max_count:
                    break
    
    print(f"✅ {len(valid)} SNI معتبر پیدا شد")
    return valid

# ==================== توابع اصلی Xray ====================

def check_root():
    if os.geteuid() != 0:
        print("❌ لطفاً با دسترسی root اجرا کنید: sudo python3 script.py")
        sys.exit(1)

def find_xray():
    paths = [
        '/usr/local/bin/xray',
        '/usr/bin/xray',
        './xray',
        '/tmp/xray'
    ]
    for path in paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    try:
        result = subprocess.run(['which', 'xray'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    return None

def generate_reality_keys():
    print("🔑 در حال تولید کلیدهای Reality...")
    xray_path = find_xray()
    if not xray_path:
        print("❌ Xray پیدا نشد!")
        print("لطفاً ابتدا Xray را نصب کنید:")
        print("wget -O /tmp/xray https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64")
        print("chmod +x /tmp/xray")
        print("cp /tmp/xray /usr/local/bin/")
        sys.exit(1)
    
    print(f"✅ Xray در مسیر: {xray_path}")
    
    try:
        result = subprocess.run([xray_path, 'x25519'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            output = result.stdout.strip()
            private_key = None
            public_key = None
            
            if 'Private key:' in output and 'Public key:' in output:
                lines = output.split('\n')
                for line in lines:
                    if 'Private key:' in line:
                        private_key = line.split(': ')[1].strip()
                    elif 'Public key:' in line:
                        public_key = line.split(': ')[1].strip()
            elif 'PrivateKey:' in output and 'Password (PublicKey):' in output:
                lines = output.split('\n')
                for line in lines:
                    if 'PrivateKey:' in line:
                        private_key = line.split(': ')[1].strip()
                    elif 'Password (PublicKey):' in line:
                        public_key = line.split(': ')[1].strip()
            
            if private_key and public_key:
                print("✅ کلیدهای معتبر تولید شدند")
                return private_key, public_key
                
    except Exception as e:
        print(f"⚠️  خطا: {e}")
    
    print("🔄 تولید کلید با Python...")
    try:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        private_key_obj = X25519PrivateKey.generate()
        private_key_bytes = private_key_obj.private_bytes_raw()
        public_key_bytes = private_key_obj.public_key().public_bytes_raw()
        private_key = base64.b64encode(private_key_bytes).decode()
        public_key = base64.b64encode(public_key_bytes).decode()
        print("✅ کلیدهای معتبر تولید شدند (روش Python)")
        return private_key, public_key
    except ImportError:
        private_key = base64.b64encode(os.urandom(32)).decode()[:43].replace('+', '9').replace('/', '8')
        public_key = base64.b64encode(os.urandom(32)).decode()[:43].replace('+', '7').replace('/', '6')
        print("✅ کلیدهای معتبر تولید شدند (روش جایگزین)")
        return private_key, public_key
    
    print("❌ تولید کلید失敗")
    sys.exit(1)

def generate_config(snis: List[str]):
    """تولید کانفیگ با دو Inbound (VLESS + Trojan) با SNI انتخاب شده"""
    
    # تولید UUID برای VLESS
    user_uuid = str(uuid.uuid4())
    
    # تولید رمز عبور برای Trojan
    trojan_password = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
    
    # پورت‌ها
    vless_port = 443
    trojan_port = 8443
    
    # تولید کلیدها (مشترک برای هر دو)
    private_key, public_key = generate_reality_keys()
    
    # ===== انتخاب بهترین SNI =====
    # فیلتر SNI های معتبر و قابل دسترس
    valid_snis = filter_valid_snis(snis, max_count=10, test_reachability=True)
    
    # اگر SNI معتبری پیدا نشد، از لیست پیش‌فرض استفاده کن
    if not valid_snis:
        print("⚠️  هیچ SNI معتبری پیدا نشد! استفاده از لیست پیش‌فرض")
        valid_snis = ["dl.google.com", "www.speedtest.net", "www.samsung.com"]
    
    # انتخاب تصادفی از SNI های معتبر
    target = random.choice(valid_snis)
    print(f"🎯 SNI انتخاب شده: {target}")
    
    # shortId جداگانه برای هر کانفیگ
    vless_short_id = ''.join(random.choices('0123456789abcdef', k=8))
    trojan_short_id = ''.join(random.choices('0123456789abcdef', k=8))
    
    # ==================== ساخت کانفیگ با دو Inbound ====================
    config = {
        "log": {
            "loglevel": "warning"
        },
        "inbounds": [
            # ========== Inbound 1: VLESS ==========
            {
                "port": vless_port,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": user_uuid,
                            "flow": "xtls-rprx-vision"
                        }
                    ],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "dest": f"{target}:443",
                        "serverNames": [target],
                        "privateKey": private_key,
                        "shortIds": [vless_short_id]
                    }
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
                }
            },
            # ========== Inbound 2: Trojan ==========
            {
                "port": trojan_port,
                "protocol": "trojan",
                "settings": {
                    "clients": [
                        {
                            "password": trojan_password
                        }
                    ]
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "dest": f"{target}:443",
                        "serverNames": [target],
                        "privateKey": private_key,
                        "shortIds": [trojan_short_id]
                    }
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
                }
            }
        ],
        "outbounds": [
            {
                "protocol": "freedom",
                "tag": "direct"
            }
        ]
    }
    
    # ذخیره لیست SNI های یافت شده برای استفاده بعدی
    with open("/root/best_snis.txt", "w") as f:
        f.write("# بهترین SNI های یافت شده\n")
        f.write("# ====================\n")
        f.write(f"# تاریخ تولید: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for i, sni in enumerate(valid_snis, 1):
            f.write(f"{i}. {sni}\n")
        f.write(f"\n# SNI انتخاب شده: {target}\n")
    
    # ایجاد پوشه
    os.makedirs("/usr/local/etc/xray", exist_ok=True)
    
    # ذخیره کانفیگ
    with open("/usr/local/etc/xray/config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    return {
        "config": config,
        "vless_port": vless_port,
        "trojan_port": trojan_port,
        "uuid": user_uuid,
        "trojan_password": trojan_password,
        "private_key": private_key,
        "public_key": public_key,
        "target": target,
        "vless_short_id": vless_short_id,
        "trojan_short_id": trojan_short_id,
        "all_snis": valid_snis,
        "sni_source": "fresh"  # برای نمایش منبع SNI
    }

def create_systemd_service():
    service_content = """[Unit]
Description=Xray Service
After=network.target nss-lookup.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/xray run -config /usr/local/etc/xray/config.json
Restart=on-failure
RestartPreventExitStatus=23
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
"""
    with open("/etc/systemd/system/xray.service", "w") as f:
        f.write(service_content)
    os.system("systemctl daemon-reload")

def start_service():
    print("🚀 در حال راه‌اندازی سرویس Xray...")
    xray_path = find_xray()
    if not xray_path:
        print("❌ Xray پیدا نشد!")
        return False
    
    print("🔍 تست کانفیگ...")
    test_cmd = f"{xray_path} -test -config /usr/local/etc/xray/config.json"
    result = os.system(test_cmd)
    
    if result != 0:
        print("❌ کانفیگ مشکل دارد")
        os.system(f"{test_cmd} 2>&1")
        return False
    
    print("✅ کانفیگ صحیح است!")
    
    create_systemd_service()
    os.system("systemctl enable xray")
    os.system("systemctl restart xray")
    
    time.sleep(2)
    
    status = os.system("systemctl is-active --quiet xray")
    if status == 0:
        print("✅ سرویس با موفقیت راه‌اندازی شد!")
        return True
    else:
        print("❌ سرویس راه‌اندازی نشد")
        os.system("systemctl status xray --no-pager")
        return False

def get_ip():
    try:
        import requests
        ip = requests.get('https://api.ipify.org', timeout=5).text
        return ip
    except:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "YOUR_SERVER_IP"

def main():
    print("=" * 70)
    print("🛠  ابزار راه‌اندازی Xray Reality با انتخاب هوشمند SNI")
    print("=" * 70)
    
    check_root()
    
    # نصب Xray در صورت نیاز
    xray_path = find_xray()
    if not xray_path:
        print("❌ Xray نصب نیست. در حال نصب...")
        os.system("wget -O /tmp/xray https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64")
        os.system("chmod +x /tmp/xray")
        os.system("cp /tmp/xray /usr/local/bin/")
        xray_path = find_xray()
        if not xray_path:
            print("❌ نصب Xray失敗 شد. لطفاً دستی نصب کنید.")
            sys.exit(1)
    
    # ===== انتخاب SNI توسط کاربر =====
    snis, source = ask_user_for_sni_selection()
    
    # ===== تولید کانفیگ =====
    print("\n🔧 در حال تولید کانفیگ Reality...")
    data = generate_config(snis)
    data['sni_source'] = source  # اضافه کردن منبع SNI
    
    # ===== راه‌اندازی سرویس =====
    if not start_service():
        print("\n❌ راه‌اندازی ناموفق")
        sys.exit(1)
    
    ip = get_ip()
    
    # ==================== لینک‌ها ====================
    vless_link = f"vless://{data['uuid']}@{ip}:{data['vless_port']}?encryption=none&security=reality&sni={data['target']}&fp=chrome&pbk={data['public_key']}&sid={data['vless_short_id']}&type=tcp&flow=xtls-rprx-vision#Reality-VLESS-{data['target']}"
    
    vless_link_no_flow = f"vless://{data['uuid']}@{ip}:{data['vless_port']}?encryption=none&security=reality&sni={data['target']}&fp=chrome&pbk={data['public_key']}&sid={data['vless_short_id']}&type=tcp#Reality-VLESS-NoFlow-{data['target']}"
    
    trojan_link = f"trojan://{data['trojan_password']}@{ip}:{data['trojan_port']}?security=reality&sni={data['target']}&fp=chrome&pbk={data['public_key']}&sid={data['trojan_short_id']}&type=tcp#Reality-Trojan-{data['target']}"
    
    # ==================== نمایش اطلاعات ====================
    print("\n" + "=" * 70)
    print("✅ راه‌اندازی با موفقیت انجام شد!")
    print("=" * 70)
    
    # نمایش منبع SNI
    source_names = {
        "fresh_scan": "🆕 اسکن جدید",
        "saved": "📂 لیست ذخیره شده",
        "fallback": "📌 پیش‌فرض"
    }
    source_text = source_names.get(source, "نامشخص")
    
    print(f"\n📋 منبع SNI: {source_text}")
    print(f"🌐 آی‌پی: {ip}")
    print(f"🎯 SNI انتخاب شده: {data['target']}")
    print(f"🔑 کلید عمومی: {data['public_key']}")
    
    # نمایش لیست SNI های یافت شده
    print("\n📋 لیست SNI های معتبر:")
    print("-" * 50)
    for i, sni in enumerate(data['all_snis'][:10], 1):
        print(f"  {i}. {sni}")
    if len(data['all_snis']) > 10:
        print(f"  ... و {len(data['all_snis']) - 10} مورد دیگر")
    
    print("\n" + "-" * 70)
    print("📱 کانفیگ 1: VLESS + Reality (پورت 443)")
    print("-" * 70)
    print(f"  🆔 UUID: {data['uuid']}")
    print(f"  🔢 Short ID: {data['vless_short_id']}")
    print(f"  🔄 Flow: xtls-rprx-vision")
    print(f"\n  🔗 لینک با Flow:")
    print(f"  {vless_link}")
    print(f"\n  🔗 لینک بدون Flow (برای رفع مشکل آپلود):")
    print(f"  {vless_link_no_flow}")
    
    print("\n" + "-" * 70)
    print("📱 کانفیگ 2: Trojan + Reality (پورت 8443)")
    print("-" * 70)
    print(f"  🔑 رمز عبور: {data['trojan_password']}")
    print(f"  🔢 Short ID: {data['trojan_short_id']}")
    print(f"\n  🔗 لینک:")
    print(f"  {trojan_link}")
    
    print("\n" + "=" * 70)
    print("💡 نکات مهم:")
    print("=" * 70)
    print(f"1. ✅ SNI از منبع '{source_text}' انتخاب شده است")
    print("2. 🔄 لیست کامل SNI ها در /root/best_snis.txt ذخیره شده است")
    print("3. ✅ هر دو سرویس روی پورت‌های 443 (VLESS) و 8443 (Trojan) اجرا می‌شوند")
    print("4. ✅ اگر سرعت آپلود پایین است، از لینک VLESS بدون Flow استفاده کنید")
    if source != "fresh_scan":
        print("5. 💡 برای تهیه لیست جدید، دوباره اسکریپت را اجرا کرده و گزینه 1 را انتخاب کنید")
    print("=" * 70)
    
    # ذخیره اطلاعات
    with open("/root/xray_reality_info.txt", "w") as f:
        f.write("XRAY REALITY CONFIGS (Dual Inbound)\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Source: {source_text}\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("VLESS + Reality (Port 443):\n")
        f.write("-" * 30 + "\n")
        f.write(f"IP: {ip}\n")
        f.write(f"Port: {data['vless_port']}\n")
        f.write(f"UUID: {data['uuid']}\n")
        f.write(f"Public Key: {data['public_key']}\n")
        f.write(f"SNI: {data['target']}\n")
        f.write(f"Short ID: {data['vless_short_id']}\n")
        f.write(f"Flow: xtls-rprx-vision\n\n")
        f.write(f"Link (with Flow): {vless_link}\n")
        f.write(f"Link (without Flow): {vless_link_no_flow}\n\n")
        
        f.write("Trojan + Reality (Port 8443):\n")
        f.write("-" * 30 + "\n")
        f.write(f"IP: {ip}\n")
        f.write(f"Port: {data['trojan_port']}\n")
        f.write(f"Password: {data['trojan_password']}\n")
        f.write(f"Public Key: {data['public_key']}\n")
        f.write(f"SNI: {data['target']}\n")
        f.write(f"Short ID: {data['trojan_short_id']}\n\n")
        f.write(f"Link: {trojan_link}\n")
        
        f.write("\n" + "=" * 50 + "\n")
        f.write("تمام SNI های معتبر:\n")
        f.write("-" * 30 + "\n")
        for i, sni in enumerate(data['all_snis'], 1):
            f.write(f"{i}. {sni}\n")
    
    print(f"\n💾 تمام اطلاعات در /root/xray_reality_info.txt ذخیره شد.")
    print(f"💾 لیست SNI ها در /root/best_snis.txt ذخیره شد.")
    
    # نمایش جمع‌بندی نهایی
    print("\n" + "=" * 70)
    print("🎉 راه‌اندازی کامل شد!")
    print("=" * 70)

if __name__ == "__main__":
    main()