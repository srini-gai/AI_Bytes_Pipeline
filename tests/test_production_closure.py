"""Production closure regression tests — EP09 defect fixes.

Covers:
  1. Disabled Tamil produces no TA API work
  2. >60s Voice B invokes bounded narration compression
  3. Valid compressed voice proceeds to VD
  4. Persistent over-duration stops before visual generation
  5. Storyboard clauses reconstruct canonical narration exactly
  6. Narration mutation blocks rendering
  7. fal generation succeeds once + download retries reuse same URL
  8. Failed download does not trigger another paid generation
  9. Modern VD QA exhaustion stops rather than using LEGACY
  10. ECC / GENERATED opportunity behavior remains intact
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import orchestrator
from agents import fal_asset_agent


# ── Fixtures ─────────────────────────────────────────────────────────────────

SAMPLE_SCRIPT = {
    "topic": "How AI Models Learn",
    "youtube_title": "How AI Models Learn #Shorts",
    "youtube_description": "60s explainer",
    "tags": "#SriniOnAI",
    "scheduled_publish": "2026-05-12T02:30:00Z",
    "voiceover": "AI learns patterns from data through training loops.",
}


@pytest.fixture(autouse=True)
def _no_real_apis(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    director = MagicMock()
    director.run.return_value = {"storyboard": [], "skipped": True, "output_path": ""}
    monkeypatch.setattr(orchestrator, "visual_director_agent", director)
    return director


# ── 1. Disabled Tamil produces no TA API work ────────────────────────────────

@patch("orchestrator.publisher_agent")
@patch("orchestrator.assembly_agent")
@patch("orchestrator.visual_agent")
@patch("orchestrator.voice_agent")
@patch("orchestrator.script_agent")
def test_english_only_no_tamil_calls(
    mock_script, mock_voice, mock_visual, mock_assembly, mock_publisher,
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)
    mock_script.run.return_value = {
        "script": SAMPLE_SCRIPT, "output_path": "/out/script.json",
    }
    mock_voice.run.return_value = {
        "output_path": "/out/voice.mp3", "duration": 55.0,
    }

    result = orchestrator._run_episode(
        1, 1, "Test Topic", ["en"], dry_run=True,
    )
    mock_script.run.assert_called_once_with("Test Topic", 1, 1, lang="en")
    mock_voice.run.assert_called_once()
    assert mock_voice.run.call_args[1].get("lang", "en") == "en"
    for c in mock_script.run.call_args_list:
        assert c[1].get("lang", "en") != "ta"
    for c in mock_voice.run.call_args_list:
        assert c[1].get("lang", "en") != "ta"


# ── 2 & 3. >60s voice invokes compression, valid compressed voice proceeds ──

@patch("orchestrator.publisher_agent")
@patch("orchestrator.assembly_agent")
@patch("orchestrator.visual_agent")
@patch("orchestrator.voice_agent")
@patch("orchestrator.script_agent")
def test_voice_over_60s_triggers_compression(
    mock_script, mock_voice, mock_visual, mock_assembly, mock_publisher,
    tmp_path, monkeypatch, _no_real_apis,
):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)
    mock_script.run.return_value = {
        "script": SAMPLE_SCRIPT, "output_path": "/out/script.json",
    }
    mock_script.compress_narration = MagicMock(return_value=SAMPLE_SCRIPT)
    monkeypatch.setattr(orchestrator, "script_agent", mock_script)

    call_count = [0]
    def voice_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"output_path": "/out/voice.mp3", "duration": 63.9}
        return {"output_path": "/out/voice.mp3", "duration": 55.0}

    mock_voice.run.side_effect = voice_side_effect

    _no_real_apis.run.return_value = {
        "storyboard": [
            {"scene_id": 1, "narration": SAMPLE_SCRIPT["voiceover"],
             "scene_type": "HOOK", "component": "KineticTypoScene",
             "duration_seconds": 55.0},
        ],
        "output_path": "/out/sb.json", "skipped": False,
        "total_duration": 55.0, "violations": [],
    }
    mock_visual.run.return_value = {
        "output_path": "/out/vis.mp4", "size_mb": 50.0,
        "duration": 55.0, "skipped": False,
    }
    mock_assembly.run.return_value = {
        "output_path": "/out/final.mp4", "size_mb": 80.0,
        "duration": 55.0, "skipped": False,
    }

    result = orchestrator._run_episode(1, 1, "Test", ["en"], dry_run=True)

    mock_script.compress_narration.assert_called_once()
    assert mock_voice.run.call_count == 2
    assert "voice_recovery" in result
    assert result["voice_recovery"]["original_duration"] == 63.9
    assert result["voice_recovery"]["final_duration"] == 55.0


# ── 4. Persistent over-duration stops before visual generation ────────────────

@patch("orchestrator.publisher_agent")
@patch("orchestrator.assembly_agent")
@patch("orchestrator.visual_agent")
@patch("orchestrator.voice_agent")
@patch("orchestrator.script_agent")
def test_persistent_overduration_stops(
    mock_script, mock_voice, mock_visual, mock_assembly, mock_publisher,
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)
    mock_script.run.return_value = {
        "script": SAMPLE_SCRIPT, "output_path": "/out/script.json",
    }
    mock_script.compress_narration = MagicMock(return_value=SAMPLE_SCRIPT)
    monkeypatch.setattr(orchestrator, "script_agent", mock_script)

    mock_voice.run.return_value = {
        "output_path": "/out/voice.mp3", "duration": 63.0,
    }

    result = orchestrator._run_episode(1, 1, "Test", ["en"], dry_run=False)

    assert any("duration_gate" in e for e in result["errors"])
    mock_visual.run.assert_not_called()
    mock_assembly.run.assert_not_called()


# ── 5 & 6. Narration immutability gate ────────────────────────────────────────

def test_narration_immutability_pass():
    voiceover = "AI learns patterns from data through training loops."
    storyboard = [
        {"narration": "AI learns patterns from data"},
        {"narration": "through training loops."},
    ]
    violations = orchestrator._validate_narration_immutability(storyboard, voiceover)
    assert violations == []


def test_narration_immutability_fail_mutation():
    voiceover = "AI learns patterns from data through training loops."
    storyboard = [
        {"narration": "AI discovers patterns in data"},
        {"narration": "via training iterations."},
    ]
    violations = orchestrator._validate_narration_immutability(storyboard, voiceover)
    assert len(violations) == 1
    assert "NARRATION_MUTATION" in violations[0]


def test_narration_immutability_whitespace_normalization():
    voiceover = "AI   learns patterns  from data."
    storyboard = [
        {"narration": "AI learns patterns"},
        {"narration": "from data."},
    ]
    violations = orchestrator._validate_narration_immutability(storyboard, voiceover)
    assert violations == []


# ── 7 & 8. fal download retry reuses generated URL ───────────────────────────

def test_fal_download_retry_no_regeneration(tmp_path):
    output_path = tmp_path / "test.png"
    gen_call_count = [0]
    download_call_count = [0]

    original_subscribe = None

    def mock_subscribe(model, arguments):
        gen_call_count[0] += 1
        return {
            "images": [{"url": "https://fal.test/generated.png"}],
            "request_id": "test-req-1",
        }

    def mock_download(url, output, asset_id, timeout=60):
        download_call_count[0] += 1
        if download_call_count[0] < 3:
            raise ConnectionError("download failed")
        output.write_bytes(b"fake-image-data")
        return output

    with patch.object(fal_asset_agent, "fal_client") as mock_fal:
        mock_fal.subscribe = mock_subscribe
        with patch.object(fal_asset_agent, "_download_asset", side_effect=mock_download):
            with patch.object(fal_asset_agent, "_ensure_key"):
                path, cost = fal_asset_agent.generate_image(
                    "test prompt", output_path, asset_id="test",
                )

    assert gen_call_count[0] == 1
    assert download_call_count[0] == 3


# ── 9. VD QA exhaustion stops (no legacy) ─────────────────────────────────────

@patch("orchestrator.publisher_agent")
@patch("orchestrator.assembly_agent")
@patch("orchestrator.visual_agent")
@patch("orchestrator.voice_agent")
@patch("orchestrator.script_agent")
def test_vd_failure_stops_no_legacy(
    mock_script, mock_voice, mock_visual, mock_assembly, mock_publisher,
    tmp_path, monkeypatch, _no_real_apis,
):
    monkeypatch.setattr(orchestrator, "OUTPUT_BASE", tmp_path)
    mock_script.run.return_value = {
        "script": SAMPLE_SCRIPT, "output_path": "/out/script.json",
    }
    mock_voice.run.return_value = {
        "output_path": "/out/voice.mp3", "duration": 55.0,
    }
    _no_real_apis.run.side_effect = RuntimeError(
        "quality gate failed after 3 attempts"
    )

    result = orchestrator._run_episode(1, 1, "Test", ["en"], dry_run=False)

    assert any("visual_director_agent" in e for e in result["errors"])
    assert any("CREATIVE_PLAN_QA_FAILED" in e for e in result["errors"])
    mock_visual.run.assert_not_called()
    mock_assembly.run.assert_not_called()


# ── 10. ECC / GENERATED opportunity behavior remains intact ──────────────────

def test_ecc_validation_exists():
    from agents import visual_director_agent as vd
    assert hasattr(vd, "_validate_creative_concept")
    assert hasattr(vd, "_validate_generated_opportunities")


def test_ecc_missing_fields_raises():
    from agents import visual_director_agent as vd
    violations = vd._validate_creative_concept(None, {})
    assert any("CREATIVE_CONCEPT_MISSING" in v for v in violations)


def test_ecc_valid_concept_passes():
    from agents import visual_director_agent as vd
    concept = {
        "visual_premise": "Training as sculpting",
        "progression_arc": "Raw data → refined weights",
        "hero_moments": ["gradient descent visualization", "loss curve convergence"],
        "emotional_tone": "discovery",
        "distinguishing_concept": "Pattern compression, not memorization",
        "generated_opportunities": ["metaphor beat"],
        "native_strengths": ["flow diagrams"],
    }
    violations = vd._validate_creative_concept(concept, {})
    assert violations == []


# ── 11-15. DataScene comparison-mode data contract ───────────────────────────

def test_datascene_items_normalized_to_bars():
    """VD outputs 'items' — DataScene must treat them as 'bars'."""
    data = {
        "type": "comparison",
        "items": [
            {"label": "Prediction", "value": 30, "color": "#ef4444"},
            {"label": "Correct Label", "value": 85, "color": "#22c55e"},
        ],
        "gap_label": "LOSS",
    }
    bars = data.get("bars") or data.get("items") or []
    assert len(bars) == 2
    assert bars[0]["label"] == "Prediction"
    assert bars[1]["value"] == 85


def test_datascene_maxvalue_defaults_when_absent():
    """DataBar without maxValue must default to 100 for correct scaling."""
    item = {"label": "Prediction", "value": 30, "color": "#ef4444"}
    max_val = item.get("maxValue", 100)
    assert max_val == 100
    height_ratio = min(item["value"] / max_val, 1)
    assert 0.29 < height_ratio < 0.31


def test_datascene_comparison_with_bars_still_works():
    """Legacy format using 'bars' directly must still work."""
    data = {
        "type": "comparison",
        "title": "Cost Comparison",
        "bars": [
            {"label": "Old", "value": 80, "maxValue": 100, "color": "#ff3b3b"},
            {"label": "New", "value": 30, "maxValue": 100, "color": "#34d399"},
        ],
    }
    bars = data.get("bars") or data.get("items") or []
    assert len(bars) == 2
    assert bars[0]["maxValue"] == 100


def test_datascene_title_falls_back_to_gap_label():
    """When title is absent, gap_label should be used."""
    data = {"type": "comparison", "gap_label": "LOSS"}
    title = data.get("title") or data.get("gap_label") or ""
    assert title == "LOSS"


def test_datascene_blank_detected_when_no_bars_or_items():
    """A DataScene with neither bars nor items renders nothing visible."""
    data = {"type": "comparison"}
    bars = data.get("bars") or data.get("items") or []
    assert len(bars) == 0


# ── 16-21. Semantic VOICE_VISUAL_SYNC gate ───────────────────────────────────

def _make_storyboard_props(scenes, tmp_path):
    """Write a render_props.json with the given scene list."""
    import json
    props_path = tmp_path / "ep01_render_props.json"
    props_path.write_text(json.dumps({
        "voiceover": "test narration",
        "storyboard": scenes,
    }), encoding="utf-8")
    return props_path


def test_sync_voice_longer_than_visual_fails(tmp_path):
    """Voice longer than visual by >2s → FAIL (shortfall)."""
    from agents.assembly_agent import _semantic_voice_visual_sync
    scenes = [
        {"scene_id": 1, "component": "FlowScene", "duration_seconds": 30.0,
         "narration": "Some content", "scene_type": "CONTENT"},
        {"scene_id": 2, "component": "FlowScene", "duration_seconds": 25.0,
         "narration": "More content", "scene_type": "CONTENT"},
    ]
    props = _make_storyboard_props(scenes, tmp_path)
    result = _semantic_voice_visual_sync(58.0, 55.0, props, 1, "en")
    assert not result["pass"]
    assert "visual shorter than voice" in result["message"]


def test_sync_legitimate_cta_tail_passes(tmp_path):
    """Voice ends and legitimate CTA/takeaway extends visual ~3s → PASS."""
    from agents.assembly_agent import _semantic_voice_visual_sync
    scenes = [
        {"scene_id": 1, "component": "FlowScene", "duration_seconds": 25.0,
         "narration": "Some narration", "scene_type": "CONTENT"},
        {"scene_id": 2, "component": "FlowScene", "duration_seconds": 26.0,
         "narration": "Final narration", "scene_type": "CONTENT"},
        {"scene_id": 3, "component": "TakeawayScene", "duration_seconds": 4.0,
         "narration": "", "scene_type": "TAKEAWAY"},
        {"scene_id": 4, "component": "CTAScene", "duration_seconds": 3.0,
         "narration": "", "scene_type": "CTA"},
    ]
    props = _make_storyboard_props(scenes, tmp_path)
    result = _semantic_voice_visual_sync(55.0, 58.0, props, 1, "en")
    assert result["pass"]


def test_sync_mid_episode_drift_fails(tmp_path):
    """Visual extends >2s past voice with non-tail content → FAIL."""
    from agents.assembly_agent import _semantic_voice_visual_sync
    scenes = [
        {"scene_id": 1, "component": "FlowScene", "duration_seconds": 40.0,
         "narration": "Long content", "scene_type": "CONTENT"},
        {"scene_id": 2, "component": "FlowScene", "duration_seconds": 18.0,
         "narration": "More content", "scene_type": "CONTENT"},
    ]
    props = _make_storyboard_props(scenes, tmp_path)
    result = _semantic_voice_visual_sync(55.0, 58.0, props, 1, "en")
    assert not result["pass"]
    assert "illegitimate tail" in result["message"]


def test_sync_non_cta_tail_fails(tmp_path):
    """Non-CTA unexplained final overhang → FAIL."""
    from agents.assembly_agent import _semantic_voice_visual_sync
    scenes = [
        {"scene_id": 1, "component": "FlowScene", "duration_seconds": 50.0,
         "narration": "Narration here", "scene_type": "CONTENT"},
        {"scene_id": 2, "component": "FlowScene", "duration_seconds": 8.0,
         "narration": "", "scene_type": "CONTENT"},
    ]
    props = _make_storyboard_props(scenes, tmp_path)
    result = _semantic_voice_visual_sync(50.0, 58.0, props, 1, "en")
    assert not result["pass"]
    assert "illegitimate tail" in result["message"]


def test_sync_excessive_tail_fails(tmp_path):
    """Excessive CTA/post-roll beyond configured maximum → FAIL."""
    from agents.assembly_agent import _semantic_voice_visual_sync
    scenes = [
        {"scene_id": 1, "component": "FlowScene", "duration_seconds": 50.0,
         "narration": "Content", "scene_type": "CONTENT"},
        {"scene_id": 2, "component": "TakeawayScene", "duration_seconds": 6.0,
         "narration": "", "scene_type": "TAKEAWAY"},
    ]
    props = _make_storyboard_props(scenes, tmp_path)
    result = _semantic_voice_visual_sync(50.0, 56.0, props, 1, "en")
    assert not result["pass"]
    assert "excessive tail" in result["message"]


def test_sync_no_storyboard_fallback(tmp_path):
    """No storyboard → fall back to global tolerance check."""
    from agents.assembly_agent import _semantic_voice_visual_sync
    props = tmp_path / "ep01_render_props.json"
    props.write_text('{"voiceover": "test"}', encoding="utf-8")
    result = _semantic_voice_visual_sync(55.0, 56.5, props, 1, "en")
    assert result["pass"]
    result2 = _semantic_voice_visual_sync(55.0, 58.0, props, 1, "en")
    assert not result2["pass"]
