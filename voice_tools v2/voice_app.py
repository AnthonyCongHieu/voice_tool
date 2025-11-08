import customtkinter as ctk  # type: ignore[import]
from tkinter import filedialog
from pydub import AudioSegment, silence  # type: ignore[import]
from pydub.audio_segment import AudioSegment
from pydub.silence import detect_silence
import sys
import os
import random
import time
import threading
import subprocess

from typing import Any, Callable, List, Optional, Tuple, cast

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
from pydub.utils import which  # type: ignore[import]
# provide typing for which to satisfy Pylance
which = cast(Callable[[str], Optional[str]], which)

# Type definitions
SilenceRange = Tuple[int, int]
ProgressCb = Callable[[int], None]


def find_ffmpeg() -> Tuple[str, str]:
    # 1. Ki?m tra bi?n m�i tru?ng PATH
    ffmpeg_in_path = which("ffmpeg")
    ffprobe_in_path = which("ffprobe")
    if ffmpeg_in_path and ffprobe_in_path:
        return ffmpeg_in_path, ffprobe_in_path

    # 2. Ki?m tra thu m?c ffmpeg n?i b? (d�ng khi d�ng g�i exe)
    meipass: Optional[str] = getattr(sys, '_MEIPASS', None)  # type: ignore[attr-defined]
    base_path: str = meipass if meipass else os.path.abspath(".")

    ffmpeg_dir = os.path.join(base_path, "ffmpeg", "bin")
    ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    ffprobe_exe = os.path.join(ffmpeg_dir, "ffprobe.exe")
    if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
        os.environ["PATH"] += os.pathsep + ffmpeg_dir
        return ffmpeg_exe, ffprobe_exe

    # 3. B�o l?i n?u kh�ng t�m th?y
    raise FileNotFoundError("Kh�ng t�m th?y ffmpeg.exe ho?c ffprobe.exe! Vui l�ng ki?m tra l?i thu m?c ffmpeg.")

# Sử dụng hàm mới
ffmpeg_path, ffprobe_path = find_ffmpeg()
AudioSegment.converter = ffmpeg_path  # type: ignore[attr-defined]
AudioSegment.ffprobe   = ffprobe_path  # type: ignore[attr-defined]

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

