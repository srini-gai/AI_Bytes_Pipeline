"""Tests for script_agent — all Claude API calls are mocked."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents import script_agent


MINIMAL_SCRIPT = {
    "episode": "01",
    "topic": "What is RAG?",
    "title": "This Is How AI Reads YOUR Documents",
    "hook": "Your AI is lying to you. Here is why.",
    "concept": "Retrieval-Augmented Generation",
    "slides": [
        {"icon": "🧠", "heading": "The Problem", "body": "LLMs hallucinate when asked about your docs."},
        {"icon": "📚", "heading": "The Fix", "body": "RAG fetches real documents at query time."},
        {"icon": "⚡", "heading": "How It Works", "body": "Query, embed, search, retrieve, inject, answer."},
        {"icon": "🎯", "heading": "Use Cases", "body": "Support bots, doc Q&A, code search."},
    ],
    "voiceover": (
        "Your AI is lying to you. Here is why. "
        "Large language models only know their training data. "
        "When you ask about your own documents they guess and often get it wrong. "
        "That is called hallucination and it is a serious problem for any business relying on AI. "
        "RAG or Retrieval Augmented Generation fixes this without any fine-tuning or retraining. "
        "Instead of guessing RAG fetches your actual documents at query time. "
        "It embeds your question searches a vector database retrieves the most relevant chunks "
        "and injects them directly into the model prompt as context. "
        "Now the model answers from real verified data not outdated training memory. "
        "No retraining required no massive compute bill no months of waiting. "
        "Just your LLM plus your real data working together in real time. "
        "This is how production AI systems stay accurate and up to date. "
        "Follow AI Bytes for one clear concept like this every single week."
    ),
    "takeaway": "RAG equals LLM plus your real data.",
    "tags": "#AIBytes #RAG #LLM #GenerativeAI",
    "youtube_title": "This Is How AI Reads YOUR Documents #Shorts",
    "youtube_description": "RAG explained in 60 seconds.\n#AIBytes #RAG #LLM",
    "scheduled_publish": "2026-05-12T02:30:00Z",
    "theme": {
        "name": "danger",
        "accent": "#ff3333",
        "accent2": "#ff6600",
        "overlay": "rgba(20,0,0,0.45)",
        "pexels_mood": "dark dramatic red",
    },
}


def _make_mock_response(data: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps(data))]
    return mock_resp


# ── _build_system_prompt ──────────────────────────────────────────────────────

def test_system_prompt_en_has_no_tamil_suffix():
    prompt = script_agent._build_system_prompt("en")
    assert "Tamil" not in prompt
    assert "தமிழ்" not in prompt


def test_system_prompt_ta_contains_tamil_instruction():
    prompt = script_agent._build_system_prompt("ta")
    assert "Tamil" in prompt
    assert "தமிழ்" in prompt
    assert "voiceover" in prompt


def test_system_prompt_ta_says_other_fields_stay_english():
    prompt = script_agent._build_system_prompt("ta")
    assert "remain in English" in prompt


# ── _validate ─────────────────────────────────────────────────────────────────

def test_validate_passes_on_good_script():
    script_agent._validate(MINIMAL_SCRIPT, 1)  # should not raise


def test_validate_rejects_missing_field():
    bad = {**MINIMAL_SCRIPT}
    del bad["hook"]
    with pytest.raises(ValueError, match="Missing fields"):
        script_agent._validate(bad, 1)


def test_validate_rejects_wrong_slide_count():
    bad = {**MINIMAL_SCRIPT, "slides": MINIMAL_SCRIPT["slides"][:3]}
    with pytest.raises(ValueError, match="4 slides"):
        script_agent._validate(bad, 1)


def test_validate_rejects_long_hook():
    bad = {**MINIMAL_SCRIPT, "hook": "one two three four five six seven eight nine ten eleven"}
    with pytest.raises(ValueError, match="10"):
        script_agent._validate(bad, 1)


def test_validate_rejects_short_voiceover():
    bad = {**MINIMAL_SCRIPT, "voiceover": "Too short."}
    with pytest.raises(ValueError, match="150"):
        script_agent._validate(bad, 1)


def test_validate_rejects_title_without_shorts():
    bad = {**MINIMAL_SCRIPT, "youtube_title": "Missing the tag"}
    with pytest.raises(ValueError, match="#Shorts"):
        script_agent._validate(bad, 1)


# ── _parse_json ───────────────────────────────────────────────────────────────

def test_parse_json_plain():
    data = {"key": "value"}
    assert script_agent._parse_json(json.dumps(data)) == data


def test_parse_json_strips_json_fence():
    raw = '```json\n{"key": "value"}\n```'
    assert script_agent._parse_json(raw) == {"key": "value"}


def test_parse_json_strips_plain_fence():
    raw = '```\n{"key": "value"}\n```'
    assert script_agent._parse_json(raw) == {"key": "value"}


# ── run() — mocked API calls ──────────────────────────────────────────────────

@patch("agents.script_agent.anthropic.Anthropic")
def test_run_en_returns_success(mock_anthropic_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_mock_response(MINIMAL_SCRIPT)
    mock_anthropic_cls.return_value = mock_client

    result = script_agent.run("What is RAG?", episode=1, week=1, lang="en")

    assert result["success"] is True
    assert result["lang"] == "en"
    assert "ep01_script_EN.json" in result["output_path"]


@patch("agents.script_agent.anthropic.Anthropic")
def test_run_ta_uses_tamil_system_prompt(mock_anthropic_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_mock_response(MINIMAL_SCRIPT)
    mock_anthropic_cls.return_value = mock_client

    script_agent.run("What is RAG?", episode=1, week=1, lang="ta")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert "Tamil" in call_kwargs["system"]
    assert "தமிழ்" in call_kwargs["system"]


@patch("agents.script_agent.anthropic.Anthropic")
def test_run_ta_saves_ta_filename(mock_anthropic_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_mock_response(MINIMAL_SCRIPT)
    mock_anthropic_cls.return_value = mock_client

    result = script_agent.run("What is RAG?", episode=1, week=1, lang="ta")

    assert "ep01_script_TA.json" in result["output_path"]
    assert Path(result["output_path"]).exists()


def test_run_rejects_invalid_lang(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    with pytest.raises(ValueError, match="Unsupported lang"):
        script_agent.run("What is RAG?", episode=1, week=1, lang="fr")


@patch("agents.script_agent.anthropic.Anthropic")
def test_run_en_system_prompt_has_no_tamil(mock_anthropic_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_mock_response(MINIMAL_SCRIPT)
    mock_anthropic_cls.return_value = mock_client

    script_agent.run("What is RAG?", episode=1, week=1, lang="en")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert "Tamil" not in call_kwargs["system"]
