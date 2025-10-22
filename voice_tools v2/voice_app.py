import customtkinter as ctk
from tkinter import filedialog
from pydub import AudioSegment, silence
import threading, os, subprocess, sys, time, random

# Ẩn cửa sổ console ngay khi khởi động (chỉ trên Windows)
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

# ============================
# Tự động tìm đường dẫn FFMPEG (dùng cho cả exe và py)
# ============================
from pydub.utils import which

def find_ffmpeg():
    # 1. Kiểm tra biến môi trường PATH
    ffmpeg_in_path = which("ffmpeg")
    ffprobe_in_path = which("ffprobe")
    if ffmpeg_in_path and ffprobe_in_path:
        return ffmpeg_in_path, ffprobe_in_path

    # 2. Kiểm tra thư mục ffmpeg nội bộ (dùng khi đóng gói exe)
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    ffmpeg_dir = os.path.join(base_path, "ffmpeg", "bin")
    ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    ffprobe_exe = os.path.join(ffmpeg_dir, "ffprobe.exe")
    if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
        os.environ["PATH"] += os.pathsep + ffmpeg_dir
        return ffmpeg_exe, ffprobe_exe

    # 3. Báo lỗi nếu không tìm thấy
    raise FileNotFoundError("Không tìm thấy ffmpeg.exe hoặc ffprobe.exe! Vui lòng kiểm tra lại thư mục ffmpeg.")

# Sử dụng hàm mới
ffmpeg_path, ffprobe_path = find_ffmpeg()
AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe   = ffprobe_path

# ============================
# Cấu hình frame logic
# ============================
FRAME_RATE = 30
FRAME_MS = 1000 // FRAME_RATE

# Các ngưỡng xử lý
PARA_CUT_MS = FRAME_MS * 24        # 800ms
PHRASE_6_MS = FRAME_MS * 7        # 200ms

# ============================
# Hàm xử lý file âm thanh
# ============================
def process_audio(input_path, output_path, silence_thresh, progress_callback, text_callback, format_out, logic_mode):
    audio = AudioSegment.from_file(input_path)
    silence_ranges = silence.detect_silence(audio, min_silence_len=FRAME_MS*4, silence_thresh=silence_thresh)

    result = AudioSegment.empty()
    last_end = 0
    total = len(silence_ranges)

    for i, (start, end) in enumerate(silence_ranges):
        silence_len = end - start
        frame_len = silence_len // FRAME_MS

        if start > last_end:
            result += audio[last_end:start]

        if logic_mode == "logic_moi":
            if frame_len <= 6:
                result += audio[start:end]
            elif 7 <= frame_len <= 19:
                choices = [v for v in (6, 7, 8) if v <= frame_len]
                target_frames = random.choice(choices or [6])
                target_ms = FRAME_MS * target_frames
                head = min(100, silence_len)
                tail = min(50, max(0, silence_len - head))
                start_head = min(end, start + head)
                end_tail = max(start, end - tail)
                used_head = start_head - start
                used_tail = end - end_tail
                mid_sil = max(0, target_ms - used_head - used_tail)
                result += audio[start:start_head]
                if mid_sil > 0:
                    result += AudioSegment.silent(duration=mid_sil)
                result += audio[end_tail:end]
            elif frame_len > 20:
                head, tail = 200, 100
                start_head = min(end, start + head)
                end_tail = max(start, end - tail)
                used_head = start_head - start
                used_tail = end - end_tail
                mid_sil = max(0, PARA_CUT_MS - used_head - used_tail)
                result += audio[start:start_head]
                if mid_sil > 0:
                    result += AudioSegment.silent(duration=mid_sil)
                result += audio[end_tail:end]
            else:
                result += audio[start:end]
        else:
            if frame_len > 20:
                head, tail = 200, 100
                mid_sil = PARA_CUT_MS - head - tail
                result += audio[start:start + head]
                result += AudioSegment.silent(duration=mid_sil)
                result += audio[end - tail:end]
            elif 6 <= frame_len <= 20:
                head, tail = 100, 50
                mid_sil = PHRASE_6_MS - head - tail
                result += audio[start:start + head]
                result += AudioSegment.silent(duration=mid_sil)
                result += audio[end - tail:end]
            else:
                result += audio[start:end]

        last_end = end
        percent = round((i + 1) / total * 100)
        progress_callback((i + 1) / total)
        text_callback(f"\u23f3 Đang xử lý... {percent}%")

    result += audio[last_end:]
    result.export(output_path, format=format_out)

