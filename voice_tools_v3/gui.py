"""Simple GUI for voice_tools v3.

Allows users to select an audio file, paste a Vietnamese script, and
export a single audio file with normalized pauses.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

if __package__ is None or __package__ == "":  # allow running as script
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from voice_tools_v3 import (
    audio_io,
    align_engine,
    config,
    exporter,
    planner,
    punctuation,
    utils,
)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("voice_tools v3")

        self.audio_path = tk.StringVar()
        self.out_path = tk.StringVar()
        self.format_var = tk.StringVar(value="mp3")
        self.crossfade_var = tk.StringVar(value="3")
        self.status_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self) -> None:
        padding = {"padx": 5, "pady": 5}

        tk.Label(self, text="Audio vào").grid(row=0, column=0, sticky="e", **padding)
        tk.Entry(self, textvariable=self.audio_path, width=40).grid(row=0, column=1, **padding)
        tk.Button(self, text="Chọn", command=self.browse_audio).grid(row=0, column=2, **padding)

        tk.Label(self, text="Kịch bản").grid(row=1, column=0, sticky="ne", **padding)
        self.script_box = tk.Text(self, width=50, height=10)
        self.script_box.grid(row=1, column=1, columnspan=2, **padding)

        tk.Label(self, text="Định dạng").grid(row=2, column=0, sticky="e", **padding)
        fmt_menu = tk.OptionMenu(self, self.format_var, "mp3", "wav", command=self._format_changed)
        fmt_menu.grid(row=2, column=1, sticky="w", **padding)

        tk.Label(self, text="File xuất").grid(row=3, column=0, sticky="e", **padding)
        tk.Entry(self, textvariable=self.out_path, width=40).grid(row=3, column=1, **padding)
        tk.Button(self, text="Lưu", command=self.browse_output).grid(row=3, column=2, **padding)

        tk.Label(self, text="Crossfade ms").grid(row=4, column=0, sticky="e", **padding)
        tk.Entry(self, textvariable=self.crossfade_var, width=5).grid(row=4, column=1, sticky="w", **padding)

        tk.Button(self, text="Bắt đầu", command=self.run).grid(row=5, column=1, **padding)
        tk.Label(self, textvariable=self.status_var).grid(row=6, column=0, columnspan=3, **padding)

    def browse_audio(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.wav *.mp3 *.m4a *.flac"), ("All", "*.*")])
        if path:
            self.audio_path.set(path)
            base, _ = os.path.splitext(path)
            self.out_path.set(base + "_out." + self.format_var.get())

    def browse_output(self) -> None:
        fmt = self.format_var.get()
        path = filedialog.asksaveasfilename(defaultextension="." + fmt, filetypes=[(fmt.upper(), f"*.{fmt}")])
        if path:
            self.out_path.set(path)

    def _format_changed(self, *_: object) -> None:
        if self.out_path.get():
            base, _ = os.path.splitext(self.out_path.get())
            self.out_path.set(base + "." + self.format_var.get())

    def run(self) -> None:
        audio = self.audio_path.get()
        script_text = self.script_box.get("1.0", tk.END).strip()
        fmt = self.format_var.get()
        out_path = self.out_path.get()
        crossfade_ms = int(self.crossfade_var.get() or 0)

        if not audio or not os.path.exists(audio):
            messagebox.showerror("Lỗi", "Chưa chọn file audio")
            return
        if not script_text:
            messagebox.showerror("Lỗi", "Chưa nhập kịch bản")
            return
        if not out_path:
            base, _ = os.path.splitext(audio)
            out_path = base + "_out." + fmt
            self.out_path.set(out_path)

        self.status_var.set("Đang xử lý...")

        def task() -> None:
            try:
                punct_map = utils.load_punct_map("default", config.DEFAULT_PUNCT_SILENCE_MS)
                target_ms = config.midpoint_targets(config.DEFAULT_TARGET_SILENCE_MS)
                master_wav = audio_io.to_mono_48k(audio)
                words = align_engine.align_with_script(master_wav, script_text)
                anchors = punctuation.sentence_anchors(words, script_text)
                plan = planner.build_plan(words, anchors, target_ms, punct_map)
                exporter.render_plan_with_ffmpeg(master_wav, plan, out_path, crossfade_ms, fmt)
                self.status_var.set(f"Đã xuất: {out_path}")
            except Exception as e:  # pragma: no cover - GUI error surface
                self.status_var.set(f"Lỗi: {e}")

        threading.Thread(target=task, daemon=True).start()


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
