# PLAYBOOK — Chẩn đoán & xử lý lỗi tương thích khi chạy game Windows trên Linux

> ## ⚠️ Phạm vi: đây là PLAYBOOK SUY RA TỪ MỘT BẢN DỰNG, không phải hướng dẫn Proton phổ quát
>
> Mọi thứ ở đây — cấu trúc tệp, tên thư mục, cổng server, vị trí hằng MD5, hành vi
> lớp tương thích Steamworks, tên tệp cấu hình — đều **đo trên một bản dựng cụ thể**
> (Unity 2022.3.52f1 / metadata v31). Chúng **không** phải quy luật của Proton,
> của IL2CPP nói chung, hay của bất kỳ lớp tương thích Steamworks nào.
>
> **Trước khi dùng cho bản dựng khác, phải xác minh lại:** tên tệp, cổng, cấu trúc
> metadata, và cách đo. Copy lệnh mà không đo thì tệ hơn không có tài liệu.

> **Nhãn bằng chứng dùng trong tài liệu này:**
> | Nhãn | Nghĩa |
> |---|---|
> | `[ĐO]` | đã chạy lệnh và xác minh — tin được |
> | `[SUY]` | suy luận từ dữ liệu đã đo, **chưa** kiểm chứng trực tiếp |
> | `[CHƯA RÕ]` | chưa biết nguyên nhân — không được khẳng định |
>
> Số liệu gốc nằm ở [`FINDINGS.md`](FINDINGS.md). Thay đổi đã áp dụng lên thư mục
> game nằm ở [`CHANGELOG.md`](CHANGELOG.md).

> **Bộ tài liệu `/mnt/games/linux-game-fix/`:**
> - [`WALKTHROUGH.md`](WALKTHROUGH.md) — quy trình từ lúc giải nén → chạy được
> - [`PLAYBOOK.md`](PLAYBOOK.md) (bài này) — **khi chạy lỗi**
> - [`FINDINGS.md`](FINDINGS.md) — dữ liệu đo + **kết quả âm** (đừng đo lại)
> - [`CHANGELOG.md`](CHANGELOG.md) — đã sửa gì trong thư mục game + cách hoàn nguyên
> - `tools/` — 2 script Python
>
> **Môi trường tham chiếu (đo 2026-10-05):** Manjaro, kernel `7.2.6-1-cachyos`,
> Proton `experimental-11.0-20261001`, Unity `2022.3.52f1`, metadata v31.
> Không phải bản dựng LTS — **đo lại nếu áp dụng ở máy khác**.

---

## 0. Nguyên tắc cốt lõi

**Không đoán. Luôn đo.** Mỗi triệu chứng phải được quy về đúng tầng trước khi sửa:

```
Tầng 0 — PE Loader / OS        : process không mở được, exit < 1s, error c0000135
Tầng 1 — Bootstrap / Integrity : mở được nhưng tự quit ở frame đầu, log có "check ... != ..."
Tầng 2 — SDK / Lớp tương thích : "Steamworks is not initialized", SteamAPI_Init fail
Tầng 3 — Networking / IPC       : "Curl error 7", port chưa listen, "Connection refused"
Tầng 4 — Application / Data     : vào được game nhưng lỗi data (404, timestamp = 0, Lua exception)
```

**Quy tắc vàng:**
1. **Log quyết định, không phải suy đoán.** Chạy 1 lần → đọc log → mới ra tay.
2. **Mỗi lần sửa đúng 1 thứ.** Sửa nhiều thứ cùng lúc sẽ không biết thứ nào hiệu quả.
3. **Backup trước, luôn.** Ghi rõ tên file backup, đừng `cp` đè lung tung.
4. **Sửa file nhị phân = chỉ thay byte không đổi độ dài.** Suy nghĩ như một người vá hex, không phải như một compiler.
5. **Không sửa `System32` của Wine prefix.** DLL luôn đặt cạnh file gọi nó (side-by-side).

---

## 1. Bảng triệu chứng → nguyên nhân (Symptom Matrix)

| # | Triệu chứng | Tầng | Nguyên nhân thường gặp | Xử lý |
|---|---|---|---|---|
| 0 | Double-click → không hiện gì / exit ngay | 0 | Thiếu DLL import (`c0000135`); Debug CRT `/MDd` | Đặt DLL cạnh file gọi nó |
| 1 | Chạy được ~0.2s rồi quit, log có `md5 != _SteamApiMd5` | 1 | **Kiểm tra toàn vẹn, MD5 hardcode** | `patch_md5.py` |
| 1b | Quit ngay, log có `Steamworks is not initialized` | 1-2 | Sai lớp tương thích / Proton nạp `lsteamclient` | Dùng emulator, bỏ wrapper client cũ |
| 2 | Vào được UI, bấm **Play** bị đơ đứng hình | 3 | Server cục bộ chưa listen port | Chạy `localServer.exe` trước |
| 2b | Log `Curl error 7: Failed to connect to localhost:<port>` | 3 | Server chưa lên / sai port | Xem §5.3 |
| 3 | Báo `Failed to load some assemblies` / `DllNotFoundException` | 0 | Plugin thiếu runtime | `WINEDEBUG=+loaddll` tìm tên DLL |
| 4 | Vào được, lỗi `404 Not Found` / `Connection timed out` | 4 | Dịch vụ nội bộ của bản dựng không tồn tại | Bỏ qua — không chặn chơi |
| 5 | Không mở được, dính lỗi path | 0 | Thư mục có dấu tiếng Việt | Dời về `/mnt/games/` |
| 6 | Steam tự đóng game ngay | 2 | `steam_appid.txt` không khớp lớp tương thích đang dùng | Sửa `steam_appid.txt` cho đúng |

---

## 2. Chuẩn bị

### 2.1. Đường dẫn — khuyến nghị mạnh, không phải luật của Proton

```bash
/mnt/games/<TenGame>/          ✅ nên dùng
~/Tài liệu/Bản tải về/<game>  ⚠️ tránh khi đang chẩn đoán
```

