# -*- coding: utf-8 -*-
"""
Voice Tools V3 - Smart Silence Editor
Supports Fast Mode (V2 Logic) and Smart Mode (Script-based Alignment)
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import sys
import threading
import time
from typing import Optional

# Fix FFmpeg path for Windows
from pydub.utils import which
ffmpeg_path = which("ffmpeg")
ffprobe_path = which("ffprobe")

# Hide Console on Windows (if running as .py)
import ctypes
try:
    kernel32 = ctypes.WinDLL('kernel32')
    user32 = ctypes.WinDLL('user32')
    hWnd = kernel32.GetConsoleWindow()
    if hWnd:
        user32.ShowWindow(hWnd, 0) # 0 = SW_HIDE
except:
    pass

if not ffmpeg_path:

    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    ffmpeg_dir = os.path.join(base_path, "ffmpeg", "bin")
    if os.path.exists(os.path.join(ffmpeg_dir, "ffmpeg.exe")):
        os.environ["PATH"] += os.pathsep + ffmpeg_dir

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import OUTPUT_FORMATS, DEFAULT_SILENCE_THRESH
from core.processor import process_audio_fast, process_audio_smart, get_audio_info


class VoiceApp(ctk.CTk):
    """Voice Tools Application - Smart & Fast"""
    
    def __init__(self):
        super().__init__()
        
        self.title("✨ Voice AI Editor Pro")
        self.title("✨ Voice AI Editor Pro")
        self.geometry("850x780")
        self.minsize(650, 550)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")  # Back to Blue theme
        
        # State
        self.input_file: str = ""
        self.output_format = ctk.StringVar(value="mp3")
        self.process_mode = ctk.StringVar(value="logic_v2")
        self.is_processing = False
        self._cancel_requested = False
        
        # Configure grid for split layout
        self.grid_columnconfigure(0, weight=0)  # Sidebar (fixed width)
        self.grid_columnconfigure(1, weight=1)  # Main Content (expand)
        self.grid_rowconfigure(0, weight=1)
        
        self.create_widgets()
        
    def create_widgets(self):
        """Create responsive Split Layout"""
        # === SIDEBAR (Left) ===
        sidebar = ctk.CTkFrame(self, width=320, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False) # Fixed width
        
        # === MAIN CONTENT (Right) ===
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=3) # Script expands
        main.grid_rowconfigure(3, weight=1) # Log expands
        
        # === SIDEBAR CONTENT ===
        
        # Header
        ctk.CTkLabel(sidebar, text="✨ Voice AI Pro", 
                     font=("Segoe UI", 24, "bold"), text_color="#60a5fa").pack(pady=(30, 5), padx=20, anchor="w")
        ctk.CTkLabel(sidebar, text="Smart Silence Editor V3.5", 
                     font=("Segoe UI", 12), text_color="#94a3b8").pack(pady=(0, 20), padx=20, anchor="w")
        
        # Input Section
        input_frame = ctk.CTkFrame(sidebar, fg_color="#1e293b", corner_radius=10)
        input_frame.pack(fill="x", padx=15, pady=10)
        
        self.input_btn = ctk.CTkButton(
            input_frame, text="📂 Chọn File Audio", 
            command=self.select_input, height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color="#2563eb", hover_color="#1d4ed8", corner_radius=8
        )
        self.input_btn.pack(fill="x", padx=15, pady=15)
        
        self.input_label = ctk.CTkLabel(
            input_frame, text="Chưa chọn file...", 
            text_color="#94a3b8", font=("Segoe UI", 12, "italic"), wraplength=250
        )
        self.input_label.pack(fill="x", padx=15, pady=(0, 15))

        # Settings Section
        settings_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        settings_frame.pack(fill="x", padx=15, pady=10)
        
        # Output Name
        ctk.CTkLabel(settings_frame, text="📝 Tên file xuất:", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.output_name = ctk.CTkEntry(settings_frame, height=35, placeholder_text="ten_file_xuat")
        self.output_name.pack(fill="x", pady=(5, 15))
        
        # Mode
        ctk.CTkLabel(settings_frame, text="⚙️ Chế độ:", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.mode_select = ctk.CTkOptionMenu(
            settings_frame, values=["🚀 Smart (AI)", "⚡ Fast (V2)"],
            command=self.on_mode_change, height=35,
            fg_color="#2563eb", button_color="#1d4ed8"
        )
        self.mode_select.set("🚀 Smart (AI)")
        self.mode_select.pack(fill="x", pady=(5, 15))
        
        # Model
        ctk.CTkLabel(settings_frame, text="🤖 AI Model:", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.model_size_var = ctk.StringVar(value="large-v3-turbo")
        self.model_select = ctk.CTkOptionMenu(
            settings_frame, values=["small (4x)", "medium (2x)", "large-v3-turbo (best)"],
            variable=self.model_size_var, height=35
        )
        self.model_select.pack(fill="x", pady=(5, 15))
        
        # Format
        ctk.CTkLabel(settings_frame, text="🎵 Định dạng:", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.format_select = ctk.CTkOptionMenu(
            settings_frame, values=OUTPUT_FORMATS,
            variable=self.output_format, height=35
        )
        self.format_select.pack(fill="x", pady=(5, 15))
        
        # dB Slider
        ctk.CTkLabel(settings_frame, text="🔊 Ngưỡng dB (Fast Mode):", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.db_slider = ctk.CTkSlider(settings_frame, from_=-60, to=-20, number_of_steps=40)
        self.db_slider.set(DEFAULT_SILENCE_THRESH)
        self.db_slider.pack(fill="x", pady=(5, 0))
        self.db_slider.configure(command=self.update_db_label)
        
        self.db_val_label = ctk.CTkLabel(settings_frame, text=f"{DEFAULT_SILENCE_THRESH} dB")
        self.db_val_label.pack(anchor="e")

        # Action Buttons (Bottom of Sidebar)
        actions_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        actions_frame.pack(side="bottom", fill="x", padx=10, pady=10) # Reduced padding
        
        self.start_btn = ctk.CTkButton(
            actions_frame, text="▶️ BẮT ĐẦU", command=self.start_processing,
            height=40, font=("Segoe UI", 14, "bold"), # Reduced height/font
            fg_color="#22c55e", hover_color="#16a34a", corner_radius=8
        )
        self.start_btn.pack(fill="x", pady=(0, 5))
        
        hbox = ctk.CTkFrame(actions_frame, fg_color="transparent")
        hbox.pack(fill="x", pady=0)
        
        self.cancel_btn = ctk.CTkButton(
            hbox, text="⏹️ HỦY", command=self.request_cancel,
            height=35, width=80, fg_color="#ef4444", hover_color="#dc2626", state="disabled"
        )
        self.cancel_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        self.restart_btn = ctk.CTkButton(
            hbox, text="🔄 RESET", command=self.restart_app,
            height=35, width=80, fg_color="#475569", hover_color="#334155"
        )
        self.restart_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))

        # === MAIN CONTENT ===
        
        # Script Section (Top Main)
        script_header = ctk.CTkFrame(main, fg_color="transparent")
        script_header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        ctk.CTkLabel(script_header, text="� Kịch Bản / Script", 
                     font=("Segoe UI", 16, "bold"), text_color="#60a5fa").pack(side="left")
        
        self.char_count = ctk.CTkLabel(script_header, text="0 ký tự", text_color="#94a3b8")
        self.char_count.pack(side="right")
        
        self.script_text = ctk.CTkTextbox(
            main, font=("Segoe UI", 13), activate_scrollbars=True,
            corner_radius=10, fg_color="#1e293b", border_width=1, border_color="#334155"
        )
        self.script_text.grid(row=1, column=0, sticky="nsew", pady=(0, 20))
        self.script_text.bind("<KeyRelease>", self.update_char_count)
        
        # Log Section (Bottom Main)
        log_header = ctk.CTkFrame(main, fg_color="transparent")
        log_header.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        
        ctk.CTkLabel(log_header, text="📋 Log Xử Lý", 
                     font=("Segoe UI", 14, "bold"), text_color="#cbd5e1").pack(side="left")
                     
        ctk.CTkButton(log_header, text="🗑️", width=30, height=20, 
                      command=self.clear_log, fg_color="transparent", text_color="gray").pack(side="right")

        self.log_text = ctk.CTkTextbox(
            main, font=("Consolas", 11), activate_scrollbars=True, state="disabled",
            corner_radius=10, fg_color="#0f172a", text_color="#60a5fa", border_width=1, border_color="#334155"
        )
        self.log_text.grid(row=3, column=0, sticky="nsew")

        # Progress Bar (Overlay or Bottom)
        self.progress_bar = ctk.CTkProgressBar(main, height=8)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=4, column=0, sticky="ew", pady=(15, 5))
        
        self.status_label = ctk.CTkLabel(main, text="Sẵn sàng", text_color="#94a3b8")
        self.status_label.grid(row=5, column=0, sticky="w")
        
        self.percent_label = ctk.CTkLabel(main, text="0%", font=("Segoe UI", 12, "bold"))
        self.percent_label.grid(row=5, column=0, sticky="e")
        
        self.output_link_label = ctk.CTkLabel(main, text="", text_color="#60a5fa", cursor="hand2")
        self.output_link_label.grid(row=6, column=0, sticky="w", pady=(0, 10))
        self.output_link_label.bind("<Button-1>", self.open_output_folder)

        
    def on_mode_change(self, mode):
        """Toggle dB slider based on mode"""
        if "Smart" in mode:
            self.db_slider.configure(state="disabled")
            self.mode_info.configure(text_color="#60a5fa") # Blueish
        else:
            self.db_slider.configure(state="normal")
            self.mode_info.configure(text_color="gray")

    def log(self, message: str):
        """Add a message to the log panel"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")  # Auto-scroll to bottom
        self.log_text.configure(state="disabled")
        self.update_idletasks()
    
    def clear_log(self):
        """Clear the log panel"""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        

    def update_db_label(self, value):
        self.db_val_label.configure(text=f"{int(value)} dB")
        
    def update_status(self, text: str, percent: int = -1, color: str = "gray"):
        self.status_label.configure(text=text, text_color=color)
        if percent >= 0:
            self.progress_bar.set(percent / 100)
            self.percent_label.configure(text=f"{percent}%")
        self.update_idletasks()
        
    def request_cancel(self):
        """Request to cancel ongoing process"""
        if self.is_processing:
            self._cancel_requested = True
            self.update_status("⌛ Đang dừng... Vui lòng đợi", color="yellow")
            self.cancel_btn.configure(state="disabled")

    def update_char_count(self, event=None):
        """Update character count label"""
        text = self.script_text.get("1.0", "end-1c")
        count = len(text)
        self.char_count.configure(text=f"{count:,} ký tự")

    def select_input(self):
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.wav *.mp3 *.m4a *.flac"), ("All", "*.*")])
        if path:
            self.input_file = path
            filename = os.path.basename(path)
            self.input_label.configure(text=filename, text_color="white")
            
            name_without_ext = os.path.splitext(filename)[0]
            self.output_name.delete(0, "end")
            self.output_name.insert(0, f"{name_without_ext}_smart")
            
            try:
                info = get_audio_info(path)
                self.update_status(f"📊 Duration: {info['duration_sec']:.1f}s", color="white")
            except: pass
            
    def start_processing(self):
        if not self.input_file:
            self.update_status("❌ Vui lòng chọn file audio!", color="#ef4444")
            return
            
        output_name = self.output_name.get().strip()
        if not output_name:
            self.update_status("❌ Vui lòng nhập tên file xuất!", color="#ef4444")
            return
            
        mode = self.mode_select.get()
        script = self.script_text.get("1.0", "end-1c").strip()
        
        if "Smart" in mode and not script:
            self.update_status("❌ Vui lòng nhập kịch bản cho Smart Mode!", color="#ef4444")
            return
            
        # UI Setup
        self.is_processing = True
        self._cancel_requested = False
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.output_link_label.configure(text="")
        
        # Run in thread
        input_dir = os.path.dirname(self.input_file)
        fmt = self.output_format.get()
        output_path = os.path.join(input_dir, f"{output_name}.{fmt}")
        
        thread = threading.Thread(target=self.run_pipeline, args=(output_path, mode, script))
        thread.daemon = True
        thread.start()
        
    def run_pipeline(self, output_path: str, mode: str, script: str):
        try:
            start_time = time.time()
            db_thresh = int(self.db_slider.get())
            
            def cb(percent, status):
                self.update_status(status, percent, "white")
                
            def cancel_check():
                return self._cancel_requested
            
            def log_callback(msg):
                """Callback to send processor logs to GUI"""
                self.log(msg)
            
            # Clear log and start
            self.clear_log()
            self.log(f"🚀 Bắt đầu xử lý: {os.path.basename(self.input_file)}")
            self.log(f"📊 Mode: {mode}")
            
            if "Smart" in mode:
                # Extract model size from dropdown value
                model_choice = self.model_size_var.get()
                model_size = model_choice.split(" ")[0]  # "medium (2x speed)" -> "medium"
                
                self.log(f"📝 Script: {len(script)} ký tự")
                self.log(f"🤖 Model: {model_size}")
                process_audio_smart(
                    self.input_file, output_path, script, 
                    silence_thresh=db_thresh, progress_callback=cb, 
                    cancel_flag=cancel_check, log_callback=log_callback,
                    model_size=model_size
                )
            else:
                process_audio_fast(
                    self.input_file, output_path,
                    silence_thresh=db_thresh, progress_callback=cb,
                    cancel_flag=cancel_check
                )
                
            elapsed = round(time.time() - start_time, 1)
            self.update_status(f"✅ Thành công! (Time: {elapsed}s)", 100, "#34d399")
            self.output_link_label.configure(text="📁 Mở thư mục")
            self.output_link_label.output_path = output_path
            
            # Popup notification
            messagebox.showinfo("Thành công", f"Đã xử lý xong!\nThời gian: {elapsed}s\nFile: {os.path.basename(output_path)}")
            
        except InterruptedError:
            self.update_status("🛑 Đã hủy bởi người dùng", color="#ef4444")
        except Exception as e:
            self.update_status(f"❌ Lỗi: {str(e)[:50]}", color="#ef4444")
            import traceback
            traceback.print_exc()
        finally:
            self.is_processing = False
            self.start_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")
            
    def open_output_folder(self, event=None):
        if hasattr(self.output_link_label, 'output_path'):
            folder = os.path.dirname(self.output_link_label.output_path)
            if os.path.exists(folder):
                os.startfile(folder)
    
    def restart_app(self):
        """Restarts the application"""
        self.destroy() # Close current window
        import subprocess
        python = sys.executable
        # Open new process independent of this one
        subprocess.Popen([python, *sys.argv])
        sys.exit()

if __name__ == "__main__":
    app = VoiceApp()
    app.mainloop()
