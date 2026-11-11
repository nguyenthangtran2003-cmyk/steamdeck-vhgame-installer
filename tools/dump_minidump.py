#!/usr/bin/env python3
"""
dump_minidump.py — Trích xuất nhanh Exception Record, RIP, RSP và Stack Frames từ file crash.dmp của Windows/Wine

Không phụ thuộc package ngoài (chỉ dùng thư viện chuẩn Python `struct`).
Hỗ trợ cả MemoryListStream (type 5) và Memory64ListStream (type 9).
"""

import sys
import struct
import os

def parse_minidump(dmp_path):
    if not os.path.exists(dmp_path):
        print(f"[-] Không tìm thấy tệp: {dmp_path}")
        return False

    with open(dmp_path, "rb") as f:
        data = f.read()

    if len(data) < 32:
        print("[-] Tệp quá nhỏ, không phải Minidump hợp lệ.")
        return False

    sig, ver, num_streams, stream_dir_rva = struct.unpack_from("<4sIIII", data, 0)[:4]
    if sig != b"MDMP":
        print(f"[-] Chữ ký không hợp lệ: {sig} (mong đợi b'MDMP')")
        return False

    print(f"[+] Minidump hợp lệ. Số lượng stream: {num_streams}")

    exception_info = None
    stack_memory = []

    # Quét thư mục Stream
    for i in range(num_streams):
        st_type, data_size, rva = struct.unpack_from("<III", data, stream_dir_rva + i * 12)
        
        # Stream 6: ExceptionStream
        if st_type == 6:
            thread_id = struct.unpack_from("<I", data, rva)[0]
            code, flags, rec, addr, nparams = struct.unpack_from("<IIQQI", data, rva + 8)
            ctx_desc_offset = rva + 8 + 4 + 4 + 8 + 8 + 4 + 4 + 15 * 8
            ctx_size, ctx_rva = struct.unpack_from("<II", data, ctx_desc_offset)
            
            # Đọc AMD64 CONTEXT: RIP ở offset 248 (0xf8), RSP ở offset 152 (0x98)
            rip = struct.unpack_from("<Q", data, ctx_rva + 0xf8)[0]
            rsp = struct.unpack_from("<Q", data, ctx_rva + 0x98)[0]
            rax = struct.unpack_from("<Q", data, ctx_rva + 0x78)[0]
            rcx = struct.unpack_from("<Q", data, ctx_rva + 0x80)[0]
            rdx = struct.unpack_from("<Q", data, ctx_rva + 0x88)[0]

            exception_info = {
                "thread_id": thread_id,
                "code": code,
                "addr": addr,
                "rip": rip,
                "rsp": rsp,
                "rax": rax,
                "rcx": rcx,
                "rdx": rdx
            }

        # Stream 5: MemoryListStream (32-bit descriptors)
        elif st_type == 5:
            num_mems = struct.unpack_from("<I", data, rva)[0]
            for j in range(num_mems):
                vaddr, msize, mrva = struct.unpack_from("<QII", data, rva + 4 + j * 16)
                stack_memory.append((vaddr, msize, mrva))

        # Stream 9: Memory64ListStream
        elif st_type == 9:
            num_mems, base_rva = struct.unpack_from("<QQ", data, rva)
            cur_rva = base_rva
            for j in range(num_mems):
                vaddr, msize = struct.unpack_from("<QQ", data, rva + 16 + j * 16)
                stack_memory.append((vaddr, msize, cur_rva))
                cur_rva += msize

    if not exception_info:
        print("[-] Không tìm thấy ExceptionStream trong dump.")
        return False

    print("\n" + "="*50)
    print("THÔNG TIN CRASH (EXCEPTION RECORD)")
    print("="*50)
    print(f"Thread ID        : {exception_info['thread_id']}")
    print(f"Exception Code   : 0x{exception_info['code']:08X} ", end="")
    if exception_info['code'] == 0xC0000005:
        print("(STATUS_ACCESS_VIOLATION)")
    else:
        print()
    print(f"Exception Address: 0x{exception_info['addr']:016X}")
    print(f"RIP              : 0x{exception_info['rip']:016X}")
    print(f"RSP              : 0x{exception_info['rsp']:016X}")
    print(f"RAX              : 0x{exception_info['rax']:016X}")
    print(f"RCX              : 0x{exception_info['rcx']:016X}")
    print(f"RDX              : 0x{exception_info['rdx']:016X}")

    if exception_info['rip'] == 0x0:
        print("\n[!] PHÁT HIỆN: RIP = 0x0 -> Lỗi NULL Pointer Dereference (gọi hàm con trỏ rỗng)!")

    # Trích xuất 16 frames trên Stack tại RSP
    rsp = exception_info['rsp']
    found_stack = False
    for vaddr, msize, mrva in stack_memory:
        if vaddr <= rsp < vaddr + msize:
            found_stack = True
            offset = rsp - vaddr
            stack_bytes = data[mrva + offset : mrva + offset + 128]
            print("\n" + "="*50)
            print("ĐỈNH STACK TẠI RSP (RETURN ADDRESSES)")
            print("="*50)
            for k in range(0, min(len(stack_bytes), 128), 8):
                val = struct.unpack_from("<Q", stack_bytes, k)[0]
                marker = " <--- Đỉnh stack / Return Address" if k == 0 else ""
                print(f"  [RSP+0x{k:02X}] = 0x{val:016X}{marker}")
            break

    if not found_stack:
        print("\n[-] Không tìm thấy vùng nhớ chứa RSP trong Memory Stream.")

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cách dùng:")
        print("  python dump_minidump.py <đường_dẫn_crash.dmp>")
        sys.exit(1)

    parse_minidump(sys.argv[1])
