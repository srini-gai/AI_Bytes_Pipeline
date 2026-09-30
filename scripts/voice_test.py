#!/usr/bin/env python3
"""
voice_test.py — ElevenLabs voice variant sampler for Srini on AI pipeline.

Generates three MP3 variants of the same 15-20 second narration using
different voice settings to help select the best creator-style delivery.

Usage (run on VPS where .env is present):
    python scripts/voice_test.py

Output:
    output/voice_test/voice_test_A.mp3   — Natural
    output/voice_test/voice_test_B.mp3   — Creator / Recommended
    output/voice_test/voice_test_C.mp3   — More Energetic

After listening to the three samples, update .env with your chosen
ELEVENLABS_* settings (see voice_agent.py for the variable names).
"""

import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Allow running from project root or scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))

import av
from dotenv import load_dotenv
from elevenlabs import ElevenLabs, VoiceSettings

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Test narration ────────────────────────────────────────────────────────────
TEST_NARRATION = (
    "Your AI just made up a fact. And the surprising part? "
    "That doesn't necessarily mean something went wrong. "
    "Large language models predict what comes next — they don't automatically know "
    "what's true. That's where grounding changes the game."
)

MODEL_ID = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"

OUTPUT_DIR = Path("output/voice_test")


@dataclass
class VoiceVariant:
    label: str
    description: str
    stability: float
    similarity_boost: float
    style: float
    speed: float
    use_speaker_boost: bool


VARIANTS: list[VoiceVariant] = [
    VoiceVariant(
        label="A",
        description="Natural",
        stability=0.50,
        similarity_boost=0.75,
        style=0.0,
        speed=1.00,
        use_speaker_boost=True,
    ),
    VoiceVariant(
        label="B",
        description="Creator / Recommended",
        stability=0.42,
        similarity_boost=0.78,
        style=0.0,
        speed=1.05,
        use_speaker_boost=True,
    ),
    VoiceVariant(
        label="C",
        description="More Energetic",
        stability=0.35,
        similarity_boost=0.78,
        style=0.0,
        speed=1.07,
        use_speaker_boost=True,
    ),
]


def _mp3_duration(path: Path) -> float:
    """Return audio duration in seconds using PyAV."""
    container = av.open(str(path))
    try:
        if container.duration is not None and container.duration > 0:
            return float(container.duration) / 1_000_000
        for stream in container.streams.audio:
            if stream.duration and stream.time_base:
                return float(stream.duration * stream.time_base)
    finally:
        container.close()
    raise ValueError(f"Could not determine duration of {path}")


def generate_variant(
    client: ElevenLabs,
    voice_id: str,
    variant: VoiceVariant,
    output_dir: Path,
) -> Path:
    """Generate one MP3 variant. Returns the output path."""
    output_path = output_dir / f"voice_test_{variant.label}.mp3"

    logger.info(
        f"Generating Test {variant.label} — {variant.description} "
        f"(stability={variant.stability}, similarity={variant.similarity_boost}, "
        f"style={variant.style}, speed={variant.speed}, "
        f"speaker_boost={variant.use_speaker_boost})"
    )

    for attempt in range(1, 4):
        try:
            audio_chunks = client.text_to_speech.convert(
                voice_id=voice_id,
                text=TEST_NARRATION,
                model_id=MODEL_ID,
                output_format=OUTPUT_FORMAT,
                voice_settings=VoiceSettings(
                    stability=variant.stability,
                    similarity_boost=variant.similarity_boost,
                    style=variant.style,
                    speed=variant.speed,
                    use_speaker_boost=variant.use_speaker_boost,
                ),
            )
            audio_bytes = b"".join(audio_chunks)
            output_path.write_bytes(audio_bytes)

            duration = _mp3_duration(output_path)
            logger.info(
                f"  ✓ voice_test_{variant.label}.mp3 — {duration:.2f}s "
                f"({len(audio_bytes):,} bytes)"
            )
            return output_path

        except Exception as e:
            logger.warning(f"  attempt {attempt}/3 failed: {e}")
            if attempt < 3:
                wait = 2 ** attempt
                logger.info(f"  retrying in {wait}s ...")
                time.sleep(wait)

    raise RuntimeError(f"Failed to generate Test {variant.label} after 3 attempts")


def main() -> None:
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key or "your-" in api_key:
        logger.error("ELEVENLABS_API_KEY not set in .env — aborting")
        sys.exit(1)

    voice_id = os.getenv("ELEVENLABS_VOICE_ID_EN", os.getenv("ELEVENLABS_VOICE_ID", ""))
    if not voice_id or "your-" in voice_id:
        logger.error("ELEVENLABS_VOICE_ID_EN (or ELEVENLABS_VOICE_ID) not set in .env — aborting")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    client = ElevenLabs(api_key=api_key)

    logger.info("=" * 60)
    logger.info("Srini on AI — Voice Style Test")
    logger.info(f"Narration ({len(TEST_NARRATION)} chars):")
    logger.info(f'  "{TEST_NARRATION[:80]}..."')
    logger.info("=" * 60)

    results: list[tuple[VoiceVariant, Path]] = []
    for variant in VARIANTS:
        path = generate_variant(client, voice_id, variant, OUTPUT_DIR)
        results.append((variant, path))
        # Brief pause between API calls to avoid rate-limit bursts
        if variant.label != VARIANTS[-1].label:
            time.sleep(1)

    logger.info("")
    logger.info("=" * 60)
    logger.info("All three samples generated:")
    for variant, path in results:
        duration = _mp3_duration(path)
        logger.info(
            f"  [{variant.label}] {variant.description:<25} → {path.name}  ({duration:.2f}s)"
        )
    logger.info("")
    logger.info("Next step: listen to all three, pick one, then add to .env:")
    logger.info("  ELEVENLABS_STABILITY=<value>")
    logger.info("  ELEVENLABS_SIMILARITY=<value>")
    logger.info("  ELEVENLABS_STYLE=0")
    logger.info("  ELEVENLABS_SPEED=<value>")
    logger.info("  ELEVENLABS_SPEAKER_BOOST=true")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
