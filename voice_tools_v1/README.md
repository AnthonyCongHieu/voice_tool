# 📦 VOICE AI EDITOR PRO - HƯỚNG DẪN CÀI ĐẶT & TRIỂN KHAI

> **Dự án:** Voice AI Editor Pro V4  
> **Mô tả:** Tool xử lý audio thông minh với AI - Điều chỉnh pause theo dấu câu  
> **Công nghệ:** Python 3.10+, Faster-Whisper, PyDub, CustomTkinter

---

## 📋 MỤC LỤC

1. [Yêu Cầu Hệ Thống](#yêu-cầu-hệ-thống)
2. [Cài Đặt Môi Trường](#cài-đặt-môi-trường)
3. [Cài Đặt Dependencies](#cài-đặt-dependencies)
4. [Chạy Ứng Dụng](#chạy-ứng-dụng)
5. [Kiểm Tra & Test](#kiểm-tra--test)
6. [Troubleshooting](#troubleshooting)
7. [Cấu Trúc Dự Án](#cấu-trúc-dự-án)
8. [Ghi Chú Quan Trọng](#ghi-chú-quan-trọng)

---

## 📌 YÊU CẦU HỆ THỐNG

### Bắt Buộc
- ✅ **Windows 10/11** (64-bit)
- ✅ **Python 3.10 hoặc 3.11** ([Tải tại đây](https://www.python.org/downloads/))
- ✅ **FFmpeg** (cho xử lý audio)
- ✅ **8GB RAM** trở lên

### Khuyến Nghị (Cho AI)
- ⭐ **NVIDIA GPU** (RTX 2060 trở lên) + CUDA 11.8/12.x
- ⭐ **16GB RAM** (để chạy model `large-v3-turbo`)
- ⭐ **SSD** (tốc độ đọc/ghi nhanh)

### Nếu Không Có GPU
- Tool vẫn chạy được trên **CPU**
- Tốc độ chậm hơn ~5-10x
- Khuyên dùng model `small` hoặc `medium`

---

## 🛠️ CÀI ĐẶT MÔI TRƯỜNG

### Bước 1: Kiểm Tra Python

```powershell
# Mở PowerShell, gõ:
python --version
```

**Kết quả mong đợi:**
```
Python 3.10.x hoặc Python 3.11.x
```

**Nếu không có Python:**
1. Tải từ [python.org](https://www.python.org/downloads/)
2. Chọn phiên bản **3.10.11** hoặc **3.11.x**
3. ✅ **QUAN TRỌNG:** Tick vào "Add Python to PATH" khi cài đặt!

---

### Bước 2: Cài Đặt FFmpeg

**Option A: Chocolatey (Khuyên dùng)**
```powershell
# Cài Chocolatey (nếu chưa có):
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Cài FFmpeg:
choco install ffmpeg -y
```

**Option B: Thủ Công**
1. Tải FFmpeg từ [ffmpeg.org](https://ffmpeg.org/download.html#build-windows)
2. Giải nén vào `C:\ffmpeg`
3. Thêm `C:\ffmpeg\bin` vào **PATH**:
   - Mở "Edit the system environment variables"
   - Click "Environment Variables"
   - Chọn "Path" → "Edit" → "New" → Dán `C:\ffmpeg\bin`
   - OK → OK → Khởi động lại PowerShell

**Kiểm tra:**
```powershell
ffmpeg -version
```

---

### Bước 3: Cài CUDA (Nếu Có GPU NVIDIA)

**Kiểm tra GPU:**
```powershell
nvidia-smi
```

**Nếu có kết quả:**
1. Tải CUDA Toolkit 11.8 hoặc 12.x từ [NVIDIA](https://developer.nvidia.com/cuda-downloads)
2. Cài đặt (giữ mặc định)
3. Khởi động lại máy

**Nếu KHÔNG có GPU:**
- Bỏ qua bước này
- Tool sẽ tự động chạy trên CPU

---

## 📦 CÀI ĐẶT DEPENDENCIES

### Bước 1: Giải Nén Dự Án

```powershell
# Giải nén file ZIP vào thư mục, ví dụ:
cd D:\Projects\voice_tools_v1
```

---

### Bước 2: Tạo Virtual Environment

```powershell
# Tạo venv
python -m venv venv

# Kích hoạt venv
.\venv\Scripts\Activate.ps1
```

**Nếu lỗi "execution policy":**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Kết quả:** Dòng lệnh sẽ có `(venv)` ở đầu

---

### Bước 3: Cài Đặt Packages

#### Option A: Từ requirements.txt (ĐƠN GIẢN)

```powershell
# Đảm bảo venv đã active (có (venv) ở đầu dòng)
pip install --upgrade pip
pip install -r requirements.txt
```

**File `requirements.txt` bao gồm:**
```
customtkinter>=5.2.0
pydub>=0.25.1
faster-whisper>=0.10.0
torch>=2.0.0
torchaudio>=2.0.0
```

---

#### Option B: Cài Thủ Công (Nếu requirements.txt Bị Lỗi)

```powershell
# Core packages
pip install customtkinter pydub

# AI packages (GPU - CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Hoặc (GPU - CUDA 12.1)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Hoặc (CPU only)
pip install torch torchvision torchaudio

# Faster-Whisper
pip install faster-whisper
```

---

### Bước 4: Kiểm Tra Cài Đặt

```powershell
python test_imports.py
```

**Kết quả mong đợi:**
```
✓ CustomTkinter: OK
✓ PyDub: OK
✓ Faster-Whisper: OK
✓ Torch: OK (CUDA available: True)
All imports successful!
```

**Nếu lỗi:** Xem [Troubleshooting](#troubleshooting)

---

## 🚀 CHẠY ỨNG DỤNG

### Cách 1: Qua File .bat (KHUYÊN DÙNG)

```powershell
# Double-click file:
run_app.bat
```

Hoặc:
```powershell
.\run_app.bat
```

---

### Cách 2: Qua Python

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Chạy GUI
python voice_app.py
```

---

### Cách 3: Qua CLI (Không cần GUI)

```powershell
.\venv\Scripts\Activate.ps1

python -m core.processor `
  --input "path/to/audio.mp3" `
  --script "path/to/script.txt" `
  --output "path/to/output.mp3" `
  --model "large-v3-turbo"
```

---

## ✅ KIỂM TRA & TEST

### Test 1: Chạy GUI

```powershell
python voice_app.py
```

**Kết quả:** Cửa sổ "✨ Voice AI Editor Pro" mở ra

---

### Test 2: Xử Lý File Mẫu

1. Chuẩn bị:
   - File audio ngắn (30s - 1 phút): `test.mp3`
   - File script tương ứng: `test.txt` (có dấu câu!)

2. Mở GUI → Chọn file → Nhập script → Click "▶️ BẮT ĐẦU"

3. Đợi 30s - 2 phút

4. Kiểm tra:
   - ✅ File output `test_processed.mp3` xuất hiện
   - ✅ Log hiển thị `✅ Thành công!`
   - ✅ Matched rate ≥ 85%

---

## ❌ TROUBLESHOOTING

### Lỗi 1: "python: command not found"

**Nguyên nhân:** Python chưa được thêm vào PATH

**Fix:**
1. Gỡ Python
2. Cài lại, **NHỚ TICK** "Add Python to PATH"
3. Khởi động lại PowerShell

---

### Lỗi 2: "ffmpeg: command not found"

**Nguyên nhân:** FFmpeg chưa cài hoặc chưa vào PATH

**Fix:**
```powershell
# Test:
ffmpeg -version

# Nếu lỗi → cài lại FFmpeg (xem Bước 2)
```

---

### Lỗi 3: "CUDA not available" (Có GPU)

**Nguyên nhân:** Torch không nhận GPU

**Fix:**
```powershell
# Kiểm tra CUDA:
nvidia-smi

# Cài lại PyTorch với CUDA:
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

### Lỗi 4: "ModuleNotFoundError: No module named 'xxx'"

**Nguyên nhân:** Thiếu package

**Fix:**
```powershell
# Activate venv:
.\venv\Scripts\Activate.ps1

# Cài lại:
pip install -r requirements.txt
```

---

### Lỗi 5: GUI Không Mở

**Nguyên nhân:** CustomTkinter lỗi

**Fix:**
```powershell
pip uninstall customtkinter
pip install customtkinter==5.2.2
```

---

### Lỗi 6: "Matched < 80%" (Kết quả xấu)

**Nguyên nhân:** Script không khớp audio

**Fix:**
- Viết lại script cho khớp audio hơn
- Script phải CÓ DẤU CÂU (. , ! ? ;)
- Khớp 85% trở lên là tốt

---

## 📁 CẤU TRÚC DỰ ÁN

```
voice_tools_v1/
├── voice_app.py              # GUI chính
├── config.py                 # Cấu hình
├── requirements.txt          # Dependencies
├── test_imports.py           # Test cài đặt
│
├── core/                     # Logic xử lý
│   ├── processor.py          # Xử lý audio V4
│   ├── transcriber.py        # AI transcribe
│   └── aligner.py            # Align script
│
├── venv/                     # Virtual environment (tạo khi setup)
│
├── run_app.bat               # Shortcut chạy GUI
├── setup.bat                 # Cài đặt tự động
│
└── README.md                 # File này
```

---

## 📝 GHI CHÚ QUAN TRỌNG

### 🔴 Khi Gửi Cho Người Khác

**GỬI:**
- ✅ Toàn bộ thư mục dự án (không bao gồm `venv/`, `dist/`, `__pycache__/`)
- ✅ File `requirements.txt`
- ✅ File `README.md` này
- ✅ Code mới nhất trong `core/processor.py` (V4)

**KHÔNG GỬI:**
- ❌ Thư mục `venv/` (người nhận tự tạo)
- ❌ Thư mục `dist/`, `build/` (build artifacts)
- ❌ Thư mục `__pycache__/`, `*.pyc` (cache)
- ❌ Thư mục `models/` (AI models sẽ tự download)

---

### 🔴 Cách Đóng Gói Gửi

**Option A: ZIP Clean**
```powershell
# Xóa venv và cache trước
rmdir /s /q venv
rmdir /s /q __pycache__
rmdir /s /q dist
rmdir /s /q build

# Zip toàn bộ thư mục còn lại
```

**File ZIP gửi đi sẽ bao gồm:**
```
voice_tools_v1.zip
  ├── voice_app.py
  ├── config.py
  ├── requirements.txt
  ├── README.md
  ├── core/
  ├── run_app.bat
  └── setup.bat
```

---

### 🔴 Người Nhận Làm Gì?

1. ✅ Giải nén ZIP
2. ✅ Đọc `README.md` (file này)
3. ✅ Cài Python 3.10/3.11
4. ✅ Cài FFmpeg
5. ✅ Chạy `setup.bat` HOẶC làm thủ công:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
6. ✅ Test: `python test_imports.py`
7. ✅ Chạy: `python voice_app.py`

---

### 🔴 Lưu Ý Về AI Models

**Lần đầu chạy:**
- AI sẽ tự động download model `large-v3-turbo` (~1.5GB)
- Đợi 5-10 phút (tùy tốc độ mạng)
- Model lưu tại: `C:\Users\<user>\.cache\huggingface\`

**Nếu muốn gửi kèm model:**
- Copy thư mục `~/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3`
- Gửi kèm ZIP (tổng ~5GB)
- Người nhận paste vào `C:\Users\<user>\.cache\huggingface\hub\`

---

### 🔴 Các Phiên Bản Logic

**V4 (Hiện tại - MỚI NHẤT):**
- Frame-based logic đơn giản (30 FPS)
- Cuối câu: ≥20f → 24f (800ms)
- Giữa câu: ≤6f giữ / 7-19f random 6-8f / ≥20f → 24f
- **File:** `core/processor.py` (đã update)

**V3 (Cũ):**
- Confidence scoring phức tạp
- Đã loại bỏ

**V2:**
- Legacy, không dùng nữa

---

## 🆘 HỖ TRỢ & LIÊN HỆ

**Gặp vấn đề?**
1. Check [Troubleshooting](#troubleshooting)
2. Đọc docs:
   - `HUONG_DAN_SU_DUNG.md` - Hướng dẫn người dùng
   - `QUY_TRINH_XU_LY_AUDIO_TIENG_VIET.md` - Hiểu logic bên trong
   - `BANG_TRA_CUU_LOG_MESSAGES.md` - Tra cứu log

3. Liên hệ dev

---

## 📜 CHANGELOG

**V4.0 (2026-01-31):**
- ✅ Đơn giản hóa logic thành pure frame-based
- ✅ Loại bỏ confidence scoring phức tạp
- ✅ Chuẩn hóa: ≥20f → 24f cho cả cuối câu và giữa câu
- ✅ Việt hóa toàn bộ docs

**V3.5:**
- Confidence scoring với multi-feature
- Loại bỏ injection logic

**V3.0:**
- Smart mode với AI alignment
- Faster-Whisper integration

---

## ✅ CHECKLIST SETUP (Cho Người Nhận)

- [ ] Đã cài Python 3.10/3.11
- [ ] Đã cài FFmpeg (test: `ffmpeg -version`)
- [ ] Đã tạo venv (`python -m venv venv`)
- [ ] Đã activate venv (có `(venv)` ở đầu dòng)
- [ ] Đã cài packages (`pip install -r requirements.txt`)
- [ ] Đã test imports (`python test_imports.py`)
- [ ] Đã chạy được GUI (`python voice_app.py`)
- [ ] Đã test xử lý 1 file mẫu
- [ ] Matched rate ≥ 85%

**Hoàn tất tất cả → Sẵn sàng sử dụng!** 🎉

---

**Chúc sử dụng tool thành công!** 🚀
