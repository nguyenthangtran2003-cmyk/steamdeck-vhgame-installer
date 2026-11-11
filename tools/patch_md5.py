#!/usr/bin/env python3
"""
patch_md5.py — Thay MỘT chuỗi hex-32 (MD5) bằng chuỗi hex-32 khác trong file nhị phân.

Dùng cho kiểm tra toàn vẹn (integrity check) của game IL2CPP: thay giá trị
_SteamApiMd5 (MD5 của DLL gốc) cho khớp với MD5 của DLL đang dùng.

Cách dùng:
    python3 patch_md5.py <file> <old_md5_hex32> <new_md5_hex32> [--dry-run]

An toàn:
    - Bắt buộc old/new cùng độ dài 32 -> không phá offset/bảng metadata.
    - Tự tạo backup <file>.bak_patch trước khi ghi.
    - --dry-run: chỉ in ra vị trí, không ghi.
"""
import sys
import shutil
import os

OLD_DEFAULT_HELP = "vd: 240d8c3d2988d66d1329d38a92525bf4"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if len(args) != 3:
        sys.exit(__doc__)
    path, old_s, new_s = args
    old = old_s.encode()
    new = new_s.encode()

    if len(old) != 32 or len(new) != 32:
        sys.exit(f"LỖI: old/new phải đúng 32 ký tự hex (old={len(old)}, new={len(new)})")
    for name, b in (("old", old), ("new", new)):
        try:
            b.decode("ascii")
        except UnicodeDecodeError:
            sys.exit(f"LỖI: {name} không phải ASCII hex")
        if not all(c in b"0123456789abcdefABCDEF" for c in b):
            sys.exit(f"LỖI: {name} không phải chuỗi hex hợp lệ: {b}")

    d = bytearray(open(path, "rb").read())
    offs = []
    i = 0
    while True:
        i = d.find(old, i)
        if i < 0:
            break
        offs.append(i)
        i += 1

    print(f"file      : {path} ({len(d)} bytes)")
    print(f"old MD5   : {old_s}")
    print(f"new MD5   : {new_s}")
    print(f"tìm thấy  : {len(offs)} vị trí -> {offs}")

    if not offs:
        print("Không có gì để patch. Kiểm tra lại giá trị (chạy find_md5_literals.py).")
        return 1

    if new in d and set(offs) == set():
        pass
    if dry:
        print("[dry-run] KHÔNG ghi file.")
        return 0

    bak = f"{path}.bak_patch"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print(f"backup    : {bak}")
    else:
        print(f"backup    : đã có {bak} (bỏ qua)")

    for o in offs:
        d[o:o + 32] = new
    open(path, "wb").write(d)

    # verify
    d2 = open(path, "rb").read()
    left = d2.count(old)
    added = d2.count(new)
    print(f"verify    : old còn {left}, new có {added} (mong đợi {len(offs)})")
    print("OK." if left == 0 and added >= len(offs) else "CẢNH BÁO: verify không khớp!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
