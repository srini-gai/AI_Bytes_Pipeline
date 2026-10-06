"""
Audio Mixer — deterministic SFX + music mixing layer.

Consumes a Sound Director manifest (ep{NN}_sound_plan_v1.json) and the
approved voice track, producing a single mixed audio file ready for
assembly_agent to mux with the visual render.

Design principles
-----------------
- Voice is the reference track and is **never** ducked, filtered or clipped.
- SFX cues are placed at exact timestamps with per-cue gain (dB).
- One generated asset can appear at multiple timestamps (reuse).
- An optional music bed can be ducked under narration and faded in/out.
- The mixer is fully deterministic: same inputs → same output.
- Final loudness is normalised to ≈ −14 LUFS (YouTube target), TP ≤ −1 dBTP.

All audio processing uses numpy + ffmpeg — no paid API calls.
"""
import json
import logging
import os
import subprocess
import shutil
import struct
import tempfile
import time
from pathlib import Path
from typing import TypedDict

import numpy as np

from agents.cache_identity import read_meta, write_meta

logger = logging.getLogger(__name__)

def _output_base() -> Path:
    return Path(os.getenv("OUTPUT_BASE_PATH", "./output"))

# ── FFmpeg helper ────────────────────────────────────────────────────────────

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
    raise RuntimeError("ffmpeg not found")


FFMPEG = _find_ffmpeg()


def _ffmpeg(*args: str, timeout: int = 120) -> str:
    """Run ffmpeg and return combined output. Raises on non-zero exit."""
    cmd = [FFMPEG, "-y"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}):\n{result.stderr[-2000:]}")
    return result.stderr  # ffmpeg writes info to stderr


def _ffprobe_duration(path: Path) -> float:
    """Return audio duration in seconds via ffprobe."""
    ffprobe = FFMPEG.replace("ffmpeg", "ffprobe")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return float(result.stdout.strip())


# ── WAV I/O helpers ──────────────────────────────────────────────────────────

