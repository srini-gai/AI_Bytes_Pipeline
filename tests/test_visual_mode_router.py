"""Tests for visual_mode_router — per-beat NATIVE/GENERATED routing layer.

Validates:
  - Beat-level classification logic
  - Episode-level mode derivation (NATIVE / GENERATED / HYBRID)
  - Storyboard annotation (non-mutating)
  - Weekly diversity tracking
  - Fingerprint enrichment
  - Regression against EP04 and EP05 production fixtures
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.visual_mode_router import (
    GENERATED_COMPONENTS,
    NATIVE_COMPONENTS,
    annotate_storyboard,
    classify_beat,
    classify_episode,
    compute_weekly_diversity,
    enrich_fingerprint,
    has_planner_declared_modes,
    route_storyboard,
    validate_routing,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ── Beat classification ────────────────────────────────────────────────────


def _scene(component: str, **kwargs) -> dict:
    base = {
        "scene_id": 1,
        "component": component,
        "duration_seconds": 5.0,
        "narration": "test",
        "scene_type": "DEMONSTRATION",
    }
    base.update(kwargs)
    return base


class TestClassifyBeat:
    def test_native_components_classify_as_native(self):
        for comp in sorted(NATIVE_COMPONENTS):
            assert classify_beat(_scene(comp)) == "NATIVE", f"{comp} should be NATIVE"

    def test_asset_scene_is_generated(self):
        assert classify_beat(_scene("AssetScene")) == "GENERATED"

    def test_asset_scene_with_src(self):
        s = _scene("AssetScene", data={"src": "assets/ep05/token.png", "media_type": "image"})
        assert classify_beat(s) == "GENERATED"

    def test_unknown_component_with_src_is_generated(self):
        s = _scene("FutureScene", data={"src": "assets/ep06/hero.png"})
        assert classify_beat(s) == "GENERATED"

    def test_unknown_component_without_src_is_native(self):
        assert classify_beat(_scene("FutureScene")) == "NATIVE"

    def test_beat_meta_generate_new_is_generated(self):
        s = _scene("AssetScene", beat_meta={"asset_decision": "generate_new"})
        assert classify_beat(s) == "GENERATED"

    def test_beat_meta_typography_only_is_native(self):
        s = _scene("KineticTypoScene", beat_meta={"asset_decision": "typography_only"})
        assert classify_beat(s) == "NATIVE"

    def test_beat_meta_cta_component_is_native(self):
        s = _scene("CTAScene", beat_meta={"asset_decision": "cta_component"})
        assert classify_beat(s) == "NATIVE"


# ── Episode classification ─────────────────────────────────────────────────


class TestClassifyEpisode:
    def test_all_native(self):
        sb = [_scene("KineticTypoScene"), _scene("TransformScene"), _scene("CTAScene")]
        assert classify_episode(sb) == "NATIVE"

    def test_all_generated(self):
        sb = [_scene("AssetScene"), _scene("AssetScene")]
        assert classify_episode(sb) == "GENERATED"

    def test_mixed_is_hybrid(self):
        sb = [_scene("KineticTypoScene"), _scene("AssetScene"), _scene("CTAScene")]
        assert classify_episode(sb) == "HYBRID"


# ── Storyboard annotation ─────────────────────────────────────────────────


class TestAnnotateStoryboard:
    def test_does_not_mutate_input(self):
        original = [_scene("TransformScene"), _scene("AssetScene")]
        original_copy = json.loads(json.dumps(original))
        annotated = annotate_storyboard(original)
        assert original == original_copy, "Input must not be mutated"
        assert all("visual_mode" in s for s in annotated)

    def test_adds_visual_mode(self):
        sb = [_scene("KineticTypoScene"), _scene("AssetScene"), _scene("CTAScene")]
        annotated = annotate_storyboard(sb)
        assert annotated[0]["visual_mode"] == "NATIVE"
        assert annotated[1]["visual_mode"] == "GENERATED"
        assert annotated[2]["visual_mode"] == "NATIVE"

    def test_preserves_all_original_fields(self):
        s = _scene("TransformScene", animation="morph", on_screen_text=["A", "B"])
        annotated = annotate_storyboard([s])[0]
        assert annotated["animation"] == "morph"
        assert annotated["on_screen_text"] == ["A", "B"]
        assert annotated["component"] == "TransformScene"


# ── Route storyboard (file I/O) ───────────────────────────────────────────


class TestRouteStoryboard:
    def test_dry_run_does_not_write(self, tmp_path):
        sb_data = {
            "storyboard": [_scene("TransformScene"), _scene("AssetScene")],
        }
        p = tmp_path / "test_sb.json"
        p.write_text(json.dumps(sb_data), encoding="utf-8")
        mtime_before = p.stat().st_mtime

        result = route_storyboard(p, dry_run=True)

        assert result["episode_mode"] == "HYBRID"
        assert result["native_beats"] == 1
        assert result["generated_beats"] == 1
        reread = json.loads(p.read_text(encoding="utf-8"))
        assert "visual_mode_routing" not in reread, "dry_run must not write"

    def test_write_adds_routing_metadata(self, tmp_path):
        sb_data = {
            "storyboard": [_scene("FlowScene"), _scene("FlowScene")],
        }
        p = tmp_path / "test_sb.json"
        p.write_text(json.dumps(sb_data), encoding="utf-8")

        result = route_storyboard(p, dry_run=False)

        assert result["episode_mode"] == "NATIVE"
        reread = json.loads(p.read_text(encoding="utf-8"))
        assert reread["visual_mode_routing"]["episode_mode"] == "NATIVE"
        assert reread["visual_mode_routing"]["native_beats"] == 2
        for scene in reread["storyboard"]:
            assert scene["visual_mode"] == "NATIVE"


# ── Weekly diversity ───────────────────────────────────────────────────────


class TestWeeklyDiversity:
    def test_empty_fingerprints(self):
        result = compute_weekly_diversity({})
        assert result["episodes_tracked"] == 0
        assert result["advisory"] == []

    def test_balanced_mix(self):
        fps = {
            "ep01": {"visual_mode_routing": {"episode_mode": "NATIVE"}},
            "ep02": {"visual_mode_routing": {"episode_mode": "NATIVE"}},
            "ep03": {"visual_mode_routing": {"episode_mode": "HYBRID"}},
            "ep04": {"visual_mode_routing": {"episode_mode": "HYBRID"}},
            "ep05": {"visual_mode_routing": {"episode_mode": "GENERATED"}},
        }
        result = compute_weekly_diversity(fps)
        assert result["native"] == 2
        assert result["hybrid"] == 2
        assert result["generated"] == 1
        assert result["advisory"] == []

    def test_native_heavy_advisory(self):
        fps = {
            f"ep{i:02d}": {"visual_mode_routing": {"episode_mode": "NATIVE"}}
            for i in range(1, 6)
        }
        result = compute_weekly_diversity(fps)
        assert any("NATIVE" in a for a in result["advisory"])

    def test_generated_heavy_advisory(self):
        fps = {
            f"ep{i:02d}": {"visual_mode_routing": {"episode_mode": "GENERATED"}}
            for i in range(1, 6)
        }
        result = compute_weekly_diversity(fps)
        assert any("GENERATED" in a for a in result["advisory"])

    def test_fingerprints_without_routing_ignored(self):
        fps = {
            "ep01": {"topic": "test", "component_sequence": ["KineticTypoScene"]},
        }
        result = compute_weekly_diversity(fps)
        assert result["episodes_tracked"] == 0


# ── Fingerprint enrichment ─────────────────────────────────────────────────


class TestEnrichFingerprint:
    def test_adds_routing_to_fingerprint(self):
        fp = {"topic": "Test", "visual_thesis": "thesis"}
        sb = [_scene("KineticTypoScene"), _scene("AssetScene"), _scene("CTAScene")]
        enriched = enrich_fingerprint(fp, sb)
        assert enriched["visual_mode_routing"]["episode_mode"] == "HYBRID"
        assert enriched["visual_mode_routing"]["native_beats"] == 2
        assert enriched["visual_mode_routing"]["generated_beats"] == 1
        assert enriched["visual_mode_routing"]["beat_sequence"] == ["NATIVE", "GENERATED", "NATIVE"]

    def test_does_not_mutate_original(self):
        fp = {"topic": "Test"}
        sb = [_scene("TransformScene")]
        fp_copy = dict(fp)
        enrich_fingerprint(fp, sb)
        assert fp == fp_copy


# ── EP04 / EP05 regression fixtures ───────────────────────────────────────


class TestEP04Regression:
    @pytest.fixture
    def ep04_storyboard(self):
        p = FIXTURES / "ep04_hybrid_storyboard_EN.json"
        if not p.exists():
            pytest.skip("EP04 fixture not found")
        return json.loads(p.read_text(encoding="utf-8"))

    def test_ep04_routing_is_hybrid(self, ep04_storyboard):
        scenes = ep04_storyboard.get("storyboard", [])
        mode = classify_episode(scenes)
        assert mode == "HYBRID", f"EP04 should be HYBRID, got {mode}"

    def test_ep04_has_both_native_and_generated(self, ep04_storyboard):
        scenes = ep04_storyboard.get("storyboard", [])
        annotated = annotate_storyboard(scenes)
        modes = {s["visual_mode"] for s in annotated}
        assert "NATIVE" in modes, "EP04 must have NATIVE beats"
        assert "GENERATED" in modes, "EP04 must have GENERATED beats"

    def test_ep04_annotation_preserves_structure(self, ep04_storyboard):
        scenes = ep04_storyboard.get("storyboard", [])
        annotated = annotate_storyboard(scenes)
        assert len(annotated) == len(scenes)
        for orig, ann in zip(scenes, annotated):
            assert ann["scene_id"] == orig["scene_id"]
            assert ann["component"] == orig["component"]
            assert ann["duration_seconds"] == orig["duration_seconds"]
            assert ann["narration"] == orig["narration"]


class TestEP05Regression:
    @pytest.fixture
    def ep05_storyboard(self):
        p = FIXTURES / "ep05_hybrid_storyboard_EN.json"
        if not p.exists():
            pytest.skip("EP05 fixture not found")
        return json.loads(p.read_text(encoding="utf-8"))

    def test_ep05_routing_is_hybrid(self, ep05_storyboard):
        scenes = ep05_storyboard.get("storyboard", [])
        mode = classify_episode(scenes)
        assert mode == "HYBRID", f"EP05 should be HYBRID, got {mode}"

    def test_ep05_has_both_native_and_generated(self, ep05_storyboard):
        scenes = ep05_storyboard.get("storyboard", [])
        annotated = annotate_storyboard(scenes)
        modes = {s["visual_mode"] for s in annotated}
        assert "NATIVE" in modes, "EP05 must have NATIVE beats"
        assert "GENERATED" in modes, "EP05 must have GENERATED beats"

    def test_ep05_annotation_preserves_storyboard_qa(self, ep05_storyboard):
        """Annotating must not break the adjacent-asset QA check."""
        from agents.storyboard_qa import check_adjacent_asset_repetition

        scenes = ep05_storyboard.get("storyboard", [])
        findings_before = check_adjacent_asset_repetition(scenes)
        annotated = annotate_storyboard(scenes)
        findings_after = check_adjacent_asset_repetition(annotated)
        assert len(findings_before) == len(findings_after), (
            "Annotation must not change adjacent-asset QA results"
        )

    def test_ep05_beat_modes_match_components(self, ep05_storyboard):
        """Every AssetScene beat should be GENERATED, KineticTypo/CTA should be NATIVE."""
        scenes = ep05_storyboard.get("storyboard", [])
        annotated = annotate_storyboard(scenes)
        for s in annotated:
            if s["component"] == "AssetScene":
                assert s["visual_mode"] == "GENERATED", (
                    f"S{s['scene_id']} AssetScene should be GENERATED"
                )
            elif s["component"] in ("KineticTypoScene", "CTAScene"):
                assert s["visual_mode"] == "NATIVE", (
                    f"S{s['scene_id']} {s['component']} should be NATIVE"
                )


# ── Compatibility: routing metadata does not alter existing manifests ──────


class TestNoSideEffects:
    def test_routing_does_not_add_keys_beyond_visual_mode(self):
        original_keys = set(_scene("TransformScene").keys())
        annotated = annotate_storyboard([_scene("TransformScene")])[0]
        new_keys = set(annotated.keys()) - original_keys
        assert new_keys == {"visual_mode"}, (
            f"Only visual_mode should be added, got extra: {new_keys - {'visual_mode'}}"
        )

    def test_existing_storyboard_qa_still_works_on_annotated(self):
        from agents.storyboard_qa import check_adjacent_asset_repetition

        scenes = [
            _scene("AssetScene", data={"src": "assets/ep05/a.png", "motion": "push"}),
            _scene("AssetScene", data={"src": "assets/ep05/a.png", "motion": "zoom"}, scene_id=2),
        ]
        scenes[1]["scene_id"] = 2

        findings_before = check_adjacent_asset_repetition(scenes)
        annotated = annotate_storyboard(scenes)
        findings_after = check_adjacent_asset_repetition(annotated)
        assert len(findings_before) == len(findings_after)


# ── Planner-declared visual_mode tests ────────────────────────────────────


class TestPlannerDeclaredMode:
    def test_planner_declares_native(self):
        s = _scene("TransformScene", visual_mode="NATIVE")
        assert classify_beat(s) == "NATIVE"
        annotated = annotate_storyboard([s])
        assert annotated[0]["visual_mode"] == "NATIVE"

    def test_planner_declares_generated(self):
        s = _scene("AssetScene", visual_mode="GENERATED",
                    data={"src": "assets/ep06/hero.png", "media_type": "image"})
        assert classify_beat(s) == "GENERATED"
        annotated = annotate_storyboard([s])
        assert annotated[0]["visual_mode"] == "GENERATED"

    def test_mixed_planner_modes_derive_hybrid(self):
        sb = [
            _scene("KineticTypoScene", visual_mode="NATIVE"),
            _scene("AssetScene", visual_mode="GENERATED"),
            _scene("FlowScene", visual_mode="NATIVE"),
            _scene("AssetScene", visual_mode="GENERATED"),
            _scene("CTAScene", visual_mode="NATIVE"),
        ]
        annotated = annotate_storyboard(sb)
        assert classify_episode(annotated) == "HYBRID"
        modes = [s["visual_mode"] for s in annotated]
        assert modes == ["NATIVE", "GENERATED", "NATIVE", "GENERATED", "NATIVE"]

    def test_planner_declared_mode_preserved_by_annotate(self):
        s = _scene("TransformScene", visual_mode="NATIVE")
        annotated = annotate_storyboard([s])
        assert annotated[0]["visual_mode"] == "NATIVE"
        s2 = _scene("AssetScene", visual_mode="GENERATED")
        annotated2 = annotate_storyboard([s2])
        assert annotated2[0]["visual_mode"] == "GENERATED"


# ── Routing validation tests ───────────────────────────────────────────────


class TestValidateRouting:
    def test_generated_mode_with_native_component_flagged(self):
        s = _scene("TransformScene", visual_mode="GENERATED")
        issues = validate_routing([s])
        assert len(issues) >= 1
        assert "GENERATED" in issues[0] and "TransformScene" in issues[0]

    def test_native_mode_with_asset_scene_flagged(self):
        s = _scene("AssetScene", visual_mode="NATIVE")
        issues = validate_routing([s])
        assert len(issues) >= 1
        assert "NATIVE" in issues[0] and "AssetScene" in issues[0]

    def test_generated_mode_without_asset_flagged(self):
        s = _scene("FutureScene", visual_mode="GENERATED")
        issues = validate_routing([s])
        assert any("no generated asset" in i for i in issues)

    def test_native_mode_with_data_src_flagged(self):
        s = _scene("TransformScene", visual_mode="NATIVE",
                    data={"src": "assets/ep06/hero.png"})
        issues = validate_routing([s])
        assert any("data.src" in i for i in issues)

    def test_hybrid_mode_at_beat_level_flagged(self):
        s = _scene("TransformScene", visual_mode="HYBRID")
        issues = validate_routing([s])
        assert any("HYBRID" in i and "not valid at beat level" in i for i in issues)

    def test_unrecognized_mode_flagged(self):
        s = _scene("TransformScene", visual_mode="MAGIC")
        issues = validate_routing([s])
        assert any("not recognized" in i for i in issues)

    def test_valid_native_passes(self):
        s = _scene("TransformScene", visual_mode="NATIVE")
        assert validate_routing([s]) == []

    def test_valid_generated_passes(self):
        s = _scene("AssetScene", visual_mode="GENERATED",
                    data={"src": "assets/ep06/hero.png"})
        assert validate_routing([s]) == []

    def test_generated_with_beat_meta_passes(self):
        s = _scene("AssetScene", visual_mode="GENERATED",
                    beat_meta={"asset_decision": "generate_new"})
        assert validate_routing([s]) == []


# ── Backward compatibility: old manifests without visual_mode ──────────────


class TestBackwardCompatibility:
    def test_missing_visual_mode_inferred_by_annotate(self):
        s = _scene("TransformScene")
        assert "visual_mode" not in s
        annotated = annotate_storyboard([s])
        assert annotated[0]["visual_mode"] == "NATIVE"

    def test_missing_visual_mode_asset_scene_inferred(self):
        s = _scene("AssetScene")
        assert "visual_mode" not in s
        annotated = annotate_storyboard([s])
        assert annotated[0]["visual_mode"] == "GENERATED"

    def test_missing_visual_mode_passes_validation(self):
        sb = [_scene("TransformScene"), _scene("AssetScene")]
        assert validate_routing(sb) == []

    def test_route_storyboard_works_without_visual_mode(self, tmp_path):
        sb_data = {
            "storyboard": [_scene("FlowScene"), _scene("AssetScene")],
        }
        p = tmp_path / "old_sb.json"
        p.write_text(json.dumps(sb_data), encoding="utf-8")
        result = route_storyboard(p, dry_run=False)
        assert result["episode_mode"] == "HYBRID"
        assert result["routing_issues"] == []
        reread = json.loads(p.read_text(encoding="utf-8"))
        assert reread["storyboard"][0]["visual_mode"] == "NATIVE"
        assert reread["storyboard"][1]["visual_mode"] == "GENERATED"


# ── EP04/EP05 fixture renderer output unchanged ───────────────────────────


class TestFixtureRendererUnchanged:
    @pytest.fixture
    def ep04_storyboard(self):
        p = FIXTURES / "ep04_hybrid_storyboard_EN.json"
        if not p.exists():
            pytest.skip("EP04 fixture not found")
        return json.loads(p.read_text(encoding="utf-8"))

    @pytest.fixture
    def ep05_storyboard(self):
        p = FIXTURES / "ep05_hybrid_storyboard_EN.json"
        if not p.exists():
            pytest.skip("EP05 fixture not found")
        return json.loads(p.read_text(encoding="utf-8"))

    def test_ep04_validation_passes_without_visual_mode(self, ep04_storyboard):
        scenes = ep04_storyboard.get("storyboard", [])
        issues = validate_routing(scenes)
        assert issues == [], f"EP04 should pass validation: {issues}"

    def test_ep05_validation_passes_without_visual_mode(self, ep05_storyboard):
        scenes = ep05_storyboard.get("storyboard", [])
        issues = validate_routing(scenes)
        assert issues == [], f"EP05 should pass validation: {issues}"

    def test_ep04_annotation_unchanged(self, ep04_storyboard):
        scenes = ep04_storyboard.get("storyboard", [])
        annotated = annotate_storyboard(scenes)
        for orig, ann in zip(scenes, annotated):
            assert ann["scene_id"] == orig["scene_id"]
            assert ann["component"] == orig["component"]
            assert ann["duration_seconds"] == orig["duration_seconds"]
            assert ann["narration"] == orig["narration"]

    def test_ep05_annotation_unchanged(self, ep05_storyboard):
        scenes = ep05_storyboard.get("storyboard", [])
        annotated = annotate_storyboard(scenes)
        for orig, ann in zip(scenes, annotated):
            assert ann["scene_id"] == orig["scene_id"]
            assert ann["component"] == orig["component"]
            assert ann["duration_seconds"] == orig["duration_seconds"]
            assert ann["narration"] == orig["narration"]


# ── Mixed-mode semantic scene test ─────────────────────────────────────────


class TestMixedModeSemanticScene:
    """A semantic scene may contain visual beats with different modes.
    visual_mode is per visual beat, not per semantic scene.
    """

    def test_semantic_scene_with_mixed_beat_modes(self):
        beats = [
            _scene("FlowScene", visual_mode="NATIVE", scene_id=1,
                   beat_meta={"semantic_scene": "SS3"}),
            _scene("AssetScene", visual_mode="GENERATED", scene_id=2,
                   data={"src": "assets/ep06/concept.png", "media_type": "image"},
                   beat_meta={"semantic_scene": "SS3"}),
            _scene("TransformScene", visual_mode="NATIVE", scene_id=3,
                   beat_meta={"semantic_scene": "SS3"}),
        ]
        annotated = annotate_storyboard(beats)
        assert annotated[0]["visual_mode"] == "NATIVE"
        assert annotated[1]["visual_mode"] == "GENERATED"
        assert annotated[2]["visual_mode"] == "NATIVE"
        assert classify_episode(annotated) == "HYBRID"
        assert validate_routing(beats) == []

    def test_ep05_fixture_has_mixed_beats_in_semantic_scene(self):
        p = FIXTURES / "ep05_hybrid_storyboard_EN.json"
        if not p.exists():
            pytest.skip("EP05 fixture not found")
        doc = json.loads(p.read_text(encoding="utf-8"))
        semantic_scenes = doc.get("semantic_scenes", [])
        storyboard = doc.get("storyboard", [])
        annotated = annotate_storyboard(storyboard)
        mode_by_beat = {s["scene_id"]: s["visual_mode"] for s in annotated}
        multi_beat_scenes = [ss for ss in semantic_scenes if len(ss.get("visual_beats", [])) > 1]
        assert len(multi_beat_scenes) > 0, "EP05 must have multi-beat semantic scenes"
        for ss in multi_beat_scenes:
            beat_modes = [mode_by_beat.get(vb) for vb in ss["visual_beats"]]
            assert all(m in ("NATIVE", "GENERATED") for m in beat_modes)


# ── Strict routing gate for new manifests ──────────────────────────────────


class TestStrictRoutingGate:
    def test_new_manifest_with_issues_is_strict(self):
        sb = [
            _scene("TransformScene", visual_mode="GENERATED"),
        ]
        assert has_planner_declared_modes(sb) is True
        issues = validate_routing(sb)
        assert len(issues) >= 1

    def test_new_manifest_clean_passes_strict(self):
        sb = [
            _scene("FlowScene", visual_mode="NATIVE"),
            _scene("AssetScene", visual_mode="GENERATED",
                   data={"src": "assets/ep06/hero.png"}),
            _scene("CTAScene", visual_mode="NATIVE"),
        ]
        assert has_planner_declared_modes(sb) is True
        assert validate_routing(sb) == []

    def test_old_manifest_without_modes_is_compat(self):
        sb = [_scene("TransformScene"), _scene("AssetScene")]
        assert has_planner_declared_modes(sb) is False
        assert validate_routing(sb) == []

    def test_route_storyboard_includes_routing_issues(self, tmp_path):
        sb_data = {
            "storyboard": [
                _scene("TransformScene", visual_mode="GENERATED"),
            ],
        }
        p = tmp_path / "bad_sb.json"
        p.write_text(json.dumps(sb_data), encoding="utf-8")
        result = route_storyboard(p, dry_run=True)
        assert len(result["routing_issues"]) >= 1
        assert "GENERATED" in result["routing_issues"][0]
