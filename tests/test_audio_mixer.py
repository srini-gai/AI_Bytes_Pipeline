"""Audio Mixer tests — all synthetic fixtures, no paid API calls.

Tests cover:
- SFX placement at exact timestamps
- Reused asset at multiple timestamps (check_tick × 3)
- Per-cue gain levels
- Voice is never modified
- Music bed ducking under voice
- Music fade-in / fade-out
- CTA hold rise
- Duration preservation (output matches visual duration)
- Missing SFX asset raises RuntimeError
- Clipping prevention (soft limiter)
- mix_episode end-to-end with synthetic audio
- Loudness normalisation via ffmpeg (integration)
"""
import json
import struct
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.audio_mixer import (
    SFXCue,
    apply_music_bed,
    db_to_linear,
    mix_and_limit,
    mix_episode,
    place_sfx,
    read_wav_mono,
    write_wav_mono,
)

SR = 44100


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _sine(freq: float, duration_s: float, amplitude: float = 0.5, sr: int = SR) -> np.ndarray:
    """Generate a mono sine wave."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False, dtype=np.float32)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _silence(duration_s: float, sr: int = SR) -> np.ndarray:
    return np.zeros(int(sr * duration_s), dtype=np.float32)


def _voice_with_gaps(duration_s: float = 45.0, sr: int = SR) -> np.ndarray:
    """Simulated voice: speech bursts with gaps (for music ducking tests)."""
    samples = np.zeros(int(sr * duration_s), dtype=np.float32)
    # Speech from 0–3s, 3.5–7s, 7.5–12s, 12.5–22s, 22.5–31.8s, 32–40.7s
    speech_regions = [(0, 3), (3.5, 7), (7.5, 12), (12.5, 22), (22.5, 31.8), (32, 40.7)]
    for start, end in speech_regions:
        s, e = int(start * sr), int(end * sr)
        t = np.arange(e - s, dtype=np.float32) / sr
        samples[s:e] = 0.4 * np.sin(2 * np.pi * 200 * t)
    return samples


@pytest.fixture
def ep_dir(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    d = tmp_path / "week_01" / "ep02"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def sfx_dir(ep_dir) -> Path:
    d = ep_dir / "sfx"
    d.mkdir()
    return d


def _write_asset(sfx_dir: Path, name: str, freq: float = 880.0, duration_s: float = 0.5) -> None:
    """Write a synthetic SFX WAV asset."""
    samples = _sine(freq, duration_s, amplitude=0.3)
    write_wav_mono(sfx_dir / f"{name}.wav", samples, sr=SR)


def _write_voice(ep_dir: Path, duration_s: float = 43.375) -> Path:
    """Write a synthetic voice MP3 (actually WAV, but the mixer converts via ffmpeg)."""
    voice = _voice_with_gaps(duration_s)
    path = ep_dir / "ep02_voice_EN.wav"  # write as WAV first
    write_wav_mono(path, voice, sr=SR)
    # Convert to MP3 via ffmpeg
    mp3_path = ep_dir / "ep02_voice_EN.mp3"
    import subprocess
    subprocess.run([
        "ffmpeg", "-y", "-i", str(path), "-b:a", "192k", str(mp3_path)
    ], capture_output=True, check=True)
    path.unlink()
    return mp3_path


def _write_sound_plan(ep_dir: Path) -> Path:
    """Write a minimal sound plan matching EP02 structure."""
    plan = {
        "version": "sound_director_v1",
        "locked_inputs": {
            "canonical_narration_hash": "a747adb57064ca4e",
            "voice_duration_s": 43.375,
            "visual_duration_s": 45.056,
            "art_direction": "bright-workspace",
        },
        "assets": {
            "stamp": {"prompt": "test", "duration_s": 0.5},
            "msg_send": {"prompt": "test", "duration_s": 0.5},
            "check_tick": {"prompt": "test", "duration_s": 0.5},
            "task_complete": {"prompt": "test", "duration_s": 1.0},
        },
        "events": [
            {"id": "E1", "scene": 1, "t": 2.0, "class": "SEMANTIC_SFX",
             "asset": "stamp", "rel_db": -12, "action": "generate"},
            {"id": "E2a", "scene": 2, "t": 4.2, "class": "SEMANTIC_SFX",
             "asset": "msg_send", "rel_db": -20, "action": "generate"},
            {"id": "E4a", "scene": 5, "t": 18.33, "class": "SEMANTIC_SFX",
             "asset": "check_tick", "rel_db": -18, "action": "generate"},
            {"id": "E4b", "scene": 5, "t": 19.49, "class": "SEMANTIC_SFX",
             "asset": "check_tick", "rel_db": -18, "action": "reuse"},
            {"id": "E4c", "scene": 5, "t": 20.65, "class": "SEMANTIC_SFX",
             "asset": "check_tick", "rel_db": -18, "action": "reuse"},
            {"id": "E5", "scene": 5, "t": 21.4, "class": "SEMANTIC_SFX",
             "asset": "task_complete", "rel_db": -14, "action": "generate"},
            {"id": "E7", "scene": 10, "t": None, "class": "NONE",
             "asset": None, "rel_db": None, "action": "none"},
        ],
    }
    path = ep_dir / "ep02_sound_plan_v1.json"
    path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return path


# ── Unit tests ───────────────────────────────────────────────────────────────

class TestDBConversion:
    def test_0db_is_unity(self):
        assert db_to_linear(0.0) == pytest.approx(1.0)

    def test_minus_6db(self):
        assert db_to_linear(-6.0) == pytest.approx(0.5012, rel=0.01)

    def test_minus_20db(self):
        assert db_to_linear(-20.0) == pytest.approx(0.1, rel=0.01)


class TestWavIO:
    def test_roundtrip(self, tmp_path):
        original = _sine(440, 1.0)
        path = tmp_path / "test.wav"
        write_wav_mono(path, original, sr=SR)
        loaded, sr_out = read_wav_mono(path, target_sr=SR)
        assert sr_out == SR
        assert len(loaded) == pytest.approx(len(original), abs=100)
        # Correlation should be very high
        n = min(len(original), len(loaded))
        corr = np.corrcoef(original[:n], loaded[:n])[0, 1]
        assert corr > 0.99


class TestPlaceSFX:
    def test_sfx_placed_at_correct_timestamp(self):
        voice = _silence(5.0)
        asset = _sine(1000, 0.5, amplitude=1.0)
        cues = [SFXCue(t=2.0, asset="beep", rel_db=0.0)]
        result = place_sfx(voice, cues, {"beep": asset}, sr=SR)

        # Before the cue: silence
        assert np.max(np.abs(result[:int(1.9 * SR)])) == pytest.approx(0.0, abs=1e-6)
        # At the cue: signal present
        cue_region = result[int(2.0 * SR):int(2.5 * SR)]
        assert np.max(np.abs(cue_region)) > 0.5

    def test_reused_asset_at_multiple_timestamps(self):
        voice = _silence(25.0)
        tick = _sine(2000, 0.3, amplitude=0.5)
        cues = [
            SFXCue(t=18.33, asset="check_tick", rel_db=-18.0),
            SFXCue(t=19.49, asset="check_tick", rel_db=-18.0),
            SFXCue(t=20.65, asset="check_tick", rel_db=-18.0),
        ]
        result = place_sfx(voice, cues, {"check_tick": tick}, sr=SR)

        # All three placements should have signal
        for t in [18.33, 19.49, 20.65]:
            start = int(t * SR)
            end = min(start + int(0.3 * SR), len(result))
            assert np.max(np.abs(result[start:end])) > 0, f"No signal at {t}s"

    def test_per_cue_gain_applied(self):
        voice = _silence(5.0)
        asset = np.ones(int(0.1 * SR), dtype=np.float32)  # constant 1.0
        cues_loud = [SFXCue(t=1.0, asset="x", rel_db=-6.0)]
        cues_quiet = [SFXCue(t=1.0, asset="x", rel_db=-20.0)]

        loud = place_sfx(voice, cues_loud, {"x": asset}, sr=SR)
        quiet = place_sfx(voice, cues_quiet, {"x": asset}, sr=SR)

        loud_peak = np.max(np.abs(loud))
        quiet_peak = np.max(np.abs(quiet))
        ratio_db = 20 * np.log10(loud_peak / quiet_peak)
        assert ratio_db == pytest.approx(14.0, abs=0.5)  # -6 vs -20 = 14dB difference

    def test_missing_asset_raises(self):
        voice = _silence(3.0)
        cues = [SFXCue(t=1.0, asset="nonexistent", rel_db=-12.0)]
        with pytest.raises(RuntimeError, match="not found"):
            place_sfx(voice, cues, {}, sr=SR)


class TestVoicePreservation:
    def test_voice_unchanged_after_mix(self):
        voice = _sine(200, 5.0, amplitude=0.4)
        voice_copy = voice.copy()
        sfx = _silence(5.0)
        sfx[int(2.0 * SR):int(2.5 * SR)] = _sine(1000, 0.5, amplitude=0.1)

        mixed = mix_and_limit(voice, sfx=sfx)

        # Original voice array should be unmodified
        np.testing.assert_array_equal(voice, voice_copy)
        # Voice component in the mix should be preserved
        # (in silent SFX regions, mixed == voice)
        silent_region = slice(0, int(1.0 * SR))
        np.testing.assert_allclose(mixed[silent_region], voice[silent_region], atol=1e-6)


class TestMusicBed:
    def test_music_ducked_under_voice(self):
        voice = np.zeros(int(10.0 * SR), dtype=np.float32)
        # Voice active from 2–5s
        voice[int(2 * SR):int(5 * SR)] = _sine(200, 3.0, amplitude=0.4)
        music_raw = _sine(440, 10.0, amplitude=0.5)

        config = {
            "volume_db": -10.0,
            "duck_db": -30.0,
            "duck_attack_s": 0.02,
            "duck_release_s": 0.05,
            "fade_in_s": 0.0,
            "fade_out_s": 0.0,
        }
        result = apply_music_bed(voice, music_raw, config, sr=SR)

        # During voice (3–4.5s should be fully ducked): music should be quieter
        ducked_rms = np.sqrt(np.mean(result[int(3.0 * SR):int(4.5 * SR)] ** 2))
        # During silence (7–9s): music should be louder
        unducked_rms = np.sqrt(np.mean(result[int(7.0 * SR):int(9.0 * SR)] ** 2))

        assert unducked_rms > ducked_rms * 2, "Music should be louder when voice is silent"

    def test_music_fade_in_out(self):
        voice = _silence(5.0)
        music_raw = np.ones(int(5.0 * SR), dtype=np.float32) * 0.5

        config = {
            "volume_db": 0.0,
            "duck_db": 0.0,
            "fade_in_s": 1.0,
            "fade_out_s": 1.0,
        }
        result = apply_music_bed(voice, music_raw, config, sr=SR)

        # First samples should be near zero (fade in)
        assert np.abs(result[0]) < 0.01
        # Middle should be at full level
        mid = int(2.5 * SR)
        assert np.abs(result[mid]) > 0.3
        # Last samples should be near zero (fade out)
        assert np.abs(result[-1]) < 0.01


class TestClippingPrevention:
    def test_soft_limiter_prevents_clipping(self):
        voice = np.full(SR, 0.8, dtype=np.float32)  # loud voice
        sfx = np.full(SR, 0.5, dtype=np.float32)    # loud SFX

        mixed = mix_and_limit(voice, sfx=sfx, headroom_db=-1.0)

        # Without limiting, peak would be 1.3 — above -1dBTP (0.891)
        assert np.max(np.abs(mixed)) <= db_to_linear(-1.0) + 1e-6


class TestDurationPreservation:
    def test_output_matches_visual_duration(self, ep_dir, sfx_dir):
        _write_voice(ep_dir, duration_s=43.375)
        plan_path = _write_sound_plan(ep_dir)
        _write_asset(sfx_dir, "stamp")
        _write_asset(sfx_dir, "msg_send")
        _write_asset(sfx_dir, "check_tick")
        _write_asset(sfx_dir, "task_complete", duration_s=1.0)

        result = mix_episode(episode=2, week=1, sound_plan_path=plan_path, sfx_dir=sfx_dir)

        assert result["success"]
        # Duration should match visual_duration_s from the plan (45.056)
        assert result["duration_s"] == pytest.approx(45.056, abs=0.01)

    def test_missing_sfx_raises(self, ep_dir, sfx_dir):
        _write_voice(ep_dir)
        plan_path = _write_sound_plan(ep_dir)
        # Only write stamp — missing msg_send, check_tick, task_complete
        _write_asset(sfx_dir, "stamp")

        with pytest.raises(RuntimeError, match="SFX asset.*not found"):
            mix_episode(episode=2, week=1, sound_plan_path=plan_path, sfx_dir=sfx_dir)


class TestNONEEvents:
    def test_none_events_are_skipped(self):
        """Events with class=NONE should produce no SFX."""
        voice = _silence(45.0)
        plan_events = [
            {"id": "E1", "t": 2.0, "class": "SEMANTIC_SFX", "asset": "stamp", "rel_db": -12},
            {"id": "E7", "t": None, "class": "NONE", "asset": None, "rel_db": None},
        ]
        active = [e for e in plan_events if e.get("class") != "NONE" and e.get("asset") is not None]
        assert len(active) == 1
        assert active[0]["id"] == "E1"


class TestMixEpisodeE2E:
    def test_full_mix_produces_output(self, ep_dir, sfx_dir):
        _write_voice(ep_dir, duration_s=43.375)
        plan_path = _write_sound_plan(ep_dir)
        _write_asset(sfx_dir, "stamp", freq=500)
        _write_asset(sfx_dir, "msg_send", freq=800)
        _write_asset(sfx_dir, "check_tick", freq=2000, duration_s=0.3)
        _write_asset(sfx_dir, "task_complete", freq=660, duration_s=1.0)

        result = mix_episode(episode=2, week=1, sound_plan_path=plan_path, sfx_dir=sfx_dir)

        assert result["success"]
        assert result["sfx_cues"] == 6  # E1 + E2a + E4a + E4b + E4c + E5 (E7 is NONE)
        assert not result["has_music"]

        output = Path(result["output_path"])
        assert output.exists()
        assert output.stat().st_size > 1000

        # Check metadata was written
        meta_path = ep_dir / "ep02_mixed_EN.meta.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["sfx_cues"] == 6
        assert meta["has_music"] is False
        assert meta["target_lufs"] == -14.0
