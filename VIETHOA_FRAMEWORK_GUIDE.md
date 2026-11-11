# VIETHOA_FRAMEWORK_GUIDE — Cẩm nang dựng bộ khung Việt Hóa game từ A-Z (Hook & Font Fallback)

> ## ⚠️ Tổng quan & Triết lý thiết kế
>
> Hướng dẫn này đúc kết phương pháp Việt Hóa game hiện đại: **Runtime Hooking & Dynamic Font Fallback** (Can thiệp thời gian thực trong bộ nhớ).
> 
> Thay vì phương pháp truyền thống (Unpack tệp asset hàng chục GB $\rightarrow$ sửa chuỗi trong giới hạn byte $\rightarrow$ Repack lại rất dễ lỗi và file patch quá nặng), phương pháp Hooking **giữ nguyên vẹn 100% tệp game gốc**, trích xuất phụ đề/văn bản ra ngoài dưới dạng tệp văn bản thuần (JSON/SRT/CSV), và nạp font tiếng Việt động lúc game khởi động.
>
> **Ưu điểm vượt trội:**
> - **Dung lượng patch siêu nhẹ:** Thường chỉ từ 2 MB – 10 MB (chỉ gồm DLL hook + font + file text).
> - **Không giới hạn độ dài chuỗi:** Tiếng Việt dài hơn tiếng gốc thoải mái, không lo tràn bộ đệm (Buffer Overflow).
> - **Kháng cập nhật (Update-proof):** Khi game update bản vá nhỏ, bản dịch vẫn hoạt động bình thường.
> - **Hỗ trợ đa nền tảng:** Chạy mượt mà trên cả Windows và Linux (Steam Deck / Wine / Proton).

---

## 0. Kiến trúc tổng thể của Bộ khung Hooking (Architecture)

Một hệ thống Việt Hóa Runtime tiêu chuẩn gồm **4 thành phần độc lập**:

```
[Game Engine (Unity / Unreal / Custom)]
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. TẦNG NẠP MÃ (Injector Layer)                             │
│    - Unity Doorstop / BepInEx / UE4SS / DLL Proxy Hijack    │
│    - Tự động nạp mã mod vào không gian bộ nhớ của game      │
└──────────────────────────────┬──────────────────────────────┘
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
┌───────────────────────────────────┐   ┌───────────────────────────────────┐
│ 2. TẦNG HOOK VĂN BẢN (Text Hook)  │   │ 3. TẦNG FONT (Font Fallback)      │
│    - Chặn hàm render văn bản      │   │    - Nạp font TTF/OTF tiếng Việt  │
│    - Lắng nghe sự kiện phát thoại │   │    - Gán làm Fallback cho Font gốc│
│    - Tra cứu từ điển bản dịch     │   │    - Triệt tiêu lỗi ô vuông [?]   │
└─────────────────┬─────────────────┘   └───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. DỮ LIỆU DỊCH BÊN NGOÀI (External Translation Storage)    │
│    - Thư mục Subtitles/ / Translations/ (JSON, CSV, SRT)    │
│    - Mã hóa nhẹ (XOR) nếu game yêu cầu                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Dựng khung cho Game Unity (Mono & IL2CPP)

Unity chiếm hơn 70% các tựa game Indie, Visual Novel, FMV và RPG hiện nay.

### 1.1. Công cụ nạp mã (Injector)
* **Unity Mono (Cổ điển):** Dùng **BepInEx 5** hoặc **Unity Doorstop**.
* **Unity IL2CPP (Hiện đại):** Dùng **BepInEx 6 (phiên bản Bleeding Edge build cho IL2CPP)** hoặc **Unity Doorstop v4**.
* **Cách cài đặt Injector 1-Click:**
  Tải bản build BepInEx 6 x64 tương ứng, giải nén toàn bộ tệp (`winhttp.dll`, `doorstop_config.ini`, thư mục `BepInEx/`) vào cạnh file `.exe` của game.

### 1.2. Kỹ thuật Hook Văn bản (Text Hooking)
Trong Unity, 95% văn bản hiển thị qua hai hệ thống:
1. `UnityEngine.UI.Text` (UI Text cũ)
2. `TMPro.TextMeshPro` / `TextMeshProUGUI` (TextMeshPro mới)

**Code C# Plugin (Harmony Hook) mẫu:**
```csharp
using BepInEx;
using HarmonyLib;
using TMPro;
using UnityEngine.UI;
using System.Collections.Generic;
using System.IO;

