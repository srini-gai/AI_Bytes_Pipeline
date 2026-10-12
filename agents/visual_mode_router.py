"""
Visual Mode Router — per-beat NATIVE / GENERATED routing layer.

Sits between the storyboard planner and the renderer. Annotates each
visual beat with a ``visual_mode`` so downstream agents know which
production path to follow:

    NATIVE     — Remotion component (typography, diagrams, data viz, flows)
    GENERATED  — fal.ai asset through AssetScene

A scene mixing both modes makes the episode HYBRID.

This module is a PLANNING layer. It does NOT modify renderer components,
Scene Composer, Visual Director, or the fal asset agent.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Components that are rendered entirely by Remotion (no external asset needed)
NATIVE_COMPONENTS: frozenset[str] = frozenset({
    "KineticTypoScene",
    "TokenScene",
    "SketchScene",
    "DataScene",
    "SplitCompareScene",
    "FlowScene",
    "HubSpokeScene",
    "ClusterScene",
    "DialScene",
    "BarChartScene",
    "NumberCounterScene",
    "TakeawayScene",
    "CTAScene",
    "TransformScene",
    "PipelineScene",
    "ContextWindowScene",
    "TokenStreamScene",
    "DocumentRetrievalScene",
    "NetworkBuildScene",
    "LayerRevealScene",
    "TimelineScene",
    "BeforeAfterScene",
    "MeterScene",
    "GraphGrowthScene",
    "CodeExecutionScene",
    "CardStackScene",
    "DataFlowScene",
    "AgentTraversalScene",
    "CircularFlowScene",
    "ComposedScene",
})

# Components that consume an externally generated asset
GENERATED_COMPONENTS: frozenset[str] = frozenset({
    "AssetScene",
})

# Scene types where generated media is semantically appropriate
GENERATED_SCENE_AFFINITY: frozenset[str] = frozenset({
    "METAPHOR",
    "DEMONSTRATION",
    "ZOOM",
    "SIMULATION",
})

# Scene types where native components are almost always the best treatment
NATIVE_SCENE_AFFINITY: frozenset[str] = frozenset({
    "HOOK",
    "TAKEAWAY",
    "CTA",
    "DATA",
    "DIAGRAM",
    "FLOW",
    "COMPARISON",
})


def classify_beat(scene: dict[str, Any]) -> str:
    """Classify a single storyboard scene/beat as NATIVE or GENERATED.

    Decision logic (in priority order):
    1. Component already decided: AssetScene → GENERATED, everything else → NATIVE
    2. If ``data.src`` references an asset path → GENERATED
    3. If ``beat_meta.asset_decision`` is explicitly set → respect it
    4. Fall back to NATIVE (the safe default — no paid generation)
    """
    component = scene.get("component", "")

    if component in GENERATED_COMPONENTS:
        return "GENERATED"

    if component in NATIVE_COMPONENTS:
        return "NATIVE"

    data = scene.get("data") or {}
    if isinstance(data, dict) and data.get("src"):
        return "GENERATED"

    beat_meta = scene.get("beat_meta") or {}
    if isinstance(beat_meta, dict):
        decision = beat_meta.get("asset_decision", "")
        if decision in ("generate_new", "reuse_existing"):
            return "GENERATED"
        if decision in ("typography_only", "cta_component", "native_component"):
            return "NATIVE"

    return "NATIVE"


def classify_episode(storyboard: list[dict[str, Any]]) -> str:
    """Return the episode-level visual mode: NATIVE, GENERATED, or HYBRID."""
    modes = {classify_beat(s) for s in storyboard}
    if modes == {"NATIVE"}:
        return "NATIVE"
    if modes == {"GENERATED"}:
        return "GENERATED"
    return "HYBRID"


def has_planner_declared_modes(storyboard: list[dict[str, Any]]) -> bool:
    """Return True if any beat has an explicit planner-declared visual_mode."""
    return any(
        s.get("visual_mode") in ("NATIVE", "GENERATED")
        for s in storyboard
    )


def validate_routing(
    storyboard: list[dict[str, Any]],
) -> list[str]:
    """Validate planner-declared visual_mode against assigned components.

    Returns a list of inconsistency strings (empty = valid). Storyboards
    without planner-declared ``visual_mode`` pass silently — the router
    infers mode via ``classify_beat()`` for backward compatibility.
    """
    issues: list[str] = []
    for scene in storyboard:
        declared = scene.get("visual_mode")
        if declared is None:
            continue

        sid = scene.get("scene_id", "?")
        component = scene.get("component", "")
        inferred = classify_beat(scene)

        if declared == "GENERATED":
            if component and component in NATIVE_COMPONENTS:
                issues.append(
                    f"S{sid}: visual_mode=GENERATED but component={component} "
                    f"is a native Remotion component — use AssetScene or change mode"
                )
            data = scene.get("data") or {}
            has_src = isinstance(data, dict) and bool(data.get("src"))
            beat_meta = scene.get("beat_meta") or {}
            has_asset_decision = (
                isinstance(beat_meta, dict)
                and beat_meta.get("asset_decision") in ("generate_new", "reuse_existing")
            )
            if component not in GENERATED_COMPONENTS and not has_src and not has_asset_decision:
                issues.append(
                    f"S{sid}: visual_mode=GENERATED but no generated asset or "
                    f"AssetScene component assigned — needs asset pipeline action"
                )

        elif declared == "NATIVE":
            if component in GENERATED_COMPONENTS:
                issues.append(
                    f"S{sid}: visual_mode=NATIVE but component={component} "
                    f"requires external generated media — change mode or component"
                )
            data = scene.get("data") or {}
            if isinstance(data, dict) and data.get("src"):
                issues.append(
                    f"S{sid}: visual_mode=NATIVE but data.src is set "
                    f"(external asset reference) — change mode to GENERATED"
                )

        elif declared == "HYBRID":
            issues.append(
                f"S{sid}: visual_mode=HYBRID is not valid at beat level — "
                f"use NATIVE or GENERATED per beat"
            )

        else:
            issues.append(
                f"S{sid}: visual_mode='{declared}' is not recognized — "
                f"must be NATIVE or GENERATED"
            )

    return issues


def annotate_storyboard(
    storyboard: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a copy of the storyboard with ``visual_mode`` on each beat.

    Does NOT mutate the input. The original storyboard is fully preserved —
    only ``visual_mode`` is added/confirmed on each scene dict.

    If a beat already has ``visual_mode`` (planner-declared), it is preserved.
    If missing, the router infers it via ``classify_beat()`` for backward
    compatibility with storyboards created before the planner declared modes.
    """
    annotated: list[dict[str, Any]] = []
    for scene in storyboard:
        enriched = dict(scene)
        if "visual_mode" not in enriched or enriched["visual_mode"] not in ("NATIVE", "GENERATED"):
            enriched["visual_mode"] = classify_beat(scene)
        annotated.append(enriched)
    return annotated