> **Lưu ý về phạm vi:** Proton/Wine hiện nay xử lý đường dẫn UTF-8 bình thường —
> **không có quy luật "Proton không chịu tiếng Việt"**. Vấn đề chúng tôi gặp là của
> **bản dựng cụ thể** (có thể do wrapper, hoặc do bản thân tệp). Nhưng khi đang
> chẩn đoán, đường dẫn không dấu là biến cần loại trừ trước, và nó miễn phí.
> `[SUY]` nguyên nhân chính xác ở bản dựng này **chưa xác minh** — đừng khẳng định.

### 2.2. Công cụ cần có

```bash
sudo pacman -S python python-pefile unrar curl iproute2
```

| Công cụ | Vai trò | Bắt buộc? |
|---|---|---|
| `python` + `python-pefile` | chạy `tools/`, đọc import table PE (§5.4) | **có** cho §5.4 |
| `unrar` | giải nén RAR5 nhiều tập | **có** nếu tải từ `.rar` |
| `curl` | kiểm tra server cục bộ | nên có |
| `iproute2` (`ss`) | kiểm tra cổng có LISTEN, lấy PID | **có** cho `play.sh` §6 |
| `7z` | mở `.001/.002` (dạng 7z split) | tùy |

> **`unrar`, không phải `7z`, cho `.rar`:** `7z` của distro thường **thiếu codec RAR5**
> và sẽ báo lỗi ngay dù bạn đã cài. `[ĐO]` máy tham chiếu: `unrar 7.30 beta`,
> hỗ trợ RAR5.

### 2.3. Định vị đường dẫn quan trọng
```bash
GAME_DIR="/mnt/games/<TenGame>"
STEAM_DIR="$HOME/.local/share/Steam"
PROTON="$STEAM_DIR/steamapps/common/Proton - Experimental/proton"
WINE="$STEAM_DIR/steamapps/common/Proton - Experimental/files/bin/wine"

# Prefix của game (tự tạo khi chạy)
PFX="$HOME/.local/share/<ten>_game_pfx/pfx"

# Log Unity — nguồn dữ liệu chính
find "$PFX/drive_c/users" -name "Player.log" -path "*AppData/LocalLow*"
find "$PFX/drive_c/users" -name "game.log"   -path "*AppData/LocalLow*"

# Log của lớp tương thích — CHỈ THAM KHẢO
# [ĐO] file này 0 byte dù đã cấu hình log_file, trong khi game chạy tốt.
# [CHƯA RÕ] nguyên nhân → xem FINDINGS.md §3.4. ĐỪNG dùng làm tiêu chí.
ls -la "$PFX/drive_c/goldberg.log"
```

### 2.4. Quy ước đặt tên trong tài liệu này

| Viết | Nghĩa |
|---|---|
| `<TenGame>` | tên bản dựng — **thay bằng tên thật**, ví dụ `WDHD5` |
| `<TenGame>_Data` | thư mục dữ liệu Unity cạnh tệp thực thi |
| `_backup_unsteam/` | thư mục cách ly wrapper client cũ — **tên thật trên đĩa** |
| `<ten>_game_pfx` / `<ten>_server_pfx` | prefix Wine, dưới `~/.local/share/` |
| `SERVER_READY_TIMEOUT` | mặc định 30 s (§6) |

> Chỉ dùng **một** tên thư mục cách ly xuyên suốt. Bản dựng tham chiếu dùng
> `_backup_unsteam/`; nếu bạn thích tên trung tính hơn (`_disabled_legacy_client/`)
> thì đổi **khắp cả ba tài liệu**, đừng trộn hai tên.

---

## 3. Quy trình 8 bước

### B1 — Bản đồ file
```bash
cd "$GAME_DIR"
ls -la
echo "--- Plugins ---"; ls -la <TenGame>_Data/Plugins/*/ 2>/dev/null
echo "--- Server ---";  ls -la Server/ 2>/dev/null
echo "--- có metadata không ---"; find . -name "global-metadata.dat"
```
Ghi lại: exe chính, DLL Steam, có folder `Server/` không, có file `.bat` khởi động server không.

### B2 — Chọn đúng entry point
| File | Bản chất | Chạy? |
|---|---|---|
| `<TenGame>_loader_*.exe` (bản wrapper) | Bơm `steamclient*.dll` vào tiến trình game | ❌ Bỏ khi dùng emulator |
| `XXX.exe` (Unity bootstrap, ~hàng trăm KB–MB) | Game thật | ✅ |
| `XXX.exe` + `ColdClientLoader.ini` | Cấu hình bơm của wrapper cũ | ⚠️ |

**Quy tắc:** Nếu đã chuyển sang **emulator** → **bỏ wrapper**, chạy thẳng exe game.

### B3 — Chạy lần đầu, thu thập log
```bash
mv "$PLAYER_LOG" "$PLAYER_LOG.pre" 2>/dev/null   # xoay log cũ

cd "$GAME_DIR"
STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_DIR" \
STEAM_COMPAT_DATA_PATH="$PFX_ROOT" \
timeout 45 "$PROTON" run "$GAME_DIR/<GameExe>.exe" 2>&1 | tee /tmp/run1.out
```
Nếu cần xem lỗi nạp DLL:
```bash
WINEDEBUG=+loaddll PROTON_LOG=1 ... 2>/tmp/run_loaddll.out
grep -E "err:module|not found|failed \(error" /tmp/run_loaddll.out
```

### B4 — Đọc log theo tầng
```bash
LOG=$(find "$PFX/drive_c/users" -name "Player.log" -path "*LocalLow*" | head -1)
grep -nE "md5|SteamApi|Quit|Dispose|not found|Curl error|Exception" "$LOG" | head -40
```
**Đọc từ trên xuống, dừng ở dòng đầu tiên có vấn đề.** Mọi thứ phía sau thường là hệ lụy.

### B5 — Xác định Case (§5) và sửa **đúng 1 thứ**

### B6 — Chạy lại, đối chiếu log
Log hợp lệ phải **thoát khỏi tầng trước** và xuất hiện log của tầng kế tiếp.

### B7 — Đóng gói vào `play.sh` (§6)

### B8 — Verify + Backup/Rollback (§7, §8)

