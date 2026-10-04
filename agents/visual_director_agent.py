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

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

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
}

# ── Quality gate thresholds (unchanged from v3.2) ───────────────────────────

MIN_VISUAL_BEATS = 8
MAX_TYPOGRAPHY_RATIO = 0.25
MAX_CONSECUTIVE_SAME_LAYOUT = 2
MIN_VISUAL_DEMONSTRATIONS = 3
MIN_VISUAL_FIRST_SCORE = 80
TARGET_MIN_SECONDS = 45.0
TARGET_MAX_SECONDS = 60.0
MAX_HOOK_SECONDS = 4.0
MAX_CTA_SECONDS = 3.0
MAX_SCENE_SECONDS_WITHOUT_BEATS = 6.0

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


def _format_fingerprints_for_prompt(fingerprints: dict) -> str:
    """Format recent fingerprints as context for the novelty guard."""
    if not fingerprints:
        return "No previous episode fingerprints available."
    lines = ["Recent episode visual fingerprints (compare your plan against these):"]
    for key, fp in fingerprints.items():
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
            lines.append(f"  Component sequence: {' → '.join(comps)}")
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
  2. Claim Classification — classify every concept/claim as FACTUAL_EXACT, ILLUSTRATIVE, or VISUAL_METAPHOR
  3. Conceptual Beat Decomposition — intellectual beats, not just narration sentences
  4. Physical Visual Actions — use meaningful action verbs (split, merge, transform, etc.)
  5. Continuity Object — carry one object through scenes as chapters of one journey
  6. Visual Grammar — what to use, what to deliberately avoid
  7. Art Director — explicitly select the episode's visual world (see ART DIRECTOR)
  8. Novelty Guard — compare against recent episode fingerprints, alter if too similar
  9. Scene Plan — duration, pacing, structure
  10. Component Mapping — ONLY NOW choose implementation components
  11. Renderability — can current components render each beat?

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
TARGET STRUCTURE (45–60 seconds total)
══════════════════════════════════════════════════════
0–3s      HOOK         — Visually surprise immediately
3–8s      DEMONSTRATION — Show the phenomenon BEFORE explaining
8–40s     EXPLANATION   — Multiple beats: diagrams, transformations, comparisons
40–50s    WHY IT MATTERS — Concrete real-world usage beats
50–55s    TAKEAWAY      — Compress the lesson into one visual moment
55–58s    CTA           — Always ≤3 seconds

