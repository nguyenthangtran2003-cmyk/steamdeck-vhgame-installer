# CHANGELOG — Nhật ký thay đổi trên bản dựng game

Tài liệu này ghi lại toàn bộ các can thiệp nhị phân đã áp dụng lên thư mục game, lý do thực hiện, bằng chứng kiểm chứng và cách hoàn nguyên (rollback).

---

## 1. Ladies' School Prince (Bản Việt Hóa HBHGAME)

**Ngày đo & áp dụng:** 2026-10-06  
**Môi trường:** Manjaro Linux, Kernel CachyOS `7.2.6-1-cachyos`, Proton `GE-Proton11-7-x86_64`.

### Thay đổi 1: Vá chuỗi Global Namespace trong DLL Native Hook
- **Tệp can thiệp:** `Game/HBHGAMENMod.dll`
- **Offset file:** `0x1257E8` (RVA `0x126DE8`)
- **Nội dung gốc:** `MyApplication\0` (UTF-16LE, 28 byte: `4d0079004100700070006c00690063006100740069006f006e000000`)
- **Nội dung vá:** `.MyApplication\0` (UTF-16LE, 30 byte: `2e004d0079004100700070006c00690063006100740069006f006e000000`)
- **Lý do:** Khắc phục lỗi Wine-Mono `corruntimehost.c` từ chối nạp class không có namespace (`strrchr` trả về NULL $\rightarrow$ `E_INVALIDARG` $\rightarrow$ Crash con trỏ `0x0`).
- **Kiểm chứng `[ĐO]`:** Game không còn crash khi bật mod, [Player.log](file:///home/thang/.local/share/kokl_game_pfx/pfx/drive_c/users/steamuser/AppData/LocalLow/SteamCraftAtelier/Ladies%27%20School%20Prince/Player.log) ghi nhận nạp TextMeshPro và phụ đề bình thường.
- **Hoàn nguyên:** 
  ```bash
  python tools/patch_hbhgame_mod.py Game/HBHGAMENMod.dll --revert
  # hoặc: cp -f Game/HBHGAMENMod.dll.orig Game/HBHGAMENMod.dll
  ```

### Thay đổi 2: Bypass Wanmei Launcher SDK Check trên Unity IL2CPP
- **Tệp can thiệp:** `Game/GameAssembly.dll`
- **Các offset đã vá:**
  1. Offset `0x32C4B0` (`LauncherSDKCtr:Init`): Thay bằng stub 28-byte invoke `Action onComplete`:
     `4883ec284885d2740e4889d0488b5028488b4840ff50184883c428c3`
  2. Offset `0x32C6F0` (`LauncherSDKCtr:IsLauncher`): Thay bằng `b001c3` (`mov $1, %al; ret`)
  3. Offset `0x32AD30` (`GameManager:Quit`): Thay bằng `c3` (`ret`)
- **Lý do:** Game bị kẹt vô tận ở màn hình loading do chờ IPC từ launcher bản quyền của nhà phát hành.
- **Kiểm chứng `[ĐO]`:** Game vượt qua màn hình loading vào thẳng menu chính.
- **Hoàn nguyên:**
  ```bash
  cp -f Game/GameAssembly.dll.bak_orig Game/GameAssembly.dll
  ```

### Thay đổi 3: Khởi chạy bằng GE-Proton để hỗ trợ Media Foundation Codec
- **Thành phần:** `play.sh` trỏ tới `~/.local/share/Steam/compatibilitytools.d/GE-Proton11-7-x86_64/proton`
- **Lý do:** Proton chuẩn thiếu codec giải mã video H.264/Media Foundation, gây hiện tượng màn hình sọc SMPTE.

---

## 2. Love is All Around: Echoes of Yesterday (Tự động hóa Việt Hóa 100%)

**Ngày thực hiện:** 2026-10-06  
**Thư mục game:** `/mnt/games/Love is All Around Echoes of Yesterday v23.08.2025`  
**Bộ công cụ & mã nguồn:** `/home/thang/viethoa_lab/`

### Thay đổi 1: Việt hóa toàn diện 718 Cutscenes Video (`LocalSubtitles`)
- **Tệp can thiệp:** `LocalSubtitles/{main,main2,main3}/{zh-CN,zh-TW,en}/*.srt` (718 tệp).
- **Định dạng:** Plain Text UTF-8 (chuẩn AVPro Video parser `-->`).
- **Phát hiện quan trọng:** Engine dùng AVPro Video (`UnityVideo.MediaPlayer:EnableSubtitles`) để phát video và đọc phụ đề trực tiếp. Trình parse của AVPro Video kiểm tra chuỗi `-->` nên bắt buộc file `.srt` phải là Plain Text UTF-8 thuần. Nếu mã hóa XOR 9, AVPro Video sẽ báo `SRT format doesn't appear to be valid` và nuốt toàn bộ phụ đề.
- **Nội dung:** 7.242 câu thoại tiếng Việt, chuẩn hóa xưng hô điện ảnh, giữ nguyên timecode mili-giây.
- **Sao lưu gốc:** Đã lưu trữ toàn bộ tại `/home/thang/viethoa_lab/backup_orig_LocalSubtitles/`.

### Thay đổi 2: Việt hóa toàn diện Giao diện UI & Cài đặt (`LanguageTb.csv` & `ServerCodeTb.csv`)
- **Tệp can thiệp:** 
  - `StreamingAssets/Datas/Language/{zh-CN,zh-TW,en}/LanguageTb.csv` (1.781 mục UI).
  - `StreamingAssets/Datas/Language/{zh-CN,zh-TW,en}/ServerCodeTb.csv` (50 mục mã lỗi server).
- **Thuật toán mã hóa:** 2-byte header nhận diện `0x04 0x41` + `XOR 9` (`byte ^ 9`) của UTF-8 BOM.
- **Nội dung:** Toàn bộ menu Cài đặt (Âm lượng tổng, Âm lượng hiệu ứng, Độ sáng, Chuẩn, Chất lượng đồ họa, Cốt truyện, Ngôn ngữ, Chế độ hiển thị, Phụ đề...), hồ sơ nhân vật, tin nhắn chat và thông báo hệ thống.
- **Đa hồ sơ ngôn ngữ:** Cài đặt đồng bộ vào cả 3 profile (`zh-CN`, `zh-TW`, `en`) để người chơi thấy tiếng Việt ngay lập tức dù đang chọn ngôn ngữ nào.
- **Sao lưu gốc:** Đã lưu trữ toàn bộ tại `/home/thang/viethoa_lab/backup_orig_Language/`.

