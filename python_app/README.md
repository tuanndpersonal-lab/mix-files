# Mix Files Python + PyQt

Bản desktop đơn giản của Mix Files, viết bằng Python và PyQt6.

## Cài Đặt

```bash
cd python_app
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Trên Windows PowerShell:

```powershell
cd python_app
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Chạy App

```bash
python mix_files_pyqt.py
```

## Tính Năng

- Kéo thả thư mục vào ô `Thư mục nhạc nguồn` hoặc `Thư mục xuất kết quả`.
- Có thể bấm nút `Chọn` nếu muốn mở hộp thoại chọn thư mục.
- Chọn số thư mục cần tạo.
- Chọn số file MP3 trong mỗi thư mục, hoặc để `Tất cả file`.
- Tùy chọn thêm số thứ tự như `1_baihat.mp3`.
- Tùy chọn xóa sạch thư mục xuất trước khi tạo.
- Tùy chọn nhập mã trộn cố định để lần sau tạo lại cùng kết quả.
- Mở thư mục xuất và copy danh sách đường dẫn sau khi tạo xong.

## Build Thành Ứng Dụng

### macOS

```bash
cd ..
./scripts/build-python-macos.sh
```

File `.app` và `.zip` được tạo trong `dist/python/`.

### Windows

Chạy trên máy Windows hoặc GitHub Actions Windows runner:

```powershell
cd ..
.\scripts\build-python-windows.ps1
```

File `.exe` và `.zip` được tạo trong `dist\python\`.

### GitHub Actions

Workflow `.github/workflows/build-python-app.yml` build artifact cho macOS và Windows khi tạo tag release.

Nếu macOS chặn app tải về, right-click app rồi chọn `Open`, hoặc chạy:

```bash
xattr -dr com.apple.quarantine /Applications/MixFiles.app
```