# ============================
# Giao diện ứng dụng
# ============================
class VoiceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("\U0001F3A7 Voice Silence Editor - Local")
        self.geometry("700x550")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.input_file = ""
        self.output_file = ""
        self.output_format = ctk.StringVar(value="mp3")
        self.logic_mode = ctk.StringVar(value="logic_cu")

        self.create_widgets()

    def create_widgets(self):
        ctk.CTkLabel(self, text="\U0001F6E0\ufe0f Voice Silence Editor", font=("Arial", 24)).pack(pady=10)
        ctk.CTkLabel(self, text="\U0001F4E4 Chọn file đầu vào:").pack()
        self.input_btn = ctk.CTkButton(self, text="\U0001F4C2 Duyệt file", command=self.select_input, width=160)
        self.input_btn.pack(pady=4)
        self.input_label = ctk.CTkLabel(self, text="Chưa chọn file.")
        self.input_label.pack()
        ctk.CTkLabel(self, text="\U0001F4BE Tên file xuất (không cần chọn nơi lưu):").pack(pady=(10, 0))
        self.output_name_entry = ctk.CTkEntry(self, placeholder_text="ten_file_xuat", width=200)
        self.output_name_entry.pack(pady=4)
        ctk.CTkLabel(self, text="\U0001F509 Ngưỡng dB để nhận im lặng (mặc định -45):").pack(pady=(10, 2))
        self.db_input = ctk.CTkEntry(self, placeholder_text="-45", width=100, justify="center")
        self.db_input.pack()
        ctk.CTkLabel(self, text="\U0001F4DD Chọn định dạng xuất ra:").pack(pady=(10, 0))
        self.format_select = ctk.CTkOptionMenu(self, values=["mp3", "wav"], variable=self.output_format)
        self.format_select.pack()
        ctk.CTkLabel(self, text="\U0001F916 Chọn chế độ xử lý:").pack(pady=(10, 0))
        self.logic_select = ctk.CTkOptionMenu(self, values=["logic_cu", "logic_moi"], variable=self.logic_mode)
        self.logic_select.pack()
        self.progress = ctk.CTkProgressBar(self, width=500)
        self.progress.set(0)
        self.progress.pack(pady=10)
        self.status = ctk.CTkLabel(self, text="", font=("Arial", 13))
        self.status.pack()

        self.start_btn = ctk.CTkButton(self, text="\U0001F680 BẮT ĐẦU XỬ LÝ", command=self.start_processing, width=200)
        self.start_btn.pack(pady=20)

        self.link_label = ctk.CTkLabel(self, text="", text_color="lightblue", cursor="hand2")
        self.link_label.pack()
        self.link_label.bind("<Button-1>", self.open_folder)

    def select_input(self):
        path = filedialog.askopenfilename(filetypes=[("Audio files", "*.wav *.mp3")])
        if path:
            self.input_file = path
            self.input_label.configure(text=os.path.basename(path))

    # Bỏ hàm chọn nơi lưu, không cần nữa

    def update_status(self, text, color="white"):
        self.status.configure(text=text, text_color=color)

    def start_processing(self):
        if not hasattr(self, 'input_file') or not self.input_file:
            self.update_status("\u274c Vui lòng chọn file đầu vào.", "red")
            return
        output_name = self.output_name_entry.get().strip()
        if not output_name:
            self.update_status("\u274c Vui lòng nhập tên file xuất.", "red")
            return
        import os
        input_dir = os.path.dirname(self.input_file)
        self.output_file = os.path.join(input_dir, output_name + ".mp3")
        try:
            db_thresh = int(self.db_input.get()) if self.db_input.get() else -45
        except:
            self.update_status("\u274c Ngưỡng dB phải là số nguyên!", "red")
            return
        self.update_status("\u23f3 Chuẩn bị xử lý...", "yellow")
        self.progress.set(0)
        self.link_label.configure(text="")
        thread = threading.Thread(target=self.run_processing, args=(db_thresh, self.logic_mode.get()))
        thread.start()

    def run_processing(self, db_thresh, logic_mode):
        try:
            start_time = time.time()
            process_audio(
                self.input_file,
                self.output_file,
                db_thresh,
                self.progress.set,
                self.update_status,
                self.output_format.get(),
                logic_mode
            )
            elapsed = round(time.time() - start_time, 2)
            self.update_status(f"\u2705 Đã xử lý xong! (⏱ {elapsed} giây)", "green")
            self.link_label.configure(text=self.output_file)

        except Exception as e:
            self.update_status(f"\u274c Lỗi: {e}", "red")

    def open_folder(self, event):
        if os.path.exists(self.output_file):
            folder = os.path.dirname(os.path.abspath(self.output_file))
            if sys.platform == "win32":
                subprocess.Popen(f'explorer "{folder}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

if __name__ == "__main__":
    app = VoiceApp()
    app.mainloop()