---

## 4. Anti-pattern — TUYỆT ĐỐI KHÔNG LÀM

| ❌ Không làm | Lý do |
|---|---|
| Patch import table đổi `msvcp140d.dll` → `msvcp140.dll` | **ABI sai.** `std::string`/`vector` bản Debug có layout khác → `Access Violation 0xC0000005` |
| `winetricks vcrun2019` để sửa lỗi `/MDd` | Nó cài bản **Release**, không có file `*d.dll` |
| `steam_appid.txt` **không khớp** với lớp tương thích đang dùng | Với **emulator**: `steam_appid.txt` là file **bắt buộc** và phải chứa đúng AppID của bản dựng. Còn nếu dùng client Steam thật (`steamclient*.dll`) với AppID mà tài khoản không có quyền → client tự kiểm tra và **đóng game** |
| Đặt game trong thư mục có dấu tiếng Việt **rồi bỏ qua việc kiểm tra đường dẫn** | Làm mất biến cần loại trừ đầu tiên. Lưu ý: bản thân Proton **không** hỏng vì tiếng Việt — xem §2.1 |
| Ghi đè `System32` của Wine prefix bằng DLL lạ | Gây DLL Hell cho mọi app khác trong cùng prefix |
| Sửa nhiều thứ 1 lúc rồi test | Không biết thứ nào hiệu quả |
| `rm` file gốc thay vì `mv` sang `_backup_xxx/` | Mất khả năng rollback |

---

## 5. Các Case đã gặp (chi tiết)

### 5.1. Case A — Chọn sai lớp tương thích Steamworks

**Triệu chứng:** `InvalidOperationException: Steamworks is not initialized`, hoặc game tự thoát khi lớp tương thích kiểm tra phiên.

**Chẩn đoán — trước hết xác định đang dùng lớp tương thích nào:**
```bash
P="$GAME_DIR/<TenGame>_Data/Plugins/x86_64"
ls -la "$P"/steam_api64.dll*
md5sum "$P"/steam_api64.dll*
strings -a "$P/steam_api64.dll" | grep -ci gbe_fork      # đếm chuỗi đặc trưng
```

| Dấu hiệu | Kết luận |
|---|---|
| ~11 MB, có chuỗi `gbe_fork` | **Emulator** ✅ (lớp tương thích đầy đủ) |
| ~300 KB, export kiểu Valve | **DLL gốc của Steam** — không có client thật thì fail |
| `steamclient.dll` + `ColdClientLoader.ini` + `unsteam.ini` | **Wrapper client cũ** — Proton hay nạp đè `lsteamclient`, gây xung đột |

**Phân biệt biến thể:** chuỗi `gbe_fork` là đặc trưng của **biến thể gbe_fork**
(Goldberg), không phải bản Goldberg gốc. **[ĐO] Bản dựng này: 4263 lần.**
Nếu hệ thống của bạn là biến thể khác thì **tên tệp cấu hình có thể khác** → hãy xác
minh bằng cách bật log rồi xem nó thực sự đọc tệp nào, thay vì đoán.

**Tệp cấu hình:** tên/số tệp **phụ thuộc biến thể**. Đây là đặc tính của lớp tương
thích nói chung, đừng mặc định mọi biến thể cần cùng một bộ tệp.
> **[ĐO] Bản dựng này:** `steam_settings/` chỉ cần **`steam_appid.txt`**.
> Không có tệp `appid` (không extension) ở bất kỳ đâu và game vẫn chạy tốt.
> `appid` là quy ước của biến thể khác — thêm vào cũng vô hại, nhưng đừng hiểu là
> "phải có cả hai".

**Xử lý:**
1. Đặt lại tệp tương thích 11 MB vào vị trí `steam_api64.dll`.
2. Tạo `steam_settings/` cạnh DLL:
   ```
   steam_settings/steam_appid.txt      → <AppID>                  ← bắt buộc
   steam_settings/appid                → <AppID>                  ← tùy biến thể
   steam_settings/steam_interfaces.txt → danh sách phiên bản interface game yêu cầu
   steam_settings/configs.user.ini     → account_name / account_id / language / ip_country
   steam_settings/configs.app.ini      → [app::log]  log_file = C:\<tên tệp log>
   ```
   > `steam_interfaces.txt` lấy từ:
   > `strings -a <steam_api64.dll gốc> | grep -E "^(STEAM|Steam).*[0-9]{3}$"`
   > hoặc giữ tệp có sẵn trong bản dựng. **Bỏ trống → báo
   > `Steam_GetHSteamUser: interface version ... not found`.**

   **Tìm AppID ở đâu:** (1) `steam_appid.txt`/`appid` có sẵn trong gói;
   (2) `strings <exe chính> | grep -E "^[0-9]{5,7}$"`; (3) tệp `app.info` cạnh tệp thực thi;
   (4) `ColdClientLoader.ini` (`AppId=`) nếu bản dựng có wrapper.

   `configs.user.ini` mẫu (từ môi trường tham chiếu):
   ```ini
   [user::general]
   account_name = Player
   account_id = 76561197960287930
   language = english
   ip_country = US
   ```
3. Chuyển toàn bộ **wrapper client cũ** sang `_backup_unsteam/` (đừng xoá).
4. Chạy thẳng exe game (bỏ wrapper).

---

### 5.2. Case B — Kiểm tra toàn vẹn bằng MD5 trong IL2CPP metadata ⭐ **(Case khó nhất)**

**Triệu chứng:**
```
[frame=1, time=0.145] _CheckSteamApiDll: md5 != _SteamApiMd5, md5:4af5a9b2f194730d5b6cbbd4e5948fee
[frame=3,   time=0.230] [CoreMain.Dispose()]
```
Game quit ở frame 3 → **không bao giờ tới được dòng `Steam Sdk 登录成功`**,
vì `SteamAPI_Init()` không được gọi.

