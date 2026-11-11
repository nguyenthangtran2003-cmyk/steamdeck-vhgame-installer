# linux-game-fix — Chạy Game Windows & Mod Việt Hóa trên Linux / Steam Deck (Proton/Wine)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Linux / SteamOS](https://img.shields.io/badge/Platform-Linux%20%7C%20SteamOS%20%7C%20Steam%20Deck-blue.svg)](https://steampowered.com)
[![Compatibility: Proton / Wine](https://img.shields.io/badge/Compatibility-Proton%20%2F%20Wine-purple.svg)](https://www.winehq.org)
[![Engine: Unity & Unreal](https://img.shields.io/badge/Engine-Unity%20IL2CPP%20%7C%20Mono%20%7C%20UE-green.svg)](https://unity.com)

Bộ tài liệu kỹ thuật và công cụ Reverse Engineering chuyên sâu dành cho việc **chạy game Windows và các bản Mod Việt Hóa trên Linux / Steam Deck qua Proton/Wine**: chẩn đoán lỗi tương thích theo mô hình 5 tầng, xử lý kiểm tra toàn vẹn nhị phân (MD5 Integrity Check trong `global-metadata.dat`), khắc phục crash CLR/Wine-Mono và Media Foundation codec.

Dự án mở ra nhằm kêu gọi cộng đồng Linux, Steam Deck và Modder **Fork, đóng góp và cùng nhau hoàn thiện** các công cụ vá lỗi game tự động.

---

## 📂 Cấu trúc Thư mục Dự Án

```text
linux-game-fix/
├── GUIDE.md                  # Cẩm nang kiến trúc tổng thể, mô hình 5 tầng & Hướng dẫn Contributor
├── WALKTHROUGH.md            # Quy trình thực hành từng bước từ lúc giải nén game đến khi chơi
├── PLAYBOOK.md               # Sổ tay chẩn đoán chi tiết 5 Case study lỗi game phức tạp
├── VIETHOA_MOD_PLAYBOOK.md   # Sổ tay chuyên sâu xử lý lỗi Mod Việt Hóa (Hook, CLR, Media Foundation)
├── VIETHOA_FRAMEWORK_GUIDE.md# Cẩm nang tự xây dựng bản mod Việt Hóa từ A-Z cho Unity & Unreal
├── CHANGELOG.md              # Lịch sử các can thiệp nhị phân đã kiểm chứng và cách hoàn nguyên
├── tools/                    # Bộ công cụ Python dịch ngược và vá nhị phân tự động
│   ├── find_md5_literals.py  # Dò hằng MD5 trong global-metadata.dat (Unity IL2CPP)
│   ├── patch_md5.py          # Vá byte MD5 in-place bảo toàn offset PE
│   ├── patch_hbhgame_mod.py  # Vá lỗi Wine-Mono Global Namespace crash
│   ├── dump_minidump.py      # Phân tích crash dump không cần công cụ nặng
│   └── README.md             # Hướng dẫn chi tiết từng công cụ
└── README.md                 # Tài liệu tổng quan dự án
```

---

## 🧭 Đọc theo mục đích

| Bạn muốn… | Đọc file | Thời gian |
|---|---|---|
| **Hiểu kiến trúc tổng thể & đóng góp dự án** | [`GUIDE.md`](GUIDE.md) | cẩm nang kỹ thuật & roadmap |
| **Cài game → giải nén → chạy được** | [`WALKTHROUGH.md`](WALKTHROUGH.md) | ~10 phút đọc |
| **Game chạy lỗi** — chẩn đoán & xử lý | [`PLAYBOOK.md`](PLAYBOOK.md) | tra theo Case (0 - 5) |
| **Game Việt Hóa lỗi** — Hook & CLR crash | [`VIETHOA_MOD_PLAYBOOK.md`](VIETHOA_MOD_PLAYBOOK.md) | tra theo Case VH (1 - 4) |
| **Tự làm Việt Hóa** — Dựng khung từ A-Z | [`VIETHOA_FRAMEWORK_GUIDE.md`](VIETHOA_FRAMEWORK_GUIDE.md) | cẩm nang đầy đủ |
| Biết đã sửa gì trong game + cách hoàn nguyên | [`CHANGELOG.md`](CHANGELOG.md) | tra cứu đối chiếu |
| Xem hướng dẫn các công cụ vá nhị phân | [`tools/README.md`](tools/README.md) | cẩm nang công cụ |

---

## 🛠 Yêu cầu môi trường

**Đã kiểm chứng trên** (đo lường thực tế):

| Hạng mục | Phiên bản |
|---|---|
| OS | Manjaro Linux / Arch Linux / SteamOS (Steam Deck) |
| Kernel | `7.2.6-1-cachyos` hoặc SteamOS Linux Kernel |
| Proton | `GE-Proton` hoặc Proton Experimental / Wine-Staging |
| Python | Python 3 có cài sẵn `python-pefile` |
| `unrar` | 7.30 beta hoặc mới hơn (hỗ trợ RAR5) |
| Game Engine | Unity `2022.3.x` (IL2CPP metadata v29-v31 / Mono), Unreal Engine 4/5 |

Cài đặt công cụ hỗ trợ trên Arch / Manjaro / Steam Deck (Desktop Mode):
```bash
sudo pacman -S python python-pefile unrar curl iproute2
```

---

## 🔬 Tóm tắt Mô hình Chẩn đoán 5 Tầng

Mỗi triệu chứng lỗi khi khởi chạy game trên Linux đều được phân loại chính xác:

- **Tầng 0 — PE Loader / OS:** Game tắt trong < 1s, mã lỗi `0xC0000135` (thiếu DLL, sai kiến trúc x86/x64, Debug CRT `/MDd`).
- **Tầng 1 — Bootstrap / Integrity:** Cửa sổ game chớp lên rồi tự tắt, log có `md5 != _SteamApiMd5` (kiểm tra toàn vẹn trong `global-metadata.dat`).
- **Tầng 2 — SDK / Lớp tương thích:** Báo lỗi `Steamworks is not initialized`, `SteamAPI_Init fail`.
- **Tầng 3 — Networking / IPC:** Lỗi `Curl error 7`, kết nối mạng nội bộ bị từ chối (`127.0.0.1:1075`).
- **Tầng 4 — Application / Game Data:** Màn hình sọc màu SMPTE (thiếu video codec Media Foundation), crash font hoặc lỗi script Lua.

Chi tiết phân tích và hướng dẫn giải quyết từng tầng xem tại **[`GUIDE.md`](GUIDE.md)** và **[`PLAYBOOK.md`](PLAYBOOK.md)**.

---

## 🤝 Kêu Gọi Cộng Đồng Fork & Đóng Góp (Call for Contributions)

Dự án này mở ra với mục tiêu trở thành **bộ cẩm nang và công cụ chuẩn hóa cho game thủ Linux và Steam Deck**. Chúng tôi rất mong cộng đồng cùng tham gia phát triển:

- [ ] **Phát triển CLI Tool (`game-fix-cli`):** Tự động quét game và áp dụng bản vá nhị phân chỉ với 1 lệnh.
- [ ] **Decky Loader Plugin:** Tích hợp trực tiếp vào giao diện cầm tay của Steam Deck.
- [ ] **Mở rộng IL2CPP Metadata v32+:** Tương thích các bản dựng Unity 2023 và Unity 6.
- [ ] **Community Game Database:** Bổ sung các bản vá cho nhiều tựa game và bản mod Việt Hóa mới.

### Cách đóng góp:
1. Nhấn **Fork** repository này về tài khoản GitHub của bạn.
2. Tạo nhánh làm việc: `git checkout -b feature/tinh-nang-moi`.
3. Kiểm thử cẩn thận và tuân thủ nguyên tắc `[ĐO]` trước khi viết tài liệu.
4. Gửi **Pull Request (PR)** để cùng thảo luận và hợp nhất mã nguồn!

---

## 📄 Bản quyền & Tuyên bố Miễn trừ Trách nhiệm (Disclaimer)

- Dự án này nhằm mục đích nghiên cứu kỹ thuật, tương thích hóa hệ điều hành Linux và hỗ trợ cộng đồng chơi game hợp pháp.
- Mọi thương hiệu và bản quyền game gốc thuộc về các nhà phát hành tương ứng.
- Bộ tài liệu và mã nguồn script trong kho lưu trữ này được phân phối dưới giấy phép **MIT License**.
