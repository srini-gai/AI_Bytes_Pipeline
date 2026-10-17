"""
Visual Director Agent — v4 Creative Visual Reasoning
Reads a script JSON and produces a storyboard JSON array.

v4 changes (Creative Visual Reasoning):
  - 11-stage planning pipeline: narration → claim classification → visual thesis →
    conceptual beats → physical actions → continuity → grammar → novelty → scene plan →
    component mapping → renderability validation
  - The model no longer starts from component selection; components are implementation
    primitives chosen AFTER the creative concept is defined
  - Claim classification: FACTUAL_EXACT / ILLUSTRATIVE / VISUAL_METAPHOR per beat
  - Visual fingerprint storage and novelty guard against recent episodes
  - Renderability validation before implementation
  - Visual-only comprehension test (muted-video understanding)
  - Art Director stage: every episode must explicitly select a registered
    art_direction (visual world) — planning FAILS if no decision is made;
    there is no default world
  - approve_episode() persists the approved visual + art-direction fingerprint

Carries forward from v3.2:
  - Quality gate thresholds (beats, duration, typography, score)
  - Numeric integrity rule (sourced_numeric vs illustrative)
  - Cache check, 3-attempt retry
  - Same output schema (storyboard JSON array with beats)

Pipeline position:  script_agent → visual_director_agent → visual_agent
Output file:        ep{NN}_storyboard_{LANG}.json
"""
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

from engine.channel_config import load_channel, get_default_channel

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

def _channel_fingerprint_key(channel: str | None = None) -> str:
    """Resolve the fingerprint channel key from channel config or fallback."""
    if channel is not None:
        return channel
    try:
        cfg = load_channel(get_default_channel())
        return cfg.visual.fingerprint_channel_key
    except Exception:
        return "ai_bytes"

# ── Visual action primitives (v4) ────────────────────────────────────────────
# These are the building blocks the planner uses to describe what happens
# visually. Components implement these; primitives do not dictate components.

VISUAL_PRIMITIVES = {
    "split", "merge", "transform", "flip", "travel", "track",
    "rank", "sort", "connect", "fill", "drain", "collapse",
    "expand", "loop", "traverse", "compare", "reveal", "zoom",
    "check-off", "accelerate", "explode", "reorganize",
}

# ── Claim classification types (v4) ─────────────────────────────────────────

CLAIM_TYPES = {"FACTUAL_EXACT", "ILLUSTRATIVE", "VISUAL_METAPHOR"}

# ── Scene registry ────────────────────────────────────────────────────────────

VALID_SCENE_TYPES = {
    "HOOK", "DEMONSTRATION", "TRANSFORMATION", "FLOW",
    "COMPARISON", "DIAGRAM", "DATA", "ZOOM",
    "SIMULATION", "METAPHOR", "TAKEAWAY", "CTA",
}

# Implementation components — chosen AFTER creative planning, not before
VALID_COMPONENTS = {
    # Original
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
    # Motion-first primitives (v3)
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
    # Creative visual reasoning components (v4)
    "AgentTraversalScene",
    "CircularFlowScene",
    # Asset-based (fal.ai generated)
    "AssetScene",
}

# ── Quality gate thresholds ─────────────────────────────────────────────────
# Global structural gates (not channel-specific)
MIN_VISUAL_BEATS = 8
MAX_TYPOGRAPHY_RATIO = 0.25
MAX_CONSECUTIVE_SAME_LAYOUT = 2
MIN_VISUAL_DEMONSTRATIONS = 3
MIN_VISUAL_FIRST_SCORE = 80
MAX_SCENE_SECONDS_WITHOUT_BEATS = 6.0

def _visual_cfg() -> "engine.channel_config.VisualConfig":
    return load_channel(get_default_channel()).visual

# Channel-configurable duration/pacing — resolved at call time
def _target_min_seconds() -> float:
    return _visual_cfg().target_min_seconds

def _target_max_seconds() -> float:
    return _visual_cfg().target_max_seconds

def _max_hook_seconds() -> float:
    return _visual_cfg().max_hook_seconds

def _max_cta_seconds() -> float:
    return _visual_cfg().max_cta_seconds

def _min_narration_wps() -> float:
    return _visual_cfg().min_narration_wps

def _max_narration_wps() -> float:
    return _visual_cfg().max_narration_wps

# Duration decision (v4.1)
DURATION_RATIONALE_KEYS = (
    "content_complexity",
    "narration_length",
    "beat_density",
    "readability",
)
# Pacing is only checked once the storyboard carries real narration
MIN_WORDS_FOR_PACING_CHECK = 40
DURATION_SUM_TOLERANCE_S = 12.0

NUMERIC_VIZ_COMPONENTS = {
    "MeterScene", "BarChartScene", "DataScene",
    "GraphGrowthScene", "NumberCounterScene", "DialScene",
}

DEMONSTRATION_TYPES = {
    "DEMONSTRATION", "TRANSFORMATION", "FLOW",
    "COMPARISON", "DIAGRAM", "DATA", "ZOOM", "SIMULATION",
}
TYPOGRAPHY_COMPONENTS = {"KineticTypoScene"}

CAMERA_MOVES = {
    "slow-push-in", "zoom-in", "zoom-out", "pan-left", "pan-right",
    "pan-follow", "reveal", "static", "focus-shift", "track-object",
}

# ── Component family classification (diversity gate) ─────────────────────────
# Maps each renderer component to a perceptual family so the diversity gate
# compares VISUAL GRAMMAR, not exact component names.  Families follow the
# user-specified taxonomy; components not listed fall to "OTHER".

COMPONENT_FAMILIES: dict[str, str] = {
    # TYPOGRAPHY — text-centric kinetic reveals
    "KineticTypoScene": "TYPOGRAPHY",
    # FLOW / PIPELINE — linear or cyclical process animations
    "FlowScene": "FLOW_PIPELINE",
    "PipelineScene": "FLOW_PIPELINE",
    "DataFlowScene": "FLOW_PIPELINE",
    "CircularFlowScene": "FLOW_PIPELINE",
    "AgentTraversalScene": "FLOW_PIPELINE",
    # DIAGRAM — node-edge / architecture / layer views
    "SketchScene": "DIAGRAM",
    "NetworkBuildScene": "DIAGRAM",
    "HubSpokeScene": "DIAGRAM",
    "LayerRevealScene": "DIAGRAM",
    # TRANSFORMATION — A morphs into B
    "TransformScene": "TRANSFORMATION",
    "BeforeAfterScene": "TRANSFORMATION",
    # COMPARISON — side-by-side or split views
    "SplitCompareScene": "COMPARISON",
    # SEQUENCE / COLLECTION
    "CardStackScene": "SEQUENCE",
    "ClusterScene": "SEQUENCE",
    "TimelineScene": "SEQUENCE",
    # DATA — numeric / chart visualisations
    "DataScene": "DATA",
    "NumberCounterScene": "DATA",
    "MeterScene": "DATA",
    "GraphGrowthScene": "DATA",
    "BarChartScene": "DATA",
    "DialScene": "DATA",
    # DOMAIN — topic-specific animated primitives
    "TokenScene": "DOMAIN",
    "TokenStreamScene": "DOMAIN",
    "ContextWindowScene": "DOMAIN",
    "DocumentRetrievalScene": "DOMAIN",
    "CodeExecutionScene": "DOMAIN",
    # GENERATED — fal.ai editorial / video assets
    "AssetScene": "GENERATED_EDITORIAL",
    # STRUCTURAL terminals
    "TakeawayScene": "TAKEAWAY",
    "CTAScene": "CTA",
    # Composed (Scene Composer output)
    "ComposedScene": "COMPOSED",
}

# The canonical ordering of families for display / comparison
FAMILY_ORDER = [
    "TYPOGRAPHY", "FLOW_PIPELINE", "DIAGRAM", "TRANSFORMATION",
    "COMPARISON", "SEQUENCE", "DATA", "DOMAIN",
    "GENERATED_EDITORIAL", "GENERATED_VIDEO",
    "COMPOSED", "TAKEAWAY", "CTA", "OTHER",
]


def classify_component_families(component_sequence: list[str]) -> list[str]:
    """Map a component sequence to its family sequence."""
    return [COMPONENT_FAMILIES.get(c, "OTHER") for c in component_sequence]


def compute_family_distribution(families: list[str]) -> dict[str, float]:
    """Return {family: fraction} for a family sequence, excluding TAKEAWAY/CTA."""
    content_families = [f for f in families if f not in {"TAKEAWAY", "CTA"}]
    if not content_families:
        return {}
    from collections import Counter
    counts = Counter(content_families)
    total = len(content_families)
    return {fam: round(counts[fam] / total, 3) for fam in sorted(counts)}


def compute_family_similarity(
    current_families: list[str],
    recent_families: list[str],
) -> dict:
    """
    Compute a similarity score between two episodes' component-family sequences.

    Returns:
        {
          "jaccard": float (0–1, family SET overlap),
          "distribution_distance": float (0–1, L1 distance of family fractions),
          "order_similarity": float (0–1, bigram overlap),
          "mode_match": bool (set later by caller based on N/G ratio),
          "overall": str ("LOW" | "MEDIUM" | "HIGH"),
          "detail": str
        }
    """
    cur = [f for f in current_families if f not in {"TAKEAWAY", "CTA"}]
    rec = [f for f in recent_families if f not in {"TAKEAWAY", "CTA"}]

    if not cur or not rec:
        return {
            "jaccard": 0.0, "distribution_distance": 1.0,
            "order_similarity": 0.0, "mode_match": False,
            "overall": "LOW", "detail": "no content families to compare",
        }

    # Jaccard on family sets
    cur_set, rec_set = set(cur), set(rec)
    jaccard = len(cur_set & rec_set) / len(cur_set | rec_set) if (cur_set | rec_set) else 0.0

    # Distribution distance (L1 / 2, normalised to 0–1)
    cur_dist = compute_family_distribution(current_families)
    rec_dist = compute_family_distribution(recent_families)
    all_fams = set(cur_dist) | set(rec_dist)
    l1 = sum(abs(cur_dist.get(f, 0) - rec_dist.get(f, 0)) for f in all_fams)
    dist_distance = round(min(l1 / 2, 1.0), 3)

    # Order similarity: bigram overlap
    def bigrams(seq: list[str]) -> set[tuple[str, str]]:
        return {(seq[i], seq[i + 1]) for i in range(len(seq) - 1)}
    cur_bi, rec_bi = bigrams(cur), bigrams(rec)
    order_sim = (
        len(cur_bi & rec_bi) / len(cur_bi | rec_bi)
        if (cur_bi | rec_bi) else 0.0
    )

    # Overall rating
    score = jaccard * 0.4 + (1 - dist_distance) * 0.3 + order_sim * 0.3
    if score >= 0.70:
        overall = "HIGH"
    elif score >= 0.45:
        overall = "MEDIUM"
    else:
        overall = "LOW"

    detail = (
        f"jaccard={jaccard:.2f}, dist_distance={dist_distance:.2f}, "
        f"order_sim={order_sim:.2f}, composite={score:.2f}"
    )
    return {
        "jaccard": round(jaccard, 3),
        "distribution_distance": dist_distance,
        "order_similarity": round(order_sim, 3),
        "mode_match": False,
        "overall": overall,
        "detail": detail,
    }