> ⚠️ **Chỗ hay mất thời gian nhất:** string literal của IL2CPP nằm ở
> `<TenGame>_Data/il2cpp_data/Metadata/global-metadata.dat`, **không** phải trong
> `GameAssembly.dll`. Quét `strings` trên 55 MB `GameAssembly.dll` là vô ích.
>
> **[ĐO]** Với bản dựng này, hằng MD5 chỉ có trong `global-metadata.dat`.
> **[KHÁC BIỆT CẦN NHỚ]** `GameAssembly.dll` là **native code do IL2CPP sinh ra** từ C#;
> trình biên dịch đặt hằng chuỗi vào metadata, không nhúng vào native code — nên đây là
> quy luật của cả IL2CPP, không riêng bản dựng này.
> Tuy vậy **vẫn nên quét cả hai tệp** (`strings <exe> | grep -E "^[0-9a-fA-F]{32}$"`),
> vì một số literal *khác* có thể được nhúng trong native code và việc này gần như miễn phí.

> ⚠️ **Đừng dùng log của lớp tương thích (`goldberg.log`) làm tiêu chí.**
> [ĐO] File này **0 byte** dù đã cấu hình `log_file`, trong khi game chạy tốt.
> **[CHƯA RÕ]** Nguyên nhân chưa xác minh (xem `FINDINGS.md` §3.4).
> Tiêu chí quyết định là **dòng trong `Player.log`**.

#### Bước 1 — Lấy MD5 của tệp Steam bạn đang dùng
```bash
P="$GAME_DIR/<TenGame>_Data/Plugins/x86_64"
md5sum "$P"/steam_api64.dll*        # xem hết các biến thể, ghi lại MD5 từng cái
```
Giá trị cần tìm: **OLD** = MD5 của tệp gốc (dung 300 KB), **NEW** = MD5 của tệp bạn đang dùng.

#### Bước 2 — Tìm mọi ứng viên trong metadata
```bash
python3 tools/find_md5_literals.py "$GAME_DIR/<TenGame>_Data/il2cpp_data/Metadata/global-metadata.dat"
```
Kết quả gồm 3 phần:
- **A)** Hằng hex-32 lấy từ bảng `stringLiteral` → **ứng viên chính**, có index + offset.
- **B)** Mọi chuỗi hex-32 trong toàn tệp → tìm thêm trong `fieldAndParameterDefaultValueData`.
- **C)** Vị trí các chuỗi kiểm tra toàn vẹn → xác nhận đúng bản dựng.

#### Bước 3 — Xác nhận ứng viên
Ứng viên đúng thường thoả **CẢ 3** điều kiện:
1. Độ dài 32 ký tự hex, có entry trong bảng `stringLiteral` (phần A).
2. **Trùng khớp** với `md5sum` của **một tệp có thật** trong gói (thường là bản `.valve_orig`).
3. Xuất hiện **≥ 2 lần**: 1 lần trong `stringLiteralData`, 1 lần trong
   `fieldAndParameterDefaultValueData` — và lần thứ 2 nằm cạnh **đường dẫn DLL**:
   ```
   240d8c3d2988d66d1329d38a92525bf4  "<TenGame>_Data/Plugins/x86_64/steam_api64.dll"
   ```
   → Chuỗi (hash, đường dẫn) kề nhau = **bằng chứng kết luận**.

**[ĐO] Kết quả thật của bản dựng này** (`FINDINGS.md` §3): ứng viên đúng nằm ở offset
`185843` và `6302623`. Ứng viên "anh em" `22e445595b0f42bd8c5fe35bc44b88d6` **không**
khớp tệp nào → đừng thử nó.

#### Bước 4 — Sửa
```bash
cp -v "$MD" "$MD.bak_original"     # backup trước

python3 tools/patch_md5.py "$MD" \
    <OLD_MD5_32_hex> \        # MD5 của tệp gốc
    <NEW_MD5_32_hex> \        # MD5 của tệp đang dùng
    --dry-run                     # xem trước: in ra toạ độ, chưa ghi

# ổn rồi thì bỏ --dry-run
```
**Tại sao an toàn:** old/new cùng **đúng 32 byte ASCII** → không lệch offset,
không phải sửa bảng `stringLiteral` (trường `length` giữ nguyên).

#### Bước 5 — Kiểm chứng
```bash
# (1) Tệp đã đổi thật chưa   (-a để grep coi tệp nhị phân là văn bản)
grep -ac "<NEW_MD5>" "$MD"     # mong đợi: 2
grep -ac "<OLD_MD5>" "$MD"     # mong đợi: 0

# (2) MD5 tệp DLL phải khớp giá trị đã sửa
md5sum "$P/steam_api64.dll"

# (3) Chạy game rồi đọc log
LOG=$(find "$PFX/drive_c/users" -name Player.log -path "*LocalLow*" | head -1)
grep -a "_CheckSteamApiDll\|Steam Sdk" "$LOG"
```

**Bốn bất biến — chỉ cái này được khẳng định (đã đo trên nhiều lần chạy):**

```
✅ có dòng  _CheckSteamApiDll: md5 == null || md5 == _SteamApiMd5
✅ có dòng  Steam Sdk 登录成功
✅ Curl error 7                   == 0
✅ "Steamworks is not initialized" == 0 lần
```

**Biến thiên — KHÔNG dùng làm tiêu chí:** `frame=`, `time=`, số lần `Curl error 28`
(đo được 6 ở một lần chạy, 13 ở lần khác), số dòng trong tệp log.

#### Nếu chọn sai ứng viên

```
1. Quan sát: game crash ngay, KHÔNG có dòng _CheckSteamApiDll ở đâu cả
   (khác hẳn với "có dòng nhưng báo !=" — dấu hiệu sai kiểu, không phải sai giá trị)
2. Hoàn nguyên ngay:
      cp -v "$MD.bak_original" "$MD"
3. Đọc lại phần A của Bước 2, lấy ứng viên kế tiếp
4. Lặp lại. Mỗi vòng chỉ sửa MỘT ứng viên.
```

Dấu hiệu phân biệt:

| Log | Nghĩa |
|---|---|
| Có dòng `md5 != _SteamApiMd5, md5:<giá trị>` | ứng viên đúng ô, nhưng **giá trị mới** sai |
| **Không có dòng nào**, crash sớm | **ứng viên sai** → hoàn nguyên rồi thử ứng viên khác |

