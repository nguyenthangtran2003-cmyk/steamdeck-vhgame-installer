#!/usr/bin/env python3
"""
find_md5_literals.py — Tìm mọi hằng số MD5 / chuỗi hex-32 được hardcode trong
global-metadata.dat của game Unity IL2CPP.

Dùng khi bản dựng có kiểm tra toàn vẹn (integrity check) dạng:
    _CheckSteamApiDll: md5 != _SteamApiMd5, md5:<computed>

Cách dùng:
    python3 find_md5_literals.py /path/to/<TenGame>_Data/il2cpp_data/Metadata/global-metadata.dat

Kết quả: danh sách hằng số hex-32 kèm OFFSET FILE (dùng để sửa) và chỉ số bảng entry.
"""
import struct
import re
import sys

HEX32 = re.compile(rb"^[0-9a-fA-F]{32}$")
HEXRUN = re.compile(rb"[0-9a-fA-F]{32,}")


def read_header(d):
    magic, ver = struct.unpack_from("<II", d, 0)
    if magic != 0xFAB11BAF:
        sys.exit(f"Không phải global-metadata.dat (magic={magic:#x})")
    h = struct.unpack_from("<" + "I" * 40, d, 8)
    # Chuẩn: (stringLiteralOffset, stringLiteralSize, stringLiteralDataOffset, stringLiteralDataSize, ...)
    return ver, h[0], h[1], h[2], h[3]


def detect_layout(d, lo, ls, do, ds):
    """Trả về ('length_first' | 'index_first') bằng cách kiểm tra tính liên tục của data."""
    n = ls // 8
    best = None
    for mode in ("length_first", "index_first"):
        prev_end = None
        ok = 0
        for k in range(min(n, 4000)):
            a, b = struct.unpack_from("<ii", d, lo + k * 8)
            L, I = (a, b) if mode == "length_first" else (b, a)
            if L < 0 or I < 0 or L > 4096 or I + L > ds:
                break
            if prev_end is not None and I == prev_end:
                ok += 1
            prev_end = I + L
        if best is None or ok > best[1]:
            best = (mode, ok)
    return best[0]


def iter_literals(d, lo, ls, do, ds, mode):
    n = ls // 8
    for k in range(n):
        a, b = struct.unpack_from("<ii", d, lo + k * 8)
        L, I = (a, b) if mode == "length_first" else (b, a)
        if L < 0 or I < 0 or L > 65536 or I + L > ds:
            continue
        off = do + I
        yield k, off, L, d[off:off + L]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    d = open(path, "rb").read()
    ver, lo, ls, do, ds = read_header(d)
    print(f"file        : {path}")
    print(f"size        : {len(d)}")
    print(f"metadata ver: {ver}")
    print(f"stringLiteral      : off={lo} size={ls}")
    print(f"stringLiteralData  : off={do} size={ds}")
    mode = detect_layout(d, lo, ls, do, ds)
    print(f"entry layout       : {mode}   (a={'length' if mode=='length_first' else 'dataIndex'}, b={'dataIndex' if mode=='length_first' else 'length'})")
    print()

    print("=" * 78)
    print("A) Literal dạng hex-32 (ứng viên _SteamApiMd5) — từ stringLiteral table")
    print("=" * 78)
    found = []
    for k, off, L, raw in iter_literals(d, lo, ls, do, ds, mode):
        if L == 32 and HEX32.match(raw):
            found.append((k, off, raw.decode()))
            print(f"  index={k:<7} file_offset={off:<10} {raw.decode()}")
    if not found:
        print("  (không có)")

    print()
    print("=" * 78)
    print("B) Mọi chuỗi hex >=32 ký tự trong TOÀN BỘ file (gồm fieldDefaultValues...)")
    print("=" * 78)
    seen = set()
    for m in HEXRUN.finditer(d):
        s = m.group()
        for i in range(0, len(s) - 31, 32):
            chunk = s[i:i + 32]
            if len(chunk) == 32 and HEX32.match(chunk):
                off = m.start() + i
                key = (off, chunk)
                if key in seen:
                    continue
                seen.add(key)
                # Bỏ các chuỗi toàn '0' / toàn 'f' (rác)
                if chunk == b"0" * 32 or chunk == b"f" * 32 or chunk == b"F" * 32:
                    continue
                print(f"  file_offset={off:<10} {chunk.decode()}")

    print()
    print("=" * 78)
    print("C) Chuỗi log kiểm tra toàn vẹn (nếu có) để xác nhận đúng bản dựng")
    print("=" * 78)
    for pat in (b"_CheckSteamApiDll", b"_SteamApiMd5", b"md5 != ", b"Application.Quit"):
        i = 0
        hits = []
        while True:
            i = d.find(pat, i)
            if i < 0:
                break
            hits.append(i)
            i += 1
            if len(hits) >= 5:
                break
        if hits:
            print(f"  {pat.decode(errors='replace'):<20} -> offsets {hits}")

    print()
    print("Gợi ý: chạy tools/patch_md5.py để thay MD5 kỳ vọng bằng MD5 của file bạn đang dùng.")


if __name__ == "__main__":
    main()
