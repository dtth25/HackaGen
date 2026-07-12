"""Assembles a narrated MP4 from a VidOutput script: per-scene Vietnamese TTS (edge-tts) +
a text-minimal still frame (Pillow), muxed into a clip (ffmpeg), then concatenated into the
final video. Heavy/optional libs (edge_tts, imageio_ffmpeg, PIL) are imported lazily inside
functions, matching the fitz/pptx pattern in generator.py, so the app still imports cleanly
before `uv sync` has pulled these in."""

import asyncio
import logging
import os
import re
import shutil
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional

from app.schemas.generator_output import VidOutput, VidScene
from app.services.pdf_utils import get_vietnamese_ttf_path, prepare_pdf_plain_text

logger = logging.getLogger(__name__)

# Mirrors the frontend's always-dark `stage-*` tokens (globals.css) so rendered frames match
# the player letterbox they'll be viewed in.
STAGE_BG = (11, 15, 25)  # #0b0f19
STAGE_FOREGROUND = (226, 232, 240)  # #e2e8f0
STAGE_ACCENT = (251, 191, 36)  # #fbbf24
STAGE_MUTED = (100, 116, 139)  # slate-500, for the small scene counter

# Accent rotates per scene (bar, keyword line) so a multi-scene video doesn't look like the
# same slide repeated — all chosen to read cleanly on the dark stage background.
SCENE_ACCENT_PALETTE = [
    (251, 191, 36),  # amber-400 (STAGE_ACCENT)
    (56, 189, 248),  # sky-400
    (52, 211, 153),  # emerald-400
    (167, 139, 250),  # violet-400
    (251, 113, 133),  # rose-400
]


def _scene_accent(idx: int) -> tuple:
    return SCENE_ACCENT_PALETTE[(idx - 1) % len(SCENE_ACCENT_PALETTE)]

# `narration` = target words per scene. Real video length = TTS reading time of the
# narration (on-screen text is minimal), so scene COUNT alone never controlled duration —
# every format produced ~2-4 short sentences/scene (~50 words) and so landed at ~2 min
# regardless of the picked mode. Vietnamese edge-tts reads ~140-150 wpm (~2.4 words/sec),
# so these word targets are what actually hit each format's stated minutes.
FORMAT_SPECS: Dict[str, Dict[str, Any]] = {
    "standard": {"width": 1280, "height": 720, "scenes": (8, 10), "label": "Tiêu chuẩn", "target": "5-7 phút", "narration": (95, 130)},
    "overview": {"width": 1280, "height": 720, "scenes": (5, 6), "label": "Tổng quan", "target": "2-3 phút", "narration": (65, 90)},
    "shorts": {"width": 720, "height": 1280, "scenes": (4, 5), "label": "Shorts", "target": "30-60 giây", "narration": (20, 30)},
}

VOICE_MAP = {
    "female": "vi-VN-HoaiMyNeural",
    "male": "vi-VN-NamMinhNeural",
}


class VideoRenderError(Exception):
    """Raised when TTS synthesis or ffmpeg rendering/concat fails."""


def resolve_format(fmt: Optional[str]) -> Dict[str, Any]:
    return FORMAT_SPECS.get((fmt or "standard").strip().lower(), FORMAT_SPECS["standard"])


def resolve_voice(voice: Optional[str]) -> str:
    return VOICE_MAP.get((voice or "female").strip().lower(), VOICE_MAP["female"])


def scene_count_hint(fmt: Optional[str]) -> str:
    lo, hi = resolve_format(fmt)["scenes"]
    return f"{lo}-{hi} phân cảnh"


def narration_hint(fmt: Optional[str]) -> str:
    """Per-scene narration length target for the vid prompt — this, not scene count, is what
    makes the finished video actually hit the format's stated duration (see FORMAT_SPECS)."""
    spec = resolve_format(fmt)
    lo, hi = spec["narration"]
    return f"khoảng {lo}-{hi} từ mỗi phân cảnh (để tổng thời lượng đạt mục tiêu {spec['target']})"