---

### 5.3. Case C — Server nội bộ cục bộ (port 1075)

**Triệu chứng:**
```
Curl error 7: Failed to connect to localhost port 1075 after 5 ms
[HttpClientMgr.PostRequest]Error=Cannot connect to destination host
```
Vào game, bấm **Play / chọn server** → treo ở màn hình "đang đăng nhập".

**Chẩn đoán — 2 kiểu server hoàn toàn khác nhau:**
```bash
ls -la "$GAME_DIR/Server/"
strings -a Server/localServer.exe | grep -iE "snapshot|express|port" | head
strings -a Server/*Server.dll     | grep -iE "cpp-httplib|Server started|user/login"
```

| Kiểu | Nhận biết | Cách chạy |
|---|---|---|
| **Standalone** (`localServer.exe` = Node/pkg + Express) | có chuỗi `C:\snapshot\...\index.js` | ✅ Chạy riêng biệt, `play.sh` start trước |
| **Injected DLL** (`LiAAEoYServer.dll`, cpp-httplib) | có `DllsToInjectFolder` trong `ColdClientLoader.ini` | ⚠️ Phải inject vào process game, hoặc thay bằng bản standalone |

**Xử lý (Hướng A — chạy độc lập, ưu tiên):**
```bash
STEAM_DIR="$HOME/.local/share/Steam"
WINE="$STEAM_DIR/steamapps/common/Proton - Experimental/files/bin/wine"
SERVER_PFX="$HOME/.local/share/<ten>_server_pfx"; mkdir -p "$SERVER_PFX"

cd "$GAME_DIR/Server"
setsid env WINEPREFIX="$SERVER_PFX" "$WINE" localServer.exe > /tmp/localserver.log 2>&1 &

sleep 6
curl -s -i http://127.0.0.1:1075/ | head -5
ss -ltn | grep 1075
```
Kỳ vọng: `Server is running on port 1075`, `ss` hiện `LISTEN`.
**HTTP 404 ở `/` là BÌNH THƯỜNG** — chỉ có endpoint cụ thể (`/user/login`, `/config`...).

> **Tách prefix server khỏi prefix game** (như template §6) để tránh tranh chấp wineserver.

> **Ghi chú từ hướng dẫn Windows của site:** site yêu cầu chạy `runLocalServer.bat`
> (nội dung chỉ đúng `.\server\localServer.exe`) và **giữ bảng đen mở**.
> Hướng dẫn đó = đúng hệt bước 2 ở trên. Cửa sổ đen bị đóng ⇒ vào game bấm Play bị đơ.

**Nếu DLL debug CRT thiếu (Case D)** — xem §5.4. *Lưu ý: `localServer.exe` **không**
import Debug-CRT; các file `*d.dll` chỉ phục vụ `LiAAEoYServer.dll` (đường inject).*

---

### 5.4. Case D — Debug CRT `/MDd` (thiếu `*d.dll`)

**Triệu chứng:** app vào được giao diện nhưng bấm chức năng thì đơ, log:
```
0140:err:module:import_dll Library MSVCP140D.dll ... not found
0140:err:module:import_dll Library VCRUNTIME140D.dll ... not found
0140:err:module:import_dll Library VCRUNTIME140_1D.dll ... not found
0140:err:module:import_dll Library ucrtbased.dll ... not found
Loading library ... failed (error c0000135)
```

**Chẩn đoán PE — PHẢI làm trước, để biết file nào cần DLL:**
```python
import pefile
pe = pefile.PE("<file.exe|dll>", fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
for e in pe.DIRECTORY_ENTRY_IMPORT:
    print(e.dll.decode())
```

> **Kết quả đo được (môi trường tham chiếu)** — giúp bạn khỏi kiểm tra lại lung tung:
>
> | File | Import Debug-CRT? |
> |---|---|
> | `Server/localServer.exe` | ❌ **Không** → chạy độc lập không cần `*d.dll` |
> | `Server/LiAAEoYServer.dll` | ✅ **Cả 4**: `MSVCP140D`, `VCRUNTIME140D`, `VCRUNTIME140_1D`, `ucrtbased` |
> | `WDHD5.exe` | ❌ Không |
> | `WDHD5_loader_x64.exe` | ❌ Không |
>
> ⇒ 4 file `*d.dll` nằm trong `Server/` **chỉ phục vụ đường bơm (inject) `LiAAEoYServer.dll`**.
> Nếu bạn **không** inject (cách làm trên Linux), chúng **không bắt buộc** — cứ để đó cho chắc.

**Xử lý — Side-by-side:**
1. Lấy 4 file từ **VS Installer CAB chính thức** (không tải từ trang lạ):
   ```bash
   curl -sL "https://aka.ms/vs/17/release/channel" -o channel.json
   # tìm Microsoft.VisualCpp.RuntimeDebug.14  -> cab1.cab
   # cabextract -d ./extracted vc_x64_cab1.cab
   ```
2. Copy `msvcp140d.dll`, `vcruntime140d.dll`, `vcruntime140_1d.dll`, `ucrtbased.dll`
   vào **cùng thư mục** với DLL/EXE gây lỗi (vd: `Server/`).
3. Linux ghi tệp hệ thống **phân biệt HOA–THƯƠNG**, còn import table trong PE thì không.
   Nếu tệp trên đĩa là `msvcp140d.dll` mà import ghi `MSVCP140D.dll` → không khớp.

   **Xác định case chính xác trước khi tạo symlink** — `strings | grep -i` **không** cho
   biết case thật trong import table. Cách đúng là đọc import table:
   ```bash
   python3 -c "
   import pefile,sys
   pe=pefile.PE(sys.argv[1],fast_load=True)
   pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
   for e in pe.DIRECTORY_ENTRY_IMPORT:
       if 'd.dll' in e.dll: print(repr(e.dll.decode()))
   " "$GAME_DIR/Server/<TenGame>Server.dll"
   ```
   rồi tạo symlink **từ tệp thật sang đúng case trong import table**:
   ```bash
   cd "$GAME_DIR/Server"
   ln -sf msvcp140d.dll          MSVCP140D.dll
   ln -sf ucrtbased.dll          UCRTBASED.dll
   ln -sf vcruntime140d.dll      VCRUNTIME140D.dll
   ln -sf vcruntime140_1d.dll    VCRUNTIME140_1D.dll
   ```
   **[ĐO] Case này:** import ghi hoa (`MSVCP140D`, `VCRUNTIME140D`, `VCRUNTIME140_1D`,
   `ucrtbased`), tệp trên đĩa đặt thường → chiều symlink như trên.
   Chiều ngược lại cũng có thể xảy ra ở bản dựng khác — **đọc import table để biết**,
   đừng đoán.

