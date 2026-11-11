# WALKTHROUGH — Cài game Windows trên Linux (Proton/Wine), từ đầu đến cuối

> **Vị trí trong bộ tài liệu `/mnt/games/linux-game-fix/`:**
> | File | Nội dung |
> |---|---|
> | `README.md` | Mục lục bộ tài liệu |
> | **`WALKTHROUGH.md` (bạn đang đọc)** | Quy trình end-to-end: giải nén → chạy được |
> | `PLAYBOOK.md` | Khi chạy lỗi: chẩn đoán theo tầng + các tình huống đã xử lý |
> | `tools/` | 2 script xử lý MD5 trong IL2CPP metadata |
>
> **Môi trường tham chiếu:** game Unity IL2CPP 2022.3.x, có **server nội bộ cục bộ**,
> dùng **lớp tương thích Steamworks (emulator)** thay cho Steam client thật.

---

## Phần 1 — Bảng ánh xạ: cài trên Windows ↔ chạy trên Linux

Mỗi bước cài đặt kiểu Windows tương ứng với bước nào trên Linux:

| # | Bước kiểu Windows | Mục đích kỹ thuật | Tương đương trên Linux |
|---|---|---|---|
| 0 | *Giải nén, mật khẩu nằm trong dấu `[ ]` của tên file* | Quy ước đặt mật khẩu | Giống hệt |
| 0b | *Tắt phần mềm diệt virus trước khi giải nén* | Tránh cảnh báo sai (heuristic) với tệp đóng gói lạ | **Không cần** trên Linux |
| 0c | *Tải đủ các Part; đặt chung thư mục; giải nén Part 1 (Extract Here)* | Archive nhiều tập RAR5, tập 1 chứa chỉ mục | Giống hệt: `unrar x part1.rar` |
| 0d | *Không đặt tên thư mục/tên file có chữ Tiếng Việt* | Tránh biến gây nhiễu khi chẩn đoán | **Nên dùng** — biến cần loại trừ đầu tiên (xem `PLAYBOOK §2.1`) |
| 1 | *Mở Steam, đăng nhập, để chạy nền* | Bản dựng cần một **Steam client đang hoạt động** cho lớp tương thích | `pgrep -x steam` trong `play.sh` |
| 2 | *Chạy `runLocalServer.bat`; **bảng đen để nguyên, không được đóng*** | Khởi động web server nội bộ `localServer.exe` lắng nghe `127.0.0.1:1075` | Chạy riêng dưới Wine prefix riêng, **block tới khi LISTEN** |
| 3 | *Mở `<tên>_loader_x64.exe`* | Wrapper cũ: bơm `steamclient.dll` + DLL trong `Server\` vào tiến trình game | ⚠️ **Bỏ wrapper**, chạy thẳng `.exe` của game + emulator (xem Phần 5) |
| 4 | *Chơi* | — | — |

**Kết luận:** 4/5 bước giữ nguyên trên Linux. **Chỉ bước 3 cần đổi** — và đó là lý do
bản dựng không khởi động được nếu làm y hệt hướng dẫn Windows.

---

## Phần 2 — Giải nén archive nhiều tập

### 2.1. Quy tắc

```
📌 Mật khẩu — QUY ƯỚC PHỔ BIẾN, KHÔNG PHẢI LUẬT CHUNG

Trong đa số trường hợp: Mật khẩu = CHỮ TRONG DẤU [ ] của tên file, BỎ hai ngoặc vuông
        [vi-du.com]_TenGame.part1.rar   →  mật khẩu: vi-du.com

Nếu mở không được, thử theo thứ tự:
   1. tệp readme.txt / password.txt / .txt đi kèm trong cùng thư mục
   2. mô tả bài đăng / trang nguồn (thường ghi mật khẩu ngay trên tiêu đề)
   3. tên site trong ngoặc vuông, không kèm dấu ngoặc
   4. "1234" / "www.<tên site>.com" — hai trường hợp này thỉnh thoảng xuất hiện

✅ Archive nhiều tập ⇒ phải có ĐỦ mọi tập. Thiếu tập ⇒ giải nén dừng giữa chừng.

✅ Các nguồn tải khác nhau có CÙNG số tập ⇒ dùng trộn được
        Tập 1 từ nguồn A + Tập 2 từ nguồn B  →  OK

✅ Đặt tất cả tập CÙNG 1 thư mục → chỉ giải nén Tập 1, các tập sau tự nối tiếp.

