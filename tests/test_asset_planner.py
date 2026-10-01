"""
tests/test_asset_planner.py — Unit tests for asset_planner_agent (Phase 3A)

Run: python -m pytest tests/test_asset_planner.py -v
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.asset_planner_agent import (
    CostConfig,
    _decide_asset_source,
    _has_deterministic_veto,
    _plan_scene,
    _planning_cost,
    _score_scene,
    run,
)
from agents.providers.base import AssetSource, GenerationType, make_cache_key


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _storyboard_path() -> Path:
    return Path(__file__).parent.parent / "output" / "week_01" / "ep01" / "ep01_storyboard_en.json"


def _load_storyboard() -> list[dict]:
    with open(_storyboard_path()) as f:
        return json.load(f)


def _make_hook_scene() -> dict:
    return {
        "scene_id": 1,
        "duration_seconds": 3.0,
        "scene_type": "HOOK",
        "component": "KineticTypoScene",
        "visual_goal": "word shatters into fragments",
        "objects": ["word_text", "shatter_fragments"],
        "on_screen_text": ["WORD", "NOT ONE."],
    }


def _make_token_scene() -> dict:
    return {
        "scene_id": 2,
        "duration_seconds": 5.0,
        "scene_type": "DEMONSTRATION",
        "component": "TokenScene",
        "visual_goal": "tokenizer splits sentence",
        "objects": ["token_boxes"],
        "on_screen_text": ["un", "believ", "able", "TOKENS ≠ WORDS"],
    }


def _make_data_scene() -> dict:
    return {
        "scene_id": 6,
        "duration_seconds": 5.5,
        "scene_type": "COMPARISON",
        "component": "DataScene",
        "visual_goal": "bar comparison",
        "objects": ["bars"],
        "on_screen_text": ["English word", "Code snippet", "Rare / foreign word"],
        "data": {"type": "bars", "bars": [{"label": "A", "value": 35}]},
    }


def _make_cta_scene() -> dict:
    return {
        "scene_id": 10,
        "duration_seconds": 3.0,
        "scene_type": "CTA",
        "component": "CTAScene",
        "visual_goal": "follow CTA",
        "objects": ["cta_label", "follow_button"],
        "on_screen_text": ["Follow for practical AI, daily"],
    }


def _make_number_counter_scene() -> dict:
    return {
        "scene_id": 7,
        "duration_seconds": 4.5,
        "scene_type": "DATA",
        "component": "NumberCounterScene",
        "visual_goal": "counter counts to 128000",
        "objects": ["counter_display"],
        "on_screen_text": ["128,000", "TOKENS", "context window"],
    }


# ── Deterministic veto tests ──────────────────────────────────────────────────

class TestDeterministicVeto(unittest.TestCase):

    def test_tokenscene_is_vetoed(self):
        self.assertTrue(_has_deterministic_veto(_make_token_scene()))

    def test_datascene_is_vetoed(self):
        self.assertTrue(_has_deterministic_veto(_make_data_scene()))

    def test_cta_is_vetoed(self):
        self.assertTrue(_has_deterministic_veto(_make_cta_scene()))

    def test_numbercounterscene_is_vetoed(self):
        self.assertTrue(_has_deterministic_veto(_make_number_counter_scene()))

    def test_network_build_scene_is_vetoed(self):
        scene = {
            "scene_id": 4, "scene_type": "FLOW",
            "component": "NetworkBuildScene",
            "on_screen_text": ["INTEGER IDs", "ATTENTION"],
        }
        self.assertTrue(_has_deterministic_veto(scene))

    def test_hook_kinetic_not_vetoed(self):
        """KineticTypoScene with HOOK type: not in deterministic component list."""
        scene = _make_hook_scene()
        self.assertFalse(_has_deterministic_veto(scene))

    def test_takeaway_scene_is_vetoed(self):
        scene = {
            "scene_id": 9, "scene_type": "TAKEAWAY",
            "component": "TakeawayScene",
            "on_screen_text": ["AI reads TOKENS", "not words"],
        }
        self.assertTrue(_has_deterministic_veto(scene))


# ── Scoring tests ─────────────────────────────────────────────────────────────

class TestScoring(unittest.TestCase):

    def test_hook_gets_high_visual_value(self):
        score = _score_scene(_make_hook_scene())
        self.assertGreaterEqual(score.visual_value, 8)

    def test_data_scene_gets_high_deterministic_requirement(self):
        score = _score_scene(_make_data_scene())
        self.assertGreaterEqual(score.deterministic_requirement, 8)

    def test_hook_gets_high_cinematic_opportunity(self):
        score = _score_scene(_make_hook_scene())
        self.assertGreaterEqual(score.cinematic_opportunity, 8)

    def test_token_scene_gets_high_deterministic_requirement(self):
        score = _score_scene(_make_token_scene())
        self.assertGreaterEqual(score.deterministic_requirement, 8)

    def test_cta_gets_high_reliability(self):
        score = _score_scene(_make_cta_scene())
        self.assertGreaterEqual(score.reliability, 7)

    def test_all_scores_in_range(self):
        for scene in _load_storyboard():
            score = _score_scene(scene)
            for field_name, val in [
                ("visual_value", score.visual_value),
                ("deterministic_requirement", score.deterministic_requirement),
                ("cinematic_opportunity", score.cinematic_opportunity),
                ("cost_efficiency", score.cost_efficiency),
                ("reuse_potential", score.reuse_potential),
                ("reliability", score.reliability),
            ]:
                self.assertGreaterEqual(val, 0, f"{field_name} out of range for scene {scene['scene_id']}")
                self.assertLessEqual(val, 10, f"{field_name} out of range for scene {scene['scene_id']}")


# ── Asset source decision tests ───────────────────────────────────────────────

class TestAssetSourceDecision(unittest.TestCase):

    def _fresh_budget(self) -> dict:
        return {
            "video_clips": 0, "video_seconds": 0.0, "video_cost_usd": 0.0,
            "image_count": 0, "image_cost_usd": 0.0,
        }

    def test_deterministic_veto_forces_remotion(self):
        from agents.asset_planner_agent import SceneScore
        score = SceneScore(
            visual_value=9, deterministic_requirement=9, cinematic_opportunity=9,
            cost_efficiency=9, reuse_potential=9, reliability=2,
        )
        source, reason = _decide_asset_source(score, self._fresh_budget(), CostConfig())
        self.assertEqual(source, AssetSource.REMOTION_ONLY)
        self.assertIn("veto", reason.lower())

    def test_high_score_non_veto_gets_generative_video(self):
        from agents.asset_planner_agent import SceneScore
        # Hook-like: high visual/cinematic, low det/reliability
        score = SceneScore(
            visual_value=9, deterministic_requirement=2, cinematic_opportunity=9,
            cost_efficiency=7, reuse_potential=9, reliability=4,
        )
        source, reason = _decide_asset_source(score, self._fresh_budget(), CostConfig())
        self.assertEqual(source, AssetSource.GENERATIVE_VIDEO)

    def test_clip_budget_cap_downgrades_to_ai_image(self):
        from agents.asset_planner_agent import SceneScore
        score = SceneScore(
            visual_value=9, deterministic_requirement=2, cinematic_opportunity=9,
            cost_efficiency=7, reuse_potential=9, reliability=4,
        )
        budget = self._fresh_budget()
        config = CostConfig()
        # Exhaust the video clip budget
        budget["video_clips"] = config.generative_video_max_clips
        source, reason = _decide_asset_source(score, budget, config)
        self.assertEqual(source, AssetSource.AI_IMAGE)
        self.assertIn("clip limit", reason.lower())

    def test_image_count_cap_forces_remotion(self):
        from agents.asset_planner_agent import SceneScore
        # Score that lands in the AI_IMAGE band: 10 ≤ raw < 18
        # raw = 5*2 + 4*1.5 + 6*1 + 7*1 - 2*3 - 5*1.5
        #     = 10 + 6 + 6 + 7 - 6 - 7.5 = 15.5  ✓
        score = SceneScore(
            visual_value=5, deterministic_requirement=2, cinematic_opportunity=4,
            cost_efficiency=6, reuse_potential=7, reliability=5,
        )
        budget = self._fresh_budget()
        config = CostConfig()
        budget["image_count"] = config.ai_image_max_per_short
        source, reason = _decide_asset_source(score, budget, config)
        self.assertEqual(source, AssetSource.REMOTION_ONLY)

    def test_low_score_gets_remotion(self):
        from agents.asset_planner_agent import SceneScore
        # Data scene: high reliability & det_req, low visual/cinematic
        score = SceneScore(
            visual_value=2, deterministic_requirement=9, cinematic_opportunity=2,
            cost_efficiency=6, reuse_potential=4, reliability=9,
        )
        source, _ = _decide_asset_source(score, self._fresh_budget(), CostConfig())
        self.assertEqual(source, AssetSource.REMOTION_ONLY)


# ── Planning cost tests ───────────────────────────────────────────────────────

class TestPlanningCost(unittest.TestCase):

    def test_remotion_costs_zero(self):
        self.assertEqual(_planning_cost(AssetSource.REMOTION_ONLY, 5.0, "", ""), 0.0)

    def test_image_cost_is_flat(self):
        cost = _planning_cost(AssetSource.AI_IMAGE, 5.0, "imagineart", "imagineart-v1")
        self.assertAlmostEqual(cost, 0.06)

    def test_video_cost_scales_with_duration(self):
        cost_3 = _planning_cost(AssetSource.GENERATIVE_VIDEO, 3.0, "higgsfield", "higgsfield-v1")
        cost_5 = _planning_cost(AssetSource.GENERATIVE_VIDEO, 5.0, "higgsfield", "higgsfield-v1")
        self.assertGreater(cost_5, cost_3)
        # At $0.08/sec: 3.0s → 0.24, 5.0s → 0.40
        self.assertAlmostEqual(cost_3, 0.24, places=4)
        self.assertAlmostEqual(cost_5, 0.40, places=4)


# ── Cache key tests ───────────────────────────────────────────────────────────

class TestCacheKey(unittest.TestCase):

    def test_same_inputs_give_same_key(self):
        k1 = make_cache_key("dark cinematic digital", "tbd", "tbd", GenerationType.VIDEO, "9:16", 3.0)
        k2 = make_cache_key("dark cinematic digital", "tbd", "tbd", GenerationType.VIDEO, "9:16", 3.0)
        self.assertEqual(k1, k2)

    def test_different_prompts_give_different_keys(self):
        k1 = make_cache_key("abstract purple", "tbd", "tbd", GenerationType.IMAGE, "9:16")
        k2 = make_cache_key("abstract teal", "tbd", "tbd", GenerationType.IMAGE, "9:16")
        self.assertNotEqual(k1, k2)

    def test_key_is_sha256_length(self):
        k = make_cache_key("test prompt", "higgsfield", "higgsfield-v1", GenerationType.VIDEO, "9:16", 4.0)
        self.assertEqual(len(k), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in k))

    def test_language_neutral_same_cache_key(self):
        """EN and TA episodes with same intent resolve to same cache key."""
        k_en = make_cache_key("word shatters into fragments", "tbd", "tbd", GenerationType.VIDEO, "9:16", 3.0)
        k_ta = make_cache_key("word shatters into fragments", "tbd", "tbd", GenerationType.VIDEO, "9:16", 3.0)
        self.assertEqual(k_en, k_ta)

    def test_key_is_case_insensitive_on_prompt(self):
        k1 = make_cache_key("Dark Cinematic", "tbd", "tbd", GenerationType.IMAGE, "9:16")
        k2 = make_cache_key("dark cinematic", "tbd", "tbd", GenerationType.IMAGE, "9:16")
        self.assertEqual(k1, k2)

    def test_duration_changes_key(self):
        k1 = make_cache_key("abstract", "tbd", "tbd", GenerationType.VIDEO, "9:16", 3.0)
        k2 = make_cache_key("abstract", "tbd", "tbd", GenerationType.VIDEO, "9:16", 5.0)
        self.assertNotEqual(k1, k2)


# ── Per-scene plan validation ─────────────────────────────────────────────────

class TestPlanScene(unittest.TestCase):

    REQUIRED_FIELDS = {
        "scene_id", "component", "asset_source", "remotion_overlay", "overlay_content",
        "reason", "scoring", "priority", "asset_duration_seconds",
        "prompt_intent", "language_neutral", "planning_estimate_usd",
        "actual_cost_usd", "provider", "model", "fallback_asset_source",
        "fallback_reason", "cache_key", "visual_continuity", "status",
    }

    def _fresh_budget(self) -> dict:
        return {
            "video_clips": 0, "video_seconds": 0.0, "video_cost_usd": 0.0,
            "image_count": 0, "image_cost_usd": 0.0,
        }

    def test_all_required_fields_present(self):
        """Every plan entry must have all 20 required fields."""
        for scene in _load_storyboard():
            plan = _plan_scene(scene, self._fresh_budget(), CostConfig(), 1, 1)
            missing = self.REQUIRED_FIELDS - set(plan.keys())
            self.assertFalse(missing, f"Scene {scene['scene_id']} missing fields: {missing}")

    def test_remotion_overlay_always_true(self):
        for scene in _load_storyboard():
            plan = _plan_scene(scene, self._fresh_budget(), CostConfig(), 1, 1)
            self.assertTrue(plan["remotion_overlay"], f"remotion_overlay must always be True (scene {scene['scene_id']})")

    def test_actual_cost_always_null_in_phase_3a(self):
        for scene in _load_storyboard():
            plan = _plan_scene(scene, self._fresh_budget(), CostConfig(), 1, 1)
            self.assertIsNone(plan["actual_cost_usd"])

    def test_status_is_planned(self):
        for scene in _load_storyboard():
            plan = _plan_scene(scene, self._fresh_budget(), CostConfig(), 1, 1)
            self.assertEqual(plan["status"], "planned")

    def test_remotion_only_has_null_prompt_and_continuity(self):
        scene = _make_token_scene()   # deterministic component → REMOTION_ONLY
        plan = _plan_scene(scene, self._fresh_budget(), CostConfig(), 1, 1)
        self.assertEqual(plan["asset_source"], AssetSource.REMOTION_ONLY.value)
        self.assertIsNone(plan["prompt_intent"])
        self.assertIsNone(plan["visual_continuity"])
        self.assertIsNone(plan["cache_key"])

    def test_cta_scene_gets_remotion(self):
        scene = _make_cta_scene()
        plan = _plan_scene(scene, self._fresh_budget(), CostConfig(), 1, 1)
        self.assertEqual(plan["asset_source"], AssetSource.REMOTION_ONLY.value)

    def test_scene_id_formatted_with_leading_zero(self):
        scene = _make_hook_scene()
        plan = _plan_scene(scene, self._fresh_budget(), CostConfig(), 1, 1)
        self.assertEqual(plan["scene_id"], "s01")

    def test_fallback_hierarchy(self):
        """GENERATIVE_VIDEO fallback → AI_IMAGE; AI_IMAGE fallback → REMOTION_ONLY."""
        hook = _make_hook_scene()
        plan = _plan_scene(hook, self._fresh_budget(), CostConfig(), 1, 1)
        if plan["asset_source"] == AssetSource.GENERATIVE_VIDEO.value:
            self.assertEqual(plan["fallback_asset_source"], AssetSource.AI_IMAGE.value)
        elif plan["asset_source"] == AssetSource.AI_IMAGE.value:
            self.assertEqual(plan["fallback_asset_source"], AssetSource.REMOTION_ONLY.value)
        else:
            self.assertIsNone(plan["fallback_asset_source"])


# ── Full run tests (dry-run — reads existing storyboard, writes plan files) ───

class TestRunAgent(unittest.TestCase):
    """
    Acceptance tests — run the full agent against ep01 storyboard.
    Expected outcome (Tokens dry-run table):
        ≥7 REMOTION_ONLY  (TokenScene, TransformScene, NetworkBuildScene,
                           TokenStreamScene, DataScene, NumberCounterScene,
                           TakeawayScene, CTAScene are all deterministic)
        ≤2 GENERATIVE_VIDEO
        ≤3 AI_IMAGE
    """

    @classmethod
    def setUpClass(cls):
        storyboard = _load_storyboard()
        cls.result = run(
            episode=1,
            week=1,
            input_data={"storyboard": storyboard},
        )
        with open(cls.result["asset_plan_path"]) as f:
            cls.asset_plan = json.load(f)
        with open(cls.result["asset_manifest_path"]) as f:
            cls.manifest = json.load(f)

    def test_run_returns_success(self):
        self.assertTrue(self.result["success"])

    def test_scene_count_matches_storyboard(self):
        storyboard = _load_storyboard()
        self.assertEqual(self.result["scene_count"], len(storyboard))

    def test_remotion_scenes_majority(self):
        """Deterministic scenes must form majority (≥7 of 10)."""
        self.assertGreaterEqual(self.result["remotion_scenes"], 7)

    def test_generative_video_within_budget(self):
        config = CostConfig()
        self.assertLessEqual(
            self.result["generative_video_scenes"],
            config.generative_video_max_clips,
        )

    def test_ai_image_within_budget(self):
        config = CostConfig()
        self.assertLessEqual(
            self.result["ai_image_scenes"],
            config.ai_image_max_per_short,
        )

    def test_asset_plan_file_exists(self):
        self.assertTrue(Path(self.result["asset_plan_path"]).exists())

    def test_asset_manifest_file_exists(self):
        self.assertTrue(Path(self.result["asset_manifest_path"]).exists())

    def test_asset_plan_has_all_scenes(self):
        self.assertEqual(
            len(self.asset_plan["scenes"]),
            self.result["scene_count"],
        )

    def test_planned_cost_is_non_negative(self):
        self.assertGreaterEqual(self.result["planned_total_cost_usd"], 0.0)

    def test_no_actual_costs_in_phase_3a(self):
        for scene in self.asset_plan["scenes"]:
            self.assertIsNone(
                scene["actual_cost_usd"],
                f"actual_cost_usd must be null in Phase 3A (scene {scene['scene_id']})",
            )

    def test_asset_plan_summary_counts_consistent(self):
        summary = self.asset_plan["summary"]
        total = (
            summary["remotion_only_scenes"]
            + summary["ai_image_scenes"]
            + summary["generative_video_scenes"]
        )
        self.assertEqual(total, summary["total_scenes"])

    def test_manifest_assets_count_matches(self):
        self.assertEqual(
            len(self.manifest["assets"]),
            self.result["scene_count"],
        )

    def test_manifest_phase_label(self):
        self.assertEqual(self.manifest["phase"], "3A_planned")

    def test_remotion_only_scenes_identified_correctly(self):
        """Named deterministic components must resolve to REMOTION_ONLY."""
        must_be_remotion = {
            "s02", "s03", "s04", "s05",  # TokenScene, TransformScene, NetworkBuildScene, TokenStreamScene
            "s06", "s07",                 # DataScene, NumberCounterScene
            "s09", "s10",                 # TakeawayScene, CTAScene
        }
        for scene in self.asset_plan["scenes"]:
            if scene["scene_id"] in must_be_remotion:
                self.assertEqual(
                    scene["asset_source"],
                    AssetSource.REMOTION_ONLY.value,
                    f"Scene {scene['scene_id']} ({scene['component']}) must be REMOTION_ONLY",
                )

    def test_missing_storyboard_raises(self):
        with self.assertRaises(RuntimeError):
            run(episode=99, week=1, input_data={})

    def test_empty_storyboard_raises(self):
        with self.assertRaises(RuntimeError):
            run(episode=99, week=1, input_data={"storyboard": []})


# ── Tokens dry-run table ──────────────────────────────────────────────────────

class TestTokensDryRun(unittest.TestCase):
    """
    Prints the dry-run planning table for human review.
    This test always passes — it is a reporting test only.
    """

    def test_print_dry_run_table(self):
        storyboard = _load_storyboard()
        result = run(episode=1, week=1, input_data={"storyboard": storyboard})

        with open(result["asset_plan_path"]) as f:
            plan = json.load(f)

        print("\n")
        print("=" * 90)
        print("TOKENS DRY-RUN — Asset Planner Phase 3A — EP01 Storyboard")
        print("=" * 90)
        header = f"{'Scene':<8} {'Component':<25} {'AssetSource':<20} {'Est. USD':>8}  Reason"
        print(header)
        print("-" * 90)
        for scene in plan["scenes"]:
            print(
                f"{scene['scene_id']:<8} "
                f"{scene['component']:<25} "
                f"{scene['asset_source']:<20} "
                f"${scene['planning_estimate_usd']:>7.4f}  "
                f"{scene['reason'][:55]}"
            )
        print("-" * 90)
        s = plan["summary"]
        print(
            f"{'TOTALS':<8} {'':25} "
            f"{'':20} "
            f"${s['planned_total_cost_usd']:>7.4f}"
        )
        print(f"\n  REMOTION_ONLY: {s['remotion_only_scenes']}")
        print(f"  AI_IMAGE:      {s['ai_image_scenes']}")
        print(f"  GEN_VIDEO:     {s['generative_video_scenes']}")
        print(f"  Total:         {s['total_scenes']}")
        print(f"\n  Est. cost/episode: ${s['planned_total_cost_usd']:.4f}")
        print(f"  Est. monthly (20 ep): ${result['estimated_monthly_cost_usd']:.2f}")
        print("=" * 90)


if __name__ == "__main__":
    unittest.main(verbosity=2)
