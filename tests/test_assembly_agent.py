"""Tests for assembly_agent — FFmpeg/Whisper calls are not exercised here.
Focused on path selection logic for visuals (lang-specific file) and guard checks.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents import assembly_agent


# ── visuals path selection ─────────────────────────────────────────────────────

def test_run_en_expects_standard_visuals_file(tmp_path, monkeypatch):
    """lang='en' should look for ep01_visuals.mp4 (no suffix)."""
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    ep_dir = tmp_path / "week_01" / "ep01"
    ep_dir.mkdir(parents=True)
    # Voice exists but visuals do not — error reveals which visuals file is expected
    (ep_dir / "ep01_voice_EN.mp3").write_bytes(b"x" * 100)

    with pytest.raises(RuntimeError, match=r"ep01_visuals\.mp4"):
        assembly_agent.run(1, 1, lang="en")


def test_run_ta_expects_ta_visuals_file(tmp_path, monkeypatch):
    """lang='ta' should look for ep01_visuals_TA.mp4."""
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    ep_dir = tmp_path / "week_01" / "ep01"
    ep_dir.mkdir(parents=True)
    (ep_dir / "ep01_voice_TA.mp3").write_bytes(b"x" * 100)

    with pytest.raises(RuntimeError, match=r"ep01_visuals_TA\.mp4"):
        assembly_agent.run(1, 1, lang="ta")


def test_run_en_visuals_path_does_not_use_ta_suffix(tmp_path, monkeypatch):
    """English assembly must never look for the _TA visuals file."""
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    ep_dir = tmp_path / "week_01" / "ep01"
    ep_dir.mkdir(parents=True)
    (ep_dir / "ep01_voice_EN.mp3").write_bytes(b"x" * 100)

    with pytest.raises(RuntimeError) as exc_info:
        assembly_agent.run(1, 1, lang="en")

    assert "_TA" not in str(exc_info.value)


def test_run_raises_on_invalid_lang(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    with pytest.raises(RuntimeError, match="unsupported lang"):
        assembly_agent.run(1, 1, lang="fr")


# ── voice path ────────────────────────────────────────────────────────────────

def test_run_raises_if_voice_missing(tmp_path, monkeypatch):
    """When visuals exist but voice is absent, the voice error fires."""
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    ep_dir = tmp_path / "week_01" / "ep01"
    ep_dir.mkdir(parents=True)
    # Create the EN visuals file so the visuals check passes
    (ep_dir / "ep01_visuals.mp4").write_bytes(b"x" * 100)
    # No voice file present

    with pytest.raises(RuntimeError, match="voice not found"):
        assembly_agent.run(1, 1, lang="en")


def test_run_ta_raises_if_ta_voice_missing(tmp_path, monkeypatch):
    """Tamil assembly needs ep01_voice_TA.mp3, not the EN voice file."""
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    ep_dir = tmp_path / "week_01" / "ep01"
    ep_dir.mkdir(parents=True)
    # Create TA visuals and EN voice — but not TA voice
    (ep_dir / "ep01_visuals_TA.mp4").write_bytes(b"x" * 100)
    (ep_dir / "ep01_voice_EN.mp3").write_bytes(b"x" * 100)

    with pytest.raises(RuntimeError, match="voice not found"):
        assembly_agent.run(1, 1, lang="ta")