❌ KHÔNG đổi tên tập (giữ nguyên ...part1.rar, ...part2.rar).
❌ KHÔNG có tiếng Việt trong tên file / tên thư mục.
```

### 2.2. Giải nén trên Linux

```bash
sudo pacman -S unrar          # hỗ trợ RAR5
# KHÔNG dùng `7z` cho .rar: bản p7zip/ubuntu-zips thường THIẾU codec RAR5.

mkdir -p /mnt/games/MyGame
cd /mnt/games/MyGame

# Đặt toàn bộ tập vào đây, rồi chỉ chạy lệnh này cho Tập 1:
unrar x -p'vi-du.com' '[vi-du.com]_TenGame.part1.rar' ./
```

> - Dấu `[ ]` và `.` trong tên file → **bắt buộc** bọc nháy đơn `''`.
> - `unrar x part1.rar` tự đọc các tập kế tiếp (multi-volume), không cần chạy từng tập.
> - File `.001 / .002` (dạng 7z split) thì dùng `7z x file.001`.

### 2.3. Kiểm tra sau khi giải nén

```bash
cd /mnt/games/MyGame
ls -la
# Phải thấy: file .exe chính, thư mục *_Data (Unity), thư mục Server/, file *.bat
find . -iname "*.rar" -o -iname "*.r[0-9][0-9]"      # phải RỖNG (không còn tập nào sót)
find . -name "*.exe"
```
Thiếu tệp → **còn tập chưa tải đủ**, tải lại tập đó.

---

## Phần 3 — Chuẩn bị Linux (chỉ 1 lần)

```bash
# 1) Đường dẫn KHÔNG DẤU  (khuyến nghị mạnh — xem PLAYBOOK §2.1 để hiểu phạm vi)
#    /mnt/games/MyGame            ✅ nên dùng
#    ~/Tài liệu/Bản tải về/MyGame ⚠️ tránh khi đang chẩn đoán

# 2) Steam phải có + đã đăng nhập
steam                                        # để chạy nền
pgrep -x steam && echo "Steam OK"

# 3) Proton Experimental
ls "$HOME/.local/share/Steam/steamapps/common/Proton - Experimental/proton"