def read_wav_mono(path: Path, target_sr: int = 44100) -> tuple[np.ndarray, int]:
    """
    Read any audio file into a mono float32 numpy array at target_sr.
    Uses ffmpeg for decoding so MP3/AAC/OGG/WAV all work.
    Returns (samples, sample_rate).
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        _ffmpeg(
            "-i", str(path),
            "-ar", str(target_sr),
            "-ac", "1",
            "-f", "wav",
            "-acodec", "pcm_f32le",
            str(tmp_path),
        )
        return _read_raw_wav(tmp_path), target_sr
    finally:
        tmp_path.unlink(missing_ok=True)


def _read_raw_wav(path: Path) -> np.ndarray:
    """Read a PCM float32 mono WAV into numpy. Minimal parser — we wrote it."""
    data = path.read_bytes()
    # Find 'data' chunk
    idx = data.find(b"data")
    if idx < 0:
        raise RuntimeError(f"No 'data' chunk in {path}")
    chunk_size = struct.unpack_from("<I", data, idx + 4)[0]
    pcm_start = idx + 8
    return np.frombuffer(data[pcm_start:pcm_start + chunk_size], dtype=np.float32).copy()


def write_wav_mono(path: Path, samples: np.ndarray, sr: int = 44100) -> None:
    """Write mono float32 samples to a WAV file."""
    samples = samples.astype(np.float32)
    pcm = samples.tobytes()
    # RIFF header
    data_size = len(pcm)
    fmt_chunk = struct.pack("<4sIHHIIHH",
                            b"fmt ", 16, 3, 1, sr, sr * 4, 4, 32)  # format 3 = float
    riff_size = 4 + (8 + 16) + (8 + data_size)
    header = struct.pack("<4sI4s", b"RIFF", riff_size, b"WAVE")
    data_header = struct.pack("<4sI", b"data", data_size)
    path.write_bytes(header + fmt_chunk + data_header + pcm)


# ── Gain / mixing ───────────────────────────────────────────────────────────

def db_to_linear(db: float) -> float:
    """Convert dB to linear gain factor."""
    return 10.0 ** (db / 20.0)


class SFXCue(TypedDict):
    """One placed SFX event."""
    t: float            # placement time in seconds
    asset: str          # asset name (key into assets dict)
    rel_db: float       # gain relative to voice, in dB


class MusicConfig(TypedDict, total=False):
    """Optional music bed configuration."""
    path: str                   # path to music file
    volume_db: float            # base volume relative to voice (e.g. -20)
    duck_db: float              # volume during narration (e.g. -30)
    duck_attack_s: float        # fade-down duration
    duck_release_s: float       # fade-up duration
    fade_in_s: float            # opening fade
    fade_out_s: float           # closing fade
    cta_rise_db: float          # optional rise in CTA hold (e.g. -16)
    cta_start_s: float          # when CTA hold begins


def place_sfx(
    voice: np.ndarray,
    cues: list[SFXCue],
    assets: dict[str, np.ndarray],
    sr: int = 44100,
) -> np.ndarray:
    """
    Place SFX cues on a buffer the same length as voice.

    Each cue is overlaid at its timestamp with its specified gain.
    Cues that would extend past the buffer end are truncated.
    Returns a new float32 array (SFX-only, same length as voice).
    """
    sfx_buf = np.zeros_like(voice, dtype=np.float32)
    for cue in cues:
        asset_name = cue["asset"]
        if asset_name not in assets:
            raise RuntimeError(f"SFX asset '{asset_name}' not found in loaded assets")
        asset_samples = assets[asset_name]
        gain = db_to_linear(cue["rel_db"])
        start_sample = int(round(cue["t"] * sr))
        if start_sample < 0:
            raise ValueError(f"SFX cue at negative time {cue['t']}s")
        if start_sample >= len(sfx_buf):
            logger.warning(f"SFX cue '{asset_name}' at {cue['t']:.2f}s past buffer end — skipped")
            continue
        end_sample = min(start_sample + len(asset_samples), len(sfx_buf))
        n = end_sample - start_sample
        sfx_buf[start_sample:end_sample] += asset_samples[:n] * gain
    return sfx_buf


def apply_music_bed(
    voice: np.ndarray,
    music_raw: np.ndarray,
    config: MusicConfig,
    voice_rms_window_s: float = 0.05,
    sr: int = 44100,
) -> np.ndarray:
    """
    Mix a music bed under voice with ducking and fades.

    - Base volume: config['volume_db']
    - Ducked to config['duck_db'] whenever voice RMS > threshold
    - Fade in/out at start/end
    - Optional CTA rise at end
    Returns a music-only buffer (same length as voice).
    """
    n = len(voice)

    # Loop or truncate music to match voice length
    if len(music_raw) >= n:
        music = music_raw[:n].copy().astype(np.float32)
    else:
        repeats = (n // len(music_raw)) + 1
        music = np.tile(music_raw, repeats)[:n].astype(np.float32)

    base_gain = db_to_linear(config.get("volume_db", -20.0))
    duck_gain = db_to_linear(config.get("duck_db", -30.0))
    duck_attack = int(config.get("duck_attack_s", 0.05) * sr)
    duck_release = int(config.get("duck_release_s", 0.15) * sr)
    fade_in = int(config.get("fade_in_s", 0.5) * sr)
    fade_out = int(config.get("fade_out_s", 1.0) * sr)

    # Build gain envelope: base_gain where voice is silent, duck_gain where voice is active
    win = max(1, int(voice_rms_window_s * sr))
    voice_energy = np.convolve(voice ** 2, np.ones(win) / win, mode="same")
    threshold = np.percentile(voice_energy[voice_energy > 0], 10) if np.any(voice_energy > 0) else 0
    voice_active = voice_energy > threshold

    gain_env = np.where(voice_active, duck_gain, base_gain).astype(np.float32)

    # Smooth transitions (attack/release) via simple exponential
    if duck_attack > 0 or duck_release > 0:
        smoothed = gain_env.copy()
        for i in range(1, n):
            if smoothed[i] < smoothed[i - 1]:
                alpha = 1.0 / max(1, duck_attack)
            else:
                alpha = 1.0 / max(1, duck_release)
            smoothed[i] = smoothed[i - 1] + alpha * (smoothed[i] - smoothed[i - 1])
        gain_env = smoothed

    # CTA rise
    cta_rise_db = config.get("cta_rise_db")
    cta_start = config.get("cta_start_s")
    if cta_rise_db is not None and cta_start is not None:
        cta_sample = int(cta_start * sr)
        cta_gain = db_to_linear(cta_rise_db)
        if cta_sample < n:
            # Ramp from current to cta_gain over 0.5s
            ramp_len = min(int(0.5 * sr), n - cta_sample)
            ramp = np.linspace(0, 1, ramp_len)
            gain_env[cta_sample:cta_sample + ramp_len] = (
                gain_env[cta_sample:cta_sample + ramp_len] * (1 - ramp) + cta_gain * ramp
            )
            gain_env[cta_sample + ramp_len:] = cta_gain

    # Fade in/out
    if fade_in > 0 and fade_in < n:
        gain_env[:fade_in] *= np.linspace(0, 1, fade_in)
    if fade_out > 0 and fade_out < n:
        gain_env[-fade_out:] *= np.linspace(1, 0, fade_out)

    music *= gain_env
    return music


def mix_and_limit(
    voice: np.ndarray,
    sfx: np.ndarray | None = None,
    music: np.ndarray | None = None,
    headroom_db: float = -1.0,
) -> np.ndarray:
    """
    Sum voice + SFX + music, then soft-limit to prevent clipping.

    Voice is never altered. SFX and music are scaled down proportionally
    if the mix would clip past headroom_db true peak.
    """
    mix = voice.copy().astype(np.float64)
    extras = np.zeros_like(mix)
    if sfx is not None:
        extras += sfx.astype(np.float64)
    if music is not None:
        extras += music.astype(np.float64)

    combined = mix + extras
    peak = np.max(np.abs(combined))
    limit = db_to_linear(headroom_db)

    if peak > limit and np.max(np.abs(extras)) > 0:
        # Scale only extras to stay under limit while preserving voice
        voice_peak = np.max(np.abs(mix))
        if voice_peak >= limit:
            # Voice alone already at limit — zero out extras
            logger.warning("Voice peak already at headroom limit — SFX/music zeroed")
            return mix.astype(np.float32)
        # Max gain for extras so that voice_peak + extras_peak * scale <= limit
        available = limit - voice_peak
        extras_peak = np.max(np.abs(extras))
        scale = available / extras_peak
        logger.info(f"Soft-limiting extras by {20 * np.log10(scale):.1f} dB to prevent clipping")
        combined = mix + extras * scale

    return combined.astype(np.float32)


# ── Loudness normalisation via ffmpeg loudnorm ───────────────────────────────

def loudnorm(
    input_path: Path,
    output_path: Path,
    target_lufs: float = -14.0,
    target_tp: float = -1.0,
) -> None:
    """
    Two-pass EBU R128 loudness normalisation via ffmpeg loudnorm filter.
    """
    # Pass 1: measure
    info = _ffmpeg(
        "-i", str(input_path),
        "-af", f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11:print_format=json",
        "-f", "null", "-",
    )
    # Extract the JSON block from ffmpeg stderr
    json_start = info.rfind("{")
    json_end = info.rfind("}") + 1
    if json_start < 0 or json_end <= json_start:
        raise RuntimeError("loudnorm pass 1 did not produce measurement JSON")
    measured = json.loads(info[json_start:json_end])

    # Pass 2: apply
    _ffmpeg(
        "-i", str(input_path),
        "-af", (
            f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11:"
            f"measured_I={measured['input_i']}:"
            f"measured_TP={measured['input_tp']}:"
            f"measured_LRA={measured['input_lra']}:"
            f"measured_thresh={measured['input_thresh']}:"
            f"offset={measured['target_offset']}:linear=true"
        ),
        "-ar", "44100",
        "-ac", "1",
        "-c:a", "pcm_f32le",
        str(output_path),
    )


# ── Top-level mix function ──────────────────────────────────────────────────

def mix_episode(
    episode: int,
    week: int,
    sound_plan_path: Path | None = None,
    sfx_dir: Path | None = None,
    music_path: Path | None = None,
    music_config: MusicConfig | None = None,
    target_lufs: float = -14.0,
    target_tp: float = -1.0,
    lang: str = "en",
) -> dict:
    """
    Mix voice + SFX (+ optional music) for one episode.

    Reads the sound plan, loads SFX assets, places cues, mixes, normalises.
    Returns metadata dict with output path and mix details.

    Does NOT call any paid API — all assets must already exist on disk.
    """
    t0 = time.monotonic()
    ep_dir = _output_base() / f"week_{week:02d}" / f"ep{episode:02d}"
    voice_path = ep_dir / f"ep{episode:02d}_voice_{lang.upper()}.mp3"

    if not voice_path.exists():
        raise RuntimeError(f"EP{episode:02d} voice not found: {voice_path}")

    # Load sound plan
    if sound_plan_path is None:
        sound_plan_path = ep_dir / f"ep{episode:02d}_sound_plan_v1.json"
    if not sound_plan_path.exists():
        raise RuntimeError(f"EP{episode:02d} sound plan not found: {sound_plan_path}")
    plan = json.loads(sound_plan_path.read_text(encoding="utf-8"))

    # SFX directory
    if sfx_dir is None:
        sfx_dir = ep_dir / "sfx"

    # Load voice
    logger.info(f"EP{episode:02d} loading voice: {voice_path.name}")
    voice, sr = read_wav_mono(voice_path, target_sr=44100)
    voice_duration = len(voice) / sr
    logger.info(f"EP{episode:02d} voice: {voice_duration:.2f}s, {len(voice)} samples @ {sr}Hz")

    # Determine total duration (visual duration from plan, or voice + buffer)
    visual_dur = plan.get("locked_inputs", {}).get("visual_duration_s", voice_duration + 2.0)
    total_samples = int(round(visual_dur * sr))
    # Extend voice buffer to total_samples (zero-pad if voice is shorter)
    if len(voice) < total_samples:
        voice = np.pad(voice, (0, total_samples - len(voice)))
    elif len(voice) > total_samples:
        voice = voice[:total_samples]

    # Load SFX assets (only those referenced by active events)
    active_events = [
        e for e in plan.get("events", [])
        if e.get("class") != "NONE" and e.get("asset") is not None
    ]
    needed_assets = set(e["asset"] for e in active_events)
    assets: dict[str, np.ndarray] = {}
    for name in needed_assets:
        asset_path = sfx_dir / f"{name}.wav"
        if not asset_path.exists():
            asset_path = sfx_dir / f"{name}.mp3"
        if not asset_path.exists():
            raise RuntimeError(
                f"EP{episode:02d} SFX asset '{name}' not found in {sfx_dir}. "
                f"Generate it first."
            )
        asset_data, _ = read_wav_mono(asset_path, target_sr=sr)
        assets[name] = asset_data
        logger.info(f"EP{episode:02d} loaded SFX: {name} ({len(asset_data)/sr:.2f}s)")

    # Build cue list
    cues: list[SFXCue] = []
    for event in active_events:
        cues.append(SFXCue(
            t=float(event["t"]),
            asset=event["asset"],
            rel_db=float(event["rel_db"]),
        ))
    logger.info(f"EP{episode:02d} placing {len(cues)} SFX cues")

    # Place SFX
    sfx_buf = place_sfx(voice, cues, assets, sr=sr) if cues else None

    # Music bed
    music_buf = None
    if music_path and Path(music_path).exists() and music_config:
        logger.info(f"EP{episode:02d} loading music bed: {music_path}")
        music_raw, _ = read_wav_mono(Path(music_path), target_sr=sr)
        music_buf = apply_music_bed(voice, music_raw, music_config, sr=sr)

    # Mix
    mixed = mix_and_limit(voice, sfx=sfx_buf, music=music_buf, headroom_db=-1.0)

    # Write intermediate WAV
    mixed_wav = ep_dir / f"ep{episode:02d}_mixed_{lang.upper()}.wav"
    write_wav_mono(mixed_wav, mixed, sr=sr)
    logger.info(f"EP{episode:02d} mixed WAV: {mixed_wav.name} ({len(mixed)/sr:.2f}s)")

    # Loudness normalisation → final WAV
    output_path = ep_dir / f"ep{episode:02d}_mixed_norm_{lang.upper()}.wav"
    loudnorm(mixed_wav, output_path, target_lufs=target_lufs, target_tp=target_tp)
    logger.info(f"EP{episode:02d} normalised: {output_path.name}")

    # Clean up intermediate
    mixed_wav.unlink(missing_ok=True)

    # Write metadata
    meta_path = ep_dir / f"ep{episode:02d}_mixed_{lang.upper()}.meta.json"
    mix_meta = {
        "voice_file": voice_path.name,
        "voice_duration_s": round(voice_duration, 3),
        "total_duration_s": round(visual_dur, 3),
        "sfx_cues": len(cues),
        "sfx_assets": sorted(needed_assets),
        "has_music": music_buf is not None,
        "target_lufs": target_lufs,
        "target_tp": target_tp,
        "mixed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    write_meta(meta_path, mix_meta)

    elapsed = time.monotonic() - t0
    logger.info(f"EP{episode:02d} mix complete in {elapsed:.1f}s")

    return {
        "success": True,
        "output_path": str(output_path),
        "duration_s": round(visual_dur, 3),
        "sfx_cues": len(cues),
        "has_music": music_buf is not None,
        "mix_time_s": round(elapsed, 1),
    }