def _get_ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _run_ffmpeg(cmd: List[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise VideoRenderError(f"ffmpeg lỗi: {result.stderr[-2000:]}")


def _probe_duration(path: str) -> float:
    """Fallback duration probe (no WordBoundary cues available) via ffmpeg's own stderr,
    since imageio-ffmpeg only bundles the ffmpeg binary, not ffprobe."""
    result = subprocess.run([_get_ffmpeg(), "-i", path], capture_output=True, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        return 3.0
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def _estimate_spoken_duration(text: str) -> float:
    """Rough spoken-duration estimate (~150 wpm) — only used by the offline test fallback,
    where there's no real TTS audio to measure."""
    words = len(text.split())
    return max(1.0, words / 2.5)


def _synthesize_silence(duration: float, mp3_path: str) -> None:
    """Generate a silent placeholder track via ffmpeg's lavfi source — no network involved.
    Used only under PYTEST_CURRENT_TEST so the render/mux/concat pipeline stays testable
    without hitting the real edge-tts endpoint (mirrors LLMService's own test/mock-mode guard)."""
    _run_ffmpeg(
        [
            _get_ffmpeg(), "-y",
            "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", str(duration),
            "-q:a", "9",
            mp3_path,
        ]
    )


def _synthesize_narration(text: str, voice_id: str, mp3_path: str) -> List[Dict[str, Any]]:
    """Generate narration audio via edge-tts and collect word-boundary cues (used to build
    vid.srt timing) as a side effect of the same streaming call."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        _synthesize_silence(_estimate_spoken_duration(text), mp3_path)
        return []

    import edge_tts

    async def _run() -> List[Dict[str, Any]]:
        communicate = edge_tts.Communicate(text, voice_id)
        cues: List[Dict[str, Any]] = []
        with open(mp3_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    cues.append(
                        {
                            "start": chunk["offset"] / 1e7,
                            "duration": chunk["duration"] / 1e7,
                            "text": chunk["text"],
                        }
                    )
        return cues

    # edge-tts talks to an unofficial Microsoft endpoint that intermittently rejects the
    # WebSocket handshake (documented upstream flakiness) — a couple of quick retries clears
    # most of these without surfacing a hard error for what is really a transient hiccup.
    attempts = 3
    last_error: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            return asyncio.run(_run())
        except Exception as e:
            last_error = e
            logger.warning(f"edge-tts attempt {attempt}/{attempts} failed: {e}")
            if attempt < attempts:
                time.sleep(1.5)
    raise VideoRenderError(f"Lỗi tổng hợp giọng đọc (TTS): {last_error}") from last_error


def _cues_duration(cues: List[Dict[str, Any]]) -> float:
    if not cues:
        return 0.0
    last = cues[-1]
    return last["start"] + last["duration"]


def _wrap_text(draw: Any, text: str, font: Any, max_width: int) -> List[str]:
    words = text.split()
    if not words:
        return []
    lines: List[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_scene_frame(scene: VidScene, idx: int, total: int, width: int, height: int, out_path: str) -> None:
    """Render a text-light still frame: heading, optional short keyword line, and up to a few
    keyword bullets, on the always-dark stage palette. Narration (spoken via TTS) still
    carries the real content — this just gives the eye a bit more to track. Alternates
    centered/left-aligned layout and rotates the accent color per scene (_scene_accent) so a
    multi-scene video doesn't look like the same slide repeated."""
    from PIL import Image, ImageDraw, ImageFont

    ttf_path = get_vietnamese_ttf_path()
    heading = prepare_pdf_plain_text(scene.title) or f"Phần {idx}"
    subtext = prepare_pdf_plain_text(scene.on_screen_text or "")
    bullets = [prepare_pdf_plain_text(kp) for kp in (scene.key_points or []) if kp and kp.strip()]
    accent = _scene_accent(idx)
    left_aligned = idx % 2 == 0

    img = Image.new("RGB", (width, height), STAGE_BG)
    draw = ImageDraw.Draw(img)

    bar_w = max(6, width // 160)
    draw.rectangle([0, 0, bar_w, height], fill=accent)

    heading_size = max(36, width // 16)
    sub_size = max(20, width // 32)
    bullet_size = max(18, width // 38)
    heading_font = ImageFont.truetype(ttf_path, heading_size) if ttf_path else ImageFont.load_default()
    sub_font = ImageFont.truetype(ttf_path, sub_size) if ttf_path else ImageFont.load_default()
    bullet_font = ImageFont.truetype(ttf_path, bullet_size) if ttf_path else ImageFont.load_default()

    max_text_width = int(width * (0.62 if left_aligned else 0.78))
    left_margin = int(width * 0.12)

    heading_lines = _wrap_text(draw, heading, heading_font, max_text_width)
    sub_lines = _wrap_text(draw, subtext, sub_font, max_text_width) if subtext else []
    bullet_lines: List[str] = []
    for bp in bullets[:3]:
        bullet_lines.extend(_wrap_text(draw, f"• {bp}", bullet_font, max_text_width))

    line_gap = int(heading_size * 0.25)
    heading_line_h = heading_size + line_gap
    sub_line_h = sub_size + line_gap // 2
    bullet_line_h = bullet_size + line_gap // 2

    total_h = len(heading_lines) * heading_line_h
    if sub_lines:
        total_h += sub_line_h // 2 + len(sub_lines) * sub_line_h
    if bullet_lines:
        total_h += int(bullet_line_h * 0.9) + len(bullet_lines) * bullet_line_h
    y = (height - total_h) // 2

    def _draw_line(text: str, font: Any, fill: tuple, y_pos: int) -> None:
        w = draw.textlength(text, font=font)
        x = left_margin if left_aligned else (width - w) / 2
        draw.text((x, y_pos), text, font=font, fill=fill)

    for line in heading_lines:
        _draw_line(line, heading_font, STAGE_FOREGROUND, y)
        y += heading_line_h

    if sub_lines:
        y += sub_line_h // 2
        for line in sub_lines:
            _draw_line(line, sub_font, accent, y)
            y += sub_line_h

    if bullet_lines:
        y += int(bullet_line_h * 0.9)
        for line in bullet_lines:
            _draw_line(line, bullet_font, STAGE_FOREGROUND, y)
            y += bullet_line_h

    counter_font = ImageFont.truetype(ttf_path, max(16, width // 48)) if ttf_path else ImageFont.load_default()
    counter_text = f"{idx} / {total}"
    cw = draw.textlength(counter_text, font=counter_font)
    draw.text((width - cw - 24, height - 24 - counter_font.size), counter_text, font=counter_font, fill=STAGE_MUTED)

    img.save(out_path, "PNG")


def build_scene_clip(png_path: str, mp3_path: str, width: int, height: int, out_path: str, duration: float) -> None:
    """Mux a looped still image with its narration track into a single scene clip, adding a
    slow zoompan (subtle Ken-Burns drift) and a short fade in/out so scenes read as motion
    graphics rather than a static slideshow. All scene clips share identical encode params so
    `concat_clips` can fast-path with `-c copy`."""
    fps = 30
    total_frames = max(1, round(duration * fps))
    fade_dur = min(0.4, duration / 4)
    fade_out_start = max(0.0, duration - fade_dur)
    vf = (
        f"zoompan=z='min(zoom+0.0006,1.05)':d={total_frames}:s={width}x{height}:fps={fps},"
        f"fade=t=in:st=0:d={fade_dur:.2f},"
        f"fade=t=out:st={fade_out_start:.2f}:d={fade_dur:.2f}"
    )
    _run_ffmpeg(
        [
            _get_ffmpeg(), "-y",
            "-loop", "1", "-i", png_path,
            "-i", mp3_path,
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            out_path,
        ]
    )


def concat_clips(clip_paths: List[str], out_path: str) -> None:
    """Concatenate scene clips via the ffmpeg concat demuxer. Tries the fast stream-copy path
    first (works because every clip was built with identical encode params); falls back to a
    full re-encode concat if that ever mismatches — this is the exact failure mode that broke
    the earlier Vid attempt, so it must not raise on the happy path alone."""
    ffmpeg = _get_ffmpeg()
    list_path = out_path + ".concat.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for p in clip_paths:
            escaped = os.path.abspath(p).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
    try:
        try:
            _run_ffmpeg([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", out_path])
        except VideoRenderError as e:
            logger.warning(f"Concat stream-copy failed, retrying with re-encode: {e}")
            _run_ffmpeg(
                [
                    ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_path,
                    "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", out_path,
                ]
            )
    finally:
        try:
            os.remove(list_path)
        except OSError:
            pass


def _group_word_cues(cues: List[Dict[str, Any]], max_words: int = 10) -> List[Dict[str, Any]]:
    """Group word-level TTS cues into readable subtitle lines (break on punctuation or a word
    cap), rather than emitting a caption per word."""
    groups: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    for c in cues:
        current.append(c)
        if len(current) >= max_words or c["text"].strip().endswith((".", "!", "?", "…", ",")):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    results = []
    for g in groups:
        text = " ".join(w["text"] for w in g).strip()
        text = re.sub(r"\s+([,.!?…])", r"\1", text)  # "chào ," -> "chào,"
        results.append({"start": g[0]["start"], "end": g[-1]["start"] + g[-1]["duration"], "text": text})
    return results


def _srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_srt(cues: List[Dict[str, Any]], path: str) -> None:
    lines = []
    for i, cue in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{_srt_timestamp(cue['start'])} --> {_srt_timestamp(cue['end'])}")
        lines.append(cue["text"])
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_transcript(vid_data: VidOutput, path: str) -> None:
    lines = [vid_data.title, ""]
    for sc in vid_data.scenes:
        lines.append(f"--- Cảnh {sc.scene_number}: {sc.title} ---")
        lines.append(sc.narration)
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def assemble_video(
    vid_data: VidOutput,
    fmt: str,
    voice: str,
    artifact_dir: str,
    progress_cb: Optional[Callable[[float], None]] = None,
) -> str:
    """Render every scene (TTS narration + still frame -> clip), concatenate into vid.mp4, and
    write the accompanying transcript.txt / vid.srt. Fills in each scene's real
    duration_seconds (from TTS audio) and the script's total_duration_seconds in-place.
    Raises VideoRenderError / propagates exceptions on failure — callers must treat that as a
    hard generation error (matches the strict, no-placeholder invariant)."""
    spec = resolve_format(fmt)
    width, height = spec["width"], spec["height"]
    voice_id = resolve_voice(voice)

    scene_dir = os.path.join(artifact_dir, "_vid_scenes")
    os.makedirs(scene_dir, exist_ok=True)

    clip_paths: List[str] = []
    srt_cues: List[Dict[str, Any]] = []
    cumulative = 0.0
    total_scenes = len(vid_data.scenes)
    if total_scenes == 0:
        raise VideoRenderError("Kịch bản video không có phân cảnh nào.")

    try:
        for i, scene in enumerate(vid_data.scenes):
            mp3_path = os.path.join(scene_dir, f"scene_{i + 1}.mp3")
            word_cues = _synthesize_narration(scene.narration, voice_id, mp3_path)
            duration = _cues_duration(word_cues) or _probe_duration(mp3_path)
            duration = max(duration, 1.0)
            scene.duration_seconds = int(round(duration))

            png_path = os.path.join(scene_dir, f"scene_{i + 1}.png")
            render_scene_frame(scene, i + 1, total_scenes, width, height, png_path)

            clip_path = os.path.join(scene_dir, f"scene_{i + 1}.mp4")
            build_scene_clip(png_path, mp3_path, width, height, clip_path, duration)
            clip_paths.append(clip_path)

            if word_cues:
                srt_cues.extend(
                    {**cue, "start": cue["start"] + cumulative, "end": cue["end"] + cumulative}
                    for cue in _group_word_cues(word_cues)
                )
            else:
                srt_cues.append({"start": cumulative, "end": cumulative + duration, "text": scene.narration})
            cumulative += duration

            if progress_cb:
                progress_cb((i + 1) / total_scenes)

        mp4_path = os.path.join(artifact_dir, "vid.mp4")
        concat_clips(clip_paths, mp4_path)

        vid_data.total_duration_seconds = int(round(cumulative))
        _write_transcript(vid_data, os.path.join(artifact_dir, "transcript.txt"))
        _write_srt(srt_cues, os.path.join(artifact_dir, "vid.srt"))
        return mp4_path
    finally:
        shutil.rmtree(scene_dir, ignore_errors=True)
