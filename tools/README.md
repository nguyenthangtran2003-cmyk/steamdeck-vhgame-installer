# `tools/` — bộ script hỗ trợ xử lý lỗi game và mod trên Linux

Cần `python` và `python-pefile` (chỉ dùng cho phần chẩn đoán PE trong `PLAYBOOK §5.4`).
Các script trong thư mục này đều có thể chạy với Python tiêu chuẩn không cần thư viện ngoài.

```bash
sudo pacman -S python python-pefile
```

---

## `find_md5_literals.py` — tìm hằng MD5 trong `global-metadata.dat`

### Dùng khi nào

Khi log của game có dòng dạng:

```
_CheckSteamApiDll: md5 != _SteamApiMd5, md5:<giá trị 32 ký tự hex>
```

nghĩa là bản dựng so MD5 của một tệp với hằng được hardcode. Ta cần biết hằng đó
nằm ở đâu để **kiểm tra xem nó có đúng là MD5 của tệp đang dùng không**.

### Cách chạy

```bash
python3 find_md5_literals.py "<TenGame>_Data/il2cpp_data/Metadata/global-metadata.dat"
```

### Kết quả gồm 3 phần

| Phần | Nội dung | Dùng để |
|---|---|---|
| **A** | hằng hex-32 trong bảng `stringLiteral`, kèm index + offset | **ứng viên chính** |
| **B** | mọi chuỗi hex ≥32 ký tự trong toàn tệp | tìm bản sao trong `fieldAndParameterDefaultValueData` |
| **C** | vị trí các chuỗi kiểm tra toàn vẹn | xác nhận đúng bản dựng |

Dòng header in ra phiên bản metadata và **cách script dò được cấu trúc bảng**:

```
metadata ver: 31
stringLiteral      : off=256   size=148576
stringLiteralData  : off=148832 size=541272
entry layout       : length_first   (a=length, b=dataIndex)
```

> `entry layout` **được tự dò**, không hardcode: script thử cả hai thứ tự trường và
> chọn thứ tự mà các entry nối tiếp nhau trong `stringLiteralData`. Nếu phiên bản
> metadata có bảng bố cục khác, dòng này sẽ hiện khác — **phải để ý**.

### Giới hạn đã biết

- Đã kiểm chứng cho **metadata version 29–31**. Trên version **32+** bảng
  `stringLiteral` có thể thêm trường → cần kiểm tra lại `entry layout` và kết quả
  trước khi tin.
- Script **chỉ liệt kê, không sửa gì**. An toàn để chạy trên bản gốc.

---

## `patch_md5.py` — thay một hằng hex-32

### Dùng khi nào

Sau khi `find_md5_literals.py` đã xác nhận **ứng viên đúng** (khớp MD5 của một tệp
có thật, và xuất hiện cạnh đường dẫn tệp đó).

### Ba điều kiện an toàn — đừng bỏ qua

1. `old` và `new` **cùng đúng 32 ký tự hex**.
   Nhờ vậy độ dài tệp không đổi, các offset phía sau không lệch, và bảng
   `stringLiteral` không phải sửa (trường `length` giữ nguyên).
2. **Luôn `--dry-run` trước.** Lệnh in ra toạ độ từng vị trí mà không ghi tệp.
3. Tự tạo backup `<file>.bak_patch` (nếu chưa có) rồi mới ghi, và tự đối chiếu
   sau khi ghi: báo rõ còn bao nhiêu mã cũ, có bao nhiêu mã mới.

### Cách chạy

```bash
# 1. xem trước (KHÔNG ghi tệp)
python3 patch_md5.py "$MD" <OLD_MD5_32_hex> <NEW_MD5_32_hex> --dry-run

# 2. áp dụng
python3 patch_md5.py "$MD" <OLD_MD5_32_hex> <NEW_MD5_32_hex>

# 3. đối chiếu bằng tay
grep -ac "<NEW_MD5>" "$MD"      # mong đợi: 2
grep -ac "<OLD_MD5>" "$MD"      # mong đợi: 0
```

> `grep -a` để coi tệp nhị phân là văn bản. `grep -c` vẫn đếm được, nhưng
> `grep -n` sẽ in `Binary file matches` thay vì số dòng nếu thiếu `-a`.

### Khi script báo "không tìm thấy"

Mã bạn đưa vào không có trong tệp. Chạy lại `find_md5_literals.py` và lấy đúng
chuỗi từ kết quả — **đừng tự gõ**, một ký tự sai là không khớp.

### Đã kiểm chứng

Chạy trên bản gốc của bản dựng tham chiếu: tìm thấy đúng **2 vị trí**
`[185843, 6302623]`, sau khi ghi → mã cũ còn `0`, mã mới có `2`. `--dry-run`
không sửa tệp (đã đối chiếu MD5 tệp trước/sau: không đổi).

---

## `patch_hbhgame_mod.py` — vá lỗi Wine-Mono Global Namespace trong mod Việt Hóa

### Dùng khi nào
Khi game cài mod Việt Hóa dạng CLR Injection (như của HBHGAME) bị sập ngay khi mở (Exit code 5, NULL dereference `0x0`). Nguyên nhân do Wine-Mono (`mscoree.dll`) từ chối nạp class không có namespace (`MyApplication`).

### Cách chạy
```bash
# Vá tệp (tự động tạo .bak):
python3 patch_hbhgame_mod.py path/to/HBHGAMENMod.dll

# Hoàn nguyên:
python3 patch_hbhgame_mod.py path/to/HBHGAMENMod.dll --revert
```

---

## `dump_minidump.py` — trích xuất Exception Record & Stack từ `crash.dmp`

### Dùng khi nào
Khi game bị crash sinh ra tệp `crash.dmp` trong Wine Prefix (`$PFX/drive_c/users/.../AppData/Local/Temp/.../Crashes/`). Script thuần Python này giúp đọc ngay Exception Code, RIP, RSP và 16 frames trên đỉnh Stack mà không cần cài đặt package ngoài.

### Cách chạy
```bash
python3 dump_minidump.py path/to/crash.dmp
```
Nếu `RIP = 0x0` và `Code = 0xC0000005`, game bị lỗi **NULL Pointer Dereference**.

---

## Xem tài liệu liên quan

- [`PLAYBOOK.md`](../PLAYBOOK.md) — chẩn đoán các lỗi integrity check, network, steam sdk
- [`VIETHOA_MOD_PLAYBOOK.md`](../VIETHOA_MOD_PLAYBOOK.md) — hướng dẫn chi tiết các tầng lỗi Mod Việt Hóa
- [`CHANGELOG.md`](../CHANGELOG.md) — nhật ký các can thiệp nhị phân trên game