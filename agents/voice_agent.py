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

# ── Duration windows ──────────────────────────────────────────────────────────
# Voice-only targets — slightly narrower than the global 45–60s visual window
# to leave headroom for assembly sync and caption timing.
MIN_DURATION = 40.0   # en — absolute floor
MAX_DURATION = 62.0   # en — absolute ceiling
TA_MIN_DURATION = 40.0
TA_MAX_DURATION = 65.0

# ── Voice settings — loaded from .env, with safe production defaults ──────────
# To change delivery style, set these in .env (no code change needed):
#   ELEVENLABS_STABILITY      — 0.0–1.0  (lower = more expressive variation)
#   ELEVENLABS_SIMILARITY     — 0.0–1.0  (higher = closer to reference voice)
#   ELEVENLABS_STYLE          — 0.0–1.0  (style exaggeration; keep at 0 for most voices)
#   ELEVENLABS_SPEED          — 0.5–2.0  (1.0 = natural, prefer tighter scripts over high speed)
#   ELEVENLABS_SPEAKER_BOOST  — true/false

def _voice_settings() -> VoiceSettings:
    """Build VoiceSettings from environment, falling back to production defaults.

    Production defaults match the 'Creator / Recommended' variant (Test B):
        stability=0.42, similarity_boost=0.78, style=0, speed=1.05, speaker_boost=True

    These can be overridden at any time via .env without a code change.
    """
    def _float(key: str, default: float) -> float:
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid value for {key} — using default {default}")
            return default

    def _bool(key: str, default: bool) -> bool:
        val = os.getenv(key, "").lower()
        if val in ("1", "true", "yes"):
            return True
        if val in ("0", "false", "no"):
            return False
        return default

    return VoiceSettings(
        stability=_float("ELEVENLABS_STABILITY", 0.42),
        similarity_boost=_float("ELEVENLABS_SIMILARITY", 0.78),
        style=_float("ELEVENLABS_STYLE", 0.0),
        speed=_float("ELEVENLABS_SPEED", 1.05),
        use_speaker_boost=_bool("ELEVENLABS_SPEAKER_BOOST", True),
    )


# ── Section-intent delivery profile (future use) ─────────────────────────────
#
# Design intent: voice_agent will eventually support per-section delivery
# profiles so each part of a Short sounds like it was written and performed
# for that specific purpose.
#
# Planned profiles (do not implement yet — design reference only):
#
#   HOOK        — punchy, curious, slightly faster
#                 stability↓ (0.35–0.40), speed 1.05–1.08, style 0
#                 Goal: grab attention in the first 2s
#
#   EXPLANATION — conversational, relaxed, room to breathe
#                 stability 0.45–0.50, speed 1.00–1.03, style 0
#                 Goal: make the concept stick, not overwhelm
#
#   KEY_REVEAL  — stronger emphasis, slightly slower on the key phrase
#                 stability 0.40, speed 0.98–1.00, style 0–0.05
#                 Goal: the "aha" moment lands
#
#   TAKEAWAY    — slower and confident, let the idea settle
#                 stability 0.50–0.55, speed 0.97–1.00, style 0
#                 Goal: viewer remembers this line
#
#   CTA         — warm and inviting, not salesy
#                 stability 0.48–0.52, speed 1.00, style 0
#                 Goal: genuine invitation, not a hard close
#
# Implementation path (when ready):
#   1. Script agent tags each voiceover segment with a section_type field
#   2. voice_agent splits the voiceover by section, calls TTS per segment
#      with matching VoiceSettings, then concatenates the audio
#   3. Timing report includes per-section durations for validation
#
# Pacing principle (binding):
#   - Prefer tighter scripts over higher speed for duration control
#   - ELEVENLABS_SPEED should never be used as a band-aid for long narration
#   - Keep speed ≤ 1.08 for English; above that, articulation degrades
# ─────────────────────────────────────────────────────────────────────────────


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

    # Cache check — skip ElevenLabs call if valid MP3 already on disk
    if output_path.exists():
        try:
            duration = _validate_duration(output_path, lang)
            logger.info(
                f"EP{episode:02d} [{lang.upper()}] — voice already on disk ({duration:.1f}s) — skipping TTS"
            )
            return {"success": True, "output_path": str(output_path), "duration": duration, "lang": lang}
        except ValueError:
            logger.warning(
                f"EP{episode:02d} [{lang.upper()}] — existing MP3 failed validation, re-generating"
            )

    voice_id_key = f"ELEVENLABS_VOICE_ID_{lang.upper()}"
    voice_id = os.getenv(voice_id_key, "")
    if not voice_id or "your-" in voice_id:
        raise RuntimeError(f"{voice_id_key} not set in .env")

    settings = _voice_settings()
    logger.info(
        f"EP{episode:02d} [{lang.upper()}] — voice settings: "
        f"stability={settings.stability}, similarity={settings.similarity_boost}, "
        f"style={settings.style}, speed={settings.speed}, "
        f"speaker_boost={settings.use_speaker_boost}"
    )

    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            logger.info(
                f"EP{episode:02d} [{lang.upper()}] — ElevenLabs TTS call (attempt {attempt}/3)"
            )

            audio_chunks = client.text_to_speech.convert(
                voice_id=voice_id,
                text=voiceover,
                model_id=MODEL_ID,
                output_format=OUTPUT_FORMAT,
                voice_settings=settings,
            )

            audio_bytes = b"".join(audio_chunks)
            output_path.write_bytes(audio_bytes)
            logger.info(
                f"EP{episode:02d} [{lang.upper()}] — MP3 written "
                f"({len(audio_bytes):,} bytes) -> {output_path}"
            )

            duration = _validate_duration(output_path, lang)
            logger.info(f"EP{episode:02d} [{lang.upper()}] — duration {duration:.1f}s — PASS")

            return {"success": True, "output_path": str(output_path), "duration": duration, "lang": lang}

        except ValueError as e:
            # Duration out of range — no point retrying with same settings
            last_error = e
            logger.error(f"EP{episode:02d} [{lang.upper()}] — validation failed: {e}")
            raise RuntimeError(
                f"EP{episode:02d} [{lang.upper()}] voice_agent validation error: {e}"
            ) from e

        except Exception as e:
            last_error = e
            logger.warning(f"EP{episode:02d} [{lang.upper()}] — attempt {attempt} failed: {e}")
            if attempt < 3:
                wait = 2 ** attempt
                logger.info(f"EP{episode:02d} [{lang.upper()}] — retrying in {wait}s")
                time.sleep(wait)

    raise RuntimeError(
        f"EP{episode:02d} [{lang.upper()}] voice_agent failed after 3 attempts: {last_error}"
    )
