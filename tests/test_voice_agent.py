"""Tests for voice_agent — all ElevenLabs and PyAV calls are mocked."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents import voice_agent


SAMPLE_SCRIPT = {
    "voiceover": (
        "Your AI is lying to you. Here is why. "
        "Large language models only know their training data and they hallucinate. "
        "RAG fixes this by fetching your actual documents at query time. "
        "Follow AI Bytes for more concepts like this every single week."
    ),
}


def _mock_av_container(duration_secs: float):
    """Return a mock av container reporting the given duration in microseconds."""
    container = MagicMock()
    container.duration = int(duration_secs * 1_000_000)
    container.__enter__ = MagicMock(return_value=container)
    container.__exit__ = MagicMock(return_value=False)
    return container


# ── _mp3_duration ─────────────────────────────────────────────────────────────

@patch("agents.voice_agent.av.open")
def test_mp3_duration_uses_container_duration(mock_av_open):
    mock_av_open.return_value = _mock_av_container(60.0)
    result = voice_agent._mp3_duration(Path("fake.mp3"))
    assert abs(result - 60.0) < 0.01


@patch("agents.voice_agent.av.open")
def test_mp3_duration_falls_back_to_stream(mock_av_open):
    container = MagicMock()
    container.duration = None  # force stream fallback
    stream = MagicMock()
    stream.duration = 1800000
    stream.time_base = 1 / 30000
    container.streams.audio = [stream]
    container.close = MagicMock()
    mock_av_open.return_value = container

    result = voice_agent._mp3_duration(Path("fake.mp3"))
    assert abs(result - 60.0) < 0.1


# ── _validate_duration ────────────────────────────────────────────────────────

@patch("agents.voice_agent._mp3_duration", return_value=60.0)
def test_validate_duration_passes_at_60s(mock_dur):
    result = voice_agent._validate_duration(Path("ok.mp3"))
    assert abs(result - 60.0) < 0.01


@patch("agents.voice_agent._mp3_duration", return_value=44.0)
def test_validate_duration_fails_below_min(mock_dur):
    with pytest.raises(ValueError, match="outside"):
        voice_agent._validate_duration(Path("short.mp3"))


@patch("agents.voice_agent._mp3_duration", return_value=75.0)
def test_validate_duration_fails_above_max(mock_dur):
    with pytest.raises(ValueError, match="outside"):
        voice_agent._validate_duration(Path("long.mp3"))


@patch("agents.voice_agent._mp3_duration", return_value=45.0)
def test_validate_duration_ta_passes_at_45s(mock_dur):
    result = voice_agent._validate_duration(Path("ta.mp3"), lang="ta")
    assert abs(result - 45.0) < 0.01


@patch("agents.voice_agent._mp3_duration", return_value=35.0)
def test_validate_duration_ta_fails_below_40s(mock_dur):
    with pytest.raises(ValueError, match="outside"):
        voice_agent._validate_duration(Path("ta_short.mp3"), lang="ta")


@patch("agents.voice_agent._mp3_duration", return_value=70.0)
def test_validate_duration_ta_fails_above_65s(mock_dur):
    with pytest.raises(ValueError, match="outside"):
        voice_agent._validate_duration(Path("ta_long.mp3"), lang="ta")


@patch("agents.voice_agent._mp3_duration", return_value=45.0)
def test_validate_duration_en_rejects_45s(mock_dur):
    with pytest.raises(ValueError, match="outside"):
        voice_agent._validate_duration(Path("en_short.mp3"), lang="en")


# ── run() — mocked API calls ──────────────────────────────────────────────────

@patch("agents.voice_agent.av.open")
@patch("agents.voice_agent.ElevenLabs")
def test_run_en_saves_en_filename(mock_elevenlabs_cls, mock_av_open, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_test")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID_EN", "voice_en_123")

    mock_client = MagicMock()
    mock_client.text_to_speech.convert.return_value = [b"fake_audio_data"]
    mock_elevenlabs_cls.return_value = mock_client
    mock_av_open.return_value = _mock_av_container(60.0)

    result = voice_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="en")

    assert result["success"] is True
    assert result["lang"] == "en"
    assert "ep01_voice_EN.mp3" in result["output_path"]
    assert Path(result["output_path"]).exists()


@patch("agents.voice_agent.av.open")
@patch("agents.voice_agent.ElevenLabs")
def test_run_ta_saves_ta_filename(mock_elevenlabs_cls, mock_av_open, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_test")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID_TA", "voice_ta_456")

    mock_client = MagicMock()
    mock_client.text_to_speech.convert.return_value = [b"fake_audio_data"]
    mock_elevenlabs_cls.return_value = mock_client
    mock_av_open.return_value = _mock_av_container(60.0)

    result = voice_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="ta")

    assert result["success"] is True
    assert result["lang"] == "ta"
    assert "ep01_voice_TA.mp3" in result["output_path"]


@patch("agents.voice_agent.av.open")
@patch("agents.voice_agent.ElevenLabs")
def test_run_ta_uses_ta_voice_id(mock_elevenlabs_cls, mock_av_open, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_test")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID_TA", "voice_ta_456")

    mock_client = MagicMock()
    mock_client.text_to_speech.convert.return_value = [b"fake_audio_data"]
    mock_elevenlabs_cls.return_value = mock_client
    mock_av_open.return_value = _mock_av_container(60.0)

    voice_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="ta")

    call_kwargs = mock_client.text_to_speech.convert.call_args[1]
    assert call_kwargs["voice_id"] == "voice_ta_456"


def test_run_rejects_invalid_lang(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    with pytest.raises(RuntimeError, match="unsupported lang"):
        voice_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="fr")


def test_run_raises_if_voiceover_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_VOICE_ID_EN", "voice_en_123")
    with pytest.raises(RuntimeError, match="no voiceover text"):
        voice_agent.run({"voiceover": ""}, episode=1, week=1, lang="en")


def test_run_raises_if_voice_id_not_set(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.delenv("ELEVENLABS_VOICE_ID_EN", raising=False)
    with pytest.raises(RuntimeError, match="ELEVENLABS_VOICE_ID_EN"):
        voice_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="en")
