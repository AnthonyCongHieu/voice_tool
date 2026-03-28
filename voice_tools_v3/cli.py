"""Command line interface for voice_tools_v3."""

from __future__ import annotations

import argparse
import os
from typing import List

from . import config, audio_io, align_engine, punctuation, planner, exporter, utils


def _read_script(script_arg: str) -> str:
    if os.path.exists(script_arg):
        with open(script_arg, "r", encoding="utf-8") as f:
            return f.read()
    return script_arg


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Normalize pauses in Vietnamese speech recordings.")
    parser.add_argument("--audio", required=True, help="Input audio file")
    parser.add_argument("--script", required=True, help="Path to script text or the text itself")
    parser.add_argument("--out", required=True, help="Output file path")
    parser.add_argument("--format", default="mp3", choices=["wav", "mp3"], help="Output format")
    parser.add_argument("--punct-map", default="default", help="Punctuation map YAML/JSON or 'default'")
    parser.add_argument("--crossfade-ms", type=int, default=3, help="Crossfade milliseconds (0 to disable)")
    args = parser.parse_args(argv)

    script_text = _read_script(args.script)

    punct_map = utils.load_punct_map(args.punct_map, config.DEFAULT_PUNCT_SILENCE_MS)
    target_ms = config.midpoint_targets(config.DEFAULT_TARGET_SILENCE_MS)

    master_wav = audio_io.to_mono_48k(args.audio)
    words = align_engine.align_with_script(master_wav, script_text)
    anchors = punctuation.sentence_anchors(words, script_text)
    plan = planner.build_plan(words, anchors, target_ms, punct_map)

    out_path = args.out
    if not os.path.splitext(out_path)[1]:
        out_path += f".{args.format}"

    exporter.render_plan_with_ffmpeg(master_wav, plan, out_path, args.crossfade_ms, args.format)
    print(f"Output written to {out_path}")


if __name__ == "__main__":
    main()
