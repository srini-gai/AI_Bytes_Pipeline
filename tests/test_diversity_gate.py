"""Tests for visual diversity planning (v4.2).

Regression tests covering:
  (a) recent channel fingerprints provided to planning
  (b) fingerprints channel-scoped
  (c) component families for similarity not only exact names
  (d) consecutive NATIVE-heavy triggers diversity consideration
  (e) semantic necessity can still produce consecutive NATIVE
  (f) no forced HYBRID quota
  (g) only one bounded diversity re-plan
  (h) paid fal only after diversity gate passes
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents import visual_director_agent as vda


RATIONALE = {k: "reason" for k in vda.ART_DIRECTION_RATIONALE_KEYS}
VALID_AD = {
    "id": "cinematic-dark",
    "visual_world": "cinematic dark-tech",
    "rationale": RATIONALE,
}
def _duration_decision(total: float) -> dict:
    return {
        "total_seconds": total,
        "rationale": {k: "reason" for k in vda.DURATION_RATIONALE_KEYS},
    }
SCRIPT = {
    "topic": "Test Topic", "concept": "c", "hook": "h",
    "takeaway": "t", "voiceover": "v",
}


def _scene(i: int, component: str, scene_type: str, dur: float,
           n_beats: int, visual_mode: str = "NATIVE") -> dict:
    return {
        "scene_id": i,
        "duration_seconds": dur,
        "narration": f"narration {i}",
        "scene_type": scene_type,
        "visual_goal": "goal",
        "visual_mode": visual_mode,
        "component": component,
        "objects": [],
        "animation": "moves",
        "on_screen_text": ["LABEL"],
        "transition": "cut",
        "beats": [
            {"start": b, "end": b + 1, "action": "transform",
             "claim_type": "ILLUSTRATIVE"}
            for b in range(n_beats)
        ],
    }


def _native_storyboard() -> list[dict]:
    """100% NATIVE storyboard similar to EP06. Sums to 46s."""
    return [
        _scene(1, "KineticTypoScene", "HOOK", 3.0, 2),
        _scene(2, "TransformScene", "DEMONSTRATION", 6.0, 2),
        _scene(3, "FlowScene", "FLOW", 6.0, 2),
        _scene(4, "SketchScene", "DIAGRAM", 5.0, 2),
        _scene(5, "SplitCompareScene", "COMPARISON", 5.0, 2),
        _scene(6, "PipelineScene", "FLOW", 5.0, 2),
        _scene(7, "TransformScene", "TRANSFORMATION", 5.0, 2),
        _scene(8, "DocumentRetrievalScene", "DEMONSTRATION", 5.0, 2),
        _scene(9, "TakeawayScene", "TAKEAWAY", 3.0, 0),
        _scene(10, "CTAScene", "CTA", 3.0, 0),
    ]


def _hybrid_storyboard() -> list[dict]:
    """HYBRID storyboard with GENERATED beats. Sums to 46s."""
    return [
        _scene(1, "KineticTypoScene", "HOOK", 3.0, 2),
        _scene(2, "AssetScene", "METAPHOR", 6.0, 2, "GENERATED"),
        _scene(3, "FlowScene", "FLOW", 6.0, 2),
        _scene(4, "AssetScene", "METAPHOR", 5.0, 2, "GENERATED"),
        _scene(5, "DataScene", "DATA", 5.0, 2),
        _scene(6, "TimelineScene", "DEMONSTRATION", 5.0, 2),
        _scene(7, "NumberCounterScene", "DATA", 5.0, 2),
        _scene(8, "AssetScene", "METAPHOR", 5.0, 2, "GENERATED"),
        _scene(9, "TakeawayScene", "TAKEAWAY", 3.0, 0),
        _scene(10, "CTAScene", "CTA", 3.0, 0),
    ]


def _different_native_storyboard() -> list[dict]:
    """NATIVE storyboard with very different family composition. Sums to 46s."""
    return [
        _scene(1, "KineticTypoScene", "HOOK", 3.0, 2),
        _scene(2, "DataScene", "DATA", 6.0, 2),
        _scene(3, "NumberCounterScene", "DATA", 6.0, 2),
        _scene(4, "CardStackScene", "DEMONSTRATION", 5.0, 2),
        _scene(5, "TimelineScene", "DEMONSTRATION", 5.0, 2),
        _scene(6, "ClusterScene", "DEMONSTRATION", 5.0, 2),
        _scene(7, "MeterScene", "DATA", 5.0, 2),
        _scene(8, "BarChartScene", "DATA", 5.0, 2),
        _scene(9, "TakeawayScene", "TAKEAWAY", 3.0, 0),
        _scene(10, "CTAScene", "CTA", 3.0, 0),
    ]


def _ep06_fingerprint() -> dict:
    """Fingerprint resembling the approved EP06 (100% NATIVE, bright-workspace)."""
    comps = [s["component"] for s in _native_storyboard()]
    return {
        "topic": "How RAG Actually Reduces AI Hallucinations",
        "art_direction": {"id": "bright-workspace", "light_or_dark": "light"},
        "component_sequence": comps,
        "component_families": vda.classify_component_families(comps),
        "scene_type_sequence": [s["scene_type"] for s in _native_storyboard()],
        "mode_ratio": {"native": 10, "generated": 0},
        "channel": "ai_bytes",
        "approved_at": "2026-10-10T12:00:00+00:00",
        "approved_by": "human",
    }


def _response(scenes: list[dict], art_direction: object = None) -> MagicMock:
    total = sum(s["duration_seconds"] for s in scenes)
    payload = {
        "visual_thesis": {"core_concept": "x"},
        "novelty_assessment": {"similarity_scores": {}},
        "visual_fingerprint": {"visual_thesis": "x"},
        "art_direction": art_direction or VALID_AD,
        "duration_decision": _duration_decision(total),
        "storyboard": scenes,
        "total_duration_seconds": total,
    }
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(payload))]
    msg.stop_reason = "end_turn"
    return msg


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(vda, "FINGERPRINT_PATH", tmp_path / "visual_fingerprints.json")
    monkeypatch.setattr(vda.time, "sleep", lambda s: None)
    return tmp_path


def _seed_fingerprints(env: Path, fingerprints: dict) -> None:
    """Write fingerprints to the test store."""
    store = {
        "version": "v4.2",
        "description": "test fingerprints",
        "episodes": fingerprints,
    }
    fp_path = env / "visual_fingerprints.json"
    fp_path.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _mock_client(*responses: MagicMock) -> MagicMock:
    client = MagicMock()
    client.messages.create.side_effect = list(responses)
    return client


# ── (a) recent channel fingerprints provided to planning ─────────────────────

def test_fingerprints_included_in_planning_prompt(env):
    """Fingerprints from prior episodes are included in the user message sent
    to the LLM planner so it can reason about diversity."""
    _seed_fingerprints(env, {"week09_ep06": _ep06_fingerprint()})
    # First response triggers diversity gate fail, second passes with different plan
    client = _mock_client(
        _response(_native_storyboard()),   # fails diversity gate
        _response(_hybrid_storyboard()),   # passes
    )
    with patch.object(vda.anthropic, "Anthropic", return_value=client):
        vda.run(SCRIPT, episode=7, week=9)
    prompt = client.messages.create.call_args_list[0].kwargs["messages"][0]["content"]
    assert "week09_ep06" in prompt
    assert "Component FAMILIES" in prompt
    assert "FLOW_PIPELINE" in prompt


# ── (b) fingerprints channel-scoped ──────────────────────────────────────────

def test_fingerprints_are_channel_scoped():
    """Fingerprints from a different channel are excluded from planning context."""
    fps = {
        "week01_ep01": {**_ep06_fingerprint(), "channel": "other_channel"},
        "week09_ep06": {**_ep06_fingerprint(), "channel": "ai_bytes"},
    }
    prompt = vda._format_fingerprints_for_prompt(fps, channel="ai_bytes")
    assert "week09_ep06" in prompt
    assert "week01_ep01" not in prompt


def test_fingerprints_from_other_channel_ignored_by_diversity_gate():
    """Diversity gate only compares against same-channel episodes."""
    other_channel_fp = {
        "week01_ep01": {**_ep06_fingerprint(), "channel": "other_channel"},
    }
    plan = {"storyboard": _native_storyboard()}
    gate = vda._diversity_gate(plan, other_channel_fp, channel="ai_bytes")
    assert gate["pass"] is True
    assert "no prior episodes in this channel" in gate["reason"]


# ── (c) component families for similarity not only exact names ───────────────

def test_similarity_uses_families_not_exact_component_names():
    """Two plans with different component names but same families are similar."""
    # Plan A uses FlowScene + PipelineScene (both FLOW_PIPELINE)
    plan_a = ["KineticTypoScene", "FlowScene", "PipelineScene", "TransformScene",
              "TakeawayScene", "CTAScene"]
    # Plan B uses DataFlowScene + CircularFlowScene (both FLOW_PIPELINE)
    plan_b = ["KineticTypoScene", "DataFlowScene", "CircularFlowScene", "BeforeAfterScene",
              "TakeawayScene", "CTAScene"]
    fam_a = vda.classify_component_families(plan_a)
    fam_b = vda.classify_component_families(plan_b)
    sim = vda.compute_family_similarity(fam_a, fam_b)
    assert sim["overall"] in {"MEDIUM", "HIGH"}, (
        f"Same-family components should show MEDIUM+ similarity, got {sim['overall']}"
    )


def test_different_families_show_low_similarity():
    """Plans using genuinely different component families show LOW similarity."""
    native_heavy = ["KineticTypoScene", "TransformScene", "FlowScene",
                    "SketchScene", "PipelineScene", "TakeawayScene", "CTAScene"]
    data_heavy = ["KineticTypoScene", "DataScene", "NumberCounterScene",
                  "MeterScene", "CardStackScene", "TakeawayScene", "CTAScene"]
    fam_a = vda.classify_component_families(native_heavy)
    fam_b = vda.classify_component_families(data_heavy)
    sim = vda.compute_family_similarity(fam_a, fam_b)
    assert sim["overall"] == "LOW", (
        f"Genuinely different families should show LOW, got {sim['overall']}"
    )


# ── (d) consecutive NATIVE-heavy triggers diversity consideration ────────────

def test_consecutive_native_heavy_triggers_diversity_gate_failure():
    """When the most recent approved episode is strongly NATIVE-dominant
    AND the new plan is also NATIVE-dominant with similar families,
    the diversity gate fails."""
    fps = {"week09_ep06": _ep06_fingerprint()}
    plan = {"storyboard": _native_storyboard()}
    gate = vda._diversity_gate(plan, fps)
    assert gate["pass"] is False, (
        f"Consecutive NATIVE-heavy with similar families should fail gate, "
        f"got pass={gate['pass']}: {gate['reason']}"
    )
    assert "NATIVE-dominant" in gate["reason"]


# ── (e) semantic necessity can still produce consecutive NATIVE ──────────────

def test_consecutive_native_passes_when_families_differ():
    """Even two consecutive NATIVE episodes pass the diversity gate if their
    component families are genuinely different — semantic necessity prevails."""
    fps = {"week09_ep06": _ep06_fingerprint()}
    plan = {"storyboard": _different_native_storyboard()}
    gate = vda._diversity_gate(plan, fps)
    assert gate["pass"] is True, (
        f"NATIVE plan with different families should pass, "
        f"got pass={gate['pass']}: {gate['reason']}"
    )


# ── (f) no forced HYBRID quota ──────────────────────────────────────────────

def test_no_forced_hybrid_quota():
    """The diversity gate does not impose a minimum GENERATED/HYBRID ratio.
    A 100% NATIVE plan passes when families are sufficiently different."""
    fps = {"week09_ep06": _ep06_fingerprint()}
    plan = {"storyboard": _different_native_storyboard()}
    gate = vda._diversity_gate(plan, fps)
    native_count = sum(
        1 for s in plan["storyboard"] if s["visual_mode"] == "NATIVE"
    )
    gen_count = sum(
        1 for s in plan["storyboard"] if s["visual_mode"] == "GENERATED"
    )
    assert native_count == 10 and gen_count == 0, "Test fixture must be 100% NATIVE"
    assert gate["pass"] is True


# ── (g) only one bounded diversity re-plan ───────────────────────────────────

def test_diversity_gate_triggers_only_one_replan(env):
    """When the diversity gate fails, it triggers at most ONE re-plan attempt.
    The second attempt does not re-trigger the gate even if still similar —
    the bounded flag suppresses the second diversity failure."""
    _seed_fingerprints(env, {"week09_ep06": _ep06_fingerprint()})

    # Both attempts return the same native-heavy storyboard.
    # Attempt 1 fails diversity gate and triggers re-plan.
    # Attempt 2 still looks similar but diversity_replan_done=True suppresses it.
    similar_storyboard = _native_storyboard()
    client = _mock_client(
        _response(similar_storyboard),  # attempt 1: diversity gate fails
        _response(similar_storyboard),  # attempt 2: gate suppressed (bounded)
    )
    with patch.object(vda.anthropic, "Anthropic", return_value=client):
        result = vda.run(SCRIPT, episode=7, week=9)

    assert result["success"] is True
    assert client.messages.create.call_count == 2
    # The retry prompt should contain DIVERSITY_GATE_FAIL
    retry_prompt = client.messages.create.call_args_list[1].kwargs["messages"][0]["content"]
    assert "DIVERSITY_GATE_FAIL" in retry_prompt
    assert "DIVERSITY FIX" in retry_prompt
    # The diversity gate result in the output should reflect the final state
    assert result["diversity_gate"]["pass"] is False  # still similar but accepted


# ── (h) paid fal only after diversity gate passes ────────────────────────────

def test_fal_assets_not_generated_before_diversity_gate(env):
    """The diversity gate runs BEFORE the storyboard is saved (which is
    before the visual render / fal asset generation pipeline). If the gate
    fails, the storyboard is not saved and paid generation cannot proceed."""
    _seed_fingerprints(env, {"week09_ep06": _ep06_fingerprint()})

    # First attempt: similar NATIVE plan -> diversity gate fails
    # Second attempt: hybrid plan with different families -> passes
    similar = _native_storyboard()
    diverse = _hybrid_storyboard()
    client = _mock_client(
        _response(similar),   # rejected by diversity gate
        _response(diverse),   # passes gate
    )
    with patch.object(vda.anthropic, "Anthropic", return_value=client):
        result = vda.run(SCRIPT, episode=7, week=9)

    assert result["success"] is True
    # The saved storyboard should be the diverse one, not the similar one
    sb_path = env / "week_09" / "ep07" / "ep07_storyboard_EN.json"
    saved = json.loads(sb_path.read_text(encoding="utf-8"))
    saved_comps = [s["component"] for s in saved["storyboard"]]
    assert "AssetScene" in saved_comps, (
        "Saved storyboard should be the diverse plan with AssetScene"
    )
    assert result["diversity_gate"]["pass"] is True


# ── Component family classification ──────────────────────────────────────────

def test_all_valid_components_have_family_mapping():
    """Every component in VALID_COMPONENTS should have a family mapping."""
    unmapped = vda.VALID_COMPONENTS - set(vda.COMPONENT_FAMILIES.keys())
    assert not unmapped, f"Components without family mapping: {unmapped}"


def test_classify_returns_other_for_unknown_components():
    """Unknown components map to OTHER."""
    families = vda.classify_component_families(["NonExistentScene"])
    assert families == ["OTHER"]


# ── approve_episode stores families and mode ratio ───────────────────────────

def test_approve_stores_component_families_and_mode_ratio(env):
    """approve_episode persists component_families, mode_ratio, and channel."""
    ep_dir = env / "week_02" / "ep03"
    ep_dir.mkdir(parents=True, exist_ok=True)
    path = ep_dir / "ep03_storyboard_EN.json"
    path.write_text(json.dumps({
        "topic": "Test",
        "art_direction": VALID_AD,
        "visual_fingerprint": {"visual_thesis": "x"},
        "storyboard": _hybrid_storyboard(),
    }), encoding="utf-8")

    vda.approve_episode(3, 2, approved_by="test")
    store = json.loads(vda.FINGERPRINT_PATH.read_text(encoding="utf-8"))
    fp = store["episodes"]["week02_ep03"]
    assert "component_families" in fp
    assert fp["component_families"][1] == "GENERATED_EDITORIAL"
    assert fp["mode_ratio"]["native"] == 7
    assert fp["mode_ratio"]["generated"] == 3
    assert fp["channel"] == "ai_bytes"