def _diversity_gate(
    current_plan: dict,
    fingerprints: dict,
    channel: str | None = None,
) -> dict:
    """
    Pre-render creative-diversity check using COMPONENT FAMILIES.

    Compares the current plan against the MOST RECENT approved episode
    (same channel). Returns a gate result:
      {"pass": bool, "similarity": dict, "recent_key": str, "reason": str}

    Gate FAILS (pass=False) when:
      - Component-family similarity is HIGH, AND
      - Both episodes are strongly NATIVE-dominant (≤1 GENERATED scene each)

    The caller should trigger ONE bounded re-plan, not an endless retry loop.
    """
    if not fingerprints:
        return {
            "pass": True, "similarity": {}, "recent_key": "",
            "reason": "no prior episodes — diversity gate skipped",
        }

    channel = _channel_fingerprint_key(channel)
    # Channel-scoped: filter to same channel
    channel_fps = {
        k: v for k, v in fingerprints.items()
        if v.get("channel", channel) == channel
    }
    if not channel_fps:
        return {
            "pass": True, "similarity": {}, "recent_key": "",
            "reason": "no prior episodes in this channel",
        }

    # Most recent approved episode
    recent_key = list(channel_fps.keys())[-1]
    recent_fp = channel_fps[recent_key]

    # Current plan families
    scenes = current_plan.get("storyboard", [])
    cur_components = [s.get("component", "") for s in scenes]
    cur_families = classify_component_families(cur_components)

    # Recent episode families
    rec_components = recent_fp.get("component_sequence", [])
    rec_families_stored = recent_fp.get("component_families", [])
    rec_families = rec_families_stored or classify_component_families(rec_components)

    similarity = compute_family_similarity(cur_families, rec_families)

    # Check mode dominance
    cur_native = sum(1 for s in scenes if s.get("visual_mode") == "NATIVE")
    cur_generated = sum(1 for s in scenes if s.get("visual_mode") == "GENERATED")
    cur_native_dominant = cur_generated <= 1

    rec_native_dominant = True
    rec_mode_data = recent_fp.get("mode_ratio")
    if isinstance(rec_mode_data, dict):
        rec_native_dominant = rec_mode_data.get("generated", 0) <= 1
    else:
        rec_comps = recent_fp.get("component_sequence", [])
        rec_native_dominant = sum(1 for c in rec_comps if c == "AssetScene") <= 1

    both_native_dominant = cur_native_dominant and rec_native_dominant
    similarity["mode_match"] = both_native_dominant

    # Gate logic:
    # When both episodes are strongly NATIVE-dominant, mode can't provide
    # novelty, so the family similarity threshold is lower (MEDIUM triggers).
    # When mode mix differs, only HIGH similarity triggers the gate.
    gate_pass = True
    reason = "diversity sufficient"
    composite = float(similarity["detail"].split("composite=")[1]) if "composite=" in similarity["detail"] else 0.0

    if both_native_dominant and similarity["overall"] in {"MEDIUM", "HIGH"}:
        gate_pass = False
        reason = (
            f"{similarity['overall']} family similarity to {recent_key} "
            f"({similarity['detail']}) with BOTH episodes NATIVE-dominant — "
            f"consecutive NATIVE-heavy episodes need more family diversity or "
            f"consider GENERATED beats where semantically appropriate"
        )
    elif similarity["overall"] == "HIGH" and not both_native_dominant:
        reason = (
            f"HIGH family similarity to {recent_key} but mode mix differs — "
            f"diversity gate passes with advisory"
        )

    return {
        "pass": gate_pass,
        "similarity": similarity,
        "recent_key": recent_key,
        "current_families": cur_families,
        "recent_families": rec_families,
        "current_mode_ratio": {"native": cur_native, "generated": cur_generated},
        "reason": reason,
    }

# ── Intra-episode repetition guard ────────────────────────────────────────────
# Flags visual repetition WITHIN a single episode: same component reused with
# near-identical visual configuration, A→B→A return patterns, or long unchanged
# semantic composition.  Different text alone does NOT make a scene novel.

def _intra_episode_repetition_gate(scenes: list[dict]) -> dict:
    """
    Detect visual repetition within a single episode's storyboard.

    Returns:
        {
            "pass": bool,
            "violations": list[str],
            "detail": dict,
        }
    """
    violations: list[str] = []
    detail: dict = {}

    # Exclude structural scenes from repetition analysis
    STRUCTURAL = {"HOOK", "TAKEAWAY", "CTA"}
    content_scenes = [
        (i, s) for i, s in enumerate(scenes)
        if s.get("scene_type") not in STRUCTURAL
    ]

    if len(content_scenes) < 3:
        return {"pass": True, "violations": [], "detail": {}}

    # ── Check 1: Same component reused with near-identical configuration ──
    # Group content scenes by component name
    comp_groups: dict[str, list[tuple[int, dict]]] = {}
    for idx, scene in content_scenes:
        comp = scene.get("component", "")
        comp_groups.setdefault(comp, []).append((idx, scene))

    for comp, group in comp_groups.items():
        if len(group) < 2:
            continue
        for a_pos in range(len(group)):
            for b_pos in range(a_pos + 1, len(group)):
                idx_a, scene_a = group[a_pos]
                idx_b, scene_b = group[b_pos]
                sim = _scene_config_similarity(scene_a, scene_b)
                if sim >= 0.70:
                    violations.append(
                        f"INTRA_REPEAT: s{idx_a + 1:02d} and s{idx_b + 1:02d} both use "
                        f"{comp} with {sim:.0%} config similarity — reuse requires "
                        f"genuinely different visual state and semantic treatment"
                    )
                    detail[f"s{idx_a + 1:02d}_vs_s{idx_b + 1:02d}"] = {
                        "component": comp,
                        "similarity": round(sim, 3),
                    }

    # ── Check 2: A→B→A return pattern (non-adjacent same family) ──────────
    families = [
        COMPONENT_FAMILIES.get(s.get("component", ""), "OTHER")
        for s in scenes
    ]
    content_families = [
        (i, families[i]) for i, s in enumerate(scenes)
        if s.get("scene_type") not in STRUCTURAL
    ]
    for pos in range(len(content_families)):
        idx_a, fam_a = content_families[pos]
        for later in range(pos + 2, len(content_families)):
            idx_b, fam_b = content_families[later]
            if fam_a == fam_b and idx_b - idx_a >= 2:
                scene_a = scenes[idx_a]
                scene_b = scenes[idx_b]
                sim = _scene_config_similarity(scene_a, scene_b)
                if sim >= 0.55:
                    key = f"s{idx_a + 1:02d}_vs_s{idx_b + 1:02d}"
                    if key not in detail:
                        violations.append(
                            f"ABA_PATTERN: s{idx_a + 1:02d} ({fam_a}) returns at "
                            f"s{idx_b + 1:02d} with {sim:.0%} similarity — "
                            f"the returning scene must be meaningfully transformed"
                        )
                        detail[key] = {
                            "pattern": "ABA",
                            "family": fam_a,
                            "similarity": round(sim, 3),
                        }

    # ── Check 3: Family concentration — >2 scenes from same family ────────
    from collections import Counter
    fam_counts = Counter(f for _, f in content_families)
    for fam, count in fam_counts.items():
        if count > 2:
            violations.append(
                f"FAMILY_CONCENTRATION: {count} content scenes use family "
                f"{fam} — consider different visual approaches for variety"
            )
            detail[f"concentration_{fam}"] = count

    gate_pass = len(violations) == 0
    return {"pass": gate_pass, "violations": violations, "detail": detail}


def _scene_config_similarity(a: dict, b: dict) -> float:
    """
    Compute visual-configuration similarity between two scenes (0.0–1.0).
    Text content is ignored; structural visual properties are compared.
    """
    score = 0.0
    weights = 0.0

    # Same component = base similarity
    if a.get("component") == b.get("component"):
        score += 0.3
    weights += 0.3

    # Same scene_type
    if a.get("scene_type") == b.get("scene_type"):
        score += 0.15
    weights += 0.15

    # Object count similarity (visual density)
    objs_a = len(a.get("objects", []))
    objs_b = len(b.get("objects", []))
    if objs_a > 0 or objs_b > 0:
        obj_sim = 1.0 - abs(objs_a - objs_b) / max(objs_a, objs_b, 1)
        score += 0.15 * obj_sim
    else:
        score += 0.15
    weights += 0.15

    # Beat count similarity (animation structure)
    beats_a = len(a.get("beats", []))
    beats_b = len(b.get("beats", []))
    if beats_a > 0 or beats_b > 0:
        beat_sim = 1.0 - abs(beats_a - beats_b) / max(beats_a, beats_b, 1)
        score += 0.10 * beat_sim
    else:
        score += 0.10
    weights += 0.10

    # Data structure similarity (for DataScene, TokenScene, etc.)
    data_a = a.get("data", {})
    data_b = b.get("data", {})
    if isinstance(data_a, dict) and isinstance(data_b, dict):
        data_type_match = data_a.get("type") == data_b.get("type") if (data_a.get("type") or data_b.get("type")) else True
        data_keys_a = set(data_a.keys()) if data_a else set()
        data_keys_b = set(data_b.keys()) if data_b else set()
        key_overlap = len(data_keys_a & data_keys_b) / max(len(data_keys_a | data_keys_b), 1)
        data_sim = 0.5 * (1.0 if data_type_match else 0.0) + 0.5 * key_overlap
        score += 0.15 * data_sim
    else:
        score += 0.15
    weights += 0.15

    # Animation style similarity
    anim_a = a.get("animation", "")
    anim_b = b.get("animation", "")
    if anim_a == anim_b and anim_a:
        score += 0.15
    weights += 0.15

    return score / weights if weights > 0 else 0.0


# ── Art Director (v4) ───────────────────────────────────────────────────────
# The registry of renderable visual worlds lives in remotion/src/themes.ts
# (ART_DIRECTIONS). It is parsed here so the planner and the renderer share one
# source of truth. There is NO default world: a missing or unregistered
# selection fails planning.

THEMES_TS_PATH = Path(__file__).resolve().parent.parent / "remotion" / "src" / "themes.ts"

ART_DIRECTION_RATIONALE_KEYS = (
    "topic_semantics",
    "visual_thesis",
    "continuity_object",
    "attention_pattern",
    "fingerprint_comparison",
)

# Sentinel the planner may return when no registered world fits the episode.
NEW_WORLD_REQUIRED = "NEW_WORLD_REQUIRED"


class ArtDirectionError(RuntimeError):
    """Planning cannot proceed without an explicit, registered Art Director decision."""


def load_art_direction_registry(themes_path: Path = THEMES_TS_PATH) -> dict[str, dict]:
    """
    Parse remotion/src/themes.ts and return {id: {name, visual_world, light_or_dark}}
    for every manifest registered in ART_DIRECTIONS.
    """
    try:
        source = themes_path.read_text(encoding="utf-8")
    except OSError as e:
        raise ArtDirectionError(f"Art direction registry unreadable: {themes_path}: {e}") from e

    registry_block = re.search(
        r"export const ART_DIRECTIONS[^=]*=\s*\{(.*?)\};", source, re.DOTALL
    )
    if not registry_block:
        raise ArtDirectionError(f"ART_DIRECTIONS registry not found in {themes_path}")

    manifests: dict[str, dict] = {}
    for const_name, body in re.findall(
        r"export const (\w+): ArtDirection = \{(.*?)\n\};", source, re.DOTALL
    ):
        manifests[const_name] = dict(
            re.findall(r"^\s{2}(id|name|visual_world|light_or_dark): '([^']*)'", body, re.MULTILINE)
        )

    registry: dict[str, dict] = {}
    for key, const_name in re.findall(r"'([^']+)'\s*:\s*(\w+)", registry_block.group(1)):
        fields = manifests.get(const_name, {})
        registry[key] = {
            "name": fields.get("name", key),
            "visual_world": fields.get("visual_world", ""),
            "light_or_dark": fields.get("light_or_dark", ""),
        }

    if not registry:
        raise ArtDirectionError(f"ART_DIRECTIONS registry in {themes_path} is empty")
    return registry


def _format_art_direction_menu(registry: dict[str, dict]) -> str:
    """Format the registered visual worlds for the planner prompt."""
    lines = ["Registered visual worlds (art_direction.id must be one of these):"]
    for ad_id, meta in registry.items():
        lines.append(
            f"  - {ad_id}: {meta.get('visual_world', '')} "
            f"[{meta.get('light_or_dark', '?')}]"
        )
    lines.append(
        f"If none genuinely fits, return art_direction.id = \"{NEW_WORLD_REQUIRED}\" "
        f"with a proposed visual_world — planning will stop for a new manifest."
    )
    return "\n".join(lines)


