"""Export plan to a single audio file using ffmpeg."""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import List

from .planner import PlanItem


def _ffmpeg(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def render_plan_with_ffmpeg(
    master_wav: str,
    plan: List[PlanItem],
    out_path: str,
    crossfade_ms: int = 3,
    out_format: str = "wav",
) -> None:
    """Render plan to output file using ffmpeg concat demuxer."""
    with tempfile.TemporaryDirectory() as tmp:
        concat_lines: List[str] = []
        speech_idx = 0
        silence_idx = 0
        for item in plan:
            if item.kind == "speech":
                if item.end_ms <= item.start_ms:
                    continue
                speech_idx += 1
                seg_path = os.path.join(tmp, f"speech_{speech_idx:03d}.wav")
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    master_wav,
                    "-ss",
                    f"{item.start_ms/1000:.3f}",
                    "-to",
                    f"{item.end_ms/1000:.3f}",
                    "-acodec",
                    "pcm_s16le",
                ]
                if crossfade_ms > 0 and item.dur_ms > 0:
                    fade_out_start = max(item.dur_ms - crossfade_ms, 0) / 1000
                    fade = (
                        f"afade=t=in:st=0:d={crossfade_ms/1000:.3f},"
                        f"afade=t=out:st={fade_out_start:.3f}:d={crossfade_ms/1000:.3f}"
                    )
                    cmd.extend(["-af", fade])
                cmd.append(seg_path)
                _ffmpeg(cmd)
                concat_lines.append(f"file '{seg_path}'\n")
            else:
                if item.dur_ms <= 0:
                    continue
                silence_idx += 1
                sil_path = os.path.join(tmp, f"sil_{silence_idx:03d}.wav")
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"anullsrc=r=48000:cl=mono",
                    "-t",
                    f"{item.dur_ms/1000:.3f}",
                    "-acodec",
                    "pcm_s16le",
                    sil_path,
                ]
                _ffmpeg(cmd)
                concat_lines.append(f"file '{sil_path}'\n")

        concat_path = os.path.join(tmp, "concat.txt")
        with open(concat_path, "w", encoding="utf-8") as f:
            f.writelines(concat_lines)

        temp_out = os.path.join(tmp, "output.wav")
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_path,
            "-c:a",
            "pcm_s16le",
            temp_out,
        ]
        _ffmpeg(cmd)

        if out_format.lower() == "mp3":
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                temp_out,
                "-c:a",
                "libmp3lame",
                "-q:a",
                "2",
                out_path,
            ]
            _ffmpeg(cmd)
        else:
            os.replace(temp_out, out_path)
