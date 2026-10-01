"""
asset_planner_agent.py — Phase 3A Asset Planner

Sits between the Visual Director and the Visual Renderer.
For every storyboard scene, decides HOW it should be produced:
    REMOTION_ONLY     — deterministic components (default)
    AI_IMAGE          — AI still image + Remotion overlay/animation
    GENERATIVE_VIDEO  — AI video clip + Remotion overlay

Phase 3A: planning and dry-run only — no paid API calls.
Phase 3B: wire live provider adapters.

Standard agent signature:
    run(episode, week, input_data) -> dict
    input_data must contain 'storyboard' (list of scene dicts).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from agents.providers.base import AssetSource, GenerationType, make_cache_key

load_dotenv()

logger = logging.getLogger(__name__)


# ── Cost controls (read from .env, safe defaults) ─────────────────────────────

def _int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid value for {key} — using default {default}")
        return default


def _float_env(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid value for {key} — using default {default}")
        return default


@dataclass
class CostConfig:
    generative_video_max_clips: int   = field(default_factory=lambda: _int_env("GENERATIVE_VIDEO_MAX_CLIPS_PER_SHORT", 2))
    generative_video_max_seconds: float = field(default_factory=lambda: _float_env("GENERATIVE_VIDEO_MAX_SECONDS_PER_SHORT", 8.0))
    generative_video_max_cost_per_short: float = field(default_factory=lambda: _float_env("GENERATIVE_VIDEO_MAX_COST_PER_SHORT_USD", 0.75))
    generative_video_monthly_budget: float = field(default_factory=lambda: _float_env("GENERATIVE_VIDEO_MONTHLY_BUDGET_USD", 25.0))
    ai_image_max_per_short: int = field(default_factory=lambda: _int_env("AI_IMAGE_MAX_IMAGES_PER_SHORT", 3))
    ai_image_max_cost_per_short: float = field(default_factory=lambda: _float_env("AI_IMAGE_MAX_COST_PER_SHORT_USD", 0.20))


# ── Planning cost estimates (not authoritative — updated when provider selected) ──

_VIDEO_PLANNING_COST_PER_SECOND = 0.08   # USD
_IMAGE_PLANNING_COST = 0.06              # USD per image


# ── Deterministic veto triggers ───────────────────────────────────────────────
# If a scene's component, scene_type, or on_screen_text content matches any of
# these, the core explanatory layer MUST remain REMOTION_ONLY.
# Generative media may still be used as a background/environment if score
# justifies it AND the scene allows an overlay — but this is a separate
# "background only" flag and does not affect the core layer decision.

_DETERMINISTIC_COMPONENTS = {
    "TokenScene",
    "TransformScene",
    "FlowScene",
    "NetworkBuildScene",
    "SketchScene",
    "DataScene",
    "NumberCounterScene",
    "BarChartScene",
    "DialScene",
    "HubSpokeScene",
    "ClusterScene",
    "SplitCompareScene",
    "PipelineScene",
    "ContextWindowScene",
    "TokenStreamScene",
    "CodeExecutionScene",
    "GraphGrowthScene",
    "LayerRevealScene",
    "TimelineScene",
}

_DETERMINISTIC_SCENE_TYPES = {
    "FLOW",
    "DIAGRAM",
    "DATA",
    "COMPARISON",  # almost always has exact labels
}

# CTA and TAKEAWAY always stay Remotion (branding + exact text)
_ALWAYS_REMOTION_TYPES = {"CTA", "TAKEAWAY"}


def _has_deterministic_veto(scene: dict) -> bool:
    """
    Return True if the scene must use REMOTION_ONLY for its core layer.

    Veto fires when:
    - component is inherently data/diagram-driven
    - scene_type is CTA/TAKEAWAY (always brand text)
    - scene_type is FLOW/DIAGRAM/DATA/COMPARISON (exact labels required)
    """
    component = scene.get("component", "")
    scene_type = scene.get("scene_type", "")

    if scene_type in _ALWAYS_REMOTION_TYPES:
        return True
    if component in _DETERMINISTIC_COMPONENTS:
        return True
    if scene_type in _DETERMINISTIC_SCENE_TYPES:
        return True
    return False


# ── Scoring ───────────────────────────────────────────────────────────────────

@dataclass
class SceneScore:
    visual_value: int              # 0–10: would generative media improve this?
    deterministic_requirement: int # 0–10: must content be exact? (high = veto)
    cinematic_opportunity: int     # 0–10: would physical/cinematic motion help?
    cost_efficiency: int           # 0–10: is this scene worth spending budget?
    reuse_potential: int           # 0–10: can asset be reused EN→TA?
    reliability: int               # 0–10: how important is deterministic output?


def _score_scene(scene: dict) -> SceneScore:
    """
    Derive a SceneScore from storyboard scene metadata.

    Scoring is rule-based and inspectable — no magic numbers beyond
    the weights below.
    """
    scene_type = scene.get("scene_type", "")
    component  = scene.get("component", "")
    duration   = scene.get("duration_seconds", 4.0)
    objects    = scene.get("objects", [])
    on_screen  = scene.get("on_screen_text", [])

    # ── Visual value ──────────────────────────────────────────────────────────
    # Hook scenes benefit most from cinematic visuals; data/diagram scenes don't
    if scene_type == "HOOK":
        visual_value = 9
    elif scene_type in ("METAPHOR", "SIMULATION"):
        visual_value = 8
    elif scene_type == "ZOOM":
        visual_value = 6
    elif scene_type in ("TRANSFORMATION",):
        visual_value = 5
    elif scene_type in ("DEMONSTRATION", "FLOW", "DIAGRAM"):
        visual_value = 3
    elif scene_type in ("DATA", "COMPARISON"):
        visual_value = 2
    else:
        visual_value = 4

    # ── Deterministic requirement ─────────────────────────────────────────────
    # Higher = scene meaning depends on exact text/numbers → veto territory
    if _has_deterministic_veto(scene):
        det_req = 9
    elif any(c.isdigit() for text in on_screen for c in text):
        det_req = 7  # numbers present — lean deterministic
    elif len(on_screen) > 2:
        det_req = 6
    else:
        det_req = 3

    # ── Cinematic opportunity ─────────────────────────────────────────────────
    if scene_type == "HOOK":
        cin_opp = 9
    elif scene_type in ("METAPHOR",):
        cin_opp = 8
    elif scene_type == "ZOOM":
        cin_opp = 6
    elif duration >= 5.0:
        cin_opp = 4
    else:
        cin_opp = 3

    # ── Cost efficiency ───────────────────────────────────────────────────────
    # Short scenes give less "screen time per dollar" for generative assets
    if duration <= 3.0:
        cost_eff = 7 if scene_type == "HOOK" else 5
    elif duration <= 5.0:
        cost_eff = 7
    else:
        cost_eff = 6

    # ── Reuse potential ───────────────────────────────────────────────────────
    # Language-neutral visual (no embedded text concept) → high reuse
    has_text_concept = any(
        kw in " ".join(on_screen).lower()
        for kw in ("follow", "subscribe", "srini", "channel")
    )
    reuse = 4 if has_text_concept else 9

    # ── Reliability ───────────────────────────────────────────────────────────
    # How critical is it that the visual matches the narration exactly?
    if scene_type in ("DATA", "COMPARISON", "DIAGRAM", "FLOW"):
        reliability = 9
    elif scene_type in ("TAKEAWAY", "CTA"):
        reliability = 8
    elif scene_type == "HOOK":
        reliability = 4  # creative latitude is fine here
    else:
        reliability = 6

    return SceneScore(
        visual_value=visual_value,
        deterministic_requirement=det_req,
        cinematic_opportunity=cin_opp,
        cost_efficiency=cost_eff,
        reuse_potential=reuse,
        reliability=reliability,
    )


def _decide_asset_source(
    score: SceneScore,
    budget_state: dict,
    cost_config: CostConfig,
) -> tuple[AssetSource, str]:
    """
    Apply scoring formula and budget constraints to decide AssetSource.

    Formula:
        raw = visual_value × 2.0
            + cinematic_opportunity × 1.5
            + cost_efficiency × 1.0
            + reuse_potential × 1.0
            - deterministic_requirement × 3.0
            - reliability × 1.5

    Thresholds:
        GENERATIVE_VIDEO  if raw ≥ 18 AND not det_veto AND budget allows
        AI_IMAGE          if raw ≥ 10 AND not det_veto AND budget allows
        REMOTION_ONLY     otherwise (default — always safe)

    Deterministic veto (det_req ≥ 8) always forces REMOTION_ONLY regardless
    of score.
    """
    det_veto = score.deterministic_requirement >= 8

    raw = (
        score.visual_value * 2.0
        + score.cinematic_opportunity * 1.5
        + score.cost_efficiency * 1.0
        + score.reuse_potential * 1.0
        - score.deterministic_requirement * 3.0
        - score.reliability * 1.5
    )

    if det_veto:
        return AssetSource.REMOTION_ONLY, "Deterministic veto — scene requires exact text/data/diagram rendering"

    if raw >= 18:
        # Check video budget
        if budget_state["video_clips"] >= cost_config.generative_video_max_clips:
            return AssetSource.AI_IMAGE, (
                f"GENERATIVE_VIDEO selected by score ({raw:.1f}) but clip limit "
                f"({cost_config.generative_video_max_clips}) reached — downgraded to AI_IMAGE"
            )
        if budget_state["video_cost_usd"] >= cost_config.generative_video_max_cost_per_short:
            return AssetSource.AI_IMAGE, (
                f"GENERATIVE_VIDEO selected by score ({raw:.1f}) but cost limit "
                f"(${cost_config.generative_video_max_cost_per_short:.2f}/short) reached — downgraded to AI_IMAGE"
            )
        return AssetSource.GENERATIVE_VIDEO, f"Cinematic visual layer improves this scene (score {raw:.1f})"

    if raw >= 10:
        # Check image budget
        if budget_state["image_count"] >= cost_config.ai_image_max_per_short:
            return AssetSource.REMOTION_ONLY, (
                f"AI_IMAGE selected by score ({raw:.1f}) but image limit "
                f"({cost_config.ai_image_max_per_short}/short) reached — using REMOTION_ONLY"
            )
        if budget_state["image_cost_usd"] >= cost_config.ai_image_max_cost_per_short:
            return AssetSource.REMOTION_ONLY, (
                f"AI_IMAGE selected by score ({raw:.1f}) but image cost limit "
                f"(${cost_config.ai_image_max_cost_per_short:.2f}/short) reached — using REMOTION_ONLY"
            )
        return AssetSource.AI_IMAGE, f"AI image + Remotion overlay improves visual depth (score {raw:.1f})"

    return AssetSource.REMOTION_ONLY, f"Deterministic Remotion is optimal for this scene (score {raw:.1f})"


# ── Prompt intent generation ──────────────────────────────────────────────────

def _build_prompt_intent(scene: dict, asset_source: AssetSource) -> Optional[str]:
    """
    Build a language-neutral visual prompt intent for generative assets.

    Prompt is written in English (for clarity) but must describe a visual
    that contains NO embedded text, logos, or legible signage.
    All text will be added as a deterministic Remotion overlay.
    """
    if asset_source == AssetSource.REMOTION_ONLY:
        return None

    visual_goal = scene.get("visual_goal", "")
    scene_type  = scene.get("scene_type", "")
    objects     = scene.get("objects", [])

    # Strip any object names that imply text (labels, counters, etc.)
    no_text_suffix = (
        " No visible text, letters, numbers, logos, watermarks, UI labels, "
        "subtitles, or signage. All text will be added in post-production."
    )

    if scene_type == "HOOK":
        return (
            f"Abstract digital environment: {visual_goal.lower()}. "
            f"Dark cinematic atmosphere, purple/teal neon accents, high motion energy."
            + no_text_suffix
        )
    elif asset_source == AssetSource.AI_IMAGE:
        return (
            f"Conceptual illustration: {visual_goal.lower()}. "
            f"Dark background, purple and teal accent colors, clean abstract style."
            + no_text_suffix
        )
    return None


# ── Visual continuity ─────────────────────────────────────────────────────────

def _build_visual_continuity(scene: dict, asset_source: AssetSource) -> Optional[dict]:
    if asset_source == AssetSource.REMOTION_ONLY:
        return None

    scene_type = scene.get("scene_type", "")

    entry = "center"
    exit_ = "right"
    color = "dark-purple"
    motion = "slow-push-in"
    transition = "cut"

    if scene_type == "HOOK":
        entry = "center"
        exit_ = "right"
        color = "dark-purple"
        motion = "push-in"
        transition = "cut-to-remotion"
    elif scene_type == "ZOOM":
        entry = "center"
        exit_ = "center"
        color = "teal"
        motion = "zoom-in"
        transition = "fade"

    return {
        "entry_direction": entry,
        "exit_direction": exit_,
        "dominant_color_family": color,
        "motion_direction": motion,
        "transition_intent": transition,
    }


# ── Fallback ──────────────────────────────────────────────────────────────────

def _fallback_for(source: AssetSource) -> Optional[str]:
    """
    Required fallback hierarchy:
        GENERATIVE_VIDEO → AI_IMAGE → REMOTION_ONLY
        AI_IMAGE → REMOTION_ONLY
        REMOTION_ONLY → (none — always available)
    """
    return {
        AssetSource.GENERATIVE_VIDEO: AssetSource.AI_IMAGE.value,
        AssetSource.AI_IMAGE: AssetSource.REMOTION_ONLY.value,
        AssetSource.REMOTION_ONLY: None,
    }[source]


def _fallback_reason(source: AssetSource) -> Optional[str]:
    return {
        AssetSource.GENERATIVE_VIDEO: (
            "Still image with parallax / Remotion animation preserves visual concept "
            "if video generation is unavailable, fails, or exceeds budget."
        ),
        AssetSource.AI_IMAGE: (
            "Deterministic Remotion scene is always available as the base layer."
        ),
        AssetSource.REMOTION_ONLY: None,
    }[source]


# ── Planning cost estimate ────────────────────────────────────────────────────

def _planning_cost(source: AssetSource, duration: float, provider: str, model: str) -> float:
    if source == AssetSource.REMOTION_ONLY:
        return 0.0
    if source == AssetSource.AI_IMAGE:
        return _IMAGE_PLANNING_COST
    if source == AssetSource.GENERATIVE_VIDEO:
        return round(duration * _VIDEO_PLANNING_COST_PER_SECOND, 4)
    return 0.0


# ── Overlay content ───────────────────────────────────────────────────────────

def _overlay_content(scene: dict) -> list[str]:
    """
    List of deterministic Remotion overlay elements for this scene.
    Always included when asset_source is not REMOTION_ONLY.
    """
    on_screen = scene.get("on_screen_text", [])
    scene_type = scene.get("scene_type", "")

    overlays = list(on_screen)  # all on-screen text is always Remotion

    if scene_type == "HOOK":
        overlays.append("Srini on AI branding")
    if scene_type == "CTA":
        overlays.extend(["channel name", "follow button"])

    return overlays


# ── Per-scene plan entry ──────────────────────────────────────────────────────

def _plan_scene(
    scene: dict,
    budget_state: dict,
    cost_config: CostConfig,
    episode: int,
    week: int,
) -> dict:
    """Build a complete asset plan entry for one storyboard scene."""
    scene_id  = f"s{scene['scene_id']:02d}"
    component = scene.get("component", "unknown")
    duration  = float(scene.get("duration_seconds", 4.0))

    score = _score_scene(scene)
    asset_source, reason = _decide_asset_source(score, budget_state, cost_config)

    # Provider/model: None until Phase 3B wires live adapters
    provider = None
    model    = None

    prompt_intent     = _build_prompt_intent(scene, asset_source)
    visual_continuity = _build_visual_continuity(scene, asset_source)
    fallback_source   = _fallback_for(asset_source)
    fallback_reason_  = _fallback_reason(asset_source)
    est_cost          = _planning_cost(asset_source, duration, provider or "", model or "")
    language_neutral  = asset_source != AssetSource.REMOTION_ONLY

    # Cache key — only meaningful for generative assets
    cache_key: Optional[str] = None
    if asset_source != AssetSource.REMOTION_ONLY and prompt_intent:
        gen_type = (
            GenerationType.VIDEO
            if asset_source == AssetSource.GENERATIVE_VIDEO
            else GenerationType.IMAGE
        )
        cache_key = make_cache_key(
            prompt_intent=prompt_intent,
            provider=provider or "tbd",
            model=model or "tbd",
            generation_type=gen_type,
            aspect_ratio="9:16",
            duration_seconds=duration if asset_source == AssetSource.GENERATIVE_VIDEO else None,
        )

    # Update budget state
    if asset_source == AssetSource.GENERATIVE_VIDEO:
        budget_state["video_clips"] += 1
        budget_state["video_seconds"] += duration
        budget_state["video_cost_usd"] += est_cost
    elif asset_source == AssetSource.AI_IMAGE:
        budget_state["image_count"] += 1
        budget_state["image_cost_usd"] += est_cost

    entry: dict[str, Any] = {
        "scene_id": scene_id,
        "component": component,
        "asset_source": asset_source.value,
        "remotion_overlay": True,                      # always True — text/branding stays in Remotion
        "overlay_content": _overlay_content(scene),
        "reason": reason,
        "scoring": {
            "visual_value": score.visual_value,
            "deterministic_requirement": score.deterministic_requirement,
            "cinematic_opportunity": score.cinematic_opportunity,
            "cost_efficiency": score.cost_efficiency,
            "reuse_potential": score.reuse_potential,
            "reliability": score.reliability,
        },
        "priority": "HIGH" if asset_source == AssetSource.GENERATIVE_VIDEO else (
            "MEDIUM" if asset_source == AssetSource.AI_IMAGE else "REQUIRED"
        ),
        "asset_duration_seconds": duration if asset_source != AssetSource.REMOTION_ONLY else None,
        "prompt_intent": prompt_intent,
        "language_neutral": language_neutral,
        "planning_estimate_usd": est_cost,
        "actual_cost_usd": None,        # populated post-generation in Phase 3B
        "provider": provider,
        "model": model,
        "fallback_asset_source": fallback_source,
        "fallback_reason": fallback_reason_,
        "cache_key": cache_key,
        "visual_continuity": visual_continuity,
        "status": "planned",
    }

    return entry


# ── Asset manifest schema ─────────────────────────────────────────────────────

def _build_manifest(
    episode: int,
    week: int,
    scenes: list[dict],
    scene_plans: list[dict],
    budget_state: dict,
) -> dict:
    """Build the asset_manifest.json schema (planned phase — no actuals yet)."""
    assets = []
    for plan in scene_plans:
        assets.append({
            "scene_id": plan["scene_id"],
            "asset_source": plan["asset_source"],
            "status": plan["status"],
            "fallback": plan["fallback_asset_source"],
            "planning_estimate_usd": plan["planning_estimate_usd"],
            "actual_cost_usd": plan["actual_cost_usd"],
            "cache_key": plan["cache_key"],
        })

    return {
        "episode": episode,
        "week": week,
        "phase": "3A_planned",
        "planned_video_cost_usd": budget_state["video_cost_usd"],
        "planned_image_cost_usd": budget_state["image_cost_usd"],
        "planned_total_cost_usd": round(
            budget_state["video_cost_usd"] + budget_state["image_cost_usd"], 4
        ),
        "actual_total_cost_usd": None,      # populated post-generation
        "assets": assets,
    }


# ── Main agent entry point ────────────────────────────────────────────────────

def run(episode: int, week: int, input_data: dict) -> dict:
    """
    Asset Planner agent — Phase 3A.

    Args:
        episode:    Episode number 1–7
        week:       Week number
        input_data: Must contain 'storyboard' (list of scene dicts from visual_director_agent)

    Returns:
        {
            "success": True,
            "asset_plan_path": str,
            "asset_manifest_path": str,
            "scene_count": int,
            "remotion_scenes": int,
            "ai_image_scenes": int,
            "generative_video_scenes": int,
            "planned_total_cost_usd": float,
            "estimated_monthly_cost_usd": float,
        }
    """
    storyboard = input_data.get("storyboard")
    if not storyboard or not isinstance(storyboard, list):
        raise RuntimeError(f"EP{episode:02d} asset_planner: 'storyboard' missing or empty in input_data")

    cost_config = CostConfig()
    logger.info(
        f"EP{episode:02d} — Asset Planner start | {len(storyboard)} scenes | "
        f"video budget: {cost_config.generative_video_max_clips} clips / "
        f"${cost_config.generative_video_max_cost_per_short:.2f} | "
        f"image budget: {cost_config.ai_image_max_per_short} images / "
        f"${cost_config.ai_image_max_cost_per_short:.2f}"
    )

    budget_state: dict[str, Any] = {
        "video_clips": 0,
        "video_seconds": 0.0,
        "video_cost_usd": 0.0,
        "image_count": 0,
        "image_cost_usd": 0.0,
    }

    scene_plans: list[dict] = []
    for scene in storyboard:
        plan = _plan_scene(scene, budget_state, cost_config, episode, week)
        scene_plans.append(plan)
        logger.info(
            f"EP{episode:02d} — {plan['scene_id']} [{scene.get('scene_type')}] "
            f"→ {plan['asset_source']}  cost=${plan['planning_estimate_usd']:.4f}"
        )

    # Summary counts
    counts = {src.value: 0 for src in AssetSource}
    for p in scene_plans:
        counts[p["asset_source"]] += 1

    # Full asset plan output
    asset_plan = {
        "episode": episode,
        "week": week,
        "phase": "3A",
        "summary": {
            "total_scenes": len(scene_plans),
            "remotion_only_scenes": counts[AssetSource.REMOTION_ONLY.value],
            "ai_image_scenes": counts[AssetSource.AI_IMAGE.value],
            "generative_video_scenes": counts[AssetSource.GENERATIVE_VIDEO.value],
            "planned_video_cost_usd": round(budget_state["video_cost_usd"], 4),
            "planned_image_cost_usd": round(budget_state["image_cost_usd"], 4),
            "planned_total_cost_usd": round(
                budget_state["video_cost_usd"] + budget_state["image_cost_usd"], 4
            ),
        },
        "cost_config": {
            "generative_video_max_clips_per_short": cost_config.generative_video_max_clips,
            "generative_video_max_seconds_per_short": cost_config.generative_video_max_seconds,
            "generative_video_max_cost_per_short_usd": cost_config.generative_video_max_cost_per_short,
            "ai_image_max_images_per_short": cost_config.ai_image_max_per_short,
            "ai_image_max_cost_per_short_usd": cost_config.ai_image_max_cost_per_short,
        },
        "scenes": scene_plans,
    }

    manifest = _build_manifest(episode, week, storyboard, scene_plans, budget_state)

    # Write outputs
    base = Path(os.getenv("OUTPUT_BASE_PATH", "./output"))
    out_dir = base / f"week_{week:02d}" / f"ep{episode:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    plan_path = out_dir / f"ep{episode:02d}_asset_plan.json"
    manifest_path = out_dir / f"ep{episode:02d}_asset_manifest.json"

    plan_path.write_text(json.dumps(asset_plan, indent=2))
    manifest_path.write_text(json.dumps(manifest, indent=2))

    total_cost = asset_plan["summary"]["planned_total_cost_usd"]
    episodes_per_month = 20  # 5/week × 4 weeks
    monthly_estimate = round(total_cost * episodes_per_month, 2)

    logger.info(
        f"EP{episode:02d} — Asset Plan complete | "
        f"Remotion={counts[AssetSource.REMOTION_ONLY.value]} "
        f"AI_Image={counts[AssetSource.AI_IMAGE.value]} "
        f"GenVideo={counts[AssetSource.GENERATIVE_VIDEO.value]} | "
        f"Est. cost/ep=${total_cost:.4f} | "
        f"Est. monthly=${monthly_estimate:.2f}"
    )
    logger.info(f"EP{episode:02d} — asset_plan     → {plan_path}")
    logger.info(f"EP{episode:02d} — asset_manifest → {manifest_path}")

    return {
        "success": True,
        "asset_plan_path": str(plan_path),
        "asset_manifest_path": str(manifest_path),
        "scene_count": len(scene_plans),
        "remotion_scenes": counts[AssetSource.REMOTION_ONLY.value],
        "ai_image_scenes": counts[AssetSource.AI_IMAGE.value],
        "generative_video_scenes": counts[AssetSource.GENERATIVE_VIDEO.value],
        "planned_total_cost_usd": total_cost,
        "estimated_monthly_cost_usd": monthly_estimate,
    }
