"""Tests for orchestrator — agent calls are all mocked."""
import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import orchestrator


# ── _auto_week ────────────────────────────────────────────────────────────────

def test_auto_week_first_day(monkeypatch):
    monkeypatch.setenv("START_PUBLISH_DATE", "2026-05-12")
    with patch("orchestrator.date") as mock_date:
        mock_date.fromisoformat.return_value = date(2026, 5, 12)
        mock_date.today.return_value = date(2026, 5, 12)
        assert orchestrator._auto_week() == 1


def test_auto_week_second_week(monkeypatch):
    monkeypatch.setenv("START_PUBLISH_DATE", "2026-05-12")
    with patch("orchestrator.date") as mock_date:
        mock_date.fromisoformat.return_value = date(2026, 5, 12)
        mock_date.today.return_value = date(2026, 5, 19)
        assert orchestrator._auto_week() == 2


def test_auto_week_missing_env(monkeypatch):
    monkeypatch.delenv("START_PUBLISH_DATE", raising=False)
    assert orchestrator._auto_week() == 1


def test_auto_week_invalid_date(monkeypatch):
    monkeypatch.setenv("START_PUBLISH_DATE", "not-a-date")
    assert orchestrator._auto_week() == 1


# ── _load_topics ──────────────────────────────────────────────────────────────

def test_load_topics_reads_file(tmp_path, monkeypatch):
    topics_file = tmp_path / "topics.txt"
    topics_file.write_text("RAG\nLLMs\n# comment\n\nAgents\n", encoding="utf-8")
    monkeypatch.setattr(orchestrator, "TOPICS_FILE", topics_file)
    topics = orchestrator._load_topics()
    assert topics == ["RAG", "LLMs", "Agents"]


def test_load_topics_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator, "TOPICS_FILE", tmp_path / "missing.txt")
    with pytest.raises(FileNotFoundError):
        orchestrator._load_topics()


def test_load_topics_empty_file(tmp_path, monkeypatch):
    topics_file = tmp_path / "topics.txt"
    topics_file.write_text("# only a comment\n", encoding="utf-8")
    monkeypatch.setattr(orchestrator, "TOPICS_FILE", topics_file)
    with pytest.raises(ValueError, match="empty"):
        orchestrator._load_topics()


def test_load_topics_explicit_path(tmp_path):
    custom = tmp_path / "topics_ta.txt"
    custom.write_text("RAG Tamil\nLLM Tamil\n", encoding="utf-8")
    topics = orchestrator._load_topics(custom)
    assert topics == ["RAG Tamil", "LLM Tamil"]


def test_load_topics_explicit_path_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        orchestrator._load_topics(tmp_path / "nonexistent.txt")


# ── _load_script_from_disk ────────────────────────────────────────────────────

def test_load_script_from_disk_found(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)
    ep_dir = tmp_path / "week_01" / "ep01"
    ep_dir.mkdir(parents=True)
    (ep_dir / "ep01_script_EN.json").write_text(
        json.dumps({"topic": "RAG"}), encoding="utf-8"
    )
    result = orchestrator._load_script_from_disk(1, 1, "en")
    assert result == {"topic": "RAG"}


def test_load_script_from_disk_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)
    assert orchestrator._load_script_from_disk(1, 1, "en") is None


def test_load_script_from_disk_invalid_json(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)
    ep_dir = tmp_path / "week_01" / "ep01"
    ep_dir.mkdir(parents=True)
    (ep_dir / "ep01_script_EN.json").write_text("not json", encoding="utf-8")
    assert orchestrator._load_script_from_disk(1, 1, "en") is None


# ── _validate_config ──────────────────────────────────────────────────────────

def test_validate_config_all_configured(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-real")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_real")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "real-token")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID_EN", "voice_en")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID_EN", "UC_real")
    issues = orchestrator._validate_config(["en"])
    assert issues == []


def test_validate_config_missing_anthropic(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_real")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "real-token")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID_EN", "voice_en")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID_EN", "UC_real")
    issues = orchestrator._validate_config(["en"])
    assert any("ANTHROPIC_API_KEY" in i for i in issues)


