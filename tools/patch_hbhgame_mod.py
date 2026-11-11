#!/usr/bin/env python3
"""
patch_hbhgame_mod.py — Vá lỗi Wine-Mono Global Namespace trong Mod Việt Hóa HBHGAME

Vấn đề:
  Wine-Mono (mscoree.dll) yêu cầu class name truyền vào ExecuteInDefaultAppDomain
  phải chứa dấu '.' (strrchr(classA, '.')). Class không có namespace như 'MyApplication'
  bị từ chối với mã lỗi E_INVALIDARG, dẫn tới NULL pointer dereference crash (0x0).

Giải pháp:
  Thay chuỗi Unicode L"MyApplication" thành L".MyApplication" trong HBHGAMENMod.dll.
  Wine sẽ tách namespace rỗng "" và class "MyApplication", nạp thành công 100%.
"""

import sys
import os
import shutil

TARGET_ORIG = "MyApplication\0".encode("utf-16le")
TARGET_PATCH = ".MyApplication\0".encode("utf-16le")

def patch_file(dll_path, revert=False):
    if not os.path.exists(dll_path):
        print(f"[-] Không tìm thấy tệp: {dll_path}")
        return False

    with open(dll_path, "rb") as f:
        data = f.read()

    bak_path = dll_path + ".bak"

    if revert:
        if TARGET_PATCH not in data:
            print("[-] Tệp chưa được patch hoặc không tìm thấy chuỗi đã patch.")
            return False
        if not os.path.exists(bak_path):
            print(f"[!] Cảnh báo: Không tìm thấy {bak_path}, tạo backup...")
            shutil.copy2(dll_path, bak_path)
        new_data = data.replace(TARGET_PATCH, TARGET_ORIG, 1)
        with open(dll_path, "wb") as f:
            f.write(new_data)
        print(f"[+] Đã khôi phục {dll_path} về nguyên bản.")
        return True
    else:
        if TARGET_ORIG not in data:
            if TARGET_PATCH in data:
                print("[*] Tệp này đã được vá trước đó (.MyApplication).")
                return True
            print("[-] Không tìm thấy chuỗi mục tiêu 'MyApplication' trong tệp.")
            return False

        if not os.path.exists(bak_path):
            shutil.copy2(dll_path, bak_path)
            print(f"[+] Đã tạo bản sao lưu tại {bak_path}")

        new_data = data.replace(TARGET_ORIG, TARGET_PATCH, 1)
        with open(dll_path, "wb") as f:
            f.write(new_data)
        print(f"[+] Đã vá thành công {dll_path}: 'MyApplication' -> '.MyApplication'")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cách dùng:")
        print("  python patch_hbhgame_mod.py <đường_dẫn_HBHGAMENMod.dll> [--revert]")
        sys.exit(1)

    path = sys.argv[1]
    revert_mode = "--revert" in sys.argv
    success = patch_file(path, revert=revert_mode)
    sys.exit(0 if success else 1)
