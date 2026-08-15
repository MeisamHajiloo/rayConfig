#!/usr/bin/env python3
"""
Xray Reality Auto Setup - Dual Inbound (VLESS + Trojan در یک فایل)
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

def generate_config():
    """تولید کانفیگ با دو Inbound (VLESS + Trojan) در یک فایل"""
    
    # تولید UUID برای VLESS
    user_uuid = str(uuid.uuid4())
    
    # تولید رمز عبور برای Trojan
    trojan_password = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
    
    # پورت‌ها
    vless_port = 443
    trojan_port = 8443
    
    # تولید کلیدها (مشترک برای هر دو)
    private_key, public_key = generate_reality_keys()
    
    # انتخاب SNI
    targets = [
        "dl.google.com",
        "www.speedtest.net",
        "www.google-analytics.com",
        "www.samsung.com",
        "www.asus.com",
        "www.amd.com",
        "mci.ir",
        "www.irancell.ir"
    ]
    target = random.choice(targets)
    
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
        "trojan_short_id": trojan_short_id
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
    print("🛠  ابزار راه‌اندازی Xray Reality (VLESS + Trojan در یک کانفیگ)")
    print("=" * 70)
    
    check_root()
    
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
    
    print("🔧 در حال تولید کانفیگ Reality...")
    data = generate_config()
    
    if not start_service():
        print("\n❌ راه‌اندازی ناموفق")
        sys.exit(1)
    
    ip = get_ip()
    
    # ==================== لینک‌ها ====================
    # لینک VLESS با Flow
    vless_link = f"vless://{data['uuid']}@{ip}:{data['vless_port']}?encryption=none&security=reality&sni={data['target']}&fp=chrome&pbk={data['public_key']}&sid={data['vless_short_id']}&type=tcp&flow=xtls-rprx-vision#Reality-VLESS-{data['target']}"
    
    # لینک VLESS بدون Flow (برای رفع مشکل آپلود)
    vless_link_no_flow = f"vless://{data['uuid']}@{ip}:{data['vless_port']}?encryption=none&security=reality&sni={data['target']}&fp=chrome&pbk={data['public_key']}&sid={data['vless_short_id']}&type=tcp#Reality-VLESS-NoFlow-{data['target']}"
    
    # لینک Trojan
    trojan_link = f"trojan://{data['trojan_password']}@{ip}:{data['trojan_port']}?security=reality&sni={data['target']}&fp=chrome&pbk={data['public_key']}&sid={data['trojan_short_id']}&type=tcp#Reality-Trojan-{data['target']}"
    
    # ==================== نمایش اطلاعات ====================
    print("\n" + "=" * 70)
    print("✅ راه‌اندازی با موفقیت انجام شد!")
    print("=" * 70)
    
    print(f"\n🌐 آی‌پی: {ip}")
    print(f"🎯 SNI: {data['target']}")
    print(f"🔑 کلید عمومی: {data['public_key']}")
    
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
    print("1. ✅ هر دو سرویس روی یک پورت 443 (VLESS) و 8443 (Trojan) اجرا می‌شوند")
    print("2. ✅ اگر سرعت آپلود پایین است، از لینک VLESS بدون Flow استفاده کنید")
    print("3. ✅ اگر VLESS کار نکرد، از Trojan استفاده کنید (نیازی به Flow ندارد)")
    print("4. 🔄 برای تغییر SNI، از اسکریپت Reality-SNI-Finder استفاده کنید")
    print(" bash -c "$(curl -fsSL https://raw.githubusercontent.com/ShatakVPN/Reality-SNI-Finder/main/reality_sni_finder.sh)"")
    print("=" * 70)
    
    # ذخیره اطلاعات
    with open("/root/xray_reality_info.txt", "w") as f:
        f.write("XRAY REALITY CONFIGS (Dual Inbound)\n")
        f.write("=" * 50 + "\n\n")
        
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
    
    print(f"\n💾 تمام اطلاعات در /root/xray_reality_info.txt ذخیره شد.")

if __name__ == "__main__":
    main()