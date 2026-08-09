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
    "diagram_spec": {
        "type": "flow",
        "steps": [
            {"icon": "🔍", "label": "Retrieve"},
            {"icon": "📎", "label": "Augment"},
            {"icon": "✨", "label": "Generate"},
            {"icon": "✅", "label": "Answer"},
        ],
    },
}


# Tamil fixture: voiceover is ~110 words (valid 95-135 range for lang='ta')
MINIMAL_SCRIPT_TA = {
    **MINIMAL_SCRIPT,
    "voiceover": (
        "உங்கள் AI உங்களுக்கு பொய் சொல்கிறது. "
        "Large language models only know their training data. "
        "When you ask about your own documents they often guess and get it completely wrong. "
        "That is called hallucination and it is a very serious problem for any business relying on AI. "
        "RAG or Retrieval Augmented Generation fixes this without any fine-tuning or retraining. "
        "RAG fetches your actual documents at query time and injects them directly as context. "
        "Now the model answers from real verified data not outdated training memory. "
        "No retraining required no massive compute bill no months of waiting. "
        "This is how production AI systems stay accurate and up to date. "
        "Follow AI Bytes for one clear concept every single day."
    ),
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


# ── diagram_spec validation ───────────────────────────────────────────────────

def test_validate_rejects_missing_diagram_spec():
    bad = {k: v for k, v in MINIMAL_SCRIPT.items() if k != "diagram_spec"}
    with pytest.raises(ValueError, match="Missing fields"):
        script_agent._validate(bad, 1)


def test_validate_rejects_invalid_diagram_type():
    bad = {**MINIMAL_SCRIPT, "diagram_spec": {"type": "pie_chart"}}
    with pytest.raises(ValueError, match="diagram_spec.type"):
        script_agent._validate(bad, 1)


def test_validate_rejects_diagram_spec_not_object():
    bad = {**MINIMAL_SCRIPT, "diagram_spec": "flow"}
    with pytest.raises(ValueError, match="must be a JSON object"):
        script_agent._validate(bad, 1)


def test_validate_rejects_hub_spoke_missing_hub():
    bad = {**MINIMAL_SCRIPT, "diagram_spec": {"type": "hub_spoke", "spokes": ["A", "B", "C"]}}
    with pytest.raises(ValueError, match="hub"):
        script_agent._validate(bad, 1)


def test_validate_rejects_hub_spoke_too_few_spokes():
    bad = {**MINIMAL_SCRIPT, "diagram_spec": {"type": "hub_spoke", "hub": "Center", "spokes": ["A", "B"]}}
    with pytest.raises(ValueError, match="3 spokes"):
        script_agent._validate(bad, 1)


def test_validate_rejects_flow_too_few_steps():
    bad = {**MINIMAL_SCRIPT, "diagram_spec": {"type": "flow", "steps": [{"icon": "🔍", "label": "Retrieve"}]}}
    with pytest.raises(ValueError, match="2 steps"):
        script_agent._validate(bad, 1)


def test_validate_rejects_flow_step_missing_icon():
    bad = {**MINIMAL_SCRIPT, "diagram_spec": {"type": "flow", "steps": [{"label": "Retrieve"}, {"label": "Generate"}]}}
    with pytest.raises(ValueError, match="icon"):
        script_agent._validate(bad, 1)


def test_validate_rejects_bar_chart_missing_title():
    bad = {**MINIMAL_SCRIPT, "diagram_spec": {"type": "bar_chart", "bars": [{"label": "A", "value": 80}, {"label": "B", "value": 60}]}}
    with pytest.raises(ValueError, match="title"):
        script_agent._validate(bad, 1)


def test_validate_rejects_bar_chart_non_numeric_value():
    bad = {**MINIMAL_SCRIPT, "diagram_spec": {"type": "bar_chart", "title": "Test", "bars": [{"label": "A", "value": "high"}, {"label": "B", "value": 60}]}}
    with pytest.raises(ValueError, match="numeric"):
        script_agent._validate(bad, 1)


def test_validate_rejects_split_compare_missing_verdict():
    bad = {**MINIMAL_SCRIPT, "diagram_spec": {
        "type": "split_compare",
        "left": {"label": "AI", "points": ["Sounds right"]},
        "right": {"label": "Reality", "points": ["Actually wrong"]},
    }}
    with pytest.raises(ValueError, match="verdict"):
        script_agent._validate(bad, 1)


def test_validate_rejects_cluster_single_group():
    bad = {**MINIMAL_SCRIPT, "diagram_spec": {
        "type": "cluster",
        "groups": [{"label": "Only Group", "items": ["a", "b", "c"]}],
    }}
    with pytest.raises(ValueError, match="2 groups"):
        script_agent._validate(bad, 1)


def test_validate_rejects_dial_missing_ticks():
    bad = {**MINIMAL_SCRIPT, "diagram_spec": {
        "type": "dial", "label": "Temperature",
        "min_label": "Precise", "max_label": "Creative",
    }}
    with pytest.raises(ValueError, match="2 ticks"):
        script_agent._validate(bad, 1)


def test_validate_passes_all_diagram_types():
    valid_specs = [
        {"type": "hub_spoke", "hub": "MCP Server", "spokes": ["Tool A", "Tool B", "Tool C", "Tool D"]},
        {"type": "cluster", "groups": [{"label": "Animals", "items": ["cat", "dog"]}, {"label": "Vehicles", "items": ["car", "bus"]}]},
        {"type": "split_compare", "left": {"label": "AI", "points": ["Confident"]}, "right": {"label": "Reality", "points": ["Wrong"]}, "verdict": "Hallucination"},
        {"type": "dial", "label": "Temp", "min_label": "0", "max_label": "1", "ticks": [{"value": 0.0, "description": "exact"}, {"value": 1.0, "description": "wild"}]},
        {"type": "bar_chart", "title": "Accuracy", "bars": [{"label": "0-shot", "value": 45}, {"label": "3-shot", "value": 87}]},
        {"type": "side_by_side", "left": {"label": "Fine-tune", "points": ["Expensive"]}, "right": {"label": "RAG", "points": ["Flexible"]}},
        {"type": "flow", "steps": [{"icon": "🔍", "label": "Retrieve"}, {"icon": "✨", "label": "Generate"}]},
    ]
    for spec in valid_specs:
        script_agent._validate_diagram_spec(spec, 1)  # should not raise


SKETCH_SCRIPT = {
    **MINIMAL_SCRIPT,
    "diagram_spec": {"type": "sketch"},
    "sketch_spec": {
        "title": "From Text to Tokens",
        "nodes": [
            {"id": "t", "label": "Your Text", "x": 80, "y": 280, "shape": "rect", "width": 140, "height": 50},
            {"id": "tk", "label": "Tokenizer", "x": 280, "y": 280, "shape": "diamond", "width": 130, "height": 60},
            {"id": "id", "label": "Token IDs", "x": 480, "y": 180, "shape": "rect", "width": 130, "height": 50},
        ],
        "edges": [
            {"from": "t", "to": "tk", "label": "splits"},
            {"from": "tk", "to": "id", "label": "maps"},
        ],
    },
}


def test_validate_passes_valid_sketch_spec():
    script_agent._validate(SKETCH_SCRIPT, 1)  # should not raise


def test_validate_rejects_sketch_with_null_sketch_spec():
    bad = {**SKETCH_SCRIPT, "sketch_spec": None}
    with pytest.raises(ValueError, match="sketch_spec"):
        script_agent._validate(bad, 1)


def test_validate_rejects_sketch_with_missing_sketch_spec_key():
    bad = {k: v for k, v in SKETCH_SCRIPT.items() if k != "sketch_spec"}
    with pytest.raises(ValueError, match="sketch_spec"):
        script_agent._validate(bad, 1)


def test_validate_rejects_sketch_too_few_nodes():
    bad = {**SKETCH_SCRIPT, "sketch_spec": {**SKETCH_SCRIPT["sketch_spec"], "nodes": SKETCH_SCRIPT["sketch_spec"]["nodes"][:2]}}
    with pytest.raises(ValueError, match="3-6 nodes"):
        script_agent._validate(bad, 1)


def test_validate_rejects_sketch_no_edges():
    bad = {**SKETCH_SCRIPT, "sketch_spec": {**SKETCH_SCRIPT["sketch_spec"], "edges": []}}
    with pytest.raises(ValueError, match="edge"):
        script_agent._validate(bad, 1)


def test_validate_rejects_sketch_edge_bad_node_ref():
    bad = {**SKETCH_SCRIPT, "sketch_spec": {**SKETCH_SCRIPT["sketch_spec"], "edges": [{"from": "t", "to": "ghost"}]}}
    with pytest.raises(ValueError, match="node ids"):
        script_agent._validate(bad, 1)


def test_validate_ta_allows_hook_up_to_15_words():
    long_hook = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen"
    good = {**MINIMAL_SCRIPT_TA, "hook": long_hook}
    script_agent._validate(good, 1, lang="ta")  # should not raise


def test_validate_ta_rejects_hook_over_15_words():
    too_long = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen"
    bad = {**MINIMAL_SCRIPT, "hook": too_long}
    with pytest.raises(ValueError, match="15"):
        script_agent._validate(bad, 1, lang="ta")


def test_validate_ta_accepts_valid_voiceover_length():
    # 110 Tamil-length words — valid for lang='ta'
    ta_vo = " ".join(["word"] * 110)
    good = {**MINIMAL_SCRIPT, "voiceover": ta_vo}
    script_agent._validate(good, 1, lang="ta")  # should not raise


def test_validate_ta_rejects_short_voiceover():
    bad = {**MINIMAL_SCRIPT, "voiceover": "Too short."}
    with pytest.raises(ValueError, match="95"):
        script_agent._validate(bad, 1, lang="ta")


def test_validate_ta_rejects_long_voiceover():
    too_long = " ".join(["word"] * 140)
    bad = {**MINIMAL_SCRIPT, "voiceover": too_long}
    with pytest.raises(ValueError, match="135"):
        script_agent._validate(bad, 1, lang="ta")


def test_validate_en_still_rejects_ta_length_voiceover():
    # 110 words passes for Tamil but must fail for English
    short_for_en = " ".join(["word"] * 110)
    bad = {**MINIMAL_SCRIPT, "voiceover": short_for_en}
    with pytest.raises(ValueError, match="150"):
        script_agent._validate(bad, 1, lang="en")


def test_system_prompt_ta_has_word_count_instruction():
    prompt = script_agent._build_system_prompt("ta")
    assert "100-130 words" in prompt
    assert "110" in prompt  # AIM FOR target


def test_system_prompt_contains_diagram_guide():
    prompt = script_agent._build_system_prompt("en")
    assert "DIAGRAM GUIDE" in prompt
    assert "hub_spoke" in prompt
    assert "split_compare" in prompt
    assert "bar_chart" in prompt


# ── sketch routing rules in system prompt ──────────────────────────────────────

def test_system_prompt_contains_sketch_routing_section():
    prompt = script_agent._build_system_prompt("en")
    assert "DIAGRAM TYPE ROUTING" in prompt
    assert "sketch" in prompt


def test_system_prompt_sketch_routing_lists_keywords():
    prompt = script_agent._build_system_prompt("en")
    for keyword in (
        "tokenization", "training", "backpropagation", "gradient",
        "attention", "transformer", "neural network", "context window",
        "embedding", "RLHF",
    ):
        assert keyword in prompt, f"missing routing keyword: {keyword}"


def test_system_prompt_sketch_has_worked_example():
    prompt = script_agent._build_system_prompt("en")
    assert "From Text to Tokens" in prompt
    assert "Tokenizer" in prompt


def test_system_prompt_sketch_spec_field_rules():
    prompt = script_agent._build_system_prompt("en")
    assert "3 to 6 nodes" in prompt
    assert "max 18 chars" in prompt
    assert "At least 2 edges" in prompt


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
    mock_client.messages.create.return_value = _make_mock_response(MINIMAL_SCRIPT_TA)
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
    mock_client.messages.create.return_value = _make_mock_response(MINIMAL_SCRIPT_TA)
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
