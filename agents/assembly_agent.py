"""
Phase 6 - Assembly Agent
Merges voice audio + visuals video. Remotion handles word-by-word captions.
Runs once per language per episode.
Output: ep{NN}_final_{LANG}.mp4  (1080x1920, 58-62s)
Also saves: ep{NN}_captions_{LANG}.srt  (for archive / review)
"""
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import av

logger = logging.getLogger(__name__)

OUTPUT_BASE = Path(os.getenv("OUTPUT_BASE_PATH", "./output"))

# Use 'base' by default — 'tiny' is faster but weaker on Tamil
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

MIN_DURATION = 55.0
MAX_DURATION = 65.0

TA_MIN_DURATION = 35.0
TA_MAX_DURATION = 65.0

# Locate ffmpeg: prefer the PATH-resolved binary, fall back to the WinGet install location
def _find_ffmpeg() -> str:
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    winget_path = (
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Microsoft" / "WinGet" / "Packages"
    )
    for candidate in winget_path.rglob("ffmpeg.exe"):
        if "bin" in candidate.parts:
            return str(candidate)
    raise RuntimeError(
        "ffmpeg not found. Install with: winget install Gyan.FFmpeg  "
        "(then restart the shell, or the path will be resolved at next run)"
    )

FFMPEG = _find_ffmpeg()


def _episode_dir(episode: int, week: int) -> Path:
    base = Path(os.getenv("OUTPUT_BASE_PATH", "./output"))
    return base / f"week_{week:02d}" / f"ep{episode:02d}"


def _ffmpeg(*args: str, timeout: int = 300, cwd: str | None = None) -> None:
    cmd = [FFMPEG, "-y"] + list(args)
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )




def _ts_srt(secs: float) -> str:
    """Seconds -> SRT timestamp  hh:mm:ss,mmm"""
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    ms = int(round((secs % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _transcribe(audio_path: Path, lang: str) -> list[dict]:
    """
    Run faster-whisper on the voice MP3, return list of word dicts:
    [{"start": float, "end": float, "text": str}, ...]

    Converts the MP3 to a temporary 16kHz mono WAV first — faster_whisper
    decodes WAV reliably on Windows; direct MP3 decoding via ctranslate2
    can silently return zero segments on paths with spaces.
    """
    import sys as _sys

    model_size = "base" if lang == "ta" else WHISPER_MODEL
    logger.info(f"Transcribing {audio_path.name} with Whisper '{model_size}' (lang={lang})")

    # Convert MP3 -> 16kHz mono WAV in a temp file so faster_whisper gets
    # its preferred format regardless of platform or path characters.
    wav_path = Path(tempfile.mktemp(suffix=".wav"))
    try:
        _ffmpeg(
            "-i", str(audio_path),
            "-ar", "16000",
            "-ac", "1",
            "-f", "wav",
            str(wav_path),
        )
        logger.info(f"WAV written to {wav_path} — starting Whisper transcription")

        # ctranslate2 occasionally raises SyntaxError on first load while it
        # compiles/caches model artifacts. Retry with cleared sys.modules entry.
        model = None
        for init_attempt in range(1, 4):
            try:
                from faster_whisper import WhisperModel
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                break
            except Exception as e:
                if init_attempt == 3:
                    raise RuntimeError(f"WhisperModel failed to load after 3 attempts: {e}") from e
                logger.warning(
                    f"WhisperModel init attempt {init_attempt}/3 failed: {e} — "
                    f"clearing cached module and retrying in 2s"
                )
                _sys.modules.pop("faster_whisper", None)
                _sys.modules.pop("ctranslate2", None)
                time.sleep(2)

        segments_iter, info = model.transcribe(
            str(wav_path),
            language=lang,
            word_timestamps=True,
        )
        logger.info(
            f"Whisper detected language: {info.language} "
            f"(probability {info.language_probability:.2f})"
        )

        words: list[dict] = []
        for seg in segments_iter:
            seg_words = getattr(seg, "words", None)
            if seg_words:
                for w in seg_words:
                    text = w.word.strip()
                    if text:
                        words.append({"start": w.start, "end": w.end, "text": text})
            else:
                text = seg.text.strip()
                if text:
                    words.append({"start": seg.start, "end": seg.end, "text": text})

        logger.info(f"Transcribed {len(words)} words from {audio_path.name}")
        return words
    finally:
        wav_path.unlink(missing_ok=True)


def _write_srt(words: list[dict], path: Path) -> None:
    """Write SRT caption file to the episode directory for archive."""
    lines: list[str] = []
    for i, w in enumerate(words, 1):
        lines += [
            str(i),
            f"{_ts_srt(w['start'])} --> {_ts_srt(w['end'])}",
            w["text"],
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")




def _validate_output(path: Path, episode: int, lang: str = "en") -> float:
    """
    Validate final MP4 with PyAV:
      - File exists and size > 500 KB
      - Video stream is 1080x1920
      - Duration within lang window (EN: 55-65s, TA: 35-65s)
    Returns duration in seconds.
    """
    if not path.exists() or path.stat().st_size < 500_000:
        raise RuntimeError(
            f"EP{episode:02d} final output missing or too small: {path}"
        )

    container = av.open(str(path))
    try:
        vs = next(iter(container.streams.video), None)
        if vs is None:
            raise RuntimeError(f"EP{episode:02d} output has no video stream")

        w, h = vs.codec_context.width, vs.codec_context.height
        if w != 1080 or h != 1920:
            raise RuntimeError(
                f"EP{episode:02d} output is {w}x{h} — expected 1080x1920"
            )

        if container.duration and container.duration > 0:
            duration = float(container.duration) / 1_000_000
        elif vs.duration and vs.time_base:
            duration = float(vs.duration * vs.time_base)
        else:
            raise RuntimeError(
                f"EP{episode:02d} could not determine output duration"
            )
    finally:
        container.close()

    lo = TA_MIN_DURATION if lang == "ta" else MIN_DURATION
    hi = TA_MAX_DURATION if lang == "ta" else MAX_DURATION
    if duration < lo or duration > hi:
        raise RuntimeError(
            f"EP{episode:02d} final duration {duration:.1f}s outside "
            f"{lo}-{hi}s window"
        )

    return duration


def run(episode: int, week: int, lang: str = "en") -> dict:
    """
    Assemble final MP4 for one language:
      1. Transcribe voice MP3 with faster-whisper -> word timestamps
      2. Save SRT to episode dir (ep{NN}_captions_{LANG}.srt)
      3. FFmpeg: replace visuals audio with voice audio (-shortest)
      4. PyAV: validate 1080x1920 and 58-62s duration

    Args:
        episode: Episode number 1-7
        week:    Week number
        lang:    "en" or "ta"

    Returns:
        {"success": True, "output_path": str, "duration": float,
         "assembly_time": float, "size_mb": float, "lang": str, "skipped": bool}
    """
    lang = lang.lower()
    if lang not in ("en", "ta"):
        raise RuntimeError(f"EP{episode:02d} unsupported lang '{lang}'")

    ep_dir = _episode_dir(episode, week)
    visuals_suffix = "_TA" if lang == "ta" else ""
    visuals_path = ep_dir / f"ep{episode:02d}_visuals{visuals_suffix}.mp4"
    voice_path   = ep_dir / f"ep{episode:02d}_voice_{lang.upper()}.mp3"
    srt_path     = ep_dir / f"ep{episode:02d}_captions_{lang.upper()}.srt"
    output_path  = ep_dir / f"ep{episode:02d}_final_{lang.upper()}.mp4"

    if not visuals_path.exists():
        raise RuntimeError(
            f"EP{episode:02d} visuals not found: {visuals_path}. "
            "Run visual_agent first."
        )
    if not voice_path.exists():
        raise RuntimeError(
            f"EP{episode:02d} [{lang.upper()}] voice not found: {voice_path}. "
            "Run voice_agent first."
        )

    if output_path.exists() and output_path.stat().st_size > 500_000:
        logger.info(f"EP{episode:02d} [{lang.upper()}] already assembled - skipping")
        return {
            "success": True,
            "output_path": str(output_path),
            "lang": lang,
            "skipped": True,
            "message": "Final video already assembled - skipping.",
        }

    t0 = time.monotonic()
    logger.info(f"EP{episode:02d} [{lang.upper()}] starting assembly")

    # Step 1: Transcribe voice -> word timestamps
    words = _transcribe(voice_path, lang)

    # Step 2: Save SRT to episode dir
    _write_srt(words, srt_path)
    logger.info(f"EP{episode:02d} [{lang.upper()}] SRT saved -> {srt_path}")

    # Step 3: Merge video + voice (+ optional lo-fi music bed at 8% volume)
    music_str = os.getenv("BACKGROUND_MUSIC_PATH", "")
    music_path = Path(music_str) if music_str else None

    if music_path and music_path.exists():
        logger.info(f"EP{episode:02d} [{lang.upper()}] merging audio + video + music bed")
        _ffmpeg(
            "-i", str(visuals_path),
            "-i", str(voice_path),
            "-i", str(music_path),
            "-filter_complex",
            "[1:a]volume=1.0[voice];[2:a]volume=0.08[music];[voice][music]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path),
        )
    else:
        logger.info(f"EP{episode:02d} [{lang.upper()}] merging audio + video")
        _ffmpeg(
            "-i", str(visuals_path),
            "-i", str(voice_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path),
        )

    # Step 4: Validate output
    duration = _validate_output(output_path, episode, lang)
    assembly_time = time.monotonic() - t0

    logger.info(
        f"EP{episode:02d} [{lang.upper()}] assembly complete in {assembly_time:.1f}s "
        f"— duration={duration:.1f}s size={output_path.stat().st_size/1_048_576:.1f}MB"
    )

    return {
        "success": True,
        "output_path": str(output_path),
        "lang": lang,
        "skipped": False,
        "duration": round(duration, 2),
        "assembly_time": round(assembly_time, 1),
        "size_mb": round(output_path.stat().st_size / 1_048_576, 1),
    }