[BepInPlugin("com.viethoa.patch", "VietHoa Framework", "1.0.0")]
public class VietHoaPlugin : BaseUnityPlugin
{
    public static Dictionary<string, string> TranslationDict = new Dictionary<string, string>();

    void Awake()
    {
        // 1. Nạp từ điển tiếng Việt từ bên ngoài
        LoadTranslations();

        // 2. Kích hoạt hook
        Harmony.CreateAndPatchAll(typeof(VietHoaPlugin));
        
        // 3. Nạp Font Fallback
        FontFallbackManager.InitFont();
    }

    private void LoadTranslations()
    {
        string path = Path.Combine(Paths.PluginPath, "Translations/strings.json");
        if (File.Exists(path))
        {
            // Parse JSON nạp vào TranslationDict
        }
    }

    // Hook TextMeshPro
    [HarmonyPatch(typeof(TMP_Text), "text", MethodType.Setter)]
    [HarmonyPrefix]
    public static void PatchTMPText(ref string value)
    {
        if (value != null && TranslationDict.TryGetValue(value, out string viText))
        {
            value = viText;
        }
    }

    // Hook UI Text cũ
    [HarmonyPatch(typeof(Text), "text", MethodType.Setter)]
    [HarmonyPrefix]
    public static void PatchLegacyText(ref string value)
    {
        if (value != null && TranslationDict.TryGetValue(value, out string viText))
        {
            value = viText;
        }
    }
}
```

### 1.3. Xử lý triệt để lỗi Font chữ bằng "Font Fallback"
Lỗi kinh điển khi dịch game là font gốc chỉ hỗ trợ bảng mã ASCII hoặc CJK (Trung/Nhật), khi gặp dấu tiếng Việt (`à, ả, ã, ơ, ư...`) sẽ hiện ra ô vuông rỗng `[?]` hoặc ký tự rác.

**Giải pháp "Font Fallback" động:**
Không cần sửa font gốc của game, chỉ cần nạp 1 font Unicode chuẩn (như *Noto Sans*, *Roboto*, *Segoe UI*) và đưa vào danh sách dự phòng (Fallback List):

```csharp
public class FontFallbackManager
{
    public static void InitFont()
    {
        // Nạp font tiếng Việt (đã nhúng sẵn vào AssetBundle riêng hoặc tệp TTF)
        Font viFont = Font.CreateDynamicFontFromOSFont("Segoe UI", 16);
        TMP_FontAsset viTMPFont = TMP_FontAsset.CreateFontAsset(viFont);

        // Duyệt toàn bộ font TextMeshPro mặc định trong game và gán font tiếng Việt làm fallback
        TMP_Settings.fallbackFontAssets.Add(viTMPFont);
    }
}
```
*Kết quả:* Khi game vẽ ký tự tiếng Việt mà font gốc không có glyph, Unity sẽ tự động lấy glyph tiếng Việt từ font Fallback để vẽ lên màn hình, sắc nét và hoàn toàn không bị lỗi ô vuông.

---

## 2. Dựng khung cho Game Unreal Engine (UE4 / UE5)

Với các game Unreal Engine, văn bản được quản lý qua hệ thống `FText` / `FString` và Slate UI.

### 2.1. Công cụ nạp mã
Sử dụng **UE4SS (Unreal Engine 4/5 Scripting System)**:
- Nạp qua DLL proxy `dwmapi.dll` hoặc `xinput1_3.dll`.
- Hỗ trợ viết script Hook bằng **C++** hoặc **Lua**.

### 2.2. Kỹ thuật Hook FText bằng Lua Script (Cực nhẹ & Không cần biên dịch)
Tạo script `scripts/main.lua` trong thư mục UE4SS:

```lua
local Translations = {}

-- Nạp từ điển tiếng Việt
local function LoadDictionary()
    local file = io.open("Mods/VietHoa/dict.json", "r")
    if file then
        local content = file:read("*all")
        -- Parse JSON vào bảng Translations
        file:close()
    end
end

LoadDictionary()