4. Verify:
   ```bash
   grep -E "err:module:import_dll" /tmp/run_loaddll.out   # phải biến mất
   grep -i "Server/" /proc/<PID>/maps                    # các module phải hiện
   ```

---

### 5.5. Case E — Lỗi tầng Application/Data (KHÔNG chặn chơi)

Sau khi qua hết 4 tầng trên, còn sót lại thường là **lỗi data**, bỏ qua được:

| Log | Ý nghĩa |
|---|---|
| `Curl error 28: Connection timed out` tới `http://10.0.x.x/...` | Dịch vụ nội bộ của bản dựng dùng IP LAN — không tồn tại |
| `[HttpClientMgr.GetRequest]Error=HTTP/1.1 404 Not Found` | Endpoint local server không có |
| `ArgumentOutOfRangeException ... FromUnixTimeSeconds` | Server trả timestamp `0` → Lua exception ở lịch điểm danh |

**Chỉ cần** `Curl error 7` (localhost) = **0** → tầng mạng cục bộ đã OK.

---

### 5.6. Kiểm chứng sau khi hoàn nguyên (rollback)

Sau khi chạy lệnh ở §8, **đừng tin là xong — hãy đo lại**:

```bash
GAME_DIR="/mnt/games/<TenGame>"
MD="$GAME_DIR/<TenGame>_Data/il2cpp_data/Metadata/global-metadata.dat"
P="$GAME_DIR/<TenGame>_Data/Plugins/x86_64"

# (1) Metadata phải khớp bản gốc
cmp -s "$MD" "$MD.bak_original" && echo "OK metadata đã hoàn nguyên" \
                                 || echo "SAI: metadata khác bản gốc"

# (2) Nếu bạn cũng khôi phục tệp tương thích
md5sum "$P/steam_api64.dll" "$P/steam_api64.dll.valve_orig"
#     → hai MD5 phải GIỐNG NHAU

# (3) Wrapper client cũ phải về đúng thư mục
ls "$GAME_DIR/_backup_unsteam/"*.dll "$GAME_DIR/_backup_unsteam/"*.ini 2>/dev/null
ls "$GAME_DIR"/steamclient*.dll 2>/dev/null && echo "→ wrapper đã về gốc" \
                                      || echo "→ nhớ copy lại từ _backup_unsteam/"

# (4) Nếu xoá sạch prefix, hãy kiểm tra prefix thật sự biến mất
ls -d "$HOME/.local/share/<ten>_game_pfx" 2>/dev/null || echo "OK prefix đã xoá"
```

> Nếu (1) hoặc (2) lệch, **đừng chạy game** — bản vá cũ còn sót sẽ gây khó chẩn đoán
> ở lần sau (vì giờ bạn không còn phân biệt được lỗi mới với lỗi cũ).
---

## 6. `play.sh` — bản đã KIỂM CHỨNG bằng chạy thật

> Bản dưới đây là bản đang dùng trong thư mục game, đã chạy thử cả **3 nhánh**
> (xem bảng kiểm chứng cuối §6). Khác biệt so với mẫu "đẹp mắt" thường thấy:
> `exec` trong subshell, `ss` thay `curl`, dọn dẹp theo PID, exit code phản ánh lỗi.
>
> **Chỉ cần đổi 3 dòng khi áp dụng cho bản dựng khác:**
> `SERVER_NAME` · `SERVER_PORT` · `GAME_EXE` (và tên prefix nếu muốn).