def _fingerprint_art_direction_id(fingerprint: dict) -> str:
    """Return the art-direction id recorded in an episode fingerprint, if any."""
    ad = fingerprint.get("art_direction")
    if isinstance(ad, dict):
        return str(ad.get("id", ""))
    if isinstance(ad, str):
        return ad
    return ""


def _validate_art_direction(
    art_direction: object,
    registry: dict[str, dict],
    fingerprints: dict,
) -> list[str]:
    """
    Validate the Art Director decision. Returns violation strings
    (empty list = valid). Never substitutes a default world.
    """
    if not isinstance(art_direction, dict) or not art_direction:
        return [
            "ART_DIRECTION_MISSING: no art_direction decision — the Art Director "
            "must explicitly select a visual world (there is no default)"
        ]

    violations: list[str] = []
    ad_id = str(art_direction.get("id", "")).strip()

    if ad_id == NEW_WORLD_REQUIRED:
        return [
            f"ART_DIRECTION_NEW_WORLD_REQUIRED: proposed visual world "
            f"'{art_direction.get('visual_world', '')}' has no registered manifest"
        ]
    if not ad_id:
        violations.append("ART_DIRECTION_MISSING: art_direction.id is empty")
    elif ad_id not in registry:
        violations.append(
            f"ART_DIRECTION_UNREGISTERED: '{ad_id}' is not in ART_DIRECTIONS "
            f"({', '.join(registry)})"
        )

    if not str(art_direction.get("visual_world", "")).strip():
        violations.append("ART_DIRECTION_INCOMPLETE: art_direction.visual_world is empty")

    rationale = art_direction.get("rationale")
    if not isinstance(rationale, dict):
        violations.append(
            "ART_DIRECTION_INCOMPLETE: art_direction.rationale missing — must cover "
            + ", ".join(ART_DIRECTION_RATIONALE_KEYS)
        )
    else:
        missing = [k for k in ART_DIRECTION_RATIONALE_KEYS if not str(rationale.get(k, "")).strip()]
        if missing:
            violations.append(
                f"ART_DIRECTION_INCOMPLETE: rationale missing {', '.join(missing)}"
            )

    # Repetition guard: reusing the most recently approved world needs a reason
    if ad_id and fingerprints:
        last_key = list(fingerprints.keys())[-1]
        if (
            _fingerprint_art_direction_id(fingerprints[last_key]) == ad_id
            and not str(art_direction.get("repeat_justification", "")).strip()
        ):
            violations.append(
                f"ART_DIRECTION_REPEAT: '{ad_id}' repeats the most recent approved "
                f"episode ({last_key}) — add repeat_justification or choose another world"
            )

    return violations


def _is_art_direction_violation(violation: str) -> bool:
    return violation.startswith("ART_DIRECTION_")


def art_direction_failure_path(episode: int, week: int, lang: str) -> Path:
    """Marker written when planning fails for lack of an Art Director decision."""
    return _episode_dir(episode, week) / f"ep{episode:02d}_art_direction_FAILED_{lang.upper()}.json"