def route_storyboard(
    storyboard_path: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Read a storyboard JSON, annotate beats with visual_mode, write back.

    When ``dry_run=True``, computes the routing but does NOT write the file.

    Returns a routing summary dict.
    """
    data = json.loads(storyboard_path.read_text(encoding="utf-8"))
    scenes = data.get("storyboard", [])

    routing_issues = validate_routing(scenes)
    annotated = annotate_storyboard(scenes)
    episode_mode = classify_episode(scenes)

    native_count = sum(1 for s in annotated if s["visual_mode"] == "NATIVE")
    generated_count = sum(1 for s in annotated if s["visual_mode"] == "GENERATED")

    summary: dict[str, Any] = {
        "episode_mode": episode_mode,
        "total_beats": len(annotated),
        "native_beats": native_count,
        "generated_beats": generated_count,
        "routing_issues": routing_issues,
        "beat_modes": [
            {
                "scene_id": s.get("scene_id"),
                "component": s.get("component", ""),
                "visual_mode": s["visual_mode"],
            }
            for s in annotated
        ],
    }

    if routing_issues:
        for issue in routing_issues:
            logger.warning(f"Routing validation: {issue}")

    if not dry_run:
        data["storyboard"] = annotated
        data["visual_mode_routing"] = {
            "episode_mode": episode_mode,
            "native_beats": native_count,
            "generated_beats": generated_count,
            "routing_issues": routing_issues,
        }
        storyboard_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(
            f"Visual mode routing applied: {episode_mode} "
            f"({native_count} native, {generated_count} generated) "
            f"-> {storyboard_path}"
        )

    return summary


# ── Weekly diversity tracking ────────────────────────────────────────────────

def compute_weekly_diversity(
    fingerprints: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Analyze recent episode visual modes for channel-level variety.

    Reads ``visual_mode_routing`` from fingerprints (if present) and
    reports how the week's mix looks against the diversity guideline:
      ~2 predominantly Native Motion explainers
      ~3 predominantly Hybrid/Generated explainers

    This is advisory only — topic semantics always take priority.
    """
    modes: list[str] = []
    for key, fp in fingerprints.items():
        routing = fp.get("visual_mode_routing", {})
        ep_mode = routing.get("episode_mode", "")
        if ep_mode:
            modes.append(ep_mode)

    native_count = modes.count("NATIVE")
    generated_count = modes.count("GENERATED")
    hybrid_count = modes.count("HYBRID")
    total = len(modes)

    native_heavy = native_count
    generated_heavy = generated_count + hybrid_count

    advisory: list[str] = []
    if total >= 3:
        if native_heavy > 3:
            advisory.append(
                f"Channel leans heavily NATIVE ({native_heavy}/{total}). "
                f"Consider GENERATED/HYBRID for upcoming episodes if topic fits."
            )
        if generated_heavy > 4:
            advisory.append(
                f"Channel leans heavily GENERATED/HYBRID ({generated_heavy}/{total}). "
                f"Consider NATIVE explainers for upcoming episodes if topic fits."
            )

    return {
        "episodes_tracked": total,
        "native": native_count,
        "generated": generated_count,
        "hybrid": hybrid_count,
        "guideline_target": {"native_motion": "~2/week", "hybrid_generated": "~3/week"},
        "advisory": advisory,
    }


def enrich_fingerprint(
    fingerprint: dict[str, Any],
    storyboard: list[dict[str, Any]],
) -> dict[str, Any]:
    """Add visual_mode_routing metadata to an episode fingerprint.

    Called at approval time so the weekly diversity tracker has data.
    Does NOT mutate the input fingerprint.
    """
    annotated = annotate_storyboard(storyboard)
    episode_mode = classify_episode(storyboard)

    native_count = sum(1 for s in annotated if s["visual_mode"] == "NATIVE")
    generated_count = sum(1 for s in annotated if s["visual_mode"] == "GENERATED")

    enriched = dict(fingerprint)
    enriched["visual_mode_routing"] = {
        "episode_mode": episode_mode,
        "native_beats": native_count,
        "generated_beats": generated_count,
        "beat_sequence": [s["visual_mode"] for s in annotated],
    }
    return enriched
