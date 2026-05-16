import logging
import os
import time
from pathlib import Path

import av
from dotenv import load_dotenv
from elevenlabs import ElevenLabs, VoiceSettings

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_ID = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"

MIN_DURATION = 55.0
MAX_DURATION = 68.0

TA_MIN_DURATION = 40.0
TA_MAX_DURATION = 65.0


def _episode_dir(episode: int, week: int) -> Path:
    base = Path(os.getenv("OUTPUT_BASE_PATH", "./output"))
    path = base / f"week_{week:02d}" / f"ep{episode:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _mp3_duration(path: Path) -> float:
    """Return audio duration in seconds using PyAV."""
    container = av.open(str(path))
    try:
        # container.duration is in AV_TIME_BASE units (microseconds)
        if container.duration is not None and container.duration > 0:
            return float(container.duration) / 1_000_000
        # Fall back to stream duration
        for stream in container.streams.audio:
            if stream.duration and stream.time_base:
                return float(stream.duration * stream.time_base)
    finally:
        container.close()
    raise ValueError(f"Could not determine duration of {path}")


def _validate_duration(path: Path, lang: str = "en") -> float:
    """Check MP3 duration is within the lang-appropriate window. Returns duration."""
    lo = TA_MIN_DURATION if lang == "ta" else MIN_DURATION
    hi = TA_MAX_DURATION if lang == "ta" else MAX_DURATION
    duration = _mp3_duration(path)
    if duration < lo or duration > hi:
        raise ValueError(
            f"MP3 duration {duration:.1f}s is outside {lo}–{hi}s window"
        )
    return duration


def run(script: dict, episode: int, week: int, lang: str = "en") -> dict:
    """Synthesise voiceover MP3 from script JSON via ElevenLabs.

    Args:
        script:  Script dict from script_agent (must contain 'voiceover' key)
        episode: Episode number 1–7
        week:    Week number
        lang:    Language code — "en" (default) or "ta" (Tamil)

    Returns:
        {"success": True, "output_path": str, "duration": float, "lang": str}
    """
    lang = lang.lower()
    if lang not in ("en", "ta"):
        raise RuntimeError(f"EP{episode:02d} unsupported lang '{lang}' — use 'en' or 'ta'")

    voiceover = script.get("voiceover", "").strip()
    if not voiceover:
        raise RuntimeError(f"EP{episode:02d} script has no voiceover text")

    output_path = _episode_dir(episode, week) / f"ep{episode:02d}_voice_{lang.upper()}.mp3"

    voice_id_key = f"ELEVENLABS_VOICE_ID_{lang.upper()}"
    voice_id = os.getenv(voice_id_key, "")
    if not voice_id or "your-" in voice_id:
        raise RuntimeError(f"{voice_id_key} not set in .env")

    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            logger.info(f"EP{episode:02d} [{lang.upper()}] — ElevenLabs TTS call (attempt {attempt}/3)")

            audio_chunks = client.text_to_speech.convert(
                voice_id=voice_id,
                text=voiceover,
                model_id=MODEL_ID,
                output_format=OUTPUT_FORMAT,
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    speed=0.95,
                ),
            )

            audio_bytes = b"".join(audio_chunks)
            output_path.write_bytes(audio_bytes)
            logger.info(f"EP{episode:02d} [{lang.upper()}] — MP3 written ({len(audio_bytes):,} bytes) -> {output_path}")

            duration = _validate_duration(output_path, lang)
            logger.info(f"EP{episode:02d} [{lang.upper()}] — duration {duration:.1f}s — PASS")

            return {"success": True, "output_path": str(output_path), "duration": duration, "lang": lang}

        except ValueError as e:
            # Duration out of range — no point retrying
            last_error = e
            logger.error(f"EP{episode:02d} [{lang.upper()}] — validation failed: {e}")
            raise RuntimeError(f"EP{episode:02d} [{lang.upper()}] voice_agent validation error: {e}") from e

        except Exception as e:
            last_error = e
            logger.warning(f"EP{episode:02d} [{lang.upper()}] — attempt {attempt} failed: {e}")
            if attempt < 3:
                wait = 2 ** attempt
                logger.info(f"EP{episode:02d} [{lang.upper()}] — retrying in {wait}s")
                time.sleep(wait)

    raise RuntimeError(f"EP{episode:02d} [{lang.upper()}] voice_agent failed after 3 attempts: {last_error}")
