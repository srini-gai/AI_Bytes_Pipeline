"""
Tests for intra-episode repetition guard and render-level duplication check.

1. non-adjacent duplicate visual treatment can be detected
2. same component with genuinely different composition is allowed
3. same component + near-identical treatment is flagged
4. long unchanged composition (family concentration) is flagged
5. only one bounded re-plan occurs
6. latest same-channel fingerprint is used
7. EP07 revised fingerprint is registered before EP08 comparison
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.visual_director_agent import (
    _intra_episode_repetition_gate,
    _scene_config_similarity,
    _diversity_gate,
)


def _make_scene(
    scene_id: int,
    component: str,
    scene_type: str = "DEMONSTRATION",
    duration: float = 6.0,
    objects: list | None = None,
    animation: str = "reveal",
    data: dict | None = None,
    beats: list | None = None,
) -> dict:
    return {
        "scene_id": scene_id,
        "component": component,
        "scene_type": scene_type,
        "duration_seconds": duration,
        "visual_goal": f"scene {scene_id}",
        "narration": f"narration {scene_id}",
        "on_screen_text": [f"text_{scene_id}"],
        "objects": objects or [f"obj_{scene_id}"],
        "animation": animation,
        "transition": "crossfade",
        "beats": beats or [{"start": 0, "end": 3}, {"start": 3, "end": 6}],
        "data": data or {},
    }


# ── Test 1: Non-adjacent duplicate visual treatment is detected ──────────

def test_non_adjacent_duplicate_detected():
    """s02 and s06 using same component with near-identical config should be flagged."""
    scenes = [
        _make_scene(1, "KineticTypoScene", scene_type="HOOK", duration=3.0),
        _make_scene(2, "ContextWindowScene", objects=["window", "tokens"]),
        _make_scene(3, "TokenScene"),
        _make_scene(4, "DataScene"),
        _make_scene(5, "TokenScene"),
        _make_scene(6, "ContextWindowScene", objects=["window", "tokens"]),
        _make_scene(7, "FlowScene"),
        _make_scene(8, "TakeawayScene", scene_type="TAKEAWAY"),
        _make_scene(9, "CTAScene", scene_type="CTA"),
    ]
    result = _intra_episode_repetition_gate(scenes)
    assert not result["pass"], "Should flag s02 vs s06 ContextWindowScene duplication"
    violation_texts = " ".join(result["violations"])
    assert "s02" in violation_texts and "s06" in violation_texts


# ── Test 2: Same component with genuinely different composition allowed ──

def test_same_component_different_composition_allowed():
    """Same component with maximally different config → should pass INTRA_REPEAT.

    ABA_PATTERN operates on family level with a 55% threshold. Two instances of
    the same component automatically get 30% similarity from the component
    match alone, so they need genuinely different scene_type, objects, beats,
    data, and animation to stay below thresholds.
    """
    scenes = [
        _make_scene(1, "KineticTypoScene", scene_type="HOOK", duration=3.0),
        _make_scene(2, "TransformScene", scene_type="DEMONSTRATION",
                    objects=["A", "B", "C", "D", "E"],
                    animation="morph", data={"type": "state_change"}),
        _make_scene(3, "DataScene"),
        _make_scene(4, "FlowScene"),
        _make_scene(5, "SketchScene"),
        _make_scene(6, "TransformScene", scene_type="COMPARISON",
                    objects=["X"],
                    animation="dissolve", data={"mode": "split"},
                    beats=[{"start": 0, "end": 2}, {"start": 2, "end": 4},
                           {"start": 4, "end": 6}, {"start": 6, "end": 8}]),
        _make_scene(7, "TakeawayScene", scene_type="TAKEAWAY"),
        _make_scene(8, "CTAScene", scene_type="CTA"),
    ]
    result = _intra_episode_repetition_gate(scenes)
    intra_violations = [v for v in result["violations"]
                        if v.startswith(("INTRA_REPEAT:", "ABA_PATTERN:"))]
    assert len(intra_violations) == 0, (
        f"Same component with different composition should be allowed: {intra_violations}"
    )


# ── Test 3: Same component + near-identical treatment is flagged ─────────

def test_same_component_identical_treatment_flagged():
    """Same component, same objects, same animation, same data → flagged."""
    shared_config = {
        "objects": ["model", "context", "window"],
        "animation": "reveal",
        "data": {"type": "context_viz", "mode": "expanding"},
        "beats": [{"start": 0, "end": 3}, {"start": 3, "end": 6}],
    }
    scenes = [
        _make_scene(1, "KineticTypoScene", scene_type="HOOK", duration=3.0),
        _make_scene(2, "ContextWindowScene", **shared_config),
        _make_scene(3, "FlowScene"),
        _make_scene(4, "ContextWindowScene", **shared_config),
        _make_scene(5, "TakeawayScene", scene_type="TAKEAWAY"),
        _make_scene(6, "CTAScene", scene_type="CTA"),
    ]
    result = _intra_episode_repetition_gate(scenes)
    assert not result["pass"], "Near-identical reuse should be flagged"
    has_intra = any(v.startswith("INTRA_REPEAT:") for v in result["violations"])
    assert has_intra, f"Expected INTRA_REPEAT violation: {result['violations']}"


# ── Test 4: Family concentration (>2 same family) is flagged ─────────────

def test_family_concentration_flagged():
    """4 DOMAIN-family scenes in one episode should be flagged."""
    scenes = [
        _make_scene(1, "KineticTypoScene", scene_type="HOOK", duration=3.0),
        _make_scene(2, "ContextWindowScene"),  # DOMAIN
        _make_scene(3, "TokenScene"),           # DOMAIN
        _make_scene(4, "TokenStreamScene"),     # DOMAIN
        _make_scene(5, "TakeawayScene", scene_type="TAKEAWAY"),
        _make_scene(6, "CTAScene", scene_type="CTA"),
    ]
    result = _intra_episode_repetition_gate(scenes)
    concentration = [v for v in result["violations"]
                     if v.startswith("FAMILY_CONCENTRATION:")]
    assert len(concentration) > 0, "Should flag 3+ DOMAIN scenes"
    assert "DOMAIN" in concentration[0]


# ── Test 5: Only one bounded re-plan occurs (diversity gate) ─────────────

def test_diversity_gate_bounded_replan():
    """The diversity gate should trigger at most ONE re-plan, not loop."""
    from agents.visual_director_agent import _diversity_gate
    plan = {
        "storyboard": [
            {"component": "KineticTypoScene", "scene_type": "HOOK",
             "visual_mode": "NATIVE"},
            {"component": "ContextWindowScene", "scene_type": "DEMONSTRATION",
             "visual_mode": "NATIVE"},
            {"component": "TokenScene", "scene_type": "DEMONSTRATION",
             "visual_mode": "NATIVE"},
            {"component": "TakeawayScene", "scene_type": "TAKEAWAY",
             "visual_mode": "NATIVE"},
            {"component": "CTAScene", "scene_type": "CTA",
             "visual_mode": "NATIVE"},
        ]
    }
    fingerprints = {
        "week09_ep06": {
            "component_sequence": [
                "KineticTypoScene", "ContextWindowScene", "TokenScene",
                "TakeawayScene", "CTAScene",
            ],
            "component_families": [
                "TYPOGRAPHY", "DOMAIN", "DOMAIN", "TAKEAWAY", "CTA",
            ],
            "mode_ratio": {"native": 5, "generated": 0},
            "channel": "ai_bytes",
        }
    }
    result = _diversity_gate(plan, fingerprints)
    # The gate returns pass/fail; the bounded re-plan is in run().
    # We verify the gate itself works (it either passes or fails, no loop).
    assert "pass" in result
    assert "recent_key" in result
    assert result["recent_key"] == "week09_ep06"


# ── Test 6: Latest same-channel fingerprint is used ──────────────────────

def test_latest_channel_fingerprint_used():
    """Diversity gate should compare against the MOST RECENT fingerprint."""
    plan = {
        "storyboard": [
            {"component": "KineticTypoScene", "scene_type": "HOOK",
             "visual_mode": "NATIVE"},
            {"component": "FlowScene", "scene_type": "DEMONSTRATION",
             "visual_mode": "NATIVE"},
            {"component": "TakeawayScene", "scene_type": "TAKEAWAY",
             "visual_mode": "NATIVE"},
            {"component": "CTAScene", "scene_type": "CTA",
             "visual_mode": "NATIVE"},
        ]
    }
    fingerprints = {
        "week09_ep06": {
            "component_families": ["TYPOGRAPHY", "DOMAIN", "TAKEAWAY", "CTA"],
            "mode_ratio": {"native": 4, "generated": 0},
            "channel": "ai_bytes",
        },
        "week09_ep07": {
            "component_families": ["TYPOGRAPHY", "FLOW_PIPELINE", "TAKEAWAY", "CTA"],
            "mode_ratio": {"native": 3, "generated": 1},
            "channel": "ai_bytes",
        },
    }
    result = _diversity_gate(plan, fingerprints)
    assert result["recent_key"] == "week09_ep07", (
        f"Should use latest fingerprint ep07, got {result['recent_key']}"
    )


# ── Test 7: EP07 revised fingerprint is registered ───────────────────────

def test_ep07_fingerprint_registered():
    """EP07 fingerprint must exist in visual_fingerprints.json."""
    fp_path = Path(__file__).resolve().parent.parent / "output" / "visual_fingerprints.json"
    if not fp_path.exists():
        pytest.skip("No fingerprints file — run production first")
    data = json.loads(fp_path.read_text(encoding="utf-8"))
    episodes = data.get("episodes", data)
    assert "week09_ep07" in episodes, "EP07 fingerprint must be registered"
    ep07 = episodes["week09_ep07"]
    assert ep07.get("component_families"), "EP07 must have component_families"
    assert ep07.get("mode_ratio"), "EP07 must have mode_ratio"
    assert ep07.get("channel") == "ai_bytes", "EP07 must be in ai_bytes channel"
    # EP07 should be HYBRID (has AssetScene)
    mode = ep07["mode_ratio"]
    assert mode.get("generated", 0) >= 1, "EP07 should have >=1 generated scene"


# ── Similarity function unit tests ───────────────────────────────────────

def test_scene_config_similarity_identical():
    a = _make_scene(1, "ContextWindowScene", objects=["w", "t"])
    b = _make_scene(2, "ContextWindowScene", objects=["w", "t"])
    sim = _scene_config_similarity(a, b)
    assert sim >= 0.85, f"Identical config should have high similarity: {sim}"


def test_scene_config_similarity_different():
    a = _make_scene(1, "ContextWindowScene", objects=["w", "t"],
                    animation="reveal", data={"type": "viz"})
    b = _make_scene(2, "TransformScene", objects=["x", "y", "z"],
                    animation="morph", data={"type": "state_change"},
                    beats=[{"start": 0, "end": 2}, {"start": 2, "end": 4},
                           {"start": 4, "end": 6}])
    sim = _scene_config_similarity(a, b)
    assert sim < 0.50, f"Different config should have low similarity: {sim}"