══════════════════════════════════════════════════════
SCENE SCHEMA
══════════════════════════════════════════════════════
Each scene must be a JSON object with EXACTLY these keys:
{
  "scene_id": <integer, 1-based>,
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


def _validate_storyboard(scenes: list, episode: int) -> list[str]:
    """
    Run the quality gate. Returns a list of violation strings.
    Empty list = storyboard passes.
    """
    violations: list[str] = []

    if not scenes:
        return ["Storyboard is empty"]

    # ── Total duration ────────────────────────────────────────────────────────
    total = sum(s.get("duration_seconds", 0) for s in scenes)
    if not (TARGET_MIN_SECONDS <= total <= TARGET_MAX_SECONDS):
        violations.append(
            f"Total duration {total:.1f}s outside {TARGET_MIN_SECONDS}–{TARGET_MAX_SECONDS}s"
        )

    # ── CTA must be last and ≤ MAX_CTA_SECONDS ───────────────────────────────
    last = scenes[-1]
    if last.get("component") != "CTAScene":
        violations.append("Last scene must be CTAScene")
    elif last.get("duration_seconds", 999) > MAX_CTA_SECONDS:
        violations.append(
            f"CTA scene is {last['duration_seconds']}s — must be ≤{MAX_CTA_SECONDS}s"
        )

    # ── Hook must be ≤ MAX_HOOK_SECONDS ──────────────────────────────────────
    first = scenes[0]
    if first.get("scene_type") == "HOOK" and first.get("duration_seconds", 0) > MAX_HOOK_SECONDS:
        violations.append(
            f"HOOK scene is {first['duration_seconds']}s — must be ≤{MAX_HOOK_SECONDS}s"
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
) -> dict:
    """
    Generate a v4 visual storyboard (creative visual reasoning) from a script JSON.

    Args:
        script:   Script dict from script_agent
        episode:  Episode number
        week:     Week number
        lang:     Language code
        dry_run:  If True, logs storyboard summary without saving

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
            violations = _validate_storyboard(scenes, episode)
            violations += _validate_art_direction(
                cached.get("art_direction"), registry, prior_fingerprints
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
        f"Follow the v4 Creative Visual Reasoning pipeline:\n"
        f"1. First think: what visual story makes this concept understandable muted?\n"
        f"2. Define your Visual Thesis before choosing any components\n"
        f"3. Classify every claim as FACTUAL_EXACT / ILLUSTRATIVE / VISUAL_METAPHOR\n"
        f"4. Decompose into conceptual beats with physical visual actions\n"
        f"5. Define continuity object and its transformation journey\n"
        f"6. Art Director: explicitly select art_direction from the registered worlds, "
        f"justified by topic semantics, visual thesis, continuity object, attention "
        f"pattern and recent fingerprints (no default world)\n"
        f"7. Check novelty against the fingerprints above — alter if too similar\n"
        f"8. ONLY THEN map to implementation components\n"
        f"9. Include claim_type in each beat\n"
        f"10. Compute visual_complexity score\n\n"
        f"Constraints:\n"
        f"- Total duration: 45–60 seconds\n"
        f"- CTA ≤ 3 seconds, HOOK ≤ 4 seconds\n"
        f"- Every scene > 4s needs ≥2 beats, > 6s needs ≥3 beats\n"
        f"- visual_first_score must be ≥80\n"
        f"- Every numeric viz scene must include source_type\n"
        f"- Return the COMPLETE JSON output including visual_thesis, art_direction, "
        f"novelty_assessment, visual_fingerprint, storyboard, and visual_complexity\n"
    )

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    last_error: Exception | None = None
    violations: list[str] = []

    for attempt in range(1, 4):
        try:
            logger.info(
                f"EP{episode:02d} — Visual Director v4 Claude call (attempt {attempt}/3)"
            )

            response = client.messages.create(
                model=MODEL,
                max_tokens=6000,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )

            raw = response.content[0].text
            data = _parse_json(raw)

            scenes = data.get("storyboard")
            if not isinstance(scenes, list) or not scenes:
                raise ValueError("Response missing 'storyboard' array")

            # Extract v4 planning outputs
            visual_thesis = data.get("visual_thesis", {})
            novelty_assessment = data.get("novelty_assessment", {})
            visual_fingerprint = data.get("visual_fingerprint", {})
            art_direction = data.get("art_direction")

            # Validate storyboard
            violations = _validate_storyboard(scenes, episode)

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

            # Validate novelty
            novelty_violations = _validate_novelty(novelty_assessment)
            if novelty_violations:
                violations.extend(novelty_violations)

            if violations:
                logger.warning(
                    f"EP{episode:02d} — v4 quality gate failed (attempt {attempt}): "
                    f"{'; '.join(violations[:4])}"
                )
                if attempt < 3:
                    user_msg_retry = (
                        user_msg
                        + f"\n\nYour previous storyboard FAILED the quality gate:\n"
                        + "\n".join(f"- {v}" for v in violations)
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
                    f"EP{episode:02d} — storyboard still has violations after 3 attempts; "
                    f"proceeding with warnings"
                )

            # Normalise scene IDs
            for i, scene in enumerate(scenes):
                scene["scene_id"] = i + 1

            # Use model-reported complexity or recompute
            complexity = data.get("visual_complexity") or _compute_visual_complexity(scenes)

            result_data = {
                "topic": script.get("topic", ""),
                "art_direction": art_direction,
                "visual_thesis": visual_thesis,
                "novelty_assessment": novelty_assessment,
                "visual_fingerprint": visual_fingerprint,
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
                "novelty_assessment": novelty_assessment,
                "violations": violations,
                "skipped": False,
            }

        except ArtDirectionError:
            raise

        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning(
                f"EP{episode:02d} — Visual Director v4 attempt {attempt} bad output: {e}"
            )
            if attempt < 3:
                time.sleep(2 ** attempt)

        except anthropic.AuthenticationError as e:
            raise RuntimeError(
                f"EP{episode:02d} Claude auth failed — check ANTHROPIC_API_KEY"
            ) from e

        except anthropic.RateLimitError as e:
            last_error = e
            logger.warning(f"EP{episode:02d} — Visual Director rate limited")
            if attempt < 3:
                time.sleep(60)

        except Exception as e:
            last_error = e
            logger.error(
                f"EP{episode:02d} — Visual Director v4 attempt {attempt} error: {e}"
            )
            if attempt < 3:
                time.sleep(2 ** attempt)

    raise RuntimeError(
        f"EP{episode:02d} visual_director_agent failed after 3 attempts: {last_error}"
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
        fingerprint.update({
            "topic": doc.get("topic", fingerprint.get("topic", "")),
            "art_direction": ad,
            "component_sequence": [s.get("component", "") for s in scenes],
            "scene_type_sequence": [s.get("scene_type", "") for s in scenes],
            "scene_count": len(scenes),
            "duration_seconds": round(sum(s.get("duration_seconds", 0) for s in scenes), 2),
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