def test_validate_config_placeholder_voice_id(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-real")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_real")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "real-token")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID_EN", "your-voice-id")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID_EN", "UC_real")
    issues = orchestrator._validate_config(["en"])
    assert any("ELEVENLABS_VOICE_ID_EN" in i for i in issues)


# ── _run_episode ──────────────────────────────────────────────────────────────

SAMPLE_SCRIPT = {
    "topic": "RAG",
    "youtube_title": "RAG Explained #Shorts",
    "youtube_description": "60s explainer",
    "tags": "#AIBytes #RAG",
    "scheduled_publish": "2026-05-12T02:30:00Z",
    "voiceover": "test",
}


@patch("orchestrator.publisher_agent")
@patch("orchestrator.assembly_agent")
@patch("orchestrator.visual_agent")
@patch("orchestrator.voice_agent")
@patch("orchestrator.script_agent")
def test_run_episode_happy_path(
    mock_script, mock_voice, mock_visual, mock_assembly, mock_publisher,
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)

    mock_script.run.return_value = {"script": SAMPLE_SCRIPT, "output_path": "/out/ep01_script_EN.json"}
    mock_voice.run.return_value = {"output_path": "/out/ep01_voice_EN.mp3", "duration": 60.0}
    mock_visual.run.return_value = {"output_path": "/out/ep01_visuals.mp4", "size_mb": 50.0, "duration": 60.0, "skipped": False}
    mock_assembly.run.return_value = {"output_path": "/out/ep01_final_EN.mp4", "size_mb": 80.0, "duration": 60.0, "skipped": False}
    mock_publisher.run.return_value = {"video_url": "https://youtube.com/watch?v=abc", "video_id": "abc", "skipped": False, "scheduled_publish": "2026-05-12T02:30:00Z"}

    result = orchestrator._run_episode(1, 1, "RAG", ["en"], dry_run=False)

    assert result["errors"] == []
    assert "en" in result["langs"]
    assert result["langs"]["en"]["video_url"] == "https://youtube.com/watch?v=abc"
    mock_script.run.assert_called_once_with("RAG", 1, 1, lang="en")
    mock_visual.run.assert_called_once()
    mock_assembly.run.assert_called_once_with(1, 1, lang="en")
    mock_publisher.run.assert_called_once()


@patch("orchestrator.publisher_agent")
@patch("orchestrator.assembly_agent")
@patch("orchestrator.visual_agent")
@patch("orchestrator.voice_agent")
@patch("orchestrator.script_agent")
def test_run_episode_dry_run_skips_visual_assembly_publish(
    mock_script, mock_voice, mock_visual, mock_assembly, mock_publisher,
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)

    mock_script.run.return_value = {"script": SAMPLE_SCRIPT, "output_path": "/out/script.json"}
    mock_voice.run.return_value = {"output_path": "/out/voice.mp3", "duration": 60.0}

    result = orchestrator._run_episode(1, 1, "RAG", ["en"], dry_run=True)

    assert result["errors"] == []
    mock_script.run.assert_called_once()
    mock_voice.run.assert_called_once()
    mock_visual.run.assert_not_called()
    mock_assembly.run.assert_not_called()
    mock_publisher.run.assert_not_called()


@patch("orchestrator.publisher_agent")
@patch("orchestrator.assembly_agent")
@patch("orchestrator.visual_agent")
@patch("orchestrator.voice_agent")
@patch("orchestrator.script_agent")
def test_run_episode_uses_cached_script(
    mock_script, mock_voice, mock_visual, mock_assembly, mock_publisher,
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)

    # Pre-write a script to disk
    ep_dir = tmp_path / "week_01" / "ep01"
    ep_dir.mkdir(parents=True)
    (ep_dir / "ep01_script_EN.json").write_text(
        json.dumps(SAMPLE_SCRIPT), encoding="utf-8"
    )

    mock_voice.run.return_value = {"output_path": "/out/voice.mp3", "duration": 60.0}
    mock_visual.run.return_value = {"output_path": "/out/visuals.mp4", "size_mb": 50.0, "duration": 60.0, "skipped": False}
    mock_assembly.run.return_value = {"output_path": "/out/final.mp4", "size_mb": 80.0, "duration": 60.0, "skipped": False}
    mock_publisher.run.return_value = {"video_url": "https://youtube.com/watch?v=xyz", "skipped": False, "scheduled_publish": ""}

    orchestrator._run_episode(1, 1, "RAG", ["en"], dry_run=False)

    # script_agent.run should NOT be called since script is on disk
    mock_script.run.assert_not_called()