def _record_art_direction_failure(
    episode: int, week: int, lang: str, violations: list[str]
) -> None:
    """Persist the failure so the downstream render cannot silently fall back."""
    path = art_direction_failure_path(episode, week, lang)
    path.write_text(
        json.dumps(
            {
                "episode": episode,
                "week": week,
                "lang": lang.upper(),
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "violations": violations,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    logger.error(f"EP{episode:02d} — Art Director decision missing/invalid -> {path}")


def _clear_art_direction_failure(episode: int, week: int, lang: str) -> None:
    path = art_direction_failure_path(episode, week, lang)
    if path.exists():
        path.unlink()
        logger.info(f"EP{episode:02d} — cleared stale Art Director failure marker")


def _episode_key(episode: int, week: int) -> str:
    return f"week{week:02d}_ep{episode:02d}"


# ── Fingerprint storage ─────────────────────────────────────────────────────

FINGERPRINT_PATH = Path(
    os.getenv("OUTPUT_BASE_PATH", "./output")
) / "visual_fingerprints.json"


def _load_fingerprints() -> dict:
    """Load recent episode visual fingerprints for novelty comparison."""
    if not FINGERPRINT_PATH.exists():
        return {}
    try:
        data = json.loads(FINGERPRINT_PATH.read_text(encoding="utf-8"))
        return data.get("episodes", {})
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not load fingerprints: {e}")
        return {}


def _save_fingerprint(episode_key: str, fingerprint: dict) -> None:
    """
    Add/replace an approved episode fingerprint in the fingerprint store.
    Raises on failure — an approval must never be silently lost.
    """
    if FINGERPRINT_PATH.exists():
        data = json.loads(FINGERPRINT_PATH.read_text(encoding="utf-8"))
    else:
        data = {
            "version": "v4.1",
            "description": "Visual + art-direction fingerprints for approved episodes",
            "episodes": {},
        }
    data.setdefault("episodes", {})
    # Re-insert so the most recently approved episode is always last
    data["episodes"].pop(episode_key, None)
    data["episodes"][episode_key] = fingerprint
    FINGERPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = FINGERPRINT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(FINGERPRINT_PATH)
    logger.info(f"Fingerprint saved: {episode_key} -> {FINGERPRINT_PATH}")


def _format_fingerprints_for_prompt(
    fingerprints: dict,
    channel: str | None = None,
) -> str:
    """Format recent fingerprints as context for the novelty guard.

    Only includes fingerprints from the same channel (channel-scoped
    creative memory).
    """
    channel = _channel_fingerprint_key(channel)
    scoped = {
        k: v for k, v in fingerprints.items()
        if v.get("channel", channel) == channel
    }
    if not scoped:
        return "No previous episode fingerprints available for this channel."
    lines = [
        "Recent episode visual fingerprints — SAME CHANNEL "
        "(compare your plan against these for DIVERSITY):"
    ]
    for key, fp in scoped.items():
        lines.append(f"\n--- {key} ({fp.get('topic', 'unknown')}) ---")
        lines.append(f"  Visual thesis: {fp.get('visual_thesis', 'N/A')}")
        lines.append(f"  Continuity object: {fp.get('continuity_object_type', 'N/A')}")
        lines.append(f"  Dominant motion: {fp.get('dominant_motion_grammar', 'N/A')}")
        lines.append(f"  Comparison structure: {fp.get('comparison_structure', 'N/A')}")
        lines.append(f"  Dominant primitives: {', '.join(fp.get('dominant_primitives', []))}")
        lines.append(f"  Visual world: {fp.get('visual_world', 'N/A')}")
        ad = fp.get("art_direction")
        if isinstance(ad, dict) and ad.get("id"):
            lines.append(
                f"  Art direction: {ad.get('id')} — {ad.get('visual_world', '')} "
                f"[{ad.get('light_or_dark', '?')}]"
            )
        comps = fp.get("component_sequence", [])
        if comps:
            lines.append(f"  Component sequence: {' -> '.join(comps)}")
        families = fp.get("component_families") or classify_component_families(comps)
        if families:
            lines.append(f"  Component FAMILIES: {' -> '.join(families)}")
        mode = fp.get("mode_ratio")
        if isinstance(mode, dict):
            lines.append(
                f"  Mode ratio: NATIVE={mode.get('native', '?')} "
                f"GENERATED={mode.get('generated', '?')}"
            )
    return "\n".join(lines)


# ── System prompt (v4 — Creative Visual Reasoning) ─────────────────────────

_SYSTEM_PROMPT = """\
You are the Visual Director v4 for "Srini on AI", a YouTube Shorts channel about AI for developers.

Your job: given a script JSON and recent episode fingerprints, REASON about the visual
story first, then produce a storyboard JSON.

══════════════════════════════════════════════════════
CORE PRINCIPLE — Creative Visual Reasoning
══════════════════════════════════════════════════════
Before choosing any component, answer:
"What visual story would make this concept understandable even with the audio muted?"

Voice EXPLAINS. Visuals DEMONSTRATE.
The viewer with sound off must understand the core idea from animation alone.

You must follow this planning order. Do NOT start from component selection:

  1. Visual Thesis — core concept, metaphor, continuity object, transformation journey
  2. EPISODE CREATIVE CONCEPT — before any component or mode selection, define the
     episode-level creative concept (see EPISODE CREATIVE CONCEPT section). This is the
     creative identity of the episode: its visual premise, visual world, progression arc,
     hero visual moments, and emotional tone. This concept must be DISTINGUISHABLE from
     recent approved episodes — changing component names alone is not sufficient.
  3. Claim Classification — classify every concept/claim as FACTUAL_EXACT, ILLUSTRATIVE, or VISUAL_METAPHOR
  4. Conceptual Beat Decomposition — intellectual beats, not just narration sentences
  5. Physical Visual Actions — use meaningful action verbs (split, merge, transform, etc.)
  6. Continuity Object — carry one object through scenes as chapters of one journey
  7. Visual Grammar — what to use, what to deliberately avoid
  8. Art Director — explicitly select the episode's visual world (see ART DIRECTOR)
  9. Generated Opportunity Evaluation — for each beat, evaluate the strongest treatment:
     NATIVE explanatory motion, GENERATED image/video/editorial, or TYPOGRAPHIC.
     Consider: semantic clarity, emotional/cinematic potential, explanatory precision,
     novelty relative to recent episodes, visual impact, generation cost.
     If a beat has strong cinematic or metaphorical potential, fal.ai GENERATED
     treatment should be considered BEFORE defaulting to a native diagram.
     (see GENERATED OPPORTUNITY EVALUATION section)
  10. Modality Intent — for each beat, decide what it SEMANTICALLY needs: process flow,
     data diagram, editorial metaphor, conceptual imagery, code walkthrough, comparison.
     This is about WHAT the beat communicates, not which component renders it.
  11. Diversity Context — compare your modality intent and family pattern against the
     RECENT EPISODE FINGERPRINTS below. The fingerprints show each prior episode's
     COMPONENT FAMILIES (TYPOGRAPHY, FLOW_PIPELINE, DIAGRAM, TRANSFORMATION, COMPARISON,
     SEQUENCE, DATA, DOMAIN, GENERATED_EDITORIAL, TAKEAWAY, CTA). If your plan produces
     an excessively similar family sequence to the most recent approved episode, alter
     your approach — different families, different modality choices, different metaphors.
     Visual novelty is a real planning objective; the viewer watches these consecutively.
  12. Visual Mode — for each beat, decide NATIVE or GENERATED (see VISUAL MODE).
      Informed by modality intent AND diversity context. Do NOT let component
      availability determine visual mode — decide what the beat NEEDS first.
  13. Scene Plan — duration, pacing, structure
  14. Component Mapping — ONLY NOW choose implementation components
  15. Renderability — can current components render each beat?

══════════════════════════════════════════════════════
ART DIRECTOR (v4 — mandatory, no default)
══════════════════════════════════════════════════════
Every episode must explicitly choose its visual world from the registered worlds
listed in the user message. There is NO default world — never pick one by habit.
Base the choice on:
  • topic/content semantics — where does this subject naturally live?
  • the Visual Thesis
  • the continuity object — what environment makes it read natively?
  • emotional/attention pattern — the mood and pacing the topic needs
  • recent art-direction fingerprints — avoid unintended repetition
Reusing the most recently approved world is allowed only with an explicit
repeat_justification. If no registered world fits, set id to "NEW_WORLD_REQUIRED".

══════════════════════════════════════════════════════
CLAIM CLASSIFICATION (v4 — required per beat)
══════════════════════════════════════════════════════
Every visual concept or claim must be classified:

FACTUAL_EXACT — A factual value or mechanism that must be represented accurately.
  Examples: sourced model limits, documented API behaviour, exact technical sequences.
  Requires source_reference when externally factual.

ILLUSTRATIVE — A simplified representation used to communicate relative behaviour.
  Examples: score badges, relative token lengths, fictional task progress, qualitative scales.
  Must not look like measured research data.

VISUAL_METAPHOR — A deliberately non-literal visual explanation.
  Examples: human preference as a judge paddle, model objective as a compass, information as travelling objects.
  The rendered design may be expressive but must not imply the metaphor is the literal implementation.

Add "claim_type" to each beat in the storyboard.

══════════════════════════════════════════════════════
VISUAL PRIMITIVES — action vocabulary
══════════════════════════════════════════════════════
Describe what happens visually using these action verbs:
  split | merge | transform | flip | travel | track | rank | sort |
  connect | fill | drain | collapse | expand | loop | traverse |
  compare | reveal | zoom | check-off | accelerate | explode | reorganize

A fade, pulse, glow, or text entrance ALONE does not qualify as a meaningful visual beat.

══════════════════════════════════════════════════════
DURATION POLICY (allowed 45–60 seconds — no default length)
══════════════════════════════════════════════════════
45s is the floor, not the target; 60s is the ceiling, not the goal.
Choose the total duration for THIS episode from:
  • content complexity — how many conceptual beats the idea genuinely needs
  • narration length — the voiceover is spoken at ≈2.5 words/second
  • beat density — one meaningful visual event every 2–4 seconds
  • readability — every on-screen label stays readable on a phone
Report the choice in "duration_decision".

STRUCTURE (proportions of the chosen total, not fixed timestamps):
  HOOK            — first; visually surprise immediately; ≤4s
  DEMONSTRATION   — show the phenomenon BEFORE explaining (next ~10%)
  EXPLANATION     — multiple beats: diagrams, transformations, comparisons
  WHY IT MATTERS  — concrete real-world usage beats
  TAKEAWAY        — compress the lesson into one visual moment
  CTA             — always last, ≤3s

══════════════════════════════════════════════════════
EPISODE CREATIVE CONCEPT (required — before component selection)
══════════════════════════════════════════════════════
Before choosing components or visual modes, define an episode-level creative concept:

  "episode_creative_concept": {
    "visual_premise": "<one line — the creative idea that makes this episode visually distinct>",
    "visual_world": "<the environment/atmosphere this concept lives in>",
    "progression_arc": "<how the visual narrative progresses across the episode>",
    "hero_moments": ["<2-4 specific moments that define the episode's visual identity>"],
    "emotional_tone": "<the feeling the visuals create — e.g. tension, clarity, wonder>",
    "recent_treatments_avoided": ["<specific visual approaches from recent episodes deliberately not used>"],
    "generated_opportunities": ["<beats where cinematic/editorial/generated visuals would be strongest>"],
    "native_strengths": ["<beats where deterministic native explanation is clearly superior>"]
  }

This concept is the creative identity of the episode. It must be DISTINGUISHABLE from
recent approved episodes. Changing component names alone is not sufficient. Changing
palette alone is not sufficient. The episode should have a distinct visual idea
appropriate to its subject.

══════════════════════════════════════════════════════
GENERATED OPPORTUNITY EVALUATION (required per beat)
══════════════════════════════════════════════════════
For each narration clause / visual beat, evaluate the strongest treatment:

  NATIVE — Remotion component renders deterministic explanatory motion.
    Best for: process flow, graph, counter, comparison, pipeline, timeline,
    data viz, architecture diagram, code execution, precise mechanism.

  GENERATED — fal.ai editorial/cinematic image or video asset (AssetScene).
    Best for: editorial metaphor, environment, real-world analogy, artistic
    interpretation, conceptual imagery, emotional/cinematic moment.

  TYPOGRAPHIC — Text-dominant kinetic treatment.
    Best for: hook punch, key contrast, takeaway compression, CTA.

For each beat, consider (in order):
  1. Semantic clarity — does the beat explain a mechanism or evoke a concept?
  2. Emotional/cinematic potential — would a generated image land harder?
  3. Explanatory precision — does the beat need exact, repeatable animation?
  4. Novelty relative to recent episodes — is this visual grammar overused?
  5. Visual impact — which treatment creates the strongest single frame?
  6. Generation cost — fal.ai has a budget; spend it on hero moments.

Do NOT choose NATIVE simply because a matching Remotion component exists.
When a beat has strong cinematic/metaphorical potential, GENERATED should be
considered before defaulting to a native diagram.

Include per-scene "treatment_evaluation" in the storyboard:
  "treatment_evaluation": {
    "considered": "<NATIVE | GENERATED | TYPOGRAPHIC>",
    "chosen": "<NATIVE | GENERATED | TYPOGRAPHIC>",
    "reason": "<why this treatment is strongest for this beat>"
  }

IMPORTANT: If the episode contains multiple strong GENERATED opportunities and
you still select 100% NATIVE, you MUST include a "native_justification" field
explaining why NATIVE is genuinely the best choice for every single beat.

No forced quotas: 100% NATIVE is valid when truly appropriate. 100% GENERATED
is valid for the right content. But the decision must be DELIBERATE, not default.

══════════════════════════════════════════════════════
VISUAL MODE — per-beat production decision (required)
══════════════════════════════════════════════════════
Every scene must declare "visual_mode": "NATIVE" or "GENERATED".
Choose based on semantic need — what the CONCEPT requires, not convenience.

NATIVE — Remotion component renders the visual entirely from code.
  Choose for: process flow, graph, counter, comparison, pipeline, timeline,
  data viz, architecture diagram, code execution, typography emphasis, CTA.

GENERATED — An externally generated image/video asset via fal.ai (AssetScene).
  Choose for: editorial metaphor, environment, person, conceptual imagery,
  real-world analogy, artistic interpretation.

Rules:
  - visual_mode is PER SCENE — choose independently for each beat
  - HYBRID is NOT a valid beat-level mode — it is episode-level only
  - GENERATED requires component = AssetScene
  - NATIVE requires a Remotion component (not AssetScene)
  - The router validates your choices after planning

══════════════════════════════════════════════════════
SCENE SCHEMA
══════════════════════════════════════════════════════
Each scene must be a JSON object with EXACTLY these keys:
{
  "scene_id": <integer, 1-based>,
  "visual_mode": "<NATIVE | GENERATED>",
  "duration_seconds": <float, 2.0–8.0 — prefer 2.5–5.0>,
  "narration": "<voiceover spoken during this scene>",
  "scene_type": "<HOOK|DEMONSTRATION|TRANSFORMATION|FLOW|COMPARISON|DIAGRAM|DATA|ZOOM|SIMULATION|METAPHOR|TAKEAWAY|CTA>",
  "visual_goal": "<one sentence: what the viewer must understand visually>",
  "component": "<component name from COMPONENT GUIDE>",
  "objects": [<named visual elements>],
  "animation": "<description of all motion>",
  "on_screen_text": [<SHORT labels only — max 6 words each — NEVER narration>],
  "data": <object or null>,
  "transition": "<fade | slide-right | zoom-in | morph | cut>",
  "carry_object_from": "<optional — named object from previous scene for continuity>",
  "beats": [
    {
      "start": <float seconds from scene start>,
      "end": <float>,
      "action": "<specific visual action — what physically changes>",
      "focus": "<element in focus>",
      "camera": "<optional — slow-push-in | zoom-in | zoom-out | pan-left | pan-right | pan-follow | reveal | static | focus-shift | track-object>",
      "claim_type": "<FACTUAL_EXACT | ILLUSTRATIVE | VISUAL_METAPHOR>"
    }
  ]
}

BEATS RULE: Every scene > 4 seconds MUST have ≥2 beats. Every scene > 6 seconds ≥3 beats.

══════════════════════════════════════════════════════
COMPONENT GUIDE — choose by what the scene DOES, AFTER creative planning
══════════════════════════════════════════════════════
STRUCTURAL:
  KineticTypoScene      — HOOK only; punchy text reveal; max 3s
  TakeawayScene         — bold takeaway line (TAKEAWAY zone only)
  CTAScene              — follow CTA (CTA zone, ≤3s)

TRANSFORMATION:
  TransformScene        — A morphs into B visually
  BeforeAfterScene      — animated wipe comparing two states

FLOW / PIPELINE:
  FlowScene             — linear step-by-step pipeline with icons
  PipelineScene         — horizontal multi-stage with moving data packet
  DataFlowScene         — labelled packets through system diagram

DATA VISUALISATION:
  DataScene             — comparison bars ({type:"bars",...} or {type:"comparison",...})
  NumberCounterScene    — large number counting up
  MeterScene            — filling gauge
  GraphGrowthScene      — chart growing in real time
  BarChartScene         — simple 0–100 bar gauge
  DialScene             — dial/knob

NETWORK / ARCHITECTURE:
  NetworkBuildScene     — graph builds node-by-node
  HubSpokeScene        — radial hub + spokes
  SketchScene           — node-edge architecture diagram
  LayerRevealScene      — stacked layers peel/reveal

SEQUENCE / COLLECTION:
  TimelineScene         — horizontal event timeline
  CardStackScene        — deck fans/sorts/filters
  ClusterScene          — semantic cluster groupings

AGENT / PROCESS (v4):
  AgentTraversalScene   — a character travels left→right through 4 labelled zones,
                          using a tool per zone; a task card checks off steps.
                          on_screen_text: [zone1, zone2, zone3, zone4, title];
                          objects: [tool icon ×3]; data.task_steps: [step ×3]; 5 beats
  CircularFlowScene     — 4-quadrant rotating loop for a cyclical process.
                          on_screen_text: [q1, q2, q3, q4, title]; objects: [icon ×4];
                          data.center_label; 5 beats

GENERATED ASSET (visual_mode = GENERATED only):
  AssetScene            — displays a fal.ai-generated image/video asset;
                          use for editorial metaphor, environment, conceptual imagery;
                          requires data.src (asset path) set by the asset pipeline

DOMAIN SPECIFIC:
  TokenScene            — text → token boxes → IDs
  TokenStreamScene      — tokens generate left-to-right
  ContextWindowScene    — rectangle fills with chunks
  DocumentRetrievalScene — card fan → relevant items travel
  CodeExecutionScene    — code runs line-by-line
  SplitCompareScene     — static side-by-side

══════════════════════════════════════════════════════
CONTINUITY — scenes are chapters, not cards
══════════════════════════════════════════════════════
Identify a continuity object. Carry it between scenes by preserving:
  identity • approximate appearance • direction • semantic meaning

Use "carry_object_from" to name the object that continues.

══════════════════════════════════════════════════════
FULL-CANVAS PRINCIPLE
══════════════════════════════════════════════════════
One obvious focal object per beat. Prefer: focus → transform → follow → reveal
Avoid: small centered diagram → labels → arrows → next diagram
  (unless the concept genuinely requires an architecture view)

══════════════════════════════════════════════════════
TEXT RESTRICTIONS
══════════════════════════════════════════════════════
Full-screen typography: HOOK, one key contrast, TAKEAWAY, CTA only.
All explanation scenes: objects + motion + labels, not headlines + sentences.
Typography-only ≤ 25% of total runtime.
NEVER duplicate voiceover narration as on_screen_text.

══════════════════════════════════════════════════════
NUMERIC INTEGRITY (permanent)
══════════════════════════════════════════════════════
Numeric viz components must include "source_type" at the scene level:
  "source_type": "sourced_numeric" + "source_reference": "<citation>"
  "source_type": "illustrative" — qualitative labels only, no invented numbers

══════════════════════════════════════════════════════
COMPOSITION VARIETY
══════════════════════════════════════════════════════
Alternate between: full-canvas | split screen | zoomed object | horizontal pipeline |
  vertical flow | graph/network | data | comparison | cinematic
No more than 2 consecutive scenes with the same composition type.

══════════════════════════════════════════════════════
VISUAL COMPLEXITY SCORE
══════════════════════════════════════════════════════
  base = min(100, visual_beats * 7)
  bonus = demonstrations * 3 + transformations * 4 + diagrams_flows * 3 + data_visuals * 2
  penalty = typography_only_scenes * 8 + repeated_layouts * 6
  visual_first_score = min(100, max(0, base + bonus - penalty))
Storyboard FAILS if visual_first_score < 80.

══════════════════════════════════════════════════════
OUTPUT FORMAT — return ONLY this JSON, no fences
══════════════════════════════════════════════════════
{
  "episode_creative_concept": {
    "visual_premise": "<one line — the creative idea that makes this episode visually distinct>",
    "visual_world": "<the environment/atmosphere this concept lives in>",
    "progression_arc": "<how the visual narrative progresses across the episode>",
    "hero_moments": ["<2-4 specific moments that define the episode's visual identity>"],
    "emotional_tone": "<the feeling the visuals create>",
    "recent_treatments_avoided": ["<specific visual approaches from recent episodes deliberately not used>"],
    "generated_opportunities": ["<beats where GENERATED treatment would be strongest>"],
    "native_strengths": ["<beats where NATIVE treatment is clearly superior>"],
    "distinguishing_concept": "<one sentence: how this episode is visually different from recent approved episodes>"
  },
  "visual_thesis": {
    "core_concept": "<one line>",
    "primary_metaphor": "<one line>",
    "continuity_object": "<what it is and how it transforms>",
    "transformation_journey": "<start → intermediate → end>",
    "visual_grammar_used": ["<action types used>"],
    "visual_grammar_avoided": ["<action types deliberately not used>"],
    "muted_comprehension": {
      "at_10s": "<what the viewer understands>",
      "at_midpoint": "<what the viewer understands>",
      "at_takeaway": "<what the viewer understands>"
    }
  },
  "art_direction": {
    "id": "<registered visual world id, or NEW_WORLD_REQUIRED>",
    "visual_world": "<one line: the visual world>",
    "rationale": {
      "topic_semantics": "<why this world fits the subject>",
      "visual_thesis": "<how it supports the visual thesis>",
      "continuity_object": "<how the continuity object reads in this world>",
      "attention_pattern": "<emotional / attention pattern it creates>",
      "fingerprint_comparison": "<how it relates to recent episodes' worlds>"
    },
    "repeat_justification": "<required only if repeating the most recent world>"
  },
  "duration_decision": {
    "total_seconds": <float — must equal the storyboard total>,
    "rationale": {
      "content_complexity": "<why the idea needs this much time>",
      "narration_length": "<narration word count vs. duration>",
      "beat_density": "<beats per second / cadence>",
      "readability": "<why labels stay readable at this pace>"
    }
  },
  "novelty_assessment": {
    "similarity_scores": {"<episode_key>": "<LOW|LOW-MEDIUM|MEDIUM|HIGH>"},
    "explanation": "<why this plan is sufficiently different>"
  },
  "visual_fingerprint": {
    "visual_thesis": "<one line>",
    "continuity_object_type": "<description>",
    "dominant_motion_grammar": "<description>",
    "scene_layout_sequence": ["<layout per scene>"],
    "camera_choreography": ["<camera per scene>"],
    "comparison_structure": "<description>",
    "dominant_primitives": ["<list>"],
    "visual_world": "<description>"
  },
  "generated_opportunity_evaluation": [
    {
      "scene_id": <int>,
      "considered_treatment": "<NATIVE | GENERATED | TYPOGRAPHIC>",
      "chosen_treatment": "<NATIVE | GENERATED | TYPOGRAPHIC>",
      "reason": "<why this treatment wins for this beat>"
    }
  ],
  "native_justification": "<required ONLY if 100% NATIVE despite generated opportunities — explain why>",
  "storyboard": [<array of scene objects>],
  "total_duration_seconds": <float>,
  "visual_summary": "<one line: the visual journey>",
  "visual_complexity": {
    "visual_beats": <int>,
    "demonstrations": <int>,
    "transformations": <int>,
    "diagrams_flows": <int>,
    "data_visuals": <int>,
    "typography_only_scenes": <int>,
    "repeated_layouts": <int>,
    "visual_first_score": <int 0-100>
  }
}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _episode_dir(episode: int, week: int) -> Path:
    base = Path(os.getenv("OUTPUT_BASE_PATH", "./output"))
    path = base / f"week_{week:02d}" / f"ep{episode:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_json(raw: str) -> dict:
    """Strip accidental code fences then parse JSON."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    return json.loads(text)


def _count_beats(scenes: list) -> int:
    """Count total meaningful visual beats across all scenes."""
    total = 0
    for s in scenes:
        beats = s.get("beats", [])
        total += len(beats)
    return total


def _compute_visual_complexity(scenes: list) -> dict:
    """Compute the visual complexity score from the storyboard."""
    structural = {"HOOK", "TAKEAWAY", "CTA"}
    demo_types = DEMONSTRATION_TYPES
    transform_types = {"TRANSFORMATION"}
    flow_diagram_types = {"FLOW", "DIAGRAM", "SIMULATION"}
    data_types = {"DATA"}

    beats = _count_beats(scenes)
    demos = sum(1 for s in scenes if s.get("scene_type") in demo_types)
    transforms = sum(1 for s in scenes if s.get("scene_type") in transform_types)
    diag_flows = sum(1 for s in scenes if s.get("scene_type") in flow_diagram_types)
    data_visuals = sum(1 for s in scenes if s.get("scene_type") in data_types)
    typo_only = sum(
        1 for s in scenes
        if s.get("component") in TYPOGRAPHY_COMPONENTS
        and s.get("scene_type") not in structural
    )
    repeated = 0
    for i in range(len(scenes) - 2):
        if (scenes[i].get("component") == scenes[i + 1].get("component") ==
                scenes[i + 2].get("component")):
            repeated += 1

    base = min(100, beats * 7)
    bonus = demos * 3 + transforms * 4 + diag_flows * 3 + data_visuals * 2
    penalty = typo_only * 8 + repeated * 6
    score = min(100, max(0, base + bonus - penalty))

    return {
        "visual_beats": beats,
        "demonstrations": demos,
        "transformations": transforms,
        "diagrams_flows": diag_flows,
        "data_visuals": data_visuals,
        "typography_only_scenes": typo_only,
        "repeated_layouts": repeated,
        "visual_first_score": score,
    }


def _validate_storyboard(
    scenes: list, episode: int, voice_duration: float | None = None,
) -> list[str]:
    """
    Run the quality gate. Returns a list of violation strings.
    Empty list = storyboard passes.

    When voice_duration is locked, the generic duration range check is skipped
    because VOICE_DURATION_MISMATCH (±2s around voice) is the authoritative gate.
    """
    violations: list[str] = []

    if not scenes:
        return ["Storyboard is empty"]

    # ── Total duration ────────────────────────────────────────────────────────
    total = sum(s.get("duration_seconds", 0) for s in scenes)
    t_min, t_max = _target_min_seconds(), _target_max_seconds()
    if voice_duration is None and not (t_min <= total <= t_max):
        violations.append(
            f"Total duration {total:.1f}s outside {t_min}–{t_max}s"
        )

    # ── CTA must be last and ≤ channel max ───────────────────────────────────
    last = scenes[-1]
    cta_max = _max_cta_seconds()
    if last.get("component") != "CTAScene":
        violations.append("Last scene must be CTAScene")
    elif last.get("duration_seconds", 999) > cta_max:
        violations.append(
            f"CTA scene is {last['duration_seconds']}s — must be ≤{cta_max}s"
        )

    # ── Hook must be ≤ channel max ───────────────────────────────────────────
    first = scenes[0]
    hook_max = _max_hook_seconds()
    if first.get("scene_type") == "HOOK" and first.get("duration_seconds", 0) > hook_max:
        violations.append(
            f"HOOK scene is {first['duration_seconds']}s — must be ≤{hook_max}s"
        )

    # ── Schema completeness ───────────────────────────────────────────────────
    required_keys = {
        "scene_id", "duration_seconds", "narration", "scene_type",
        "visual_goal", "component", "objects", "animation", "on_screen_text",
        "transition", "beats",
    }
    for i, scene in enumerate(scenes):
        missing = required_keys - set(scene.keys())
        if missing:
            violations.append(f"Scene {i + 1} missing keys: {missing}")
        if scene.get("scene_type") not in VALID_SCENE_TYPES:
            violations.append(
                f"Scene {i + 1} invalid scene_type: '{scene.get('scene_type')}'"
            )
        if scene.get("component") not in VALID_COMPONENTS:
            violations.append(
                f"Scene {i + 1} invalid component: '{scene.get('component')}'"
            )
        narration = scene.get("narration", "")
        for label in scene.get("on_screen_text", []):
            if len(label.split()) > 8:
                violations.append(
                    f"Scene {i + 1} on_screen_text too long (>8 words): '{label}'"
                )
            if narration and label.lower() in narration.lower() and len(label.split()) > 5:
                violations.append(
                    f"Scene {i + 1} on_screen_text duplicates narration: '{label}'"
                )

        dur = scene.get("duration_seconds", 0)
        beats = scene.get("beats", [])
        n_beats = len(beats) if isinstance(beats, list) else 0
        if dur > 8.0 and n_beats < 3:
            violations.append(
                f"Scene {i + 1} is {dur}s with only {n_beats} beat(s) — need ≥3 for scenes >8s"
            )
        elif dur > 6.0 and n_beats < 2:
            violations.append(
                f"Scene {i + 1} is {dur}s with only {n_beats} beat(s) — need ≥2 for scenes >6s"
            )

    # ── Numeric integrity ────────────────────────────────────────────────────
    for i, scene in enumerate(scenes):
        comp = scene.get("component", "")
        if comp in NUMERIC_VIZ_COMPONENTS:
            src_type = scene.get("source_type", "")
            if src_type not in {"sourced_numeric", "illustrative"}:
                violations.append(
                    f"Scene {i + 1} ({comp}) missing 'source_type' — "
                    f"must be 'sourced_numeric' or 'illustrative'"
                )
            elif src_type == "sourced_numeric" and not scene.get("source_reference", "").strip():
                violations.append(
                    f"Scene {i + 1} ({comp}) has source_type='sourced_numeric' "
                    f"but 'source_reference' is empty"
                )

    # ── Total visual beat count ───────────────────────────────────────────────
    total_beats = _count_beats(scenes)
    if total_beats < MIN_VISUAL_BEATS:
        violations.append(
            f"Only {total_beats} visual beats total — need ≥{MIN_VISUAL_BEATS}"
        )

    # ── Typography runtime cap ────────────────────────────────────────────────
    structural = {"HOOK", "TAKEAWAY", "CTA"}
    typo_runtime = sum(
        s.get("duration_seconds", 0)
        for s in scenes
        if s.get("component") in TYPOGRAPHY_COMPONENTS
        and s.get("scene_type") not in structural
    )
    if total > 0 and (typo_runtime / total) > MAX_TYPOGRAPHY_RATIO:
        violations.append(
            f"Typography-only runtime {typo_runtime:.1f}s is "
            f"{typo_runtime / total:.0%} — exceeds {MAX_TYPOGRAPHY_RATIO:.0%} cap"
        )

    # ── Visual demonstration count ────────────────────────────────────────────
    explanatory = [s for s in scenes if s.get("scene_type") not in structural]
    demo_count = sum(1 for s in explanatory if s.get("scene_type") in DEMONSTRATION_TYPES)
    if demo_count < MIN_VISUAL_DEMONSTRATIONS:
        violations.append(
            f"Only {demo_count} visual demonstrations — need ≥{MIN_VISUAL_DEMONSTRATIONS}"
        )

    # ── Consecutive same composition ─────────────────────────────────────────
    for i in range(len(scenes) - MAX_CONSECUTIVE_SAME_LAYOUT):
        window_comps = [
            scenes[i + j].get("component")
            for j in range(MAX_CONSECUTIVE_SAME_LAYOUT + 1)
        ]
        if len(set(window_comps)) == 1 and window_comps[0] not in {"CTAScene", "TakeawayScene"}:
            violations.append(
                f"Scenes {i + 1}–{i + MAX_CONSECUTIVE_SAME_LAYOUT + 1}: "
                f"3 consecutive '{window_comps[0]}' — vary composition"
            )

    # ── Intra-episode repetition gate ──────────────────────────────────────────
    intra_result = _intra_episode_repetition_gate(scenes)
    if not intra_result["pass"]:
        for v in intra_result["violations"]:
            violations.append(v)

    # ── Visual-first score gate ───────────────────────────────────────────────
    complexity = _compute_visual_complexity(scenes)
    score = complexity["visual_first_score"]
    if score < MIN_VISUAL_FIRST_SCORE:
        violations.append(
            f"Visual-first score {score}/100 is below minimum {MIN_VISUAL_FIRST_SCORE}"
        )

    # ── v4: Claim type validation ─────────────────────────────────────────────
    for i, scene in enumerate(scenes):
        for j, beat in enumerate(scene.get("beats", [])):
            ct = beat.get("claim_type")
            if ct and ct not in CLAIM_TYPES:
                violations.append(
                    f"Scene {i + 1} beat {j + 1}: invalid claim_type '{ct}'"
                )

    return violations


def _validate_creative_concept(
    concept: object,
    fingerprints: dict,
    channel: str | None = None,
) -> list[str]:
    """Validate the Episode Creative Concept. Returns violation strings."""
    if not isinstance(concept, dict) or not concept:
        return [
            "CREATIVE_CONCEPT_MISSING: episode_creative_concept is required — "
            "define the creative identity before choosing components"
        ]
    violations: list[str] = []
    required_keys = (
        "visual_premise", "progression_arc", "hero_moments",
        "emotional_tone", "distinguishing_concept",
    )
    for key in required_keys:
        val = concept.get(key)
        if not val or (isinstance(val, str) and not val.strip()):
            violations.append(f"CREATIVE_CONCEPT_INCOMPLETE: {key} is empty")
        elif isinstance(val, list) and len(val) == 0:
            violations.append(f"CREATIVE_CONCEPT_INCOMPLETE: {key} is empty list")
    hero = concept.get("hero_moments", [])
    if isinstance(hero, list) and len(hero) < 2:
        violations.append(
            "CREATIVE_CONCEPT_INCOMPLETE: hero_moments needs at least 2 entries"
        )
    return violations


def _validate_generated_opportunities(
    scenes: list[dict],
    concept: dict | None,
    gen_eval: list | None,
) -> list[str]:
    """
    When 100% NATIVE despite multiple strong GENERATED opportunities,
    require explicit justification. Returns violation strings.
    """
    if not scenes:
        return []

    native_count = sum(1 for s in scenes if s.get("visual_mode") == "NATIVE")
    gen_count = sum(1 for s in scenes if s.get("visual_mode") == "GENERATED")
    total = native_count + gen_count

    if gen_count > 0 or total == 0:
        return []

    gen_affinity_types = {"METAPHOR", "SIMULATION", "ZOOM", "DEMONSTRATION"}
    affinity_scenes = [
        s for s in scenes
        if s.get("scene_type") in gen_affinity_types
        and s.get("scene_type") != "HOOK"
        and s.get("component") not in {"TakeawayScene", "CTAScene"}
    ]

    if len(affinity_scenes) < 2:
        return []

    gen_opps = []
    if isinstance(concept, dict):
        gen_opps = concept.get("generated_opportunities", [])

    if len(gen_opps) >= 2:
        native_just = None
        if isinstance(concept, dict):
            native_just = concept.get("native_justification")
        if isinstance(gen_eval, list):
            for entry in gen_eval:
                if isinstance(entry, dict) and entry.get("native_justification"):
                    native_just = entry["native_justification"]
                    break

        if not native_just:
            return [
                f"GENERATED_OPPORTUNITY_UNJUSTIFIED: episode has {len(gen_opps)} "
                f"identified GENERATED opportunities and {len(affinity_scenes)} "
                f"high-affinity scenes but selects 100% NATIVE — add "
                f"native_justification explaining why NATIVE is genuinely "
                f"the best choice for every beat"
            ]
    return []


def _validate_novelty(
    novelty_assessment: dict,
    threshold: str = "HIGH",
) -> list[str]:
    """
    Check if novelty assessment indicates excessive similarity.
    Returns violation strings if any episode is too similar.
    """
    violations: list[str] = []
    severity = {"LOW": 0, "LOW-MEDIUM": 1, "MEDIUM": 2, "HIGH": 3}
    threshold_val = severity.get(threshold, 3)

    scores = novelty_assessment.get("similarity_scores", {})
    for ep_key, rating in scores.items():
        if severity.get(rating, 0) >= threshold_val:
            violations.append(
                f"Novelty guard: similarity to {ep_key} is {rating} — "
                f"plan needs more visual differentiation"
            )
    return violations


def _validate_duration_decision(
    decision: object, scenes: list, canonical_voiceover: str = ""
) -> list[str]:
    """
    The planner must justify the chosen total duration (45–60s, no default).
    Returns violation strings; empty list = valid.
    """
    if not isinstance(decision, dict) or not decision:
        return [
            "DURATION_DECISION_MISSING: explain the chosen total duration "
            "(content complexity, narration length, beat density, readability)"
        ]

    violations: list[str] = []
    rationale = decision.get("rationale")
    if not isinstance(rationale, dict):
        violations.append(
            "DURATION_DECISION_INCOMPLETE: rationale missing — must cover "
            + ", ".join(DURATION_RATIONALE_KEYS)
        )
    else:
        missing = [k for k in DURATION_RATIONALE_KEYS if not str(rationale.get(k, "")).strip()]
        if missing:
            violations.append(f"DURATION_DECISION_INCOMPLETE: rationale missing {', '.join(missing)}")

    total = sum(s.get("duration_seconds", 0) for s in scenes)
    declared = 0.0
    try:
        declared = float(decision.get("total_seconds"))
        if abs(declared - total) > DURATION_SUM_TOLERANCE_S:
            violations.append(
                f"DURATION_DECISION_MISMATCH: declared {declared:.1f}s but storyboard totals {total:.1f}s"
            )
    except (TypeError, ValueError):
        violations.append("DURATION_DECISION_INCOMPLETE: total_seconds missing or not a number")

    words = (
        len(canonical_voiceover.split()) if canonical_voiceover.strip()
        else sum(len(str(s.get("narration", "")).split()) for s in scenes)
    )
    denom = declared if declared and declared > 0 else total
    max_wps, min_wps = _max_narration_wps(), _min_narration_wps()
    if words >= MIN_WORDS_FOR_PACING_CHECK and denom > 0:
        wps = words / denom
        if wps > max_wps:
            violations.append(
                f"DURATION_TOO_SHORT_FOR_NARRATION: {words} words in {denom:.1f}s "
                f"({wps:.2f} w/s > {max_wps}) — lengthen or tighten the script"
            )
        elif wps < min_wps:
            violations.append(
                f"DURATION_TOO_LONG_FOR_NARRATION: {words} words in {denom:.1f}s "
                f"({wps:.2f} w/s < {min_wps}) — shorten the storyboard"
            )
    return violations


def _print_storyboard_summary(
    scenes: list,
    episode: int,
    complexity: dict | None = None,
    visual_thesis: dict | None = None,
) -> None:
    """Print a human-readable storyboard table."""
    logger.info(f"\n{'─' * 100}")
    logger.info(f"  EP{episode:02d} STORYBOARD v4 — {len(scenes)} scenes")
    logger.info(f"{'─' * 100}")

    if visual_thesis:
        logger.info(f"  Visual Thesis: {visual_thesis.get('core_concept', 'N/A')}")
        logger.info(f"  Metaphor: {visual_thesis.get('primary_metaphor', 'N/A')}")
        logger.info(f"  Continuity: {visual_thesis.get('continuity_object', 'N/A')}")
        logger.info(f"{'─' * 100}")

    logger.info(
        f"  {'#':>2}  {'TIME':>7}  {'Type':<14}  {'Component':<24}  {'Beats':>5}  Visual action"
    )
    logger.info(f"{'─' * 100}")
    cumulative = 0.0
    for s in scenes:
        dur = s.get("duration_seconds", 0)
        end = cumulative + dur
        comp = s.get("component", "?")
        stype = s.get("scene_type", "?")
        anim = s.get("animation", "")[:40]
        n_beats = len(s.get("beats") or [])
        logger.info(
            f"  {s.get('scene_id', '?'):>2}  "
            f"{cumulative:>4.1f}–{end:>4.1f}s  "
            f"{stype:<14}  {comp:<24}  {n_beats:>5}  {anim}"
        )
        for b in (s.get("beats") or []):
            ct = b.get("claim_type", "")
            ct_label = f" [{ct}]" if ct else ""
            logger.info(
                f"      {b.get('start', 0):>4.1f}–{b.get('end', 0):>4.1f}s  "
                f"    ↳ {b.get('action', '')[:50]}{ct_label}"
            )
        cumulative = end
    logger.info(f"{'─' * 100}")
    logger.info(f"  Total: {cumulative:.1f}s")
    if complexity:
        logger.info(f"\n  Visual Complexity Score:")
        logger.info(f"    Visual beats      : {complexity.get('visual_beats', 0)}")
        logger.info(f"    Demonstrations    : {complexity.get('demonstrations', 0)}")
        logger.info(f"    Transformations   : {complexity.get('transformations', 0)}")
        logger.info(f"    Diagrams / flows  : {complexity.get('diagrams_flows', 0)}")
        logger.info(f"    Data visuals      : {complexity.get('data_visuals', 0)}")
        logger.info(f"    Typography-only   : {complexity.get('typography_only_scenes', 0)}")
        logger.info(f"    Repeated layouts  : {complexity.get('repeated_layouts', 0)}")
        logger.info(f"    ─────────────────────────────────")
        score = complexity.get('visual_first_score', 0)
        status = "✓ PASS" if score >= MIN_VISUAL_FIRST_SCORE else "✗ FAIL"
        logger.info(f"    Visual-first score: {score}/100  {status}")


def run(
    script: dict,
    episode: int,
    week: int,
    lang: str = "en",
    dry_run: bool = False,
    voice_duration: float | None = None,
) -> dict:
    """
    Generate a v4 visual storyboard (creative visual reasoning) from a script JSON.

    Args:
        script:         Script dict from script_agent
        episode:        Episode number
        week:           Week number
        lang:           Language code
        dry_run:        If True, logs storyboard summary without saving
        voice_duration: Measured Voice B duration in seconds. When provided,
                        scene durations must sum to this value (±2s) instead
                        of an LLM-estimated duration.

    Returns:
        {
          "success": True,
          "output_path": str,
          "storyboard": list,
          "total_duration": float,
          "visual_complexity": dict,
          "visual_thesis": dict,
          "visual_fingerprint": dict,
          "art_direction": dict,
          "novelty_assessment": dict,
          "violations": list[str],
          "skipped": bool
        }

    Raises:
        ArtDirectionError: no explicit, registered Art Director decision. A
            failure marker is written so the visual render cannot fall back.
    """
    lang = lang.lower()
    output_path = (
        _episode_dir(episode, week) / f"ep{episode:02d}_storyboard_{lang.upper()}.json"
    )

    # Art Director inputs: registered worlds + recent approved fingerprints
    try:
        registry = load_art_direction_registry()
    except ArtDirectionError as e:
        _record_art_direction_failure(episode, week, lang, [str(e)])
        raise
    fingerprints = _load_fingerprints()
    # An episode is never compared against its own previously approved fingerprint
    prior_fingerprints = {
        k: v for k, v in fingerprints.items() if k != _episode_key(episode, week)
    }

    # Cache check — skip Claude call if storyboard already on disk and passes
    if output_path.exists():
        try:
            cached = json.loads(output_path.read_text(encoding="utf-8"))
            scenes = cached.get("storyboard", [])
            violations = _validate_storyboard(scenes, episode, voice_duration)
            violations += _validate_art_direction(
                cached.get("art_direction"), registry, prior_fingerprints
            )
            violations += _validate_duration_decision(
                cached.get("duration_decision"), scenes, script.get("voiceover", "")
            )
            if not violations:
                complexity = cached.get(
                    "visual_complexity", _compute_visual_complexity(scenes)
                )
                logger.info(
                    f"EP{episode:02d} — storyboard already on disk "
                    f"({len(scenes)} scenes, score {complexity.get('visual_first_score', 0)}) "
                    f"— skipping Visual Director"
                )
                if dry_run:
                    _print_storyboard_summary(
                        scenes, episode, complexity,
                        cached.get("visual_thesis"),
                    )
                return {
                    "success": True,
                    "output_path": str(output_path),
                    "storyboard": scenes,
                    "total_duration": cached.get("total_duration_seconds", 0),
                    "visual_complexity": complexity,
                    "visual_thesis": cached.get("visual_thesis", {}),
                    "visual_fingerprint": cached.get("visual_fingerprint", {}),
                    "art_direction": cached.get("art_direction", {}),
                    "novelty_assessment": cached.get("novelty_assessment", {}),
                    "violations": [],
                    "skipped": True,
                }
            else:
                logger.warning(
                    f"EP{episode:02d} — cached storyboard failed quality gate: "
                    f"{violations[:3]} — regenerating"
                )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"EP{episode:02d} — could not read cached storyboard: {e}")

    # Recent fingerprints for the novelty guard + Art Director
    fingerprint_context = _format_fingerprints_for_prompt(prior_fingerprints)

    # Build user message from script — v4 includes fingerprint context
    user_msg = (
        f"Topic: {script.get('topic', '')}\n"
        f"Episode: {episode:02d}\n"
        f"Concept: {script.get('concept', '')}\n"
        f"Hook: {script.get('hook', '')}\n"
        f"Takeaway: {script.get('takeaway', '')}\n"
        f"Theme accent: {script.get('theme', {}).get('accent', '#a78bfa')}\n\n"
        f"Full voiceover:\n{script.get('voiceover', '')}\n\n"
    )

    if script.get("token_spec"):
        user_msg += f"Token spec: {json.dumps(script['token_spec'])}\n\n"
    if script.get("sketch_spec"):
        user_msg += f"Sketch spec: {json.dumps(script['sketch_spec'])}\n\n"
    if script.get("data_spec"):
        user_msg += f"Data spec: {json.dumps(script['data_spec'])}\n\n"

    user_msg += (
        f"══════════════════════════════════════════════════════\n"
        f"RECENT EPISODE FINGERPRINTS (for novelty guard)\n"
        f"══════════════════════════════════════════════════════\n"
        f"{fingerprint_context}\n\n"
        f"══════════════════════════════════════════════════════\n"
        f"ART DIRECTOR — REGISTERED VISUAL WORLDS\n"
        f"══════════════════════════════════════════════════════\n"
        f"{_format_art_direction_menu(registry)}\n\n"
        f"══════════════════════════════════════════════════════\n"
        f"INSTRUCTIONS\n"
        f"══════════════════════════════════════════════════════\n"
        f"Follow the v4.3 Creative Visual Reasoning pipeline:\n"
        f"1. First think: what visual story makes this concept understandable muted?\n"
        f"2. Define your Visual Thesis before choosing any components\n"
        f"3. EPISODE CREATIVE CONCEPT: define the episode's creative identity — "
        f"visual premise, visual world, progression arc, hero moments, emotional tone, "
        f"recent treatments to avoid, GENERATED opportunities, NATIVE strengths, and "
        f"a distinguishing_concept sentence. This must be DIFFERENT from recent episodes.\n"
        f"4. Classify every claim as FACTUAL_EXACT / ILLUSTRATIVE / VISUAL_METAPHOR\n"
        f"5. Decompose into conceptual beats with physical visual actions\n"
        f"6. Define continuity object and its transformation journey\n"
        f"7. Art Director: explicitly select art_direction from the registered worlds, "
        f"justified by topic semantics, visual thesis, continuity object, attention "
        f"pattern and recent fingerprints (no default world)\n"
        f"8. GENERATED OPPORTUNITY EVALUATION: for each beat, evaluate whether NATIVE, "
        f"GENERATED, or TYPOGRAPHIC is the strongest treatment. Consider semantic "
        f"clarity, cinematic potential, explanatory precision, novelty, visual impact, "
        f"and generation cost. Do NOT default to NATIVE because a component exists. "
        f"Report per-scene in generated_opportunity_evaluation.\n"
        f"9. Modality Intent: for each beat, decide what it SEMANTICALLY NEEDS\n"
        f"10. Diversity Context: compare against recent episode fingerprints\n"
        f"11. Visual Mode: decide NATIVE or GENERATED per beat\n"
        f"12. ONLY THEN map to implementation components\n"
        f"13. Include claim_type in each beat and treatment_evaluation per scene\n"
        f"14. Compute visual_complexity score\n"
        f"15. If 100% NATIVE despite GENERATED opportunities, include native_justification\n\n"
        f"Constraints:\n"
        + (
            f"- LOCKED VOICE DURATION: {voice_duration:.1f}s. Scene durations MUST sum "
            f"to within ±5s of {voice_duration:.1f}s. Target exactly {voice_duration:.1f}s. "
            f"This is the measured Voice B duration — do not estimate or override. "
            f"Report it in duration_decision.\n"
            f"  DURATION BUDGET: HOOK ~3s + CTA ~3s = 6s fixed. "
            f"Remaining {voice_duration - 6.0:.1f}s for DEMONSTRATION scenes. "
            f"With 7 DEMONSTRATION scenes = ~{(voice_duration - 6.0) / 7:.1f}s each. "
            f"With 8 = ~{(voice_duration - 6.0) / 8:.1f}s each. "
            f"VERIFY: add up all scene durations before outputting.\n"
            if voice_duration is not None
            else
            f"- Total duration: choose within 45–60 seconds from content complexity, "
            f"narration length, beat density and readability (no default length); "
            f"report it in duration_decision\n"
        ) +
        f"- CTA ≤ 3 seconds, HOOK ≤ 4 seconds\n"
        f"- Every scene > 4s needs ≥2 beats, > 6s needs ≥3 beats\n"
        f"- visual_first_score must be ≥80\n"
        f"- Every numeric viz scene must include source_type\n"
        f"- Return the COMPLETE JSON output including episode_creative_concept, "
        f"visual_thesis, art_direction, duration_decision, novelty_assessment, "
        f"generated_opportunity_evaluation, visual_fingerprint, storyboard, "
        f"and visual_complexity\n\n"
        f"CRITICAL: Your ENTIRE response must be a single valid JSON object. "
        f"No markdown, no explanation, no code fences. Start with {{ and end with }}.\n"
    )

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    last_error: Exception | None = None
    violations: list[str] = []
    diversity_replan_done = False
    retry_counts: dict[str, int] = {
        "EMPTY_RESPONSE": 0,
        "JSON_PARSE": 0,
        "SCHEMA": 0,
        "DURATION": 0,
        "CONTENT_GATE": 0,
        "DIVERSITY": 0,
        "RATE_LIMIT": 0,
        "API_ERROR": 0,
    }

    for attempt in range(1, 4):
        try:
            logger.info(
                f"EP{episode:02d} — Visual Director v4 Claude call (attempt {attempt}/3)"
            )

            ch_cfg = load_channel(get_default_channel())
            sys_prompt = _SYSTEM_PROMPT.replace(
                '"Srini on AI"',
                f'"{ch_cfg.name}"',
            )
            if ch_cfg.domain.visual_guidance.strip():
                sys_prompt += (
                    "\n\n══════════════════════════════════════════════════════\n"
                    "DOMAIN VISUAL GUIDANCE\n"
                    "══════════════════════════════════════════════════════\n"
                    + ch_cfg.domain.visual_guidance.strip()
                )
            response = client.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=sys_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )

            raw = response.content[0].text if response.content else ""

            logger.info(
                f"EP{episode:02d} — response: {len(raw)} chars, "
                f"stop_reason={response.stop_reason}"
            )

            if not raw.strip() or len(raw.strip()) < 10:
                retry_counts["EMPTY_RESPONSE"] += 1
                raise ValueError(
                    f"EMPTY_RESPONSE: Claude returned {len(raw)} chars "
                    f"(stop_reason={response.stop_reason})"
                )

            data = _parse_json(raw)

            scenes = data.get("storyboard")
            if not isinstance(scenes, list) or not scenes:
                raise ValueError("Response missing 'storyboard' array")

            # Extract v4 planning outputs
            visual_thesis = data.get("visual_thesis", {})
            novelty_assessment = data.get("novelty_assessment", {})
            visual_fingerprint = data.get("visual_fingerprint", {})
            art_direction = data.get("art_direction")
            episode_creative_concept = data.get("episode_creative_concept")
            generated_opportunity_evaluation = data.get("generated_opportunity_evaluation")

            # Auto-repair common model omissions before validation
            for sc in scenes:
                comp = sc.get("component", "")
                sid = sc.get("scene_id", "?")
                # Missing source_type on numeric viz components
                if comp in NUMERIC_VIZ_COMPONENTS:
                    if sc.get("source_type", "") not in {"sourced_numeric", "illustrative"}:
                        sc["source_type"] = "illustrative"
                        logger.info(f"EP{episode:02d} — auto-repaired source_type on {comp} (s{sid})")
                # BeforeAfterScene needs ≥4 on_screen_text entries
                if comp == "BeforeAfterScene":
                    ost = sc.get("on_screen_text", [])
                    while len(ost) < 4:
                        ost.append("—")
                    sc["on_screen_text"] = ost
                    if len(ost) > len(sc.get("on_screen_text", [])):
                        logger.info(f"EP{episode:02d} — auto-repaired on_screen_text on {comp} (s{sid})")
                # TransformScene needs ≥3 on_screen_text entries
                if comp == "TransformScene":
                    ost = sc.get("on_screen_text", [])
                    while len(ost) < 3:
                        ost.append("—")
                    sc["on_screen_text"] = ost
                # TakeawayScene narration should be empty (takeaway is on-screen, not spoken)
                if comp == "TakeawayScene" and sc.get("narration", "").strip():
                    takeaway = script.get("takeaway", "")
                    nar = sc.get("narration", "").strip()
                    if nar and nar not in script.get("voiceover", ""):
                        sc["narration"] = ""
                        logger.info(f"EP{episode:02d} — cleared non-voiceover narration from {comp} (s{sid})")

            # Validate storyboard
            violations = _validate_storyboard(scenes, episode, voice_duration)

            # Validate the Art Director decision — no default world, ever
            ad_violations = _validate_art_direction(
                art_direction, registry, prior_fingerprints
            )
            if any(v.startswith("ART_DIRECTION_NEW_WORLD_REQUIRED") for v in ad_violations):
                _record_art_direction_failure(episode, week, lang, ad_violations)
                raise ArtDirectionError(
                    f"EP{episode:02d} planning stopped: {ad_violations[0]} — "
                    f"add a manifest to remotion/src/themes.ts and re-plan"
                )
            violations.extend(ad_violations)

            # Validate the duration decision
            duration_decision = data.get("duration_decision")
            if voice_duration is not None:
                scene_sum = sum(s.get("duration_seconds", 0) for s in scenes)
                if abs(scene_sum - voice_duration) > 5.0:
                    violations.append(
                        f"VOICE_DURATION_MISMATCH: scenes total {scene_sum:.1f}s "
                        f"but locked voice is {voice_duration:.1f}s (±5s tolerance)"
                    )
            else:
                violations.extend(_validate_duration_decision(
                    duration_decision, scenes, script.get("voiceover", "")
                ))

            # Validate novelty
            novelty_violations = _validate_novelty(novelty_assessment)
            if novelty_violations:
                violations.extend(novelty_violations)

            # Validate episode creative concept
            concept_violations = _validate_creative_concept(
                episode_creative_concept, prior_fingerprints
            )
            violations.extend(concept_violations)

            # Validate generated opportunity justification
            native_justification = data.get("native_justification")
            if isinstance(episode_creative_concept, dict) and native_justification:
                episode_creative_concept["native_justification"] = native_justification
            gen_opp_violations = _validate_generated_opportunities(
                scenes, episode_creative_concept,
                generated_opportunity_evaluation,
            )
            violations.extend(gen_opp_violations)

            # ── Diversity gate (v4.2) — component-family similarity ──────────
            # Runs BEFORE paid asset generation. ONE bounded re-plan on failure,
            # not an endless retry loop.
            diversity_result = _diversity_gate(data, prior_fingerprints)
            if not diversity_result["pass"]:
                if not diversity_replan_done:
                    diversity_replan_done = True
                    retry_counts["DIVERSITY"] += 1
                    violations.append(
                        f"DIVERSITY_GATE_FAIL: {diversity_result['reason']}"
                    )
                    logger.warning(
                        f"EP{episode:02d} — diversity gate FAILED: "
                        f"{diversity_result['reason']} — triggering ONE re-plan"
                    )
                else:
                    logger.info(
                        f"EP{episode:02d} — diversity gate still shows similarity "
                        f"after re-plan, but second re-plan suppressed (bounded)"
                    )

            if violations:
                for v in violations:
                    if "VOICE_DURATION_MISMATCH" in v or "DURATION" in v:
                        retry_counts["DURATION"] += 1
                    elif "DIVERSITY_GATE" in v:
                        pass  # already counted above
                    elif "ART_DIRECTION" in v or "NOVELTY" in v:
                        retry_counts["CONTENT_GATE"] += 1
                    else:
                        retry_counts["SCHEMA"] += 1

                logger.warning(
                    f"EP{episode:02d} — v4 quality gate failed (attempt {attempt}): "
                    f"{'; '.join(violations[:4])}"
                )
                if attempt < 3:
                    fix_hints = ""
                    if voice_duration is not None and any("VOICE_DURATION_MISMATCH" in v for v in violations):
                        scene_sum = sum(s.get("duration_seconds", 0) for s in scenes)
                        delta = voice_duration - scene_sum
                        fix_hints += (
                            f"\n\nDURATION FIX: Your scenes total {scene_sum:.1f}s but the "
                            f"locked voice is {voice_duration:.1f}s. You need to "
                            f"{'ADD' if delta > 0 else 'REMOVE'} ~{abs(delta):.1f}s. "
                            f"Distribute this across DEMONSTRATION scenes (not HOOK/CTA). "
                            f"Target each DEMONSTRATION scene at 6-8s."
                        )
                    if any("DIVERSITY_GATE_FAIL" in v for v in violations):
                        recent_key = diversity_result.get("recent_key", "?")
                        cur_fam = diversity_result.get("current_families", [])
                        rec_fam = diversity_result.get("recent_families", [])
                        fix_hints += (
                            f"\n\nDIVERSITY FIX: Your component-family sequence "
                            f"{' -> '.join(cur_fam)} is too similar to {recent_key}'s "
                            f"{' -> '.join(rec_fam)}. Change your visual approach: "
                            f"use different families (e.g. GENERATED_EDITORIAL for "
                            f"editorial metaphors via AssetScene, or families like "
                            f"SEQUENCE/DATA/COMPARISON that the recent episode did not "
                            f"use). Do NOT just rename components within the same family. "
                            f"The viewer watches these episodes consecutively — visual "
                            f"novelty matters."
                        )
                    intra_violations = [v for v in violations if v.startswith(("INTRA_REPEAT:", "ABA_PATTERN:", "FAMILY_CONCENTRATION:"))]
                    if intra_violations:
                        fix_hints += (
                            f"\n\nINTRA-EPISODE REPETITION FIX: Your storyboard has "
                            f"visual repetition WITHIN the episode:\n"
                            + "\n".join(f"- {v}" for v in intra_violations)
                            + "\n\nDifferent TEXT alone does NOT make a scene novel. "
                            f"Zoom/pan/color changes alone do NOT make a repeated "
                            f"composition novel. You MUST use genuinely different "
                            f"visual treatments: different component families, different "
                            f"animation structures, different semantic metaphors. "
                            f"Consider using GENERATED/editorial treatment (AssetScene) "
                            f"for conceptual/metaphorical scenes instead of repeating "
                            f"the same domain-specific component."
                        )
                    user_msg_retry = (
                        user_msg
                        + f"\n\nYour previous storyboard FAILED the quality gate:\n"
                        + "\n".join(f"- {v}" for v in violations)
                        + fix_hints
                        + "\n\nFix these issues. Keep the v4 creative reasoning pipeline."
                    )
                    user_msg = user_msg_retry
                    time.sleep(2 ** attempt)
                    continue
                remaining_ad = [v for v in violations if _is_art_direction_violation(v)]
                if remaining_ad:
                    _record_art_direction_failure(episode, week, lang, remaining_ad)
                    raise ArtDirectionError(
                        f"EP{episode:02d} planning failed: no valid Art Director decision "
                        f"after 3 attempts: {'; '.join(remaining_ad)}"
                    )
                logger.error(
                    f"EP{episode:02d} — storyboard failed quality gate after 3 attempts "
                    f"(retry_counts={retry_counts}): {'; '.join(violations)}"
                )
                raise RuntimeError(
                    f"EP{episode:02d} visual_director_agent quality gate failed "
                    f"after 3 attempts: {'; '.join(violations[:3])}"
                )

            # Normalise scene IDs
            for i, scene in enumerate(scenes):
                scene["scene_id"] = i + 1

            # Use model-reported complexity or recompute
            complexity = data.get("visual_complexity") or _compute_visual_complexity(scenes)

            result_data = {
                "topic": script.get("topic", ""),
                "episode_creative_concept": episode_creative_concept,
                "art_direction": art_direction,
                "duration_decision": duration_decision,
                "visual_thesis": visual_thesis,
                "novelty_assessment": novelty_assessment,
                "generated_opportunity_evaluation": generated_opportunity_evaluation,
                "visual_fingerprint": visual_fingerprint,
                "diversity_gate": diversity_result,
                "storyboard": scenes,
                "total_duration_seconds": data.get(
                    "total_duration_seconds",
                    round(sum(s.get("duration_seconds", 0) for s in scenes), 2),
                ),
                "visual_summary": data.get("visual_summary", ""),
                "visual_complexity": complexity,
                "violations": violations,
            }

            _clear_art_direction_failure(episode, week, lang)

            if not dry_run:
                output_path.write_text(
                    json.dumps(result_data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                logger.info(
                    f"EP{episode:02d} — v4 storyboard saved ({len(scenes)} scenes, "
                    f"score {complexity.get('visual_first_score', 0)}) -> {output_path}"
                )

            if dry_run:
                _print_storyboard_summary(scenes, episode, complexity, visual_thesis)

            return {
                "success": True,
                "output_path": str(output_path),
                "storyboard": scenes,
                "total_duration": result_data["total_duration_seconds"],
                "visual_complexity": complexity,
                "visual_thesis": visual_thesis,
                "visual_fingerprint": visual_fingerprint,
                "art_direction": art_direction,
                "episode_creative_concept": episode_creative_concept,
                "generated_opportunity_evaluation": generated_opportunity_evaluation,
                "novelty_assessment": novelty_assessment,
                "diversity_gate": diversity_result,
                "violations": violations,
                "retry_counts": retry_counts,
                "skipped": False,
            }

        except ArtDirectionError:
            raise

        except json.JSONDecodeError as e:
            retry_counts["JSON_PARSE"] += 1
            last_error = e
            logger.warning(
                f"EP{episode:02d} — Visual Director attempt {attempt} "
                f"JSON_PARSE: {e} (retry_counts={retry_counts})"
            )
            if attempt < 3:
                time.sleep(2 ** attempt)

        except ValueError as e:
            category = "EMPTY_RESPONSE" if "EMPTY_RESPONSE" in str(e) else "SCHEMA"
            if category != "EMPTY_RESPONSE":
                retry_counts[category] += 1
            last_error = e
            logger.warning(
                f"EP{episode:02d} — Visual Director attempt {attempt} "
                f"{category}: {e} (retry_counts={retry_counts})"
            )
            if attempt < 3:
                time.sleep(2 ** attempt)

        except anthropic.AuthenticationError as e:
            raise RuntimeError(
                f"EP{episode:02d} Claude auth failed — check ANTHROPIC_API_KEY"
            ) from e

        except anthropic.RateLimitError as e:
            retry_counts["RATE_LIMIT"] += 1
            last_error = e
            logger.warning(
                f"EP{episode:02d} — Visual Director attempt {attempt} "
                f"RATE_LIMIT (retry_counts={retry_counts})"
            )
            if attempt < 3:
                time.sleep(60)

        except Exception as e:
            retry_counts["API_ERROR"] += 1
            last_error = e
            logger.error(
                f"EP{episode:02d} — Visual Director attempt {attempt} "
                f"API_ERROR: {e} (retry_counts={retry_counts})"
            )
            if attempt < 3:
                time.sleep(2 ** attempt)

    raise RuntimeError(
        f"EP{episode:02d} visual_director_agent failed after 3 attempts "
        f"(retry_counts={retry_counts}): {last_error}"
    )


# ── Approval: persist the art-direction fingerprint ─────────────────────────

def approve_episode(
    episode: int,
    week: int,
    lang: str = "en",
    source: Path | None = None,
    approved_by: str = "human",
) -> dict:
    """
    Persist the approved episode's visual + art-direction fingerprint to
    visual_fingerprints.json so future plans can avoid unintended repetition.

    Call only after a human has approved the episode visuals.

    Args:
        source: storyboard doc (default ep{NN}_storyboard_{LANG}.json) or a
                render-props JSON whose art_direction is a manifest id.

    Raises:
        ArtDirectionError: the approved episode has no registered art direction.
    """
    try:
        lang = lang.lower()
        path = Path(source) if source else (
            _episode_dir(episode, week) / f"ep{episode:02d}_storyboard_{lang.upper()}.json"
        )
        doc = json.loads(path.read_text(encoding="utf-8"))
        scenes = doc.get("storyboard") or []
        if not scenes:
            raise ValueError(f"{path.name} has no storyboard to fingerprint")

        registry = load_art_direction_registry()
        raw_ad = doc.get("art_direction")
        ad: dict = dict(raw_ad) if isinstance(raw_ad, dict) else (
            {"id": raw_ad} if isinstance(raw_ad, str) else {}
        )
        ad_id = str(ad.get("id", "")).strip()
        if ad_id not in registry:
            raise ArtDirectionError(
                f"EP{episode:02d} cannot be approved: art_direction "
                f"'{ad_id or 'MISSING'}' is not a registered visual world"
            )
        meta = registry[ad_id]
        ad.setdefault("visual_world", meta["visual_world"])
        ad["name"] = meta["name"]
        ad["light_or_dark"] = meta["light_or_dark"]

        fingerprint = dict(doc.get("visual_fingerprint") or {})
        comp_seq = [s.get("component", "") for s in scenes]
        native_count = sum(1 for s in scenes if s.get("visual_mode") == "NATIVE")
        gen_count = sum(1 for s in scenes if s.get("visual_mode") == "GENERATED")
        fingerprint.update({
            "topic": doc.get("topic", fingerprint.get("topic", "")),
            "art_direction": ad,
            "component_sequence": comp_seq,
            "component_families": classify_component_families(comp_seq),
            "scene_type_sequence": [s.get("scene_type", "") for s in scenes],
            "scene_count": len(scenes),
            "duration_seconds": round(sum(s.get("duration_seconds", 0) for s in scenes), 2),
            "mode_ratio": {"native": native_count, "generated": gen_count},
            "channel": _channel_fingerprint_key(),
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": approved_by,
            "source": path.name,
        })
        fingerprint.setdefault("visual_world", ad["visual_world"])

        key = _episode_key(episode, week)
        _save_fingerprint(key, fingerprint)
        logger.info(f"EP{episode:02d} — approved; art direction '{ad_id}' fingerprinted as {key}")
        return {"success": True, "output_path": str(FINGERPRINT_PATH), "episode_key": key}
    except Exception as e:
        logger.error(f"EP{episode:02d} — approval fingerprint failed: {e}")
        raise