```bash
#!/usr/bin/env bash
# ==============================================================================
# Khởi chạy game có server nội bộ cục bộ trên Linux (Steam Proton)
#
# Ba điều chỉnh so với bản cũ:
#  1. SERVER_PID bắt đúng PID của wine nhờ `exec` trong subshell
#     (bản cũ dùng ( ... ) & nên $! là PID subshell → `kill` là no-op).
#  2. Sẵn sàng được kiểm bằng ss (port có LISTEN) thay vì curl — curl trả 0
#     cả khi HTTP 404 nên không phản ánh "server đã sẵn sàng ứng dụng".
#  3. Dọn dẹp theo đúng PID do script bật; KHÔNG pkill -f theo tên file.
#
# Biến môi trường:
#   SERVER_READY_TIMEOUT=<giây>   (mặc định 30)
#   SKIP_GAME=1                   chỉ bật server, không mở game (để kiểm thử)
# ==============================================================================
set -uo pipefail

GAME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$GAME_DIR/Server"
SERVER_NAME="localServer.exe"
SERVER_PORT="${SERVER_PORT:-1075}"
SERVER_READY_TIMEOUT="${SERVER_READY_TIMEOUT:-30}"
SERVER_LOG="/tmp/localserver.log"

# Chạy thẳng exe của game. Wrapper client cũ (<TenGame>_loader_x64.exe + steamclient*.dll
# + ColdClientLoader.ini) đã cách ly vào _backup_unsteam/ và không còn
# cần thiết: bản dựng đã dùng lớp tương thích (emulator) + giá trị kiểm tra
# toàn vẹn trong global-metadata.dat đã được sửa cho khớp.
GAME_EXE="$GAME_DIR/WDHD5.exe"

STEAM_DIR="$HOME/.local/share/Steam"
PROTON_BIN="$STEAM_DIR/steamapps/common/Proton - Experimental/proton"
WINE_BIN="$STEAM_DIR/steamapps/common/Proton - Experimental/files/bin/wine"
SERVER_PFX="$HOME/.local/share/<ten>_server_pfx"
GAME_PFX="$HOME/.local/share/<ten>_game_pfx"

mkdir -p "$SERVER_PFX" "$GAME_PFX"

# --- hàm tiện ích -------------------------------------------------------------
port_ready() { ss -ltnH "sport = :$SERVER_PORT" 2>/dev/null | grep -q LISTEN; }

port_listener_pids() { ss -ltnpH "sport = :$SERVER_PORT" 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2; }

start_server() {
    # exec trong subshell => $! là PID của chính process wine
    ( cd "$SERVER_DIR" && exec env WINEPREFIX="$SERVER_PFX" "$WINE_BIN" "$SERVER_NAME" ) \
        > "$SERVER_LOG" 2>&1 &
    SERVER_PID=$!
    SERVER_OWNED=1
    for _ in $(seq 1 $((SERVER_READY_TIMEOUT * 5))); do
        if port_ready; then return 0; fi
        kill -0 "$SERVER_PID" 2>/dev/null || break   # process đã chết -> không chờ nữa
        sleep 0.2
    done
    return 1
}

stop_server() {
    [ -z "${SERVER_PID:-}" ] && return 0
    kill "$SERVER_PID" 2>/dev/null || return 0
    for _ in $(seq 1 25); do
        kill -0 "$SERVER_PID" 2>/dev/null || { echo ">> Server đã dừng (PID $SERVER_PID)"; return 0; }
        sleep 0.2
    done
    kill -9 "$SERVER_PID" 2>/dev/null
    echo ">> Server buộc phải kết thúc (PID $SERVER_PID)"
}

# --- 1. Steam ---------------------------------------------------------------
if ! pgrep -x steam >/dev/null; then
    echo ">> Steam chưa chạy. Đang khởi động..."
    steam &
    sleep 3
fi

# --- 2. Server nội bộ cục bộ ----------------------------------------------
SERVER_PID=""
SERVER_OWNED=0
SERVER_FAILED=0

if port_ready; then
    echo ">> Cổng $SERVER_PORT đã có tiến động lắng nghe (PID: $(port_listener_pids | tr '\n' ' '))."
    echo "   Script KHÔNG bật server nên sẽ KHÔNG tắt nó khi thoát game."
else
    echo ">> Đang khởi động server nội bộ (log: $SERVER_LOG)..."
    if start_server; then
        echo ">> Server sẵn sàng: cổng $SERVER_PORT đang LISTEN (PID $SERVER_PID)."
    else
        SERVER_FAILED=1
        echo "!! CẢNH BÁO: server không lên được trong ${SERVER_READY_TIMEOUT}s."
        echo "   Vào game sẽ bị đơ ở màn hình đăng nhập. Log:"
        tail -20 "$SERVER_LOG" 2>/dev/null
    fi
fi

# --- 3. Mở game -------------------------------------------------------------
if [ "${SKIP_GAME:-0}" = "1" ]; then
    echo ">> SKIP_GAME=1 — bỏ qua bước mở game."
else
    echo ">> Đang mở game..."
    cd "$GAME_DIR"
    STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_DIR" \
    STEAM_COMPAT_DATA_PATH="$GAME_PFX" \
    "$PROTON_BIN" run "$GAME_EXE"
fi

# --- 4. Dọn dẹp -------------------------------------------------------------
if [ "$SERVER_OWNED" = "1" ]; then
    echo ">> Game đã đóng, đang tắt server..."
    stop_server
else
    echo ">> Giữ nguyên tiến động có sẵn trên cổng $SERVER_PORT."
fi

if [ "$SERVER_FAILED" = "1" ]; then
    echo ">> Hoàn tất (CÓ LỖI: server nội bộ không chạy)."
    exit 1
fi
echo ">> Hoàn tất!"
```

### Đã kiểm chứng (chạy thật, không phải đọc suông)

| Tình huống | Kết quả mong đợi | Kết quả thực tế |
|---|---|---|
| port trống → bật server | PID từ `ss` khớp PID của `exec` | ✅ khớp, kill sạch, port trống sau đó |
| port đã có tiến động | không tắt tiến động của người khác | ✅ PID trước = PID sau |
| server không lên được | cảnh báo + **exit 1** | ✅ exit 1, fail-fast 0.045 s |
| `SKIP_GAME=1` | không mở cửa sổ game | ✅ |

**Chưa kiểm chứng:** nhánh mở game thật (bước 3 giữ nguyên so với bản cũ).

**Thêm vào Steam (tuỳ chọn, KHÔNG bắt buộc):** Add a Non-Steam Game → chọn `play.sh`
→ tab Compatibility **KHÔNG tick Proton** (script đã tự gọi Proton).

**Thêm vào Steam (tuỳ chọn, KHÔNG bắt buộc):** Add a Non-Steam Game → chọn `play.sh`
→ tab Compatibility **KHÔNG tick Proton** (script đã tự gọi Proton).

---

## 7. Checklist kiểm chứng

**Bất biến — mỗi dòng phải đúng (đây mới là tiêu chí):**

```
[ ] Đường dẫn game không có dấu tiếng Việt
[ ] Wrapper client cũ đã ở trong _backup_unsteam/ (không còn ở thư mục gốc)
[ ] steam_api64.dll = lớp tương thích 11 MB; steam_settings/ có steam_appid.txt
[ ] md5sum steam_api64.dll  ==  giá trị đã sửa trong global-metadata.dat
[ ] grep -ac "<MD5 MỚI>" global-metadata.dat   → 2
[ ] grep -ac "<MD5 CŨ>"   global-metadata.dat   → 0
[ ] Player.log CÓ dòng  _CheckSteamApiDll: md5 == null || md5 == _SteamApiMd5
[ ] Player.log CÓ dòng  Steam Sdk 登录成功
[ ] Player.log KHÔNG có "Steamworks is not initialized"
[ ] grep -c "Curl error 7" Player.log           → 0
[ ] ss -ltnH "sport = :<port>" | grep LISTEN    → có
[ ] Qua được màn hình đăng nhập → vào được màn hình chính
[ ] Bản .bak_original còn nguyên; đã thử hoàn nguyên 1 lần (§5.6)
```