@patch("orchestrator.publisher_agent")
@patch("orchestrator.assembly_agent")
@patch("orchestrator.visual_agent")
@patch("orchestrator.voice_agent")
@patch("orchestrator.script_agent")
def test_run_episode_visual_failure_skips_assembly_and_publish(
    mock_script, mock_voice, mock_visual, mock_assembly, mock_publisher,
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)

    mock_script.run.return_value = {"script": SAMPLE_SCRIPT, "output_path": "/out/script.json"}
    mock_voice.run.return_value = {"output_path": "/out/voice.mp3", "duration": 60.0}
    mock_visual.run.side_effect = RuntimeError("render failed")

    result = orchestrator._run_episode(1, 1, "RAG", ["en"], dry_run=False)

    assert any("visual_agent" in e for e in result["errors"])
    mock_assembly.run.assert_not_called()
    mock_publisher.run.assert_not_called()


@patch("orchestrator.publisher_agent")
@patch("orchestrator.assembly_agent")
@patch("orchestrator.visual_agent")
@patch("orchestrator.voice_agent")
@patch("orchestrator.script_agent")
def test_run_episode_script_failure_skips_all_downstream(
    mock_script, mock_voice, mock_visual, mock_assembly, mock_publisher,
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)
    mock_script.run.side_effect = RuntimeError("Claude API down")

    result = orchestrator._run_episode(1, 1, "RAG", ["en"], dry_run=False)

    assert any("script_agent" in e for e in result["errors"])
    mock_voice.run.assert_not_called()
    mock_visual.run.assert_not_called()
    mock_assembly.run.assert_not_called()
    mock_publisher.run.assert_not_called()


@patch("orchestrator.publisher_agent")
@patch("orchestrator.assembly_agent")
@patch("orchestrator.visual_agent")
@patch("orchestrator.voice_agent")
@patch("orchestrator.script_agent")
def test_run_episode_voice_failure_skips_assembly_and_publish(
    mock_script, mock_voice, mock_visual, mock_assembly, mock_publisher,
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)

    mock_script.run.return_value = {"script": SAMPLE_SCRIPT, "output_path": "/out/script.json"}
    mock_voice.run.side_effect = RuntimeError("ElevenLabs quota")
    mock_visual.run.return_value = {"output_path": "/out/visuals.mp4", "size_mb": 50.0, "duration": 60.0, "skipped": False}

    result = orchestrator._run_episode(1, 1, "RAG", ["en"], dry_run=False)

    assert any("voice_agent" in e for e in result["errors"])
    mock_assembly.run.assert_not_called()
    mock_publisher.run.assert_not_called()


@patch("orchestrator.publisher_agent")
@patch("orchestrator.assembly_agent")
@patch("orchestrator.visual_agent")
@patch("orchestrator.voice_agent")
@patch("orchestrator.script_agent")
def test_run_episode_publish_skipped_if_already_uploaded(
    mock_script, mock_voice, mock_visual, mock_assembly, mock_publisher,
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)

    mock_script.run.return_value = {"script": SAMPLE_SCRIPT, "output_path": "/out/script.json"}
    mock_voice.run.return_value = {"output_path": "/out/voice.mp3", "duration": 60.0}
    mock_visual.run.return_value = {"output_path": "/out/visuals.mp4", "size_mb": 50.0, "duration": 60.0, "skipped": False}
    mock_assembly.run.return_value = {"output_path": "/out/final.mp4", "size_mb": 80.0, "duration": 60.0, "skipped": False}
    mock_publisher.run.return_value = {
        "video_url": "https://youtube.com/watch?v=existing",
        "video_id": "existing",
        "skipped": True,
        "scheduled_publish": "",
    }

    result = orchestrator._run_episode(1, 1, "RAG", ["en"], dry_run=False)

    assert result["errors"] == []
    assert result["langs"]["en"]["video_url"] == "https://youtube.com/watch?v=existing"