def process_audio(
    input_path: str,
    output_path: str,
    silence_thresh: int,
    progress_callback: ProgressCb | None,
    text_callback: Callable[[str], None],
    format_out: str,
    logic_mode: str,
) -> AudioSegment:
    audio: AudioSegment = cast(AudioSegment, AudioSegment.from_file(input_path))
    silence_ranges: List[SilenceRange] = [
        (int(s), int(e)) for s, e in detect_silence(
            audio_segment=audio,
            min_silence_len=FRAME_MS * 4,
            silence_thresh=silence_thresh,
            seek_step=1
        )
    ]

    result: AudioSegment = AudioSegment.empty()
    last_end: int = 0
    total: int = len(silence_ranges)

    for i, (start, end) in enumerate(silence_ranges):
        silence_len: int = end - start
        frame_len: int = silence_len // FRAME_MS

        if start > last_end:
            result += audio[last_end:start]

        if logic_mode == "logic_v2":
            # Giua cau: 0-10 frame giu nguyen
            if frame_len <= 10:
                result += audio[start:end]
            # Giua cau: tren 10 den 20 -> giam xuong random 8-10 frame
            elif 11 <= frame_len <= 20:
                target_frames = random.randint(8, 10)
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
            # Cuoi cau: chi cat neu > 24 frame, dua ve 24 frame
            elif frame_len > 24:
                target_ms = PARA_CUT_MS
                head, tail = 200, 100
                start_head = min(end, start + head)
                end_tail = max(start, end - tail)
                used_head = start_head - start
                used_tail = end - end_tail
                mid_sil = max(0, target_ms - used_head - used_tail)
                result += audio[start:start_head]
                if mid_sil > 0:
                    result += AudioSegment.silent(duration=mid_sil)
                result += audio[end_tail:end]
            else:
                # 21-24 frame: giu nguyen
                result += audio[start:end]
        else:
            # logic_cu (giu lai de tuong thich)
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
        percent = round((i + 1) / total * 100) if total else 100
        if progress_callback:
            progress_callback(percent)
        text_callback(f"\u23f3 Dang x? ly... {percent}%")

    result += audio[last_end:]
    result.export(out_f=output_path, format=format_out)  # pyright: ignore[reportUnknownMemberType]
    return result

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

        self.input_file: str = ""
        self.output_file: str = ""
        self.output_format: Any = ctk.StringVar(value="mp3")
        self.logic_mode: Any = ctk.StringVar(value="logic_v2")

        self.create_widgets()

    def create_widgets(self):
        ctk.CTkLabel(self, text="\U0001F6E0\ufe0f Voice Silence Editor", font=("Arial", 24)).pack(pady=10)  # type: ignore[reportUnknownMemberType]
        ctk.CTkLabel(self, text="\U0001F4E4 Chọn file đầu vào:").pack()  # type: ignore[reportUnknownMemberType]
        self.input_btn: Any = ctk.CTkButton(self, text="\U0001F4C2 Duyệt file", command=self.select_input, width=160)
        self.input_btn.pack(pady=4)  # type: ignore[reportUnknownMemberType]
        self.input_label: Any = ctk.CTkLabel(self, text="Chưa chọn file.")
        self.input_label.pack()  # type: ignore[reportUnknownMemberType]
        ctk.CTkLabel(self, text="\U0001F4BE Tên file xuất (không cần chọn nơi lưu):").pack(pady=(10, 0))  # type: ignore[reportUnknownMemberType]
        self.output_name_entry: Any = ctk.CTkEntry(self, placeholder_text="ten_file_xuat", width=200)
        self.output_name_entry.pack(pady=4)  # type: ignore[reportUnknownMemberType]
        ctk.CTkLabel(self, text="\U0001F509 Ngưỡng dB để nhận im lặng (mặc định -45):").pack(pady=(10, 2))  # type: ignore[reportUnknownMemberType]
        self.db_input: Any = ctk.CTkEntry(self, placeholder_text="-45", width=100, justify="center")
        self.db_input.pack()  # type: ignore[reportUnknownMemberType]
        ctk.CTkLabel(self, text="\U0001F4DD Chọn định dạng xuất ra:").pack(pady=(10, 0))  # type: ignore[reportUnknownMemberType]
        self.format_select: Any = ctk.CTkOptionMenu(self, values=["mp3", "wav"], variable=self.output_format)
        self.format_select.pack()  # type: ignore[reportUnknownMemberType]
        ctk.CTkLabel(self, text="\U0001F916 Chọn chế độ xử lý:").pack(pady=(10, 0))  # type: ignore[reportUnknownMemberType]
        self.logic_select: Any = ctk.CTkOptionMenu(self, values=["logic_cu", "logic_v2"], variable=self.logic_mode)
        self.logic_select.pack()  # type: ignore[reportUnknownMemberType]
        self.progress: Any = ctk.CTkProgressBar(self, width=500)
        self.progress.set(0)  # type: ignore[reportUnknownMemberType]
        self.progress.pack(pady=10)  # type: ignore[reportUnknownMemberType]
        self.status: Any = ctk.CTkLabel(self, text="", font=("Arial", 13))
        self.status.pack()  # type: ignore[reportUnknownMemberType]

        self.start_btn: Any = ctk.CTkButton(self, text="\U0001F680 BẮT ĐẦU XỬ LÝ", command=self.start_processing, width=200)
        self.start_btn.pack(pady=20)  # type: ignore[reportUnknownMemberType]

        self.link_label: Any = ctk.CTkLabel(self, text="", text_color="lightblue", cursor="hand2")
        self.link_label.pack()  # type: ignore[reportUnknownMemberType]
        self.link_label.bind("<Button-1>", self.open_folder)  # type: ignore[reportUnknownMemberType]

    def select_input(self):
        path = filedialog.askopenfilename(filetypes=[("Audio files", "*.wav *.mp3")])
        if path:
            self.input_file = path
            self.input_label.configure(text=os.path.basename(path))  # type: ignore[reportUnknownMemberType]

    # Bỏ hàm chọn nơi lưu, không cần nữa

    def update_status(self, text: str, color: str = "white"):
        self.status.configure(text=text, text_color=color)  # type: ignore[reportUnknownMemberType]

    def start_processing(self):
        if not hasattr(self, 'input_file') or not self.input_file:
            self.update_status("\u274c Vui lòng chọn file đầu vào.", "red")
            return
        output_name = self.output_name_entry.get().strip()  # type: ignore[reportUnknownMemberType]
        if not output_name:
            self.update_status("\u274c Vui lòng nhập tên file xuất.", "red")
            return
        input_dir = os.path.dirname(self.input_file)
        self.output_file = os.path.join(input_dir, output_name + ".mp3")
        try:
            db_thresh = int(self.db_input.get()) if self.db_input.get() else -45  # type: ignore[reportUnknownMemberType]
        except:
            self.update_status("\u274c Ngưỡng dB phải là số nguyên!", "red")
            return
        self.update_status("\u23f3 Chuẩn bị xử lý...", "yellow")
        self.progress.set(0)  # type: ignore[reportUnknownMemberType]
        self.link_label.configure(text="")  # type: ignore[reportUnknownMemberType]
        def on_progress(v: int) -> None:
            self.progress.set(v / 100.0)  # type: ignore[reportUnknownMemberType]
        thread = threading.Thread(target=self.run_processing, args=(db_thresh, self.logic_mode.get(), on_progress))
        thread.start()

    def run_processing(self, db_thresh: int, logic_mode: str, progress_callback: ProgressCb):
        try:
            start_time = time.time()
            process_audio(
                self.input_file,
                self.output_file,
                db_thresh,
                progress_callback,
                self.update_status,
                self.output_format.get(),  # type: ignore[reportUnknownMemberType]
                logic_mode
            )
            elapsed = round(time.time() - start_time, 2)
            self.update_status(f"\u2705 Đã xử lý xong! (⏱ {elapsed} giây)", "green")
            self.link_label.configure(text=self.output_file)  # type: ignore[reportUnknownMemberType]

        except Exception as e:
            self.update_status(f"\u274c Lỗi: {e}", "red")

    def open_folder(self, event: Any):
        if os.path.exists(self.output_file):
            folder = os.path.dirname(os.path.abspath(self.output_file))
            if sys.platform == "win32":
                subprocess.Popen(f'explorer "{folder}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

if __name__ == "__main__":
    app: Any = VoiceApp()
    app.mainloop()  # type: ignore[reportUnknownMemberType]








