"""Subtitle/script consistency review and visual preview helpers."""
from __future__ import annotations
import difflib
import re
import shutil
import subprocess
from pathlib import Path

def _subtitle_text(path: str) -> str:
    lines = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.isdigit() or "-->" in stripped:
            continue
        lines.append(stripped)
    return " ".join(lines)

def _normalized(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))

def build_review_report(subtitle_path: str, *, script_path: str | None = None, max_diff_ratio: float = 0.12) -> dict:
    subtitle = _normalized(_subtitle_text(subtitle_path))
    if script_path is None:
        return {"status": "skipped", "diff_ratio": None, "subtitle_path": subtitle_path}
    script = _normalized(Path(script_path).read_text(encoding="utf-8-sig"))
    ratio = 1.0 - difflib.SequenceMatcher(None, subtitle.split(), script.split()).ratio()
    return {"status": "pass" if ratio <= max_diff_ratio else "fail",
            "diff_ratio": ratio, "max_diff_ratio": max_diff_ratio,
            "subtitle_path": subtitle_path, "script_path": script_path}

def ensure_subtitle_consistency(subtitle_path: str, script_path: str, *, max_diff_ratio: float = 0.12) -> dict:
    report = build_review_report(subtitle_path, script_path=script_path, max_diff_ratio=max_diff_ratio)
    if report["status"] != "pass":
        raise RuntimeError(f"Subtitle/script review failed: difference ratio {report['diff_ratio']:.3f} exceeds {max_diff_ratio:.3f}")
    return report

def render_preview_frame(video_path: str, subtitle_path: str, *, at: str = "00:00:00.000", output_path: str) -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to render a preview frame")
    subtitle_filter_path = str(Path(subtitle_path).resolve()).replace("\\", "/").replace("'", "\\'")
    command = [ffmpeg, "-y", "-ss", at, "-i", video_path, "-vf",
               f"subtitles='{subtitle_filter_path}'", "-frames:v", "1", output_path]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg preview failed: {result.stderr}")
    return output_path