# 4) Bộ công cụ
sudo pacman -S python python-pefile unrar curl iproute2
#   python-pefile : đọc import table PE  (PLAYBOOK §5.4)
#   unrar         : RAR5 nhiều tập (KHÔNG dùng 7z cho .rar — thiếu codec)
#   iproute2      : lệnh ss, dùng để kiểm tra cổng server
```

**Bản đồ thư mục sau khi giải nén (môi trường tham chiếu):**

```
MyGame/
├── <TenGame>.exe                  ← exe game THẬT (Unity bootstrap)      ✅ Linux chạy tệp này
├── <TenGame>_loader_x64.exe       ← wrapper client cũ (ColdClient)      ❌ không dùng trên Linux
├── <TenGame>_loader_x32.exe       ← bản 32-bit của wrapper              ❌
├── steamclient.dll / steamclient64.dll  ← client Steam cũ (đã gỡ)      ❌ → _backup_unsteam/
├── GameAssembly.dll               ← IL2CPP native (KHÔNG chứa string)   📖
├── <TenGame>_Data/
│   ├── Plugins/x86_64/steam_api64.dll   ← LỚP TƯƠNG THÍCH (emulator)  ⭐
│   └── il2cpp_data/Metadata/global-metadata.dat  ← MD5 kiểm tra toàn vẹn ⭐
├── Server/
│   ├── localServer.exe            ← web server :1075 (Node/pkg)         ✅ Linux cần tệp này
│   └── <TenGame>Server.dll        ← server dự phòng, bơm vào game       ⚠️ chỉ dùng kiểu Windows
├── runLocalServer.bat             ← `.\server\localServer.exe`           → play.sh làm việc này
├── play.sh                        ← script Linux 1-click (đã tạo)
└── WALKTHROUGH.md
```

### 3.1. Game build Mono (khác IL2CPP)

Bản dựng tham chiếu là **IL2CPP**. Nếu bản dựng của bạn là **Mono**, nhiều bước
trong `PLAYBOOK.md` sẽ không áp dụng:

| | IL2CPP | Mono |
|---|---|---|
| Tệp cho code C# | `GameAssembly.dll` (native) | `<TenGame>_Data/Managed/Assembly-CSharp.dll` |
| Tệp metadata | `global-metadata.dat` | không có — nằm trong các DLL managed |
| Hằng chuỗi cần sửa | trong `global-metadata.dat` | trong `Assembly-CSharp.dll` |
| Công cụ | script Python ở `tools/` | `ilspycmd` / dnSpy để đọc & sửa IL |

**Phát hiện nhanh:**
```bash
ls <TenGame>_Data/Managed/*.dll 2>/dev/null && echo "→ build MONO"
ls <TenGame>_Data/il2cpp_data/Metadata/global-metadata.dat 2>/dev/null && echo "→ build IL2CPP"
```

> Sửa hằng trong DLL managed **khó hơn hẳn**: bảng metadata của .NET có ràng buộc
> checksum/length, sửa tay dễ làm hỏng tệp. Cần công cụ decompile rồi build lại,
> không phải vá byte. Nếu gặp Mono, hãy dừng lại và tra đường đi riêng thay vì
> cố áp `tools/` của tài liệu này.

---

## Phần 4 — Cách chạy kiểu Windows (tham chiếu)

```
[1] Mở Steam, đăng nhập, để nền
[2] Chạy runLocalServer.bat  → cửa sổ đen mở ra, ĐỂ NGUYÊN, KHÔNG ĐÓNG
                                (đóng = vào game bấm Play bị đơ)
[3] Chạy <TenGame>_loader_x64.exe → wrapper đọc ColdClientLoader.ini:
                                      Exe=<TenGame>.exe
                                      SteamClientDll=steamclient64.dll
                                      DllsToInjectFolder=Server  ← bơm DLL server dự phòng
                                   → khởi động game với lớp tương thích
[4] Chơi
```

> **Chi tiết đã kiểm chứng:** `<TenGame>Server.dll` là tệp DUY NHẤT import bộ Debug-CRT
> (`MSVCP140D.dll`, `VCRUNTIME140D.dll`, `VCRUNTIME140_1D.dll`, `ucrtbased.dll`).
> `localServer.exe`, `.exe` của game, và wrapper **không** import tệp nào trong số đó.
> → 4 DLL `*d.dll` trong `Server/` tồn tại **chỉ vì bước bơm (inject)**, không liên quan server standalone.

---

## Phần 5 — Cách chạy trên Linux (đã kiểm chứng)

Toàn bộ 4 bước Windows được gộp thành **1 click**: `play.sh`

```bash
"/mnt/games/MyGame/play.sh"
```

`play.sh` làm đúng thứ tự sau (xem source bên trong tệp):

```
1. pgrep steam  → nếu chưa có thì mở + chờ 3s            ≙ Bước 1
2. curl 127.0.0.1:1075 → nếu chưa OK thì start
     localServer.exe dưới WINEPREFIX RIÊNG               ≙ Bước 2
   + block poll 15s cho tới khi LISTEN
     (bổ sung: kiểu Windows cũng phải chờ "bảng đen sẵn sàng")
3. Proton run  <TenGame>.exe                              ⚠️ THAY BƯỚC 3
4. Game thoát → kill server + pkill localServer.exe        (bổ sung dọn dẹp)
```

> ### 📌 Dừng lại đọc trước khi làm bước 3
>
> 3 điểm dưới đây là **khác biệt so với cách làm kiểu Windows**, chứ không phải
> quy tắc bắt buộc. Cụ thể:
>
> - **Nếu bản dựng của bạn chạy được ngay trên Linux bằng wrapper client cũ** →
>   đừng đổi gì cả. Không có lý do gì phải bỏ nó.
> - Chỉ chuyển sang lớp tương thích (emulator) khi **không** làm được theo kiểu cũ,
>   hoặc khi tài liệu của bạn nói rõ lớp tương thích bắt buộc phải khớp MD5 (§5.1, §5.2).
> - Sửa MD5 trong `global-metadata.dat` là việc **sửa tệp nhị phân**. Chỉ làm khi
>   log chỉ ra đúng nguyên nhân (dòng `md5 != _SteamApiMd5`), và luôn giữ bản gốc.

**3 điểm DỊCH so với kiểu Windows — và vì sao:**

| # | Windows | Linux | Lý do |
|---|---|---|---|
| 1 | Chạy `<TenGame>_loader_x64.exe` | Chạy thẳng **`<TenGame>.exe`** | Proton tự nạp `lsteamclient.so`; cộng với `steamclient64.dll` của wrapper cũ → 2 lớp tương thích tranh nhau, game chết. Dùng emulator thì wrapper không còn tác dụng. |
| 2 | Không cần sửa gì | **Sửa MD5 kiểm tra toàn vẹn** trong `global-metadata.dat` | Bản dựng so MD5 của `steam_api64.dll` với giá trị hardcode của DLL gốc. Đổi sang emulator → MD5 lệch → quit ở frame 3. Kiểu Windows không gặp vì wrapper giữ nguyên DLL gốc. |
| 3 | Một cửa sổ đen duy nhất | **2 Wine prefix riêng biệt** (server / game) | Tránh tranh chấp wineserver, log tách bạch, hỏng prefix này không ảnh hưởng prefix kia. |

---

## Phần 6 — Kiểm chứng sau khi chạy

Không cần nhìn cửa sổ game — đọc tệp log:

```bash
D="$HOME/.local/share/<ten>_game_pfx/pfx/drive_c/users/steamuser/AppData/LocalLow/<Company>/<Product>"
grep -n "_CheckSteamApiDll\|Steam Sdk\|Curl error" "$D/Player.log"
```

**Bốn bất biến — đây mới là tiêu chí (đã đo trên nhiều lần chạy):**

```
✅ CÓ dòng  _CheckSteamApiDll: md5 == null || md5 == _SteamApiMd5   ← kiểm tra toàn vẹn PASS
✅ CÓ dòng  Steam Sdk 登录成功                                      ← SDK OK
✅ Curl error 7  = 0 lần                                             ← server cục bộ OK
✅ "Steamworks is not initialized" = 0 lần
```

**Biến thiên — đừng dùng làm tiêu chí:** `frame=`, `time=`, số lần `Curl error 28`,
địa chỉ IP nội bộ, số dòng trong tệp log. Đã đo ở hai lần chạy:

| | Lần A | Lần B |
|---|---|---|
| dòng kiểm tra MD5 | `frame=1 time=0.287` | `frame=1 time=0.455` |
| dòng SDK | `frame=388 time=7.068` | `frame=384 time=7.091` |
| `Curl error 28` | 6 lần | 13 lần |

> `Curl error 28` tới địa chỉ nội bộ của bản dựng là **vô hại** — game vẫn chơi được.

Dấu hiệu **CHƯA OK:**

| Log có | Nghĩa | Xử lý ở đâu |
|---|---|---|
| `md5 != _SteamApiMd5` | Kiểm tra toàn vẹn fail | `PLAYBOOK §5.2` |
| `Curl error 7 ... port 1075` | Server chưa lên | `PLAYBOOK §5.3` |
| `Steamworks is not initialized` | Sai lớp tương thích | `PLAYBOOK §5.1` |
| `import_dll ... not found` | Thiếu DLL | `PLAYBOOK §5.4` |
| `md5 !=` nhưng **không** sửa được | Đường dẫn có dấu / wrapper còn sót | `PLAYBOOK §4` |

---

## Phần 7 — Checklist tổng (một trang)

```
GIẢI NÉN
[ ] Đủ mọi tập, tất cả tập cùng 1 thư mục
[ ] Mật khẩu = chữ trong [ ] (bỏ ngoặc vuông)
[ ] Chỉ giải nén Tập 1 (unrar x ... part1.rar)
[ ] Tên file/thư mục KHÔNG có tiếng Việt
[ ] find .rar → rỗng; đủ .exe game, thư mục *_Data/, Server/, runLocalServer.bat

CHUẨN BỊ
[ ] Đường dẫn game không dấu
[ ] Steam đã mở + đăng nhập
[ ] Có Proton Experimental

XỬ LÝ TƯƠNG THÍCH (xem PLAYBOOK)
[ ] steam_api64.dll = lớp tương thích; steam_settings/ có steam_appid.txt + steam_interfaces.txt
[ ] Wrapper client cũ đã chuyển sang _backup_unsteam/
[ ] global-metadata.dat: giá trị MD5 cũ → mới (2 vị trí), có .bak_original
[ ] play.sh: GAME_EXE = .exe thật (KHÔNG phải wrapper)

CHẠY
[ ] play.sh 1-click
[ ] log có dòng kiểm tra MD5 ở trạng thái khớp
[ ] log có "Steam Sdk 登录成功"
[ ] Curl error 7 == 0
[ ] Qua màn hình đăng nhập → màn hình chính
```

---

## Phần 8 — Cài lại từ đầu (rollback)

```bash
GAME_DIR="/mnt/games/MyGame"

# (a) Hoàn nguyên về trạng thái gốc của bản dựng:
mv "$GAME_DIR/_backup_unsteam/"*.dll "$GAME_DIR/"
mv "$GAME_DIR/_backup_unsteam/"*.ini "$GAME_DIR/"
cp -v "$GAME_DIR/<TenGame>_Data/il2cpp_data/Metadata/global-metadata.dat.bak_original" \
      "$GAME_DIR/<TenGame>_Data/il2cpp_data/Metadata/global-metadata.dat"

# (b) Cách ly triệt để: chỉ cần XÓA 2 thư mục prefix rồi chạy lại play.sh
rm -rf "$HOME/.local/share/<ten>_game_pfx" "$HOME/.local/share/<ten>_server_pfx"

# (c) Chạy lại
"$GAME_DIR/play.sh"
```
