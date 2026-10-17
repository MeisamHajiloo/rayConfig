#!/usr/bin/env python3
"""
Xray Reality Auto Setup
- انتخاب هوشمند SNI
- انتخاب پورت دلخواه با بررسی اشغال بودن
- فعال سازی Fragment
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
import socket
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
                    domain_pattern = (
                        r'[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
                        r'(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*'
                        r'\.[a-zA-Z]{2,}'
                    )
                    found = re.findall(domain_pattern, content)
                    for match in found:
                        domain = match[0] if isinstance(match, tuple) else match
                        if domain and len(domain) > 3:
                            snis.append(domain)
                    if snis:
                        break
            except Exception:
                continue
    snis = list(dict.fromkeys(snis))[:20]
    return snis


def ask_user_for_sni_selection() -> Tuple[List[str], str]:
    """از کاربر می پرسد که آیا SNI Finder اجرا شود یا از لیست قبلی استفاده کند"""
    print("\n" + "=" * 70)
    print("🎯 انتخاب روش تهیه SNI")
    print("=" * 70)

    has_finder = check_sni_finder_exists()
    saved_snis = get_saved_snis()

    if not has_finder and not saved_snis:
        print("⚠️  فایل reality_sni_finder.py یافت نشد و هیچ SNI قبلی وجود ندارد.")
        print("📌 استفاده از SNI های پیش فرض...")
        return (
            ["dl.google.com", "www.speedtest.net", "www.samsung.com"],
            "fallback"
        )

    print("\nگزینه های موجود:")
    print("-" * 50)

    options = []
    if has_finder:
        options.append(("1", "🆕 اجرای reality_sni_finder و تهیه لیست جدید (توصیه می شود)"))
    if saved_snis:
        options.append(("2", f"📂 استفاده از لیست قبلی ({len(saved_snis)} SNI)"))
    options.append(("3", "📌 استفاده از SNI های پیش فرض (بدون اسکن)"))

    for key, desc in options:
        print(f"   [{key}] {desc}")

    print("\n" + "-" * 50)

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
                    print("📂 استفاده از لیست قبلی...")
                    return saved_snis, "saved"
                else:
                    return (
                        ["dl.google.com", "www.speedtest.net", "www.samsung.com"],
                        "fallback"
                    )

        elif choice == "2" and saved_snis:
            print(f"📂 استفاده از {len(saved_snis)} SNI ذخیره شده...")
            return saved_snis, "saved"

        elif choice == "3":
            print("📌 استفاده از SNI های پیش فرض...")
            return (
                ["dl.google.com", "www.speedtest.net", "www.samsung.com",
                 "www.google-analytics.com", "www.asus.com"],
                "fallback"
            )

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
        env = os.environ.copy()
        env["RSF_BLOCKS"] = "4"
        env["RSF_RATE"] = "2000"
        env["RSF_VERIFY_H2"] = "1"
        env["RSF_TIMEOUT"] = "6"
        env["RSF_THREADS"] = "32"

        result = subprocess.run(
            [sys.executable, "./reality_sni_finder.py"],
            capture_output=True,
            text=True,
            timeout=180,
            env=env
        )

        if result.stdout:
            print(result.stdout)

        if os.path.exists("domains.txt"):
            with open("domains.txt", "r") as f:
                domains = [line.strip() for line in f.readlines() if line.strip()]
            if domains:
                print(f"✅ {len(domains)} SNI جدید پیدا شد!")
                return domains

        if os.path.exists("/root/best_snis.txt"):
            with open("/root/best_snis.txt", "r") as f:
                content = f.read()
                domain_pattern = (
                    r'[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
                    r'(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*'
                    r'\.[a-zA-Z]{2,}'
                )
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
    pattern = (
        r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
        r'(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*'
        r'\.[a-zA-Z]{2,}$'
    )
    return bool(re.match(pattern, sni))


def test_sni_reachability(sni: str, timeout: float = 2.0) -> bool:
    """تست سریع قابلیت دسترسی به SNI"""
    try:
        socket.create_connection((sni, 443), timeout=timeout)
        return True
    except Exception:
        return False


def filter_valid_snis(snis: List[str], max_count: int = 10,
                     test_reachability: bool = True) -> List[str]:
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


# ==================== بررسی پورت ====================

def is_port_in_use(port: int) -> bool:
    """بررسی می کند که آیا پورت مورد نظر اشغال است یا خیر"""
    # روش اول: تلاش برای bind کردن
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            return True
    # روش دوم: بررسی با ss (برای پورت های TIME_WAIT یا فرآیندهای دیگر)
    try:
        result = subprocess.run(
            ["ss", "-tulnp"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            pattern = re.compile(rf":{port}\b")
            if pattern.search(result.stdout):
                return True
    except Exception:
        pass
    return False


def get_port_owner(port: int) -> str:
    """در صورت اشغال بودن پورت، نام فرآیند و PID مالک را برمی گرداند"""
    try:
        result = subprocess.run(
            ["ss", "-tulnp"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if re.search(rf":{port}\b", line):
                    m = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
                    if m:
                        return f"{m.group(1)} (PID: {m.group(2)})"
                    return line.strip()
    except Exception:
        pass
    return "نامشخص"


def list_common_used_ports() -> List[int]:
    """لیست پورت های رایجی که معمولاً اشغال هستند"""
    common_ports = [22, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995,
                    3306, 3389, 5432, 6379, 8080, 8443, 9000, 27017]
    used = []
    for p in common_ports:
        if is_port_in_use(p):
            used.append(p)
    return used


def find_free_port_near(port: int, max_tries: int = 20) -> Optional[int]:
    """یک پورت آزاد نزدیک به پورت داده شده پیدا می کند"""
    for offset in range(1, max_tries + 1):
        candidate = port + offset
        if candidate > 65535:
            break
        if not is_port_in_use(candidate):
            return candidate
    return None


def ask_user_for_single_port(service_name: str, default_port: int,
                             used_ports: List[int]) -> int:
    """
    از کاربر یک پورت می گیرد و بررسی می کند:
      - عدد معتبر باشد
      - در لیست پورت های قبلاً انتخاب شده نباشد
      - اشغال نباشد
    """
    while True:
        port_input = input(
            f"👉 پورت {service_name} (پیش فرض {default_port}): "
        ).strip()

        if not port_input:
            port = default_port
        else:
            try:
                port = int(port_input)
            except ValueError:
                print("❌ لطفاً یک عدد معتبر وارد کنید.")
                continue

        if not (1 <= port <= 65535):
            print("❌ پورت باید بین 1 تا 65535 باشد.")
            continue

        # بررسی تداخل با پورت های قبلاً انتخاب شده
        if port in used_ports:
            print(f"❌ پورت {port} قبلاً برای سرویس دیگری انتخاب شده است.")
            print("🔄 لطفاً پورت دیگری وارد کنید.")
            continue

        # بررسی اشغال بودن پورت
        if is_port_in_use(port):
            owner = get_port_owner(port)
            print(f"❌ پورت {port} در حال حاضر اشغال است.")
            print(f"   🔍 مالک پورت: {owner}")
            print("🔄 لطفاً پورت دیگری وارد کنید.")
            suggestion = find_free_port_near(port)
            if suggestion:
                print(f"💡 پیشنهاد: پورت {suggestion} آزاد است.")
            continue

        # هشدار برای پورت های رزرو شده
        if port < 1024:
            print(f"⚠️  پورت {port} در محدودهٔ پورت های رزرو شده است.")
            print("   ممکن است با سرویس های سیستمی تداخل داشته باشد.")
            confirm = input("   آیا ادامه می دهید؟ (y/N): ").strip().lower()
            if confirm != "y":
                continue

        print(f"✅ پورت {service_name}: {port}")
        return port


def ask_user_for_ports() -> Tuple[int, int]:
    """از کاربر می پرسد پورت های مورد نظر برای VLESS و Trojan چیست"""
    print("\n" + "=" * 70)
    print("🔌 انتخاب پورت های سرویس")
    print("=" * 70)
    print("⚠️  نکته: پورت های 443 و 8443 پیش فرض هستند")
    print("⚠️  اگر پورت مورد نظر اشغال باشد، به شما اطلاع داده می شود")
    print("⚠️  پورت های پیشنهادی: 2443, 4443, 8443, 9443, 2083, 2087")
    print("-" * 50)

    used_common = list_common_used_ports()
    if used_common:
        print("📋 پورت های رایجی که در حال حاضر اشغال هستند:")
        print(f"   {', '.join(map(str, used_common))}")
        print("-" * 50)

    used_ports: List[int] = []

    vless_port = ask_user_for_single_port("VLESS", 443, used_ports)
    used_ports.append(vless_port)

    trojan_port = ask_user_for_single_port("Trojan", 8443, used_ports)

    print(f"\n✅ پورت VLESS: {vless_port}")
    print(f"✅ پورت Trojan: {trojan_port}")
    return vless_port, trojan_port


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
    except Exception:
        pass
    return None


def generate_reality_keys():
    """تولید کلیدهای Reality با روش های مختلف (سازگار با همه نسخه ها)"""
    print("🔑 در حال تولید کلیدهای Reality...")
    xray_path = find_xray()
    if not xray_path:
        print("❌ Xray پیدا نشد!")
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
                print("✅ کلیدهای معتبر تولید شدند (با Xray)")
                return private_key, public_key

    except Exception as e:
        print(f"⚠️  خطا در Xray: {e}")

    print("🔄 تولید کلید با Python...")
    try:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        private_key_obj = X25519PrivateKey.generate()

        try:
            private_key_bytes = private_key_obj.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_key_bytes = private_key_obj.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        except AttributeError:
            private_key_bytes = private_key_obj.private_bytes_raw()
            public_key_bytes = private_key_obj.public_key().public_bytes_raw()

        private_key = base64.b64encode(private_key_bytes).decode()
        public_key = base64.b64encode(public_key_bytes).decode()
        print("✅ کلیدهای معتبر تولید شدند (روش Python)")
        return private_key, public_key

    except ImportError:
        print("⚠️  کتابخانه cryptography نصب نیست. استفاده از روش جایگزین...")
        private_key = base64.b64encode(os.urandom(32)).decode()[:43].replace('+', '9').replace('/', '8')
        public_key = base64.b64encode(os.urandom(32)).decode()[:43].replace('+', '7').replace('/', '6')
        print("✅ کلیدهای جایگزین تولید شدند")
        return private_key, public_key
    except Exception as e:
        print(f"❌ تولید کلید با Python شکست خورد: {e}")
        private_key = base64.b64encode(os.urandom(32)).decode()[:43].replace('+', '9').replace('/', '8')
        public_key = base64.b64encode(os.urandom(32)).decode()[:43].replace('+', '7').replace('/', '6')
        print("✅ کلیدهای جایگزین تولید شدند")
        return private_key, public_key


def build_fragment_settings():
    """تنظیمات fragment برای قرار گرفتن در streamSettings"""
    return {
        "packets": "tlshello",
        "length": "100-200",
        "interval": "10-20"
    }


def generate_config(snis: List[str], vless_port: int, trojan_port: int):
    """تولید کانفیگ با دو Inbound (VLESS + Trojan) با SNI انتخاب شده و پورت های دلخواه"""

    user_uuid = str(uuid.uuid4())
    trojan_password = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
    private_key, public_key = generate_reality_keys()

    valid_snis = filter_valid_snis(snis, max_count=10, test_reachability=True)
    if not valid_snis:
        print("⚠️  هیچ SNI معتبری پیدا نشد! استفاده از لیست پیش فرض")
        valid_snis = ["dl.google.com", "www.speedtest.net", "www.samsung.com"]

    target = random.choice(valid_snis)
    print(f"🎯 SNI انتخاب شده: {target}")

    vless_short_id = ''.join(random.choices('0123456789abcdef', k=8))
    trojan_short_id = ''.join(random.choices('0123456789abcdef', k=8))

    fragment_settings = build_fragment_settings()

    base_stream = {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
            "dest": f"{target}:443",
            "serverNames": [target],
            "privateKey": private_key,
            "shortIds": [vless_short_id]
        },
        "fragment": fragment_settings,
        "sockopt": {
            "tcpFastOpen": True,
            "tcpNoDelay": True,
            "domainStrategy": "UseIP"
        }
    }

    trojan_stream = json.loads(json.dumps(base_stream))
    trojan_stream["realitySettings"]["shortIds"] = [trojan_short_id]

    config = {
        "log": {
            "loglevel": "warning"
        },
        "dns": {
            "servers": ["1.1.1.1", "8.8.8.8"]
        },
        "inbounds": [
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
                "streamSettings": base_stream,
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
                }
            },
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
                "streamSettings": trojan_stream,
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

    with open("/root/best_snis.txt", "w") as f:
        f.write("# بهترین SNI های یافت شده\n")
        f.write("# ====================\n")
        f.write(f"# تاریخ تولید: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for i, sni in enumerate(valid_snis, 1):
            f.write(f"{i}. {sni}\n")
        f.write(f"\n# SNI انتخاب شده: {target}\n")

    os.makedirs("/usr/local/etc/xray", exist_ok=True)

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
        "sni_source": "fresh"
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
    print("🚀 در حال راه اندازی سرویس Xray...")
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
        print("✅ سرویس با موفقیت راه اندازی شد!")
        return True
    else:
        print("❌ سرویس راه اندازی نشد")
        os.system("systemctl status xray --no-pager")
        return False


def get_ip():
    try:
        import requests
        ip = requests.get('https://api.ipify.org', timeout=5).text
        return ip
    except Exception:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "YOUR_SERVER_IP"


def main():
    print("=" * 70)
    print("🛠  ابزار راه اندازی Xray Reality با انتخاب هوشمند SNI، پورت و Fragment")
    print("=" * 70)

    check_root()

    xray_path = find_xray()
    if not xray_path:
        print("❌ Xray نصب نیست. لطفاً ابتدا Xray را نصب کنید.")
        sys.exit(1)

    # ===== انتخاب SNI توسط کاربر =====
    snis, source = ask_user_for_sni_selection()

    # ===== انتخاب پورت توسط کاربر (با بررسی اشغال بودن) =====
    vless_port, trojan_port = ask_user_for_ports()

    # ===== تولید کانفیگ =====
    print("\n🔧 در حال تولید کانفیگ Reality با Fragment...")
    data = generate_config(snis, vless_port, trojan_port)
    data['sni_source'] = source

    # ===== راه اندازی سرویس =====
    if not start_service():
        print("\n❌ راه اندازی ناموفق")
        sys.exit(1)

    ip = get_ip()

    # ==================== لینک ها با Fragment ====================
    frag_params = "fragment=1&fragmentLength=100-200&fragmentInterval=10-20"

    vless_link = (
        f"vless://{data['uuid']}@{ip}:{data['vless_port']}"
        f"?encryption=none&security=reality&sni={data['target']}&fp=chrome"
        f"&pbk={data['public_key']}&sid={data['vless_short_id']}&type=tcp"
        f"&flow=xtls-rprx-vision&{frag_params}"
        f"#Reality-VLESS-Fragment-{data['target']}"
    )

    vless_link_no_flow = (
        f"vless://{data['uuid']}@{ip}:{data['vless_port']}"
        f"?encryption=none&security=reality&sni={data['target']}&fp=chrome"
        f"&pbk={data['public_key']}&sid={data['vless_short_id']}&type=tcp"
        f"&{frag_params}"
        f"#Reality-VLESS-NoFlow-Fragment-{data['target']}"
    )

    trojan_link = (
        f"trojan://{data['trojan_password']}@{ip}:{data['trojan_port']}"
        f"?security=reality&sni={data['target']}&fp=chrome"
        f"&pbk={data['public_key']}&sid={data['trojan_short_id']}&type=tcp"
        f"&{frag_params}"
        f"#Reality-Trojan-Fragment-{data['target']}"
    )

    # ==================== نمایش اطلاعات ====================
    print("\n" + "=" * 70)
    print("✅ راه اندازی با موفقیت انجام شد!")
    print("=" * 70)

    source_names = {
        "fresh_scan": "🆕 اسکن جدید",
        "saved": "📂 لیست ذخیره شده",
        "fallback": "📌 پیش فرض"
    }
    source_text = source_names.get(source, "نامشخص")

    print(f"\n📋 منبع SNI: {source_text}")
    print(f"🌐 آی پی: {ip}")
    print(f"🎯 SNI انتخاب شده: {data['target']}")
    print(f"🔑 کلید عمومی: {data['public_key']}")
    print(f"🔌 پورت VLESS: {data['vless_port']}")
    print(f"🔌 پورت Trojan: {data['trojan_port']}")
    print("🧩 Fragment: فعال (packets=tlshello, length=100-200, interval=10-20)")

    print("\n📋 لیست SNI های معتبر:")
    print("-" * 50)
    for i, sni in enumerate(data['all_snis'][:10], 1):
        print(f"  {i}. {sni}")
    if len(data['all_snis']) > 10:
        print(f"  ... و {len(data['all_snis']) - 10} مورد دیگر")

    print("\n" + "-" * 70)
    print(f"📱 کانفیگ 1: VLESS + Reality + Fragment (پورت {data['vless_port']})")
    print("-" * 70)
    print(f"  🆔 UUID: {data['uuid']}")
    print(f"  🔢 Short ID: {data['vless_short_id']}")
    print("  🔄 Flow: xtls-rprx-vision")
    print("\n  🔗 لینک با Flow و Fragment:")
    print(f"  {vless_link}")
    print("\n  🔗 لینک بدون Flow و با Fragment (برای رفع مشکل آپلود):")
    print(f"  {vless_link_no_flow}")

    print("\n" + "-" * 70)
    print(f"📱 کانفیگ 2: Trojan + Reality + Fragment (پورت {data['trojan_port']})")
    print("-" * 70)
    print(f"  🔑 رمز عبور: {data['trojan_password']}")
    print(f"  🔢 Short ID: {data['trojan_short_id']}")
    print("\n  🔗 لینک با Fragment:")
    print(f"  {trojan_link}")

    print("\n" + "=" * 70)
    print("💡 نکات مهم:")
    print("=" * 70)
    print(f"1. ✅ SNI از منبع '{source_text}' انتخاب شده است")
    print(f"2. 🔌 پورت VLESS: {data['vless_port']} | پورت Trojan: {data['trojan_port']}")
    print("3. 🧩 Fragment فعال است (packets=tlshello, length=100-200, interval=10-20)")
    print("4. 🔄 لیست کامل SNI ها در /root/best_snis.txt ذخیره شده است")
    print("5. ✅ اگر سرعت آپلود پایین است، از لینک VLESS بدون Flow استفاده کنید")
    print("6. ⚠️ برخی کلاینت ها ممکن است پارامترهای fragment در لینک را نادیده بگیرند؛")
    print("   در آن صورت باید fragment را دستی در کلاینت فعال کنید.")
    if source != "fresh_scan":
        print("7. 💡 برای تهیه لیست جدید، دوباره اسکریپت را اجرا کرده و گزینه 1 را انتخاب کنید")
    print("=" * 70)

    with open("/root/xray_reality_info.txt", "w") as f:
        f.write("XRAY REALITY CONFIGS (Dual Inbound + Fragment)\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Source: {source_text}\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write(f"VLESS + Reality + Fragment (Port {data['vless_port']}):\n")
        f.write("-" * 30 + "\n")
        f.write(f"IP: {ip}\n")
        f.write(f"Port: {data['vless_port']}\n")
        f.write(f"UUID: {data['uuid']}\n")
        f.write(f"Public Key: {data['public_key']}\n")
        f.write(f"SNI: {data['target']}\n")
        f.write(f"Short ID: {data['vless_short_id']}\n")
        f.write("Flow: xtls-rprx-vision\n")
        f.write("Fragment: packets=tlshello, length=100-200, interval=10-20\n\n")
        f.write(f"Link (with Flow + Fragment): {vless_link}\n")
        f.write(f"Link (without Flow + Fragment): {vless_link_no_flow}\n\n")

        f.write(f"Trojan + Reality + Fragment (Port {data['trojan_port']}):\n")
        f.write("-" * 30 + "\n")
        f.write(f"IP: {ip}\n")
        f.write(f"Port: {data['trojan_port']}\n")
        f.write(f"Password: {data['trojan_password']}\n")
        f.write(f"Public Key: {data['public_key']}\n")
        f.write(f"SNI: {data['target']}\n")
        f.write(f"Short ID: {data['trojan_short_id']}\n")
        f.write("Fragment: packets=tlshello, length=100-200, interval=10-20\n\n")
        f.write(f"Link: {trojan_link}\n")

        f.write("\n" + "=" * 50 + "\n")
        f.write("تمام SNI های معتبر:\n")
        f.write("-" * 30 + "\n")
        for i, sni in enumerate(data['all_snis'], 1):
            f.write(f"{i}. {sni}\n")

    print(f"\n💾 تمام اطلاعات در /root/xray_reality_info.txt ذخیره شد.")
    print(f"💾 لیست SNI ها در /root/best_snis.txt ذخیره شد.")

    print("\n" + "=" * 70)
    print("🎉 راه‌اندازی کامل شد!")
    print("=" * 70)


if __name__ == "__main__":
    main()