-- Hook hàm khởi tạo FText hoặc TextBlock Widget
RegisterHook("/Script/UMG.TextBlock:SetText", function(self, Text)
    local origStr = Text:get():ToString()
    if Translations[origStr] then
        Text:set(Translations[origStr])
    end
end)
```

---

## 3. Dựng khung cho Game FMV / Phim tương tác (Video-Heavy)

Các game FMV (như *Love is All Around*, *Ladies' School Prince*) có lời thoại nằm trong video chứ không phải văn bản UI thông thường.

### 3.1. Cơ chế Overlay Subtitle Hook
1. **Lắng nghe sự kiện phát Video (`VideoPlayer` / Media Framework):**
   Mỗi khi game chuyển cảnh hoặc phát một cutscene, ta trích xuất tên file video hoặc mã băm MD5/SHA256 của video đó.
2. **Khớp file phụ đề ngoài:**
   Dùng mã băm đó để tìm file phụ đề tương ứng trong thư mục mod (ví dụ: `Subtitles/<hash>.srt` hoặc `<hash>.json`).
3. **Lưu ý đặc biệt về Trình phát Video (AVPro Video vs Native Hook):**
   - Nếu game sử dụng **AVPro Video** (RenderHeads - `UnityVideo.MediaPlayer:EnableSubtitles`): AVPro Video đọc trực tiếp file `.srt` và parse bằng `SubtitleUtils.ParseSubtitlesSRT(text)`. Hàm này kiểm tra dấu mốc `-->` của định dạng SRT thuần. **Tuyệt đối không mã hóa nhị phân file `.srt` (phải để Plain-Text UTF-8 chuẩn)**, nếu không AVPro Video sẽ báo lỗi `[AVProVideo] SRT format doesn't appear to be valid` và nuốt toàn bộ phụ đề!
   - Nếu game có lớp Hook riêng hoặc game tự parse phụ đề qua code nội bộ: Khi đó mới sử dụng mã hóa đối xứng nhẹ (như XOR 9 trên các bảng dữ liệu `LanguageTb.csv`).


### 3.2. Kết hợp AI để tự động tạo Subtitle khi video không có sub gốc
Khi gặp các video không có sẵn file `.srt` (chỉ có video người thật nói tiếng nước ngoài):
- **Bước 1:** Dùng `ffmpeg` tách âm thanh sang container `.mp4` audio-only nhẹ.
- **Bước 2:** Áp dụng skill `/video-gemini-transcribe` (dùng Gemini AI hoặc Whisper) "lắng nghe" âm thanh và tự động xuất ra file `.srt` chuẩn timecode từng milli-giây.
- **Bước 3:** Đưa file `.srt` vào Pipeline biên dịch tiếng Việt.

---

## 4. Quy trình Biên dịch Tự động bằng AI (Translation Pipeline)

Với số lượng hàng ngàn dòng thoại, việc tự động hóa bằng AI giúp tiết kiệm 95% thời gian nhưng vẫn đảm bảo chất lượng:

```
[Phụ đề gốc EN/ZH] 
        │
        ▼
[1. Script Trích xuất (Extractor)] ──► Gom toàn bộ về tệp JSON song ngữ
        │
        ▼
[2. Phân chia Batch (Batching)] ──► Chia thành các gói ~80 cutscenes (~800 câu)
        │
        ▼
[3. Subagents dịch song song] ──► Dịch đối chiếu cả tiếng Trung và Anh
        │                         Chuẩn hóa xưng hô, văn phong điện ảnh
        ▼
[4. Validator & Builder] ──► Kiểm tra timecode SRT, mã hóa XOR, đóng gói mod
```

### Prompt mẫu chuẩn mực cho AI Dịch thuật Game FMV/Phim:
```text
Bạn là một chuyên gia biên dịch phụ đề tiếng Việt chuyên nghiệp cho phim ảnh/game FMV.
Nhiệm vụ: Dịch danh sách các đoạn thoại sau đây sang tiếng Việt tự nhiên, giàu cảm xúc.
Yêu cầu bắt buộc:
1. Đối chiếu song song cả bản gốc tiếng Trung (zh) và tiếng Anh (en) để hiểu đúng ngữ cảnh.
2. Giữ nguyên 100% timecode và chỉ số đánh số dòng của từng block SRT.
3. Chuẩn hóa xưng hô đời sống tự nhiên:
   - Nam chính (Cố Dịch) và các nữ chính: xưng Anh - Em, Cậu - Tớ, hoặc Dì - Cháu tùy vai vế.
   - Bạn bè thân thiết: xưng Tôi - Ông/Bà, Tớ - Cậu, Mày - Tao tùy sắc thái thân mật/cà khịa.
4. Tuyệt đối không dịch máy thô cứng (dịch thoát ý, giữ vần điệu và sự hài hước).
```

---

## 5. Quy chuẩn Đóng gói Bộ cài đặt Mod 1-Click An toàn

Một bản Mod hoàn chỉnh phải tuân thủ **nguyên tắc an toàn dữ liệu**:
- **Không bao giờ làm mất file gốc của người chơi:** Phải có cơ chế tự động backup trước khi cài đè.
- **Luôn cung cấp script gỡ bỏ (Uninstall):** Khôi phục 100% nguyên trạng ban đầu khi người chơi không muốn dùng mod.

