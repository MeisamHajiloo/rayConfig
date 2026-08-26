#!/usr/bin/env python3
"""
WireGuard Auto Setup - راه‌اندازی خودکار WireGuard روی VPS
"""

import os
import subprocess
import sys
import time
import re
import ipaddress
from typing import Tuple, Optional

# ==================== توابع کمکی ====================

def check_root():
    """بررسی دسترسی root"""
    if os.geteuid() != 0:
        print("❌ لطفاً با دسترسی root اجرا کنید: sudo python3 wireguard_auto_setup.py")
        sys.exit(1)

def run_command(cmd: str, capture: bool = True) -> Tuple[int, str, str]:
    """اجرای دستور و بازگرداندن نتیجه"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def get_interface_name() -> str:
    """پیدا کردن نام اینترفیس شبکه اصلی"""
    try:
        # روش 1: از مسیر پیش‌فرض
        result = subprocess.run(
            "ip route | grep default | awk '{print $5}'",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        
        # روش 2: از ip link
        result = subprocess.run(
            "ip link show | grep -E '^[0-9]+: (en|eth|ens)' | head -1 | awk -F': ' '{print $2}'",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        
        # روش 3: برگشتن به eth0
        return "eth0"
    except:
        return "eth0"

def get_server_ip() -> str:
    """گرفتن آی‌پی عمومی سرور"""
    try:
        import requests
        ip = requests.get('https://api.ipify.org', timeout=5).text
        if ip:
            return ip
    except:
        pass
    
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "YOUR_SERVER_IP"

def is_wireguard_installed() -> bool:
    """بررسی نصب WireGuard"""
    returncode, _, _ = run_command("which wg")
    return returncode == 0

def install_wireguard() -> bool:
    """نصب WireGuard"""
    print("📦 در حال نصب WireGuard...")
    
    # به‌روزرسانی
    run_command("apt update", capture=True)
    
    # نصب
    returncode, stdout, stderr = run_command("apt install wireguard wireguard-tools -y", capture=True)
    
    if returncode == 0:
        print("✅ WireGuard نصب شد!")
        return True
    else:
        print(f"❌ خطا در نصب: {stderr}")
        return False

def generate_keys(key_type: str = "server") -> Tuple[str, str]:
    """تولید کلیدهای خصوصی و عمومی"""
    print(f"🔑 در حال تولید کلیدهای {key_type}...")
    
    # تولید کلید خصوصی
    private_key = None
    returncode, stdout, _ = run_command("wg genkey", capture=True)
    if returncode == 0 and stdout:
        private_key = stdout.strip()
    
    if not private_key:
        print("❌ خطا در تولید کلید خصوصی")
        sys.exit(1)
    
    # تولید کلید عمومی از کلید خصوصی
    public_key = None
    cmd = f"echo '{private_key}' | wg pubkey"
    returncode, stdout, _ = run_command(cmd, capture=True)
    if returncode == 0 and stdout:
        public_key = stdout.strip()
    
    if not public_key:
        print("❌ خطا در تولید کلید عمومی")
        sys.exit(1)
    
    return private_key, public_key

def setup_wireguard(interface: str, private_key: str, public_key: str) -> bool:
    """پیکربندی WireGuard روی سرور"""
    
    print(f"🔧 در حال پیکربندی WireGuard روی اینترفیس {interface}...")
    
    # ایجاد پوشه
    os.makedirs("/etc/wireguard", exist_ok=True)
    
    # ذخیره کلیدها
    with open("/etc/wireguard/server_private.key", "w") as f:
        f.write(private_key)
    os.chmod("/etc/wireguard/server_private.key", 0o600)
    
    with open("/etc/wireguard/server_public.key", "w") as f:
        f.write(public_key)
    os.chmod("/etc/wireguard/server_public.key", 0o644)
    
    # ایجاد کانفیگ سرور
    config_content = f"""[Interface]
Address = 10.0.0.1/24
SaveConfig = false
ListenPort = 51820
PrivateKey = {private_key}

PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o {interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o {interface} -j MASQUERADE
"""
    
    with open("/etc/wireguard/wg0.conf", "w") as f:
        f.write(config_content)
    
    # فعال‌سازی IP Forwarding
    with open("/etc/sysctl.conf", "a") as f:
        f.write("\n# WireGuard Settings\n")
        f.write("net.ipv4.ip_forward = 1\n")
        f.write("net.ipv6.conf.all.forwarding = 1\n")
    
    run_command("sysctl -p", capture=True)
    
    print("✅ پیکربندی کامل شد!")
    return True

def start_wireguard() -> bool:
    """راه‌اندازی سرویس WireGuard"""
    print("🚀 در حال راه‌اندازی WireGuard...")
    
    # بالا آوردن اینترفیس
    returncode, stdout, stderr = run_command("wg-quick up wg0", capture=True)
    
    if returncode != 0:
        print(f"❌ خطا در راه‌اندازی: {stderr}")
        print(stdout)
        return False
    
    # فعال کردن سرویس
    run_command("systemctl enable wg-quick@wg0", capture=True)
    
    time.sleep(2)
    
    # بررسی وضعیت
    returncode, _, _ = run_command("systemctl is-active --quiet wg-quick@wg0", capture=True)
    
    if returncode == 0:
        print("✅ سرویس WireGuard با موفقیت راه‌اندازی شد!")
        return True
    else:
        print("⚠️  سرویس راه‌اندازی شد اما بررسی وضعیت ناموفق بود")
        return True  # همچنان True برگردانیم چون ممکن است سرویس بالا آمده باشد

def create_client_config() -> Tuple[str, str]:
    """تولید کانفیگ کلاینت"""
    print("📱 در حال تولید کانفیگ کلاینت...")
    
    # تولید کلیدهای کلاینت
    client_private, client_public = generate_keys("client")
    
    # خواندن کلید عمومی سرور
    with open("/etc/wireguard/server_public.key", "r") as f:
        server_public = f.read().strip()
    
    # خواندن آی‌پی سرور
    server_ip = get_server_ip()
    
    # ساخت کانفیگ کلاینت
    config_content = f"""[Interface]
PrivateKey = {client_private}
Address = 10.0.0.2/24
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {server_public}
Endpoint = {server_ip}:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    
    # ذخیره کانفیگ کلاینت روی سرور
    with open("/etc/wireguard/client.conf", "w") as f:
        f.write(config_content)
    
    # ذخیره کلیدهای کلاینت برای استفاده بعدی
    with open("/etc/wireguard/client_private.key", "w") as f:
        f.write(client_private)
    os.chmod("/etc/wireguard/client_private.key", 0o600)
    
    with open("/etc/wireguard/client_public.key", "w") as f:
        f.write(client_public)
    os.chmod("/etc/wireguard/client_public.key", 0o644)
    
    # اضافه کردن کلاینت به کانفیگ سرور
    with open("/etc/wireguard/wg0.conf", "a") as f:
        f.write(f"""
[Peer]
PublicKey = {client_public}
AllowedIPs = 10.0.0.2/32
""")
    
    # ری‌استارت WireGuard برای اعمال تغییرات
    run_command("wg-quick down wg0", capture=True)
    run_command("wg-quick up wg0", capture=True)
    
    print("✅ کانفیگ کلاینت تولید شد!")
    return client_private, config_content

def generate_qr_code(content: str) -> bool:
    """تولید کد QR از کانفیگ"""
    try:
        # نصب qrencode اگر وجود ندارد
        run_command("apt install qrencode -y", capture=True)
        
        # تولید QR
        print("\n📱 کد QR برای اسکن در برنامه WireGuard موبایل:")
        print("-" * 50)
        cmd = f"echo '{content}' | qrencode -t ansiutf8"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            print(result.stdout)
            print("-" * 50)
            return True
        else:
            print("⚠️  ابزار qrencode نصب نشد یا خطا داشت")
            return False
    except Exception as e:
        print(f"⚠️  خطا در تولید QR: {e}")
        return False

def display_info(client_config: str):
    """نمایش اطلاعات کامل"""
    print("\n" + "=" * 70)
    print("✅ راه‌اندازی WireGuard با موفقیت انجام شد!")
    print("=" * 70)
    
    server_ip = get_server_ip()
    
    print(f"\n🌐 آی‌پی سرور: {server_ip}")
    print(f"🔢 پورت: 51820")
    print(f"🔑 پروتکل: UDP")
    
    # خواندن کلیدها
    with open("/etc/wireguard/server_public.key", "r") as f:
        server_public = f.read().strip()
    
    with open("/etc/wireguard/client_private.key", "r") as f:
        client_private = f.read().strip()
    
    print(f"\n🔑 کلید عمومی سرور: {server_public}")
    print(f"🔑 کلید خصوصی کلاینت: {client_private}")
    
    print("\n" + "-" * 70)
    print("📱 کانفیگ کلاینت:")
    print("-" * 70)
    print(client_config)
    
    # تولید QR
    print("\n" + "-" * 70)
    generate_qr_code(client_config)
    
    # ذخیره اطلاعات در فایل
    with open("/root/wireguard_info.txt", "w") as f:
        f.write("=" * 70 + "\n")
        f.write("WIREGUARD VPN INFORMATION\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Server IP: {server_ip}\n")
        f.write(f"Port: 51820\n")
        f.write(f"Protocol: UDP\n\n")
        f.write("Client Config:\n")
        f.write("-" * 50 + "\n")
        f.write(client_config)
        f.write("\n" + "-" * 50 + "\n")
        f.write(f"Server Public Key: {server_public}\n")
        f.write(f"Client Private Key: {client_private}\n")
        f.write(f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"\n💾 تمام اطلاعات در /root/wireguard_info.txt ذخیره شد.")
    
    print("\n" + "=" * 70)
    print("🎉 راه‌اندازی کامل شد!")
    print("=" * 70)
    
    print("\n💡 نکات مهم:")
    print("=" * 70)
    print("1. 📱 فایل کانفیگ بالا را در برنامه WireGuard موبایل ایمپورت کنید")
    print("2. 📸 یا از کد QR برای اسکن مستقیم استفاده کنید")
    print("3. 🔄 در صورت نیاز به کلاینت جدید، کلیدهای جدید تولید کنید")
    print("4. ✅ برای تست، آی‌پی خود را در سایت ifconfig.me چک کنید")
    print("=" * 70)

# ==================== تابع اصلی ====================

def main():
    """تابع اصلی برنامه"""
    print("=" * 70)
    print("🛠  ابزار راه‌اندازی خودکار WireGuard VPN")
    print("=" * 70)
    
    # بررسی دسترسی root
    check_root()
    
    # بررسی نصب WireGuard
    if not is_wireguard_installed():
        print("⚠️  WireGuard نصب نیست!")
        if not install_wireguard():
            print("❌ نصب WireGuard ناموفق بود!")
            sys.exit(1)
    else:
        print("✅ WireGuard قبلاً نصب شده است.")
    
    # پیدا کردن اینترفیس شبکه
    interface = get_interface_name()
    print(f"🌐 اینترفیس شبکه شناسایی شده: {interface}")
    
    # بررسی اینکه آیا WireGuard قبلاً پیکربندی شده
    if os.path.exists("/etc/wireguard/wg0.conf"):
        print("\n⚠️  کانفیگ قبلی WireGuard پیدا شد!")
        choice = input("آیا می‌خواهید کانفیگ جدید بسازید؟ (y/n): ").strip().lower()
        if choice != 'y':
            print("❌ نصب لغو شد.")
            sys.exit(0)
        
        # پاک کردن کانفیگ قبلی
        run_command("wg-quick down wg0", capture=True)
        run_command("rm -rf /etc/wireguard/*", capture=True)
        print("🗑️  کانفیگ قبلی پاک شد.")
    
    # تولید کلیدهای سرور
    server_private, server_public = generate_keys("server")
    
    # پیکربندی سرور
    if not setup_wireguard(interface, server_private, server_public):
        print("❌ پیکربندی ناموفق!")
        sys.exit(1)
    
    # راه‌اندازی سرویس
    if not start_wireguard():
        print("❌ راه‌اندازی سرویس ناموفق!")
        sys.exit(1)
    
    # تولید کانفیگ کلاینت
    client_private, client_config = create_client_config()
    
    # نمایش اطلاعات
    display_info(client_config)

if __name__ == "__main__":
    main()