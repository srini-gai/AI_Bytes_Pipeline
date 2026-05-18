"""Tests for assembly_agent — FFmpeg/Whisper calls are not exercised here.
Focused on path selection logic for visuals (lang-specific file) and guard checks,
plus _validate_output duration window per language.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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


# ── _validate_output duration windows ─────────────────────────────────────────

def _make_mock_av_container(duration_secs: float, width: int = 1080, height: int = 1920):
    """Return a mock av container with the given duration and dimensions."""
    vs = MagicMock()
    vs.codec_context.width = width
    vs.codec_context.height = height
    vs.duration = None
    vs.time_base = None

    container = MagicMock()
    container.duration = int(duration_secs * 1_000_000)
    container.streams.video = [vs]
    return container


@patch("agents.assembly_agent.av.open")
def test_validate_output_en_passes_at_60s(mock_av_open, tmp_path):
    path = tmp_path / "final.mp4"
    path.write_bytes(b"x" * 600_000)
    mock_av_open.return_value = _make_mock_av_container(60.0)
    result = assembly_agent._validate_output(path, 1, lang="en")
    assert abs(result - 60.0) < 0.01


@patch("agents.assembly_agent.av.open")
def test_validate_output_en_fails_below_55s(mock_av_open, tmp_path):
    path = tmp_path / "final.mp4"
    path.write_bytes(b"x" * 600_000)
    mock_av_open.return_value = _make_mock_av_container(50.0)
    with pytest.raises(RuntimeError, match="outside"):
        assembly_agent._validate_output(path, 1, lang="en")


@patch("agents.assembly_agent.av.open")
def test_validate_output_ta_passes_at_40s(mock_av_open, tmp_path):
    """40s is valid for Tamil (35-65s window) but would fail EN (55-65s)."""
    path = tmp_path / "final.mp4"
    path.write_bytes(b"x" * 600_000)
    mock_av_open.return_value = _make_mock_av_container(40.0)
    result = assembly_agent._validate_output(path, 1, lang="ta")
    assert abs(result - 40.0) < 0.01


@patch("agents.assembly_agent.av.open")
def test_validate_output_ta_fails_below_35s(mock_av_open, tmp_path):
    path = tmp_path / "final.mp4"
    path.write_bytes(b"x" * 600_000)
    mock_av_open.return_value = _make_mock_av_container(30.0)
    with pytest.raises(RuntimeError, match="outside"):
        assembly_agent._validate_output(path, 1, lang="ta")


@patch("agents.assembly_agent.av.open")
def test_validate_output_ta_fails_above_65s(mock_av_open, tmp_path):
    path = tmp_path / "final.mp4"
    path.write_bytes(b"x" * 600_000)
    mock_av_open.return_value = _make_mock_av_container(70.0)
    with pytest.raises(RuntimeError, match="outside"):
        assembly_agent._validate_output(path, 1, lang="ta")


@patch("agents.assembly_agent.av.open")
def test_validate_output_en_rejects_40s(mock_av_open, tmp_path):
    """40s passes Tamil but must fail English."""
    path = tmp_path / "final.mp4"
    path.write_bytes(b"x" * 600_000)
    mock_av_open.return_value = _make_mock_av_container(40.0)
    with pytest.raises(RuntimeError, match="outside"):
        assembly_agent._validate_output(path, 1, lang="en")
