"""Tests for publisher_agent — all Google API calls are mocked."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents import publisher_agent


# ── fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_SCRIPT = {
    "youtube_title": "What Is RAG? AI Reads Your Docs #Shorts",
    "youtube_description": "RAG explained in 60 seconds.\n#AIBytes #RAG",
    "tags": "#AIBytes #RAG #LLM #GenerativeAI",
    "scheduled_publish": "2026-05-12T02:30:00Z",
}


def _make_final_mp4(ep_dir: Path, lang: str = "en") -> Path:
    """Create a stub final MP4 large enough to pass the existence check."""
    ep_dir.mkdir(parents=True, exist_ok=True)
    path = ep_dir / f"ep01_final_{lang.upper()}.mp4"
    path.write_bytes(b"0" * 600_000)   # 600 KB stub
    return path


def _env(monkeypatch, lang: str = "en", **overrides):
    # OUTPUT_BASE_PATH is always set explicitly by each test before calling _env
    defaults = {
        "YOUTUBE_REFRESH_TOKEN": "test-refresh-token",
        "YOUTUBE_CLIENT_ID": "test-client-id",
        "YOUTUBE_CLIENT_SECRET": "test-client-secret",
        f"YOUTUBE_CHANNEL_ID_{lang.upper()}": f"UC_{lang}_test",
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        monkeypatch.setenv(k, v)


# ── _parse_tags ───────────────────────────────────────────────────────────────

def test_parse_tags_space_separated():
    assert publisher_agent._parse_tags("#AIBytes #RAG #LLM") == ["AIBytes", "RAG", "LLM"]


def test_parse_tags_comma_separated():
    assert publisher_agent._parse_tags("#AIBytes,#RAG,#LLM") == ["AIBytes", "RAG", "LLM"]


def test_parse_tags_ignores_non_hash():
    assert publisher_agent._parse_tags("no hash here") == []


# ── _build_credentials_from_env ───────────────────────────────────────────────

@patch("agents.publisher_agent.Request")
@patch("agents.publisher_agent.Credentials")
def test_env_credentials_uses_refresh_token(mock_creds_cls, mock_request, monkeypatch):
    monkeypatch.delenv("YOUTUBE_REFRESH_TOKEN_EN", raising=False)  # ensure fallback path
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "real-refresh-token")
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "client-id")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "client-secret")

    mock_creds = MagicMock()
    mock_creds_cls.return_value = mock_creds

    result = publisher_agent._build_credentials_from_env()

    mock_creds_cls.assert_called_once()
    call_kwargs = mock_creds_cls.call_args[1]
    assert call_kwargs["refresh_token"] == "real-refresh-token"
    assert call_kwargs["client_id"] == "client-id"
    mock_creds.refresh.assert_called_once()
    assert result is mock_creds


def test_env_credentials_returns_none_if_placeholder(monkeypatch):
    monkeypatch.delenv("YOUTUBE_REFRESH_TOKEN_EN", raising=False)
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "your-refresh-token")
    assert publisher_agent._build_credentials_from_env() is None


def test_env_credentials_returns_none_if_missing(monkeypatch):
    monkeypatch.delenv("YOUTUBE_REFRESH_TOKEN_EN", raising=False)
    monkeypatch.delenv("YOUTUBE_REFRESH_TOKEN_TA", raising=False)
    monkeypatch.delenv("YOUTUBE_REFRESH_TOKEN", raising=False)
    assert publisher_agent._build_credentials_from_env() is None


@patch("agents.publisher_agent.Request")
@patch("agents.publisher_agent.Credentials")
def test_env_credentials_ta_uses_ta_token(mock_creds_cls, mock_request, monkeypatch):
    """lang='ta' must use YOUTUBE_REFRESH_TOKEN_TA, never the EN token."""
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN_TA", "ta-refresh-token")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN_EN", "en-refresh-token")
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "client-id")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "client-secret")

    mock_creds = MagicMock()
    mock_creds_cls.return_value = mock_creds

    publisher_agent._build_credentials_from_env(lang="ta")

    call_kwargs = mock_creds_cls.call_args[1]
    assert call_kwargs["refresh_token"] == "ta-refresh-token"


@patch("agents.publisher_agent.Request")
@patch("agents.publisher_agent.Credentials")
def test_env_credentials_en_uses_en_specific_token(mock_creds_cls, mock_request, monkeypatch):
    """lang='en' with YOUTUBE_REFRESH_TOKEN_EN set must use that token."""
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN_EN", "en-specific-token")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "generic-token")
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "client-id")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "client-secret")

    mock_creds = MagicMock()
    mock_creds_cls.return_value = mock_creds

    publisher_agent._build_credentials_from_env(lang="en")

    call_kwargs = mock_creds_cls.call_args[1]
    assert call_kwargs["refresh_token"] == "en-specific-token"


@patch("agents.publisher_agent.Request")
@patch("agents.publisher_agent.Credentials")
def test_env_credentials_en_falls_back_to_generic_token(mock_creds_cls, mock_request, monkeypatch):
    """When YOUTUBE_REFRESH_TOKEN_EN is absent, EN falls back to YOUTUBE_REFRESH_TOKEN."""
    monkeypatch.delenv("YOUTUBE_REFRESH_TOKEN_EN", raising=False)
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "generic-token")
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "client-id")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "client-secret")

    mock_creds = MagicMock()
    mock_creds_cls.return_value = mock_creds

    publisher_agent._build_credentials_from_env(lang="en")

    call_kwargs = mock_creds_cls.call_args[1]
    assert call_kwargs["refresh_token"] == "generic-token"


# ── run() — happy path ────────────────────────────────────────────────────────

@patch("agents.publisher_agent._get_youtube_client")
def test_run_uploads_and_saves_receipt(mock_get_yt, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    _env(monkeypatch, lang="en")
    ep_dir = tmp_path / "week_01" / "ep01"
    _make_final_mp4(ep_dir, "en")

    mock_yt = MagicMock()
    mock_yt.videos().insert().next_chunk.return_value = (None, {"id": "vid_abc123"})
    mock_get_yt.return_value = mock_yt

    with patch("agents.publisher_agent.MediaFileUpload"):
        result = publisher_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="en")

    assert result["success"] is True
    assert result["video_id"] == "vid_abc123"
    assert "youtube.com/watch?v=vid_abc123" in result["video_url"]
    assert result["lang"] == "en"
    assert result["scheduled_publish"] == "2026-05-12T02:30:00Z"

    receipt_path = ep_dir / "ep01_upload_EN.json"
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["video_id"] == "vid_abc123"
    assert receipt["channel_id"] == "UC_en_test"


@patch("agents.publisher_agent._get_youtube_client")
def test_run_sets_scheduled_privacy(mock_get_yt, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    _env(monkeypatch, lang="en")
    ep_dir = tmp_path / "week_01" / "ep01"
    _make_final_mp4(ep_dir, "en")

    mock_yt = MagicMock()
    mock_yt.videos().insert().next_chunk.return_value = (None, {"id": "vid_xyz"})
    mock_get_yt.return_value = mock_yt

    with patch("agents.publisher_agent.MediaFileUpload"):
        publisher_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="en")

    insert_call = mock_yt.videos().insert.call_args
    body = insert_call[1]["body"]
    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["publishAt"] == "2026-05-12T02:30:00Z"


@patch("agents.publisher_agent._get_youtube_client")
def test_run_immediate_publish_sets_public(mock_get_yt, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    _env(monkeypatch, lang="en")
    ep_dir = tmp_path / "week_01" / "ep01"
    _make_final_mp4(ep_dir, "en")

    mock_yt = MagicMock()
    mock_yt.videos().insert().next_chunk.return_value = (None, {"id": "vid_pub"})
    mock_get_yt.return_value = mock_yt

    script_no_schedule = {**SAMPLE_SCRIPT, "scheduled_publish": ""}

    with patch("agents.publisher_agent.MediaFileUpload"):
        publisher_agent.run(script_no_schedule, episode=1, week=1, lang="en")

    insert_call = mock_yt.videos().insert.call_args
    body = insert_call[1]["body"]
    assert body["status"]["privacyStatus"] == "public"
    assert "publishAt" not in body["status"]


@patch("agents.publisher_agent._get_youtube_client")
def test_run_ta_uses_ta_channel(mock_get_yt, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    _env(monkeypatch, lang="ta")
    ep_dir = tmp_path / "week_01" / "ep01"
    _make_final_mp4(ep_dir, "ta")

    mock_yt = MagicMock()
    mock_yt.videos().insert().next_chunk.return_value = (None, {"id": "vid_ta"})
    mock_get_yt.return_value = mock_yt

    with patch("agents.publisher_agent.MediaFileUpload"):
        result = publisher_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="ta")

    assert result["lang"] == "ta"
    receipt_path = ep_dir / "ep01_upload_TA.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["channel_id"] == "UC_ta_test"


# ── run() — idempotency ───────────────────────────────────────────────────────

@patch("agents.publisher_agent._get_youtube_client")
def test_run_skips_if_receipt_exists(mock_get_yt, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    _env(monkeypatch, lang="en")
    ep_dir = tmp_path / "week_01" / "ep01"
    ep_dir.mkdir(parents=True)

    existing = {
        "video_id": "already_uploaded",
        "video_url": "https://www.youtube.com/watch?v=already_uploaded",
        "lang": "en",
        "scheduled_publish": "2026-05-12T02:30:00Z",
        "channel_id": "UC_en_test",
        "upload_time_s": 12.3,
    }
    (ep_dir / "ep01_upload_EN.json").write_text(
        json.dumps(existing), encoding="utf-8"
    )

    result = publisher_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="en")

    assert result["skipped"] is True
    assert result["video_id"] == "already_uploaded"
    mock_get_yt.assert_not_called()


# ── run() — error handling ────────────────────────────────────────────────────

def test_run_raises_if_final_video_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    _env(monkeypatch, lang="en")

    with pytest.raises(RuntimeError, match="final video not found"):
        publisher_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="en")


def test_run_raises_if_channel_not_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    _env(monkeypatch, lang="en")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID_EN", "your-english-channel-id")
    ep_dir = tmp_path / "week_01" / "ep01"
    _make_final_mp4(ep_dir, "en")

    with pytest.raises(RuntimeError, match="YOUTUBE_CHANNEL_ID_EN"):
        publisher_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="en")


def test_run_raises_on_invalid_lang(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    with pytest.raises(RuntimeError, match="unsupported lang"):
        publisher_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="fr")


@patch("agents.publisher_agent._get_youtube_client")
def test_run_en_does_not_use_ta_channel(mock_get_yt, tmp_path, monkeypatch):
    """Even when both channels are configured, EN run must use YOUTUBE_CHANNEL_ID_EN."""
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test-refresh-token")
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID_EN", "UC_english_channel")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID_TA", "UC_tamil_channel")
    ep_dir = tmp_path / "week_01" / "ep01"
    _make_final_mp4(ep_dir, "en")

    mock_yt = MagicMock()
    mock_yt.videos().insert().next_chunk.return_value = (None, {"id": "vid_en"})
    mock_get_yt.return_value = mock_yt

    with patch("agents.publisher_agent.MediaFileUpload"):
        result = publisher_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="en")

    receipt_path = ep_dir / "ep01_upload_EN.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["channel_id"] == "UC_english_channel"
    assert receipt["channel_id"] != "UC_tamil_channel"


@patch("agents.publisher_agent._get_youtube_client")
def test_run_ta_does_not_use_en_channel(mock_get_yt, tmp_path, monkeypatch):
    """Tamil run must use YOUTUBE_CHANNEL_ID_TA, never YOUTUBE_CHANNEL_ID_EN."""
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test-refresh-token")
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID_EN", "UC_english_channel")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID_TA", "UC_tamil_channel")
    ep_dir = tmp_path / "week_01" / "ep01"
    _make_final_mp4(ep_dir, "ta")

    mock_yt = MagicMock()
    mock_yt.videos().insert().next_chunk.return_value = (None, {"id": "vid_ta"})
    mock_get_yt.return_value = mock_yt

    with patch("agents.publisher_agent.MediaFileUpload"):
        result = publisher_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="ta")

    receipt_path = ep_dir / "ep01_upload_TA.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["channel_id"] == "UC_tamil_channel"
    assert receipt["channel_id"] != "UC_english_channel"
