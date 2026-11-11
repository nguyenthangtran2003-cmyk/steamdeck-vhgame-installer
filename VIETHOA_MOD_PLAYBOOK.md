# VIETHOA_MOD_PLAYBOOK — Chẩn đoán & xử lý mod Việt Hóa Unity/IL2CPP trên Linux (Proton/Wine)

> ## ⚠️ Phạm vi & Đối tượng áp dụng
>
> Tài liệu này tổng hợp phân tích thực nghiệm từ trường hợp mod Việt Hóa dạng **Hook & CLR Injection** (điển hình: bản dịch của nhóm HBHGAME cho game Unity IL2CPP như *Ladies' School Prince* / *KOKL*).
> 
> Khác với game dịch đè asset hoặc patch ngôn ngữ chính thức, các bản Việt Hóa này sử dụng cơ chế **tiêm mã 2 tầng** (Native Hook + .NET CLR Runtime) để đọc phụ đề rời từ bên ngoài và đè lên màn hình, tránh can thiệp vào các tệp AssetBundle lớn (20GB+).
>
> ⚠️ **ĐẶC BIỆT LƯU Ý VỀ TỆP `.ini` (QUY TẮC VÀNG):**
> Bản mod **tự động dò tìm RVA và ghi đè địa chỉ runtime** vào `hbhgame_mod.ini` và `hbhgame_mod1.ini` ngay khi khởi động thành công. Tệp `.ini` đi kèm bản tải về thường lưu địa chỉ của build cũ (lệch RVA). **Tuyệt đối không sửa `.ini` thủ công** — việc chỉnh sửa này hoàn toàn vô tác dụng và đi ngược hướng chẩn đoán.
>
> **Nhãn bằng chứng trong tài liệu:**
> | Nhãn | Nghĩa |
> |---|---|
> | `[ĐO]` | Đã chạy lệnh, phân tích dump, đo đạc nhị phân và xác minh thực tế trong phiên |
> | `[SUY]` | Suy luận kỹ thuật từ kiến trúc mã nguồn Wine/Mono, engine Unity hoặc tham chiếu bên ngoài |
> | `[CHƯA RÕ]` | Hiện tượng chưa xác định rõ cơ chế sâu hơn |

---

## 0. Kiến trúc Mod Việt Hóa 2 tầng (Native + Managed)

Các bản game Unity FMV / Visual Novel thường đóng gói phụ đề bên trong hàng ngàn tệp `AssetBundle` đã serialize (ví dụ: `subtitle_assets_assets/bundles/common/subtitle/*.bundle`). Việc trích xuất, chỉnh sửa và đóng gói lại 20GB+ asset là bất khả thi hoặc làm bản patch quá nặng. Do đó, các nhóm dịch sử dụng kiến trúc tiêm mã:

```
[Khởi động Game]
       │
       ▼
[Tầng 0: PE Hijack]
   baselib.dll (bản mod proxy) được UnityPlayer.dll nạp
       │
       ├─► Nạp HBHGAMENMod.dll (Native C++ Hook)
       │
       ▼
[Tầng 1: Native C++ Hook]
   Hook il2cpp_domain_assembly_open & il2cpp_add_internal_call trong GameAssembly.dll
       │
       ├─► Tự động ghi lại địa chỉ runtime vào hbhgame_mod.ini & hbhgame_mod1.ini
       ├─► Khởi tạo Windows CLR Runtime thông qua mscoree.dll (CLRCreateInstance)
       │   Gọi ICLRRuntimeHost::Start()
       │   Gọi ICLRRuntimeHost::ExecuteInDefaultAppDomain("HBHGAMEMod.dll", "MyApplication", "Main")
       │
       ▼
[Tầng 2: Managed C# .NET Runtime]
   HBHGAMEMod.dll (.NET Framework v4.0) thực thi
       │
       ├─► Lắng nghe sự kiện phát video / cutscene
       ├─► Đọc trực tiếp tệp text từ thư mục Subtitle/*.subtitle.txt
       └─► Nạp vn_font (TextMeshPro font asset) và vẽ đè phụ đề tiếng Việt lên màn hình
```

---

## 1. Bảng triệu chứng & Tầng lỗi (Symptom Matrix)

| # | Triệu chứng | Tầng lỗi | Nguyên nhân gốc rễ | Cách xử lý |
|---|---|---|---|---|
| **VH-1** ⭐ | Game sập ngay khi mở (sau 1-3s), Exit Code 5 | CLR / Mono | **Wine-Mono bug `strrchr`**: Từ chối nạp class không có namespace, dẫn đến **NULL Pointer Dereference** tại `0x0` `[ĐO]` | Vá chuỗi `MyApplication` thành `.MyApplication` trong DLL Native |
| **VH-2** | Màn hình sọc màu kiểm tra (SMPTE Color Bars), âm thanh có nhưng không có hình | Media / Codec | Proton chuẩn thiếu codec giải mã Media Foundation (H.264/WMV/AAC) `[SUY]` | Sử dụng **GE-Proton** (Proton-GE) |
| **VH-3** | Kẹt vô tận ở màn hình Loading / bắt mở Launcher | Unity Engine | Hàm kiểm tra Launcher bản quyền trong `GameAssembly.dll` kẹt chờ IPC `[SUY]` | Vá invoke callback `onComplete` và `IsLauncher -> true` (áp dụng theo build) |
| **VH-4** | Game chạy nhưng không thấy phụ đề tiếng Việt | Application | Chưa nạp font, mod bị tắt bằng phím tắt, hoặc cấu hình RVA trong `.ini` bị lệch `[SUY]` | Bấm F5/F6 trong game, kiểm tra quyền ghi thư mục game |

---

## 2. Phân tích chi tiết các Case

### Case VH-1 ⭐: Bug Wine-Mono CLR Hosting & Crash NULL Dereference

#### Triệu chứng `[ĐO]`
Game thoát đột ngột với mã lỗi `code 5` trong vòng 3 giây đầu. 
File `crash.dmp` trong thư mục crash ghi nhận:
```
Code: 0xc0000005 (STATUS_ACCESS_VIOLATION), Addr: 0x0000000000000000
RIP: 0x0000000000000000, RSP: 0x00000000000feb48
Return Address trên Stack: [RSP+0x00] = 0x00006ffff7e09afe (trong HBHGAMENMod.dll)
```

#### Cơ chế & Phân tích gốc rễ (Root Cause) `[ĐO]`
1. Tại địa chỉ lệnh `180049af8` của DLL Native:
   ```asm
   call QWORD PTR [rip+0x14256a]   # Gọi con trỏ hàm tại 0x18018c068
   ```
   Con trỏ hàm này được khởi tạo bởi hàm `ICLRRuntimeHost::ExecuteInDefaultAppDomain` của Windows CLR Host.
2. Kiểm tra mã nguồn Wine (`dlls/mscoree/corruntimehost.c`):
   ```c
   ns = strrchr(classA, '.');
   if (ns)
       *ns = '\0';
   else
       hr = E_INVALIDARG; // 0x80070057
   ```
   **Lập trình viên Wine đã giả định mọi class C# đều phải có namespace và chứa dấu chấm `.`**.
3. Class `MyApplication` trong `HBHGAMEMod.dll` thuộc **Global/Default Namespace** (namespace rỗng, không có dấu chấm).
4. Trên Windows thật, Microsoft CLR chấp nhận chuỗi `"MyApplication"`.
   Nhưng trên Wine-Mono, `strrchr` trả về `NULL` $\rightarrow$ Wine trả về mã lỗi `E_INVALIDARG`.
5. DLL Native gặp lỗi trả về liền bỏ qua bước gán delegate, để lại con trỏ hàm rỗng (`0x0000000000000000`).
6. Khi engine Unity gọi `il2cpp_domain_assembly_open`, DLL Native gọi con trỏ `0x0`, sinh lỗi **NULL pointer dereference**.

#### Phương pháp xử lý `[ĐO]`
Không cần cài đặt Microsoft .NET 4.8 nặng nề vào prefix. Thay vào đó, **vá chuỗi trực tiếp trong binary Native**:
- Chuỗi gốc: `L"MyApplication\0"` gồm 13 ký tự UTF-16 = 26 byte nội dung + 2 byte null kết thúc = **28 byte**.
- Chuỗi vá: `L".MyApplication\0"` gồm 14 ký tự UTF-16 = 28 byte nội dung + 2 byte null kết thúc = **30 byte**.
- Vùng đệm trong tệp gốc dành sẵn **32 byte** (từ offset `0x126de8` đến `0x126e08`, có sẵn 4 byte null padding) $\rightarrow$ ghi 30 byte vào hoàn toàn vừa vặn, còn dư 2 byte null padding, tuyệt đối không làm dịch chuyển các chuỗi lân cận.
- Khi có dấu chấm ở đầu:
  - `strrchr` tìm thấy dấu chấm tại vị trí đầu tiên.
  - Wine tách ra: Namespace rỗng `""` và Class name `"MyApplication"`.
  - Wine gọi `mono_class_from_name(image, "", "MyApplication")` $\rightarrow$ Wine-Mono tìm thấy class thành công 100%!

---

### Case VH-2: Màn hình sọc kiểm tra SMPTE (Thiếu Video Codec)

#### Triệu chứng `[SUY]`
Game FMV vào được menu, có nhạc nền, nhưng toàn bộ video diễn viên chỉ hiển thị màn hình sọc màu kiểm tra tín hiệu (SMPTE Color Bars).

#### Cơ chế & Phân tích gốc rễ `[SUY]`
- Game FMV Unity sử dụng `Windows Media Foundation` (WMF) để giải mã video định dạng MP4/H.264.
- Các bản Wine hoặc Proton tiêu chuẩn thường không đi kèm codec độc quyền do vấn đề bản quyền phần mềm, nên phát video test sọc màu thay vì crash.

#### Phương pháp xử lý `[ĐO]`
1. Cài đặt **GE-Proton** (Proton GloriousEggroll) vào thư mục `~/.local/share/Steam/compatibilitytools.d/`:
   ```bash
   curl -sLO https://github.com/GloriousEggroll/proton-ge-custom/releases/download/GE-Proton11-7/GE-Proton11-7.tar.gz
   tar -xzf GE-Proton11-7.tar.gz -C ~/.local/share/Steam/compatibilitytools.d/
   ```
2. Cấu hình script khởi chạy sử dụng GE-Proton:
   GE-Proton đã tích hợp sẵn hệ thống GStreamer/FFMPEG patch đầy đủ, video lập tức hiển thị bình thường.

---

### Case VH-3: Bypass Launcher Check trên Unity IL2CPP

> ⚠️ **Lưu ý phạm vi:** Các offset dưới đây được trích xuất cho **bản dựng cụ thể của game này** (Unity 2022.3.52f1). Bản dựng khác **bắt buộc phải dò lại offset** bằng Ghidra / IDA Pro / IL2CppDumper.

#### Triệu chứng `[SUY]`
Game mở lên nhưng dừng vĩnh viễn ở thanh tiến trình hoặc hiện thông báo bắt mở launcher gốc của nhà phát hành (Wanmei/Perfect World Launcher).

#### Cơ chế & Phân tích gốc rễ `[SUY]`
Trong `GameAssembly.dll`, game có các hàm SDK quản lý:
- `LauncherSDKCtr:Init(Action onComplete)`: Gửi yêu cầu IPC tới client launcher trên Windows. Nếu không có launcher phản hồi, callback `onComplete` không bao giờ được gọi.
- `LauncherSDKCtr:IsLauncher()`: Kiểm tra cờ khởi chạy qua launcher.

#### Phương pháp xử lý `[ĐO]`
Sử dụng script Python vá nhị phân trực tiếp trên `GameAssembly.dll`:
1. **Offset `0x32c4b0` (`LauncherSDKCtr:Init`)**: Thay toàn bộ hàm bằng stub 28-byte x86_64 invoke ngay lập tức `Action onComplete`:
   ```hex
   4883ec284885d2740e4889d0488b5028488b4840ff50184883c428c3
   ```
2. **Offset `0x32c6f0` (`LauncherSDKCtr:IsLauncher`)**: Sửa thành luôn trả về `true` (3 bytes):
   ```hex
   b001c3   # mov $1, %al; ret
   ```
3. **Offset `0x32ad30` (`GameManager:Quit`)**: Stub lệnh thoát:
   ```hex
   c3       # ret
   ```

---

## 3. Quy trình Chẩn đoán & Phân định Nhanh

Khi gặp một bản game Việt Hóa bị lỗi trên Linux, hãy thực hiện theo đúng **quy trình 4 bước**:

### Bước 1: Phân định Engine vs Mod (Kiểm tra Proxy Baselib)
Đừng đoán tên tệp, hãy **đo số lượng tham chiếu mod** trong `baselib.dll`:
```bash
strings -a baselib.dll | grep -ci hbhgame
```
- Nếu kết quả **> 0**: Tệp hiện tại là **proxy injector** của mod (thường dung lượng ~425 KB).
- Nếu kết quả **== 0**: Tệp hiện tại là **baselib gốc sạch** của Unity (thường dung lượng ~419 KB).

**Phép thử:** Khôi phục `baselib.dll` về bản sạch (kết quả `strings == 0`):
- Nếu game **vẫn crash**: Lỗi 100% thuộc về Engine, Video Codec hoặc Launcher Check (Case VH-2, VH-3).
- Nếu game **hết crash** (chạy bình thường nhưng tiếng Trung/Anh): Engine hoàn toàn ổn định, lỗi 100% nằm ở tầng Mod Việt Hóa / CLR.

### Bước 2: Đọc Crash Dump bằng Python thuần
Tìm tệp crash dump trong Wine Prefix:
```bash
find "$PFX" -name "crash.dmp"
```
Chạy công cụ [`tools/dump_minidump.py`](tools/dump_minidump.py) có sẵn trong bộ tài liệu:
```bash
python tools/dump_minidump.py path/to/crash.dmp
```
- Nếu `RIP = 0x0` và `Code = 0xC0000005`: Chắc chắn là **NULL Pointer Dereference** do CLR Host thất bại (Case VH-1).

### Bước 3: Kiểm tra Wine CLR Trace
Chạy game với biến môi trường debug:
```bash
WINEDEBUG=+mscoree,+mono ./play.sh
```
Quan sát xem có lỗi nạp Type hoặc `E_INVALIDARG` (0x80070057) không.

### Bước 4: Áp dụng bản vá chuỗi
Chạy công cụ tự động vá chuỗi namespace:
```bash
python tools/patch_hbhgame_mod.py Game/HBHGAMENMod.dll
```

---

## 4. Bảng kiểm tra Bất biến vs Biến thiên

| Hạng mục | Tính chất | Ghi chú |
|---|---|---|
| **Cơ chế nạp CLR của Wine** | Bất biến | Cần dấu chấm `.` khi tìm kiếm class trong `corruntimehost.c` |
| **Phụ đề trong `Subtitle/*.txt`** | Bất biến | Tệp văn bản thuần, không cần chỉnh sửa định dạng |
| **Cơ chế tự ghi đè `.ini`** | Bất biến | Mod luôn tự cập nhật RVA vào `.ini`, không sửa thủ công |
| **Tên DLL hook (`HBHGAMENMod.dll`)** | Biến thiên | Tùy thuộc vào nhóm dịch, có thể là tên khác |
| **Offset trong `GameAssembly.dll`** | Biến thiên | Thay đổi theo từng phiên bản game, phải dò lại bằng Ghidra |
| **RVA trong file `.ini`** | Biến thiên | Runtime tự sinh, phụ thuộc vào ImageBase của build |

---

## 5. Công cụ hỗ trợ đi kèm

1. [`tools/patch_hbhgame_mod.py`](tools/patch_hbhgame_mod.py) — Vá an toàn chuỗi namespace `.MyApplication` trong DLL Native.
2. [`tools/dump_minidump.py`](tools/dump_minidump.py) — Trích xuất Exception Record, RIP, RSP và Stack Frames từ tệp `crash.dmp` không cần cài thư viện ngoài.