### Cấu trúc gói Mod chuẩn (`VietHoa_Pack/`):
```
VietHoa_Pack/
├── Subtitles/            # Chứa các file phụ đề tiếng Việt đã mã hóa/format
├── BepInEx/ (hoặc DLL)   # Bộ nạp mã và font fallback (nếu dùng hook)
├── install.sh            # Script cài đặt tự động (Linux/Steam Deck)
├── install.bat           # Script cài đặt tự động (Windows)
├── uninstall.sh          # Script hoàn nguyên nguyên bản (Linux)
└── uninstall.bat         # Script hoàn nguyên nguyên bản (Windows)
```

### Script cài đặt an toàn mẫu (`install.sh`):
```bash
#!/bin/bash
GAME_DIR="/path/to/game"
MOD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[*] Đang sao lưu tệp gốc vào _backup_orig..."
mkdir -p "$MOD_DIR/_backup_orig"
cp -rn "$GAME_DIR/Subtitles" "$MOD_DIR/_backup_orig/"

echo "[*] Đang cài đặt bản Việt Hóa..."
cp -rf "$MOD_DIR/Subtitles"/* "$GAME_DIR/Subtitles/"

echo "[+] Cài đặt hoàn tất! Khởi động game để trải nghiệm tiếng Việt."
```

---

## 6. Checklist kiểm tra chất lượng trước khi phát hành

- [ ] **Kiểm tra Font:** Các nguyên âm tiếng Việt phức tạp (`ở, ỡ, ợ, ứ, ử, ữ, ề, ể, ễ`) có bị mất dấu hoặc hiển thị thành ô vuông không?
- [ ] **Kiểm tra Timecode:** Phụ đề có xuất hiện và biến mất đúng lúc nhân vật mở miệng/ngừng nói không?
- [ ] **Kiểm tra độ dài hiển thị:** Dòng thoại dài có bị tràn ra ngoài viền màn hình (Screen overflow) không? (Nếu có, chèn dấu ngắt dòng `\n`).
- [ ] **Kiểm tra tính năng Rollback:** Chạy `uninstall.sh` và xác nhận game trở về nguyên bản 100%.

---

## 7. Cơ chế Việt Hóa Giao diện Game UI (FairyGUI & Bảng CSV Data Table)

Bên cạnh phụ đề cutscene video, toàn bộ giao diện Menu, Cài đặt (Settings), Nút bấm và Thông báo hệ thống thường được lưu trong các bảng dữ liệu cấu trúc (Data Tables):

### 7.1. Cấu trúc lưu trữ UI & Cơ chế Obfuscation
Nhiều tựa game Unity sử dụng FairyGUI hoặc bảng CSV trong `StreamingAssets/Datas/Language/`:
- Các thư mục ngôn ngữ: `zh-CN/` (Giản thể), `zh-TW/` (Phồn thể), `en/` (Tiếng Anh).
- **Mã hóa Header + XOR:** Bảng CSV có thể được bọc bởi header nhận diện 2-byte cố định (`0x04 0x41`) kết hợp thuật toán đối xứng `XOR 9` (`byte ^ 9`) trên luồng UTF-8 có BOM:
  ```python
  import csv, io, codecs

  # Giải mã
  def decrypt_table(raw_bytes: bytes) -> list:
      header = raw_bytes[:2] # 0x04 0x41
      dec = bytes([b ^ 9 for b in raw_bytes[2:]])
      text = dec.decode('utf-8-sig', errors='replace')
      return list(csv.reader(io.StringIO(text)))

  # Đóng gói mã hóa
  def encrypt_table(rows: list) -> bytes:
      out_csv = io.StringIO()
      writer = csv.writer(out_csv, lineterminator='\r\n')
      writer.writerows(rows)
      body = codecs.BOM_UTF8 + out_csv.getvalue().encode('utf-8')
      return bytes([0x04, 0x41]) + bytes([b ^ 9 for b in body])
  ```

### 7.2. Đồng bộ đa hồ sơ ngôn ngữ (Profile Multi-Injection)
Để người chơi không cần chuyển đổi cài đặt hoặc bị phụ thuộc vào profile ngôn ngữ mặc định của game/Steam:
- Luôn ghi đè bản dịch vào **cả 3 thư mục**: `zh-CN`, `zh-TW` và `en`.
- Dù người chơi chọn ngôn ngữ nào trong menu, giao diện và phụ đề đều hiển thị tiếng Việt hoàn hảo.

