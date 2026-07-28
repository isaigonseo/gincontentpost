"""
GinContent Post — License Verification & Activation
Uses Supabase for online verification + HWID-based offline validation.
"""

import os
import sys
import json
import base64
import hashlib
import uuid
import platform
import subprocess
import requests
from datetime import datetime, timedelta

SUPABASE_URL = "https://ahixqnsnpdvtrakqaynl.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFoaXhxbnNucGR2dHJha3FheW5sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk0NjQ4MjAsImV4cCI6MjA5NTA0MDgyMH0.NlPBemsRqjkNAsBGjYjRVQH7P6gODwWEI0eQiPSxk6Q"

if getattr(sys, 'frozen', False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))

LICENSE_FILE = os.path.join(_base_dir, "license.lic")


def get_hwid():
    uuid_out = ""
    try:
        if sys.platform == "win32":
            cmd = "wmic csproduct get uuid"
            creationflags = 0x08000000
            lines = subprocess.check_output(cmd, shell=True, creationflags=creationflags).decode(errors='ignore').split("\n")
            if len(lines) > 1:
                uuid_out = lines[1].strip()
    except Exception:
        pass

    if not uuid_out or "UUID" in uuid_out or len(uuid_out.replace("0", "").replace("-", "").strip()) == 0:
        uuid_out = "fallback-uuid"

    try:
        mac = str(uuid.getnode())
        proc = platform.processor() or "cpu"
        node = platform.node() or "pc"
        raw_id = f"{uuid_out}-{mac}-{proc}-{node}"
        return hashlib.sha256(raw_id.encode('utf-8')).hexdigest()
    except Exception:
        return hashlib.sha256(f"emergency-{platform.node()}".encode('utf-8')).hexdigest()


def get_device_name():
    try:
        return platform.node() or "Unknown PC"
    except:
        return "Unknown PC"


def encrypt_license(data, hwid):
    try:
        json_str = json.dumps(data)
        key = hashlib.sha256(hwid.encode('utf-8')).digest()
        encrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(json_str.encode('utf-8'))])
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception:
        return ""


def decrypt_license(encrypted_str, hwid):
    try:
        encrypted = base64.b64decode(encrypted_str.encode('utf-8'))
        key = hashlib.sha256(hwid.encode('utf-8')).digest()
        decrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(encrypted)])
        return json.loads(decrypted.decode('utf-8'))
    except Exception:
        return None


def check_offline_license():
    if not os.path.exists(LICENSE_FILE):
        return False, "Không tìm thấy file bản quyền."

    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            encrypted_str = f.read().strip()
    except Exception as e:
        return False, f"Không thể đọc file bản quyền: {e}"

    hwid = get_hwid()
    license_data = decrypt_license(encrypted_str, hwid)
    if not license_data:
        return False, "File bản quyền không hợp lệ hoặc copy từ máy khác."

    expires_at = license_data.get("expires_at")
    if expires_at and expires_at != "forever":
        try:
            exp_date_str = expires_at.split("T")[0]
            exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").date()
            if exp_date < datetime.now().date():
                return False, f"Bản quyền đã hết hạn vào ngày {exp_date_str}."
        except Exception:
            return False, "Định dạng thời hạn không hợp lệ."

    hardware_id = license_data.get("hardware_id")
    if hardware_id != hwid:
        return False, "Mã thiết bị của máy hiện tại không trùng khớp với bản quyền."

    if license_data.get("status") == "revoked":
        return False, "Bản quyền này đã bị khóa (Revoked)."

    # Ghi nhận lần sử dụng cuối lên Supabase (ngầm, bỏ qua nếu lỗi)
    update_last_seen(license_data.get("key"))

    return True, license_data


def update_last_seen(license_key):
    if not license_key:
        return
    try:
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json"
        }
        patch_url = f"{SUPABASE_URL}/rest/v1/licenses?key=eq.{license_key}"
        patch_data = {"last_seen": datetime.now().isoformat()}
        requests.patch(patch_url, headers=headers, json=patch_data, timeout=5)
    except:
        pass


def activate_online(license_key):
    license_key = license_key.strip()
    if not license_key:
        return False, "Mã key bản quyền không được để trống."

    hwid = get_hwid()
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json"
    }

    try:
        url = f"{SUPABASE_URL}/rest/v1/licenses?key=eq.{license_key}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return False, f"Không kết nối được máy chủ (HTTP {response.status_code})."
        
        results = response.json()
        if not results:
            return False, "Mã key bản quyền không tồn tại."
        
        license_data = results[0]
    except Exception as e:
        return False, f"Lỗi máy chủ Supabase: {e}"

    if license_data.get("status") == "revoked":
        return False, "Bản quyền này đã bị khóa."

    hardware_id = license_data.get("hardware_id")
    expires_at = license_data.get("expires_at")
    status = license_data.get("status")
    
    is_first_activation = False
    # Kích hoạt lần đầu nếu status = unused hoặc chưa có hardware_id
    if status == "unused" or not hardware_id:
        is_first_activation = True
        
    if is_first_activation:
        if not expires_at:
            new_exp = datetime.now() + timedelta(days=30)
            expires_at = new_exp.strftime("%Y-%m-%dT%H:%M:%S")
            license_data["expires_at"] = expires_at

    if expires_at:
        try:
            exp_date_str = expires_at.split("T")[0]
            exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").date()
            if exp_date < datetime.now().date():
                return False, f"Mã key này đã hết hạn vào ngày {exp_date_str}."
        except Exception:
            return False, "Thời hạn của mã key không hợp lệ."

    if not is_first_activation:
        if hardware_id != hwid:
            return False, "Key đã được sử dụng ở thiết bị khác. Vui lòng liên hệ Admin để reset thiết bị."

    # Update Supabase
    try:
        patch_url = f"{SUPABASE_URL}/rest/v1/licenses?key=eq.{license_key}"
        now_str = datetime.now().isoformat()
        patch_data = {
            "last_seen": now_str
        }
        
        if is_first_activation:
            patch_data["hardware_id"] = hwid
            patch_data["status"] = "active"
            patch_data["device_name"] = get_device_name()
            patch_data["activated_at"] = now_str
            patch_data["expires_at"] = expires_at
            
        headers["Prefer"] = "return=representation"
        patch_response = requests.patch(patch_url, headers=headers, json=patch_data, timeout=10)
        
        if patch_response.status_code not in (200, 204):
            return False, f"Không thể đăng ký thiết bị: {patch_response.text}"
        
        updated_data = patch_response.json()[0]
    except Exception as e:
        return False, f"Lỗi cập nhật thiết bị lên Supabase: {e}"

    # Save locally
    encrypted_str = encrypt_license(updated_data, hwid)
    try:
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            f.write(encrypted_str)
        return True, updated_data
    except Exception as e:
        return False, f"Không thể lưu file bản quyền: {e}"