**Biến thiên — đừng dùng làm tiêu chí (đã chứng kiến đổi giữa hai lần chạy):**

```
frame=…      1        và        1
time=…       0.287    và        0.455
dòng SDK     frame=388 và        frame=384
Curl error 28:  6 lần  và        13 lần
```

> Nếu tài liệu nào khẳng định "sau N giây phải thấy dòng X" thì đó là mô tả của
> **một lần chạy**, không phải tiêu chí. Chỉ "có/không" mới đáng kiểm.

---

## 8. Rollback

```bash
GAME_DIR="/mnt/games/<TenGame>"
MD="$GAME_DIR/<TenGame>_Data/il2cpp_data/Metadata/global-metadata.dat"
P="$GAME_DIR/<TenGame>_Data/Plugins/x86_64"

# (1) Kiểm tra toàn vẹn — về bản gốc
cp -v "$MD.bak_original" "$MD"                 # hoặc .bak_patch

# (2) Tệp tương thích — về bản gốc 300 KB
cp -v "$P/steam_api64.dll.valve_orig" "$P/steam_api64.dll"
# hoặc về lớp tương thích:
# cp -v "$P/steam_api64.dll.goldberg_backup" "$P/steam_api64.dll"

# (3) Wrapper client cũ — về thư mục gốc
mv "$GAME_DIR/_backup_unsteam/"*.dll "$GAME_DIR/" 2>/dev/null
mv "$GAME_DIR/_backup_unsteam/"*.ini "$GAME_DIR/" 2>/dev/null
```

> **Bắt buộc: chạy §5.6 sau khi hoàn nguyên.** Nếu không đo lại, bạn không phân biệt
> được lỗi mới với lỗi cũ ở lần chạy sau.

---

## 9. Checklist khi nhận 1 game MỚI

```
TẢI & GIẢI NÉN        → xem WALKTHROUGH.md Phần 2
 1. Giải nén vào đường dẫn không dấu
 2. Lập bản đồ tệp: ls -la · ls */Plugins/*/ · ls Server/
 3. Ghi nhật ký dữ liệu trước khi sửa gì   → FINDINGS.md
 4. file <exe> chính, strings <steam_api64.dll>  → lớp tương thích nào? biến thể nào?
 5. md5sum các biến thể steam_api64.dll     → ghi lại (cái nào là OLD, cái nào là NEW)
 6. Chạy 1 lần, XOAY Player.log trước
 7. Đọc log → quy về đúng tầng theo §1
 8. Chọn Case (§5) → sửa ĐÚNG 1 thứ → chạy lại → phải qua tầng cũ
 9. Kiểm chứng theo §7 (bất biến, không theo con số)
10. Hoàn nguyên thử 1 lần + kiểm chứng §5.6
```

---

## 10. Công cụ kèm theo

| Tệp | Công dụng |
|---|---|
| `tools/find_md5_literals.py <global-metadata.dat>` | Liệt kê hằng hex-32 kèm offset; **tự dò** cấu trúc bảng `stringLiteral` (đừng hardcode thứ tự trường); dò chuỗi kiểm tra toàn vẹn |
| `tools/patch_md5.py <file> <old32> <new32> [--dry-run]` | Thay hex-32 an toàn: bắt buộc cùng độ dài 32, tự backup, tự đối chiếu |

```bash
cd /mnt/games/linux-game-fix/tools

# tìm ứng viên
python3 find_md5_literals.py "$GAME_DIR/<TenGame>_Data/il2cpp_data/Metadata/global-metadata.dat"

# xem trước (không ghi)
python3 patch_md5.py "$MD" <OLD_MD5_32_hex> <NEW_MD5_32_hex> --dry-run

# áp dụng
python3 patch_md5.py "$MD" <OLD_MD5_32_hex> <NEW_MD5_32_hex>
```

**Giới hạn đã biết:** `find_md5_literals.py` được viết và kiểm chứng cho
**metadata version 29–31**. Trên version 32+ bảng `stringLiteral` có thể thêm trường →
`detect_layout()` sẽ in `entry layout` khác, và **phải kiểm tra lại kết quả** trước khi tin.

---

## Phụ lục A — `global-metadata.dat` là gì

Bản dựng IL2CPP chia làm hai tệp:

| Tệp | Chứa gì |
|---|---|
| `GameAssembly.dll` | **native code** C++ do IL2CPP sinh ra từ C# |
| `global-metadata.dat` | **metadata**: class, method, **string literal**, giá trị mặc định của field |

Khi C# có:
```csharp
const string _SteamApiMd5 = "240d8c3d…";
```
thì hằng chuỗi được đặt vào **metadata**, không nhúng vào native code → đó là lý do
tìm MD5 trong `GameAssembly.dll` là vô ích.

### Header (đo được trên bản dựng này — version 31)

```
offset 0x00 : magic            0xFAB11BAF
offset 0x04 : version          31
offset 0x08 : stringLiteralOffset    256
offset 0x0C : stringLiteralSize      148576
offset 0x14 : stringLiteralDataOffset 148832
offset 0x18 : stringLiteralDataSize   541272
```

Bảng `stringLiteral` gồm các cặp 8 byte. Ở version 31 thứ tự trường là
**`(length, dataIndex)`**, và `dataIndex` trỏ vào `stringLiteralData`.
> Công cụ `find_md5_literals.py` **tự dò** thứ tự này bằng cách kiểm tra các entry
> có nối tiếp `dataIndex` hay không — vì thứ tự trường **có thể khác giữa các version**.
> Đừng hardcode.

### Hai nơi chứa cùng một hằng

| Nơi | Cách nhận biết |
|---|---|
| `stringLiteralData` | trong bảng literal, index + offset tường minh |
| `fieldAndParameterDefaultValueData` | hằng nằm cạnh **đường dẫn tệp** |

Sự xuất hiện ở cả hai nơi — nhất là khi hằng nằm ngay cạnh đường dẫn DLL — là
**bằng chứng kết luận** cho việc hằng đó được dùng để so sánh tệp đó.
