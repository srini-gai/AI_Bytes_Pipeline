"""
Visual Director Agent — Phase 2.5 / v3.2 Motion Storytelling
Reads a script JSON and produces a storyboard JSON array.

v3 changes (Motion Storytelling Upgrade):
  - Each scene contains timed "beats" (meaningful visual events every 2–4s)
  - Visual complexity score (beats, demos, transformations, score/100)
  - Stricter quality gate (≥8 beats, hook ≤4s, CTA ≤3s, ≥80 visual score)
  - 14 new motion-first scene primitives
  - Camera choreography per beat
  - Continuity field: carry_object_from
  - Typography runtime cap at 25%
  - Tighter Short structure (0–3 hook, 3–8 demo, 8–40 explain, 40–50 why, 50–55 takeaway, 55–58 CTA)

v3.2 global-default promotion (from RAG reference episode, commit 45d1e20):
  - Target duration lowered to 45–60 s (was 55–62 s) — approved range from known-good baseline
  - CTA capped at exactly 3 s (was ≤4 s)
  - Numeric integrity rule: sourced_numeric vs illustrative distinction enforced in quality gate
  - Scene diversity rule: Visual Director must not copy RAG scene ordering or component selection
  - Full rules in skills/VISUAL_DIRECTOR.md

Pipeline position:  script_agent → visual_director_agent → visual_agent
Output file:        ep{NN}_storyboard_{LANG}.json
"""
import json
import logging
import os
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

# ── Scene registry ────────────────────────────────────────────────────────────

VALID_SCENE_TYPES = {
    "HOOK", "DEMONSTRATION", "TRANSFORMATION", "FLOW",
    "COMPARISON", "DIAGRAM", "DATA", "ZOOM",
    "SIMULATION", "METAPHOR", "TAKEAWAY", "CTA",
}

# Original components + v3 motion-first primitives
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
    # v3 motion-first primitives
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

# ── Quality gate thresholds (v3.2 global defaults) ───────────────────────────
# Promoted from RAG reference episode (commit 45d1e20, tag v3.2-known-good).
# These values apply to all future Shorts regardless of topic.
# See skills/VISUAL_DIRECTOR.md for rationale and full rules.

MIN_VISUAL_BEATS = 8
MAX_TYPOGRAPHY_RATIO = 0.25          # ≤25% of total runtime as typography
MAX_CONSECUTIVE_SAME_LAYOUT = 2      # no 3 in a row same composition
MIN_VISUAL_DEMONSTRATIONS = 3
MIN_VISUAL_FIRST_SCORE = 80          # 0–100 composite score
TARGET_MIN_SECONDS = 45.0            # approved range floor (was 55.0; RAG ran 51.5s)
TARGET_MAX_SECONDS = 60.0            # approved range ceiling (was 62.0)
MAX_HOOK_SECONDS = 4.0
MAX_CTA_SECONDS = 3.0                # CTA must be ≤3 s (was ≤4 s)
MAX_SCENE_SECONDS_WITHOUT_BEATS = 6.0  # scenes >6s MUST have ≥2 beats; >8s ≥3 beats

# Numeric visualization components that must declare source_type
NUMERIC_VIZ_COMPONENTS = {
    "MeterScene", "BarChartScene", "DataScene",
    "GraphGrowthScene", "NumberCounterScene", "DialScene",
}

DEMONSTRATION_TYPES = {
    "DEMONSTRATION", "TRANSFORMATION", "FLOW",
    "COMPARISON", "DIAGRAM", "DATA", "ZOOM", "SIMULATION",
}
TYPOGRAPHY_COMPONENTS = {"KineticTypoScene"}   # pure-text components
# HOOK, TAKEAWAY, CTA are structural, not counted in typography ratio

CAMERA_MOVES = {
    "slow-push-in", "zoom-in", "zoom-out", "pan-left", "pan-right",
    "pan-follow", "reveal", "static", "focus-shift", "track-object",
}


# ── System prompt (v3) ───────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are the Visual Director for "Srini on AI", a YouTube Shorts channel about AI for developers.

Your job: given a script JSON, produce a storyboard JSON that describes what the viewer
SEES on screen — not what they read. Every visual event must DEMONSTRATE, not display.

══════════════════════════════════════════════════════
CORE PRINCIPLE — Motion Storytelling
══════════════════════════════════════════════════════
Voice EXPLAINS. Visuals DEMONSTRATE.
The viewer with sound off must understand the core idea from animation alone.

A 50–60 second Short must contain ≥10 meaningful VISUAL BEATS.
A beat = one meaningful visual event: object enters, transforms, moves, reveals, etc.
Pulsing backgrounds and ambient particles do NOT count as beats.

Every 2–4 seconds: at least one meaningful visual event must occur:
  object enters • object transforms • information moves • comparison changes
  meter fills • graph grows • nodes connect • item splits • camera reframes
  state changes • result appears

══════════════════════════════════════════════════════
TARGET STRUCTURE (58 seconds total)
══════════════════════════════════════════════════════
0–3s      HOOK         — Visually surprise immediately; one punchy statement or phenomenon
3–8s      DEMONSTRATION — Show the phenomenon BEFORE explaining it
8–40s     EXPLANATION   — Multiple beats: diagrams, transformations, comparisons, simulations
40–50s    WHY IT MATTERS — Apply concept to real scenario; concrete usage beats
50–55s    TAKEAWAY      — Compress the entire lesson into one visual moment
55–58s    CTA           — Always EXACTLY 3 seconds — no longer

══════════════════════════════════════════════════════
SCENE SCHEMA
══════════════════════════════════════════════════════
Each scene must be a JSON object with EXACTLY these keys:
{
  "scene_id": <integer, 1-based>,
  "duration_seconds": <float, 2.0–8.0 — prefer 2.5–5.0>,
  "narration": "<the voiceover spoken during this scene>",
  "scene_type": "<HOOK|DEMONSTRATION|TRANSFORMATION|FLOW|COMPARISON|DIAGRAM|DATA|ZOOM|SIMULATION|METAPHOR|TAKEAWAY|CTA>",
  "visual_goal": "<one sentence: what the viewer must understand visually — not what they hear>",
  "component": "<see COMPONENT GUIDE below>",
  "objects": [<named visual elements present: e.g. 'query bubble', 'doc cards', 'context window'>],
  "animation": "<brief description of all motion that happens in this scene>",
  "on_screen_text": [<SHORT labels only — max 6 words each — NEVER a narration sentence>],
  "data": <object or null — structured payload for data-driven components>,
  "transition": "<how this scene ends / how the next begins: fade | slide-right | zoom-in | morph | cut>",
  "carry_object_from": "<optional — name a visual object from the PREVIOUS scene that enters this scene to maintain continuity>",
  "beats": [
    {
      "start": <float seconds from scene start>,
      "end": <float seconds from scene start>,
      "action": "<what visually happens — be specific: 'query bubble enters from bottom, lands in retrieval node'>",
      "focus": "<optional — which element is in focus>",
      "camera": "<optional — one of: slow-push-in | zoom-in | zoom-out | pan-left | pan-right | pan-follow | reveal | static | focus-shift | track-object>"
    }
  ]
}

BEATS RULE: Every scene > 4 seconds MUST have ≥2 beats. Every scene > 6 seconds MUST have ≥3 beats.
Any scene > 8 seconds with fewer than 3 beats will FAIL the quality gate.

══════════════════════════════════════════════════════
COMPONENT GUIDE — choose by what the scene DOES
══════════════════════════════════════════════════════
ORIGINAL COMPONENTS:
  KineticTypoScene      — HOOK only; punchy text glitch/reveal; max 3 seconds for hook
  TokenScene            — tokenization: text → token boxes → IDs
  SketchScene           — node-edge diagram (pipeline, architecture)
  DataScene             — animated bar chart or comparison bars
  NumberCounterScene    — large number counting up (use data: {type:"counter",...})
  SplitCompareScene     — left vs right / before vs after comparison
  FlowScene             — linear step-by-step pipeline with icons
  HubSpokeScene         — radial hub+spokes (MCP, orchestrators)
  ClusterScene          — semantic cluster groupings
  DialScene             — dial/knob (temperature, confidence)
  BarChartScene         — simple 0–100 bar gauge
  TakeawayScene         — single bold takeaway line (TAKEAWAY zone only)
  CTAScene              — follow CTA (CTA zone only, 3 seconds)

MOTION-FIRST PRIMITIVES (v3 — prefer these for visual density):
  TransformScene        — A morphs into B; shows state change visually (e.g. words → tokens → IDs)
  PipelineScene         — horizontal multi-stage pipeline; data packet travels through stages
  ContextWindowScene    — rectangle fills with chunks/tokens as context grows
  TokenStreamScene      — tokens generate one-by-one from left to right
  DocumentRetrievalScene — document cards fan out; relevant chunks light up and travel
  NetworkBuildScene     — neural network or graph builds node-by-node with edges appearing
  LayerRevealScene      — stacked system layers peel/reveal from top (e.g. LLM architecture)
  TimelineScene         — horizontal timeline with animated event markers
  BeforeAfterScene      — animated wipe comparing two visual states
  MeterScene            — filling gauge/progress bar (accuracy, speed, cost)
  GraphGrowthScene      — line or bar chart growing in real time
  CodeExecutionScene    — code runs line-by-line with output appearing
  CardStackScene        — deck of cards fans/sorts/filters
  DataFlowScene         — labelled data packets move through a system diagram

══════════════════════════════════════════════════════
COMPOSITION VARIETY — do NOT repeat the same layout
══════════════════════════════════════════════════════
Alternate between:
  full-canvas visual | split screen | zoomed object | horizontal pipeline
  vertical flow | graph/network | dashboard data | comparison | cinematic illustration
No more than 2 consecutive scenes with the same composition type.

══════════════════════════════════════════════════════
CONTINUITY — carry objects between scenes
══════════════════════════════════════════════════════
Where possible, carry an object from one scene into the next.
Example: token boxes created in scene 2 travel right into the context window in scene 3.
Use "carry_object_from" to name the object that continues.

══════════════════════════════════════════════════════
TEXT RESTRICTIONS (v3 — stricter)
══════════════════════════════════════════════════════
Full-screen typography is allowed ONLY for: HOOK, one key contrast, TAKEAWAY, CTA.
All explanation scenes MUST use objects + motion + labels — not headlines + sentences.
Typography-only scenes must be ≤25% of total episode runtime.
NEVER duplicate voiceover narration as on_screen_text.

══════════════════════════════════════════════════════
DATA FIELD FORMATS
══════════════════════════════════════════════════════
NumberCounterScene:
  "data": {"type":"counter","value":<n>,"label":"<what it means>","suffix":"<unit>"}

DataScene bars:
  "data": {"type":"bars","title":"<title>","bars":[{"label":"...","value":<0-100>},...]}

DataScene comparison:
  "data": {"type":"comparison","title":"...","bars":[{"label":"before","value":<n>,"maxValue":<m>},{"label":"after","value":<n>,"maxValue":<m>}]}

══════════════════════════════════════════════════════
VISUAL COMPLEXITY SCORE — compute this at the end
══════════════════════════════════════════════════════
Count these in your storyboard, then compute a score 0–100:

  visual_beats            — total number of beats across all scenes
  demonstrations          — scenes with scene_type in {DEMONSTRATION, TRANSFORMATION, FLOW, COMPARISON, DIAGRAM, DATA, ZOOM, SIMULATION}
  transformations         — scenes explicitly showing A→B state change
  diagrams_flows          — scenes with multi-node diagrams or flow animations
  data_visuals            — scenes with charts, counters, meters
  typography_only_scenes  — scenes where visuals are text-only (penalised)
  repeated_layouts        — consecutive scenes with same composition (penalised)

Score formula (approximate):
  base = min(100, visual_beats * 7)
  bonus = demonstrations * 3 + transformations * 4 + diagrams_flows * 3 + data_visuals * 2
  penalty = typography_only_scenes * 8 + repeated_layouts * 6
  visual_first_score = min(100, max(0, base + bonus - penalty))

Storyboard FAILS if visual_first_score < 80.

══════════════════════════════════════════════════════
NUMERIC INTEGRITY — permanent rule for all numeric components
══════════════════════════════════════════════════════
Any scene using MeterScene, BarChartScene, DataScene, GraphGrowthScene,
NumberCounterScene, or DialScene MUST include "source_type" at the scene level:

  "source_type": "sourced_numeric"   — real verifiable number; ALSO include
  "source_reference": "<citation>"   — paper / benchmark / official doc

  "source_type": "illustrative"      — no verified source; use qualitative labels

With sourced_numeric: precise percentages, accuracy scores, dollar savings,
and performance gains are ALLOWED.

With illustrative: NO exact percentages, NO invented accuracy numbers, NO
made-up performance gains. Communicate relationships qualitatively:
  - Use zone-centre positions for gauges (midpoint of the intended zone).
  - Use relative terms: HIGHER / LOWER / FASTER / MORE / LESS, not 27% or +63 pts.
  - On-screen labels must be qualitative: e.g. HIGHER RISK / MORE GROUNDED.

Inventing a number to populate a chart or gauge is FORBIDDEN regardless of
how plausible it sounds. If you cannot cite a source, use illustrative mode.

══════════════════════════════════════════════════════
SCENE DIVERSITY — do NOT copy the RAG episode template
══════════════════════════════════════════════════════
The RAG reference episode used a specific 11-scene sequence:
  BeforeAfterScene → TransformScene → DataFlowScene → DocumentRetrievalScene
  → ContextWindowScene → TokenStreamScene → PipelineScene → SplitCompareScene
  → MeterScene → TakeawayScene → CTAScene

Do NOT reproduce this sequence for other topics. Choose scenes that fit
the concept you are visualising. Every topic deserves its own scene selection.

Specifically forbidden as RAG-carry-over defaults:
  - Two-gauge MeterScene comparing "without X" vs "with X" (illustrative)
  - DocumentRetrievalScene unless the concept actually involves document retrieval
  - ContextWindowScene unless the concept involves context / token windows
  - 11-scene count or ~51 s as a target
  - Red/green zone positioning borrowed from the RAG gauge

══════════════════════════════════════════════════════
OUTPUT FORMAT — return ONLY this JSON object, no fences, no explanation
══════════════════════════════════════════════════════
{
  "storyboard": [<array of scene objects>],
  "total_duration_seconds": <float>,
  "visual_summary": "<one line: the visual journey of this episode>",
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
    """
    Compute the visual complexity score from the storyboard.
    Returns the full visual_complexity dict.
    """
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
        if (scenes[i].get("component") == scenes[i+1].get("component") ==
                scenes[i+2].get("component")):
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
    Run the v3 quality gate. Returns a list of violation strings.
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
            violations.append(f"Scene {i+1} missing keys: {missing}")
        if scene.get("scene_type") not in VALID_SCENE_TYPES:
            violations.append(
                f"Scene {i+1} invalid scene_type: '{scene.get('scene_type')}'"
            )
        if scene.get("component") not in VALID_COMPONENTS:
            violations.append(
                f"Scene {i+1} invalid component: '{scene.get('component')}'"
            )
        # Narration must not appear verbatim in on_screen_text
        narration = scene.get("narration", "")
        for label in scene.get("on_screen_text", []):
            if len(label.split()) > 8:
                violations.append(
                    f"Scene {i+1} on_screen_text too long (>8 words): '{label}'"
                )
            if narration and label.lower() in narration.lower() and len(label.split()) > 5:
                violations.append(
                    f"Scene {i+1} on_screen_text duplicates narration: '{label}'"
                )

        # Beats required for longer scenes
        dur = scene.get("duration_seconds", 0)
        beats = scene.get("beats", [])
        n_beats = len(beats) if isinstance(beats, list) else 0
        if dur > 8.0 and n_beats < 3:
            violations.append(
                f"Scene {i+1} is {dur}s with only {n_beats} beat(s) — need ≥3 for scenes >8s"
            )
        elif dur > 6.0 and n_beats < 2:
            violations.append(
                f"Scene {i+1} is {dur}s with only {n_beats} beat(s) — need ≥2 for scenes >6s"
            )

    # ── Numeric integrity: source_type required on numeric viz components ────
    for i, scene in enumerate(scenes):
        comp = scene.get("component", "")
        if comp in NUMERIC_VIZ_COMPONENTS:
            src_type = scene.get("source_type", "")
            if src_type not in {"sourced_numeric", "illustrative"}:
                violations.append(
                    f"Scene {i+1} ({comp}) is missing 'source_type' — "
                    f"must be 'sourced_numeric' or 'illustrative'"
                )
            elif src_type == "sourced_numeric" and not scene.get("source_reference", "").strip():
                violations.append(
                    f"Scene {i+1} ({comp}) has source_type='sourced_numeric' "
                    f"but 'source_reference' is empty — provide a citation"
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
            f"{typo_runtime/total:.0%} — exceeds {MAX_TYPOGRAPHY_RATIO:.0%} cap"
        )

    # ── Visual demonstration count ────────────────────────────────────────────
    explanatory = [s for s in scenes if s.get("scene_type") not in structural]
    demo_count = sum(1 for s in explanatory if s.get("scene_type") in DEMONSTRATION_TYPES)
    if demo_count < MIN_VISUAL_DEMONSTRATIONS:
        violations.append(
            f"Only {demo_count} visual demonstrations — need ≥{MIN_VISUAL_DEMONSTRATIONS}"
        )

    # ── Consecutive same composition (3+ in a row fails) ─────────────────────
    for i in range(len(scenes) - MAX_CONSECUTIVE_SAME_LAYOUT):
        window_comps = [
            scenes[i + j].get("component")
            for j in range(MAX_CONSECUTIVE_SAME_LAYOUT + 1)
        ]
        if len(set(window_comps)) == 1 and window_comps[0] not in {"CTAScene", "TakeawayScene"}:
            violations.append(
                f"Scenes {i+1}–{i+MAX_CONSECUTIVE_SAME_LAYOUT+1}: "
                f"3 consecutive '{window_comps[0]}' — vary composition"
            )

    # ── Visual-first score gate ───────────────────────────────────────────────
    complexity = _compute_visual_complexity(scenes)
    score = complexity["visual_first_score"]
    if score < MIN_VISUAL_FIRST_SCORE:
        violations.append(
            f"Visual-first score {score}/100 is below minimum {MIN_VISUAL_FIRST_SCORE}"
        )

    return violations


def _print_storyboard_summary(scenes: list, episode: int, complexity: dict | None = None) -> None:
    """Print a human-readable storyboard table to stdout (used by dry-run)."""
    print(f"\n{'─'*100}")
    print(f"  EP{episode:02d} STORYBOARD v3 — {len(scenes)} scenes")
    print(f"{'─'*100}")
    print(f"  {'#':>2}  {'TIME':>7}  {'Type':<14}  {'Component':<24}  {'Beats':>5}  Visual action")
    print(f"{'─'*100}")
    cumulative = 0.0
    for s in scenes:
        dur = s.get("duration_seconds", 0)
        end = cumulative + dur
        comp = s.get("component", "?")
        stype = s.get("scene_type", "?")
        anim = s.get("animation", "")[:40]
        n_beats = len(s.get("beats") or [])
        print(
            f"  {s.get('scene_id', '?'):>2}  "
            f"{cumulative:>4.1f}–{end:>4.1f}s  "
            f"{stype:<14}  {comp:<24}  {n_beats:>5}  {anim}"
        )
        for b in (s.get("beats") or []):
            print(
                f"      {b.get('start',0):>4.1f}–{b.get('end',0):>4.1f}s  "
                f"    ↳ {b.get('action','')[:60]}"
            )
        cumulative = end
    print(f"{'─'*100}")
    print(f"  Total: {cumulative:.1f}s")
    if complexity:
        print(f"\n  Visual Complexity Score:")
        print(f"    Visual beats      : {complexity.get('visual_beats', 0)}")
        print(f"    Demonstrations    : {complexity.get('demonstrations', 0)}")
        print(f"    Transformations   : {complexity.get('transformations', 0)}")
        print(f"    Diagrams / flows  : {complexity.get('diagrams_flows', 0)}")
        print(f"    Data visuals      : {complexity.get('data_visuals', 0)}")
        print(f"    Typography-only   : {complexity.get('typography_only_scenes', 0)}")
        print(f"    Repeated layouts  : {complexity.get('repeated_layouts', 0)}")
        print(f"    ─────────────────────────────────")
        score = complexity.get('visual_first_score', 0)
        status = "✓ PASS" if score >= MIN_VISUAL_FIRST_SCORE else "✗ FAIL"
        print(f"    Visual-first score: {score}/100  {status}")
    print()


def run(
    script: dict,
    episode: int,
    week: int,
    lang: str = "en",
    dry_run: bool = False,
) -> dict:
    """
    Generate a v3 visual storyboard (motion-storytelling) from a script JSON.

    Args:
        script:   Script dict from script_agent
        episode:  Episode number
        week:     Week number
        lang:     Language code
        dry_run:  If True, prints storyboard summary without saving

    Returns:
        {
          "success": True,
          "output_path": str,
          "storyboard": list,
          "total_duration": float,
          "visual_complexity": dict,
          "violations": list[str],
          "skipped": bool
        }
    """
    lang = lang.lower()
    output_path = (
        _episode_dir(episode, week) / f"ep{episode:02d}_storyboard_{lang.upper()}.json"
    )

    # Cache check — skip Claude call if storyboard already on disk and passes
    if output_path.exists():
        try:
            cached = json.loads(output_path.read_text(encoding="utf-8"))
            scenes = cached.get("storyboard", [])
            violations = _validate_storyboard(scenes, episode)
            if not violations:
                complexity = cached.get(
                    "visual_complexity", _compute_visual_complexity(scenes)
                )
                logger.info(
                    f"EP{episode:02d} — storyboard already on disk "
                    f"({len(scenes)} scenes, score {complexity.get('visual_first_score',0)}) "
                    f"— skipping Visual Director"
                )
                if dry_run:
                    _print_storyboard_summary(scenes, episode, complexity)
                return {
                    "success": True,
                    "output_path": str(output_path),
                    "storyboard": scenes,
                    "total_duration": cached.get("total_duration_seconds", 0),
                    "visual_complexity": complexity,
                    "violations": [],
                    "skipped": True,
                }
            else:
                logger.warning(
                    f"EP{episode:02d} — cached storyboard failed v3 quality gate: "
                    f"{violations[:3]} — regenerating"
                )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"EP{episode:02d} — could not read cached storyboard: {e}")

    # Build user message from script
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
        user_msg += f"Token spec (for TokenScene/TokenStreamScene): {json.dumps(script['token_spec'])}\n\n"
    if script.get("sketch_spec"):
        user_msg += f"Sketch spec (for SketchScene/DataFlowScene): {json.dumps(script['sketch_spec'])}\n\n"
    if script.get("data_spec"):
        user_msg += f"Data spec (for DataScene/MeterScene/GraphGrowthScene): {json.dumps(script['data_spec'])}\n\n"

    user_msg += (
        "Generate the v3.2 storyboard now. Remember:\n"
        "- Include beats[] for every scene > 4 seconds\n"
        "- Use motion-first primitives wherever possible\n"
        "- Compute and include visual_complexity score\n"
        "- Structure: 0–3s hook, 3–8s demo, 8–40s explain, 40–50s why, 50–55s takeaway, 55–58s CTA\n"
        "- CTA must be exactly 3 seconds (≤3 s)\n"
        "- Total duration: 45–60 seconds\n"
        "- Every numeric viz scene (MeterScene, BarChartScene, etc.) must include source_type\n"
        "- Choose scenes that fit THIS topic — do not copy the RAG episode template\n"
    )

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    last_error: Exception | None = None
    violations: list[str] = []

    for attempt in range(1, 4):
        try:
            logger.info(
                f"EP{episode:02d} — Visual Director v3 Claude call (attempt {attempt}/3)"
            )

            response = client.messages.create(
                model=MODEL,
                max_tokens=4000,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )

            raw = response.content[0].text
            data = _parse_json(raw)

            scenes = data.get("storyboard")
            if not isinstance(scenes, list) or not scenes:
                raise ValueError("Response missing 'storyboard' array")

            violations = _validate_storyboard(scenes, episode)
            if violations:
                logger.warning(
                    f"EP{episode:02d} — v3 quality gate failed (attempt {attempt}): "
                    f"{'; '.join(violations[:4])}"
                )
                if attempt < 3:
                    user_msg_retry = (
                        user_msg
                        + f"\n\nYour previous storyboard FAILED the v3 quality gate:\n"
                        + "\n".join(f"- {v}" for v in violations)
                        + "\n\nFix these issues. Remember: "
                        + "every scene >4s needs beats[], "
                        + "CTA must be ≤3s, HOOK must be ≤4s, "
                        + "visual_first_score must be ≥80."
                    )
                    user_msg = user_msg_retry
                    time.sleep(2 ** attempt)
                    continue
                logger.error(
                    f"EP{episode:02d} — storyboard still has violations after 3 attempts; "
                    f"proceeding with warnings"
                )

            # Normalise scene IDs
            for i, scene in enumerate(scenes):
                scene["scene_id"] = i + 1

            # Use model-reported complexity or recompute it
            complexity = data.get("visual_complexity") or _compute_visual_complexity(scenes)

            result_data = {
                "storyboard": scenes,
                "total_duration_seconds": data.get(
                    "total_duration_seconds",
                    round(sum(s.get("duration_seconds", 0) for s in scenes), 2),
                ),
                "visual_summary": data.get("visual_summary", ""),
                "visual_complexity": complexity,
                "violations": violations,
            }

            if not dry_run:
                output_path.write_text(
                    json.dumps(result_data, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                logger.info(
                    f"EP{episode:02d} — v3 storyboard saved ({len(scenes)} scenes, "
                    f"score {complexity.get('visual_first_score',0)}) -> {output_path}"
                )

            if dry_run:
                _print_storyboard_summary(scenes, episode, complexity)

            return {
                "success": True,
                "output_path": str(output_path),
                "storyboard": scenes,
                "total_duration": result_data["total_duration_seconds"],
                "visual_complexity": complexity,
                "violations": violations,
                "skipped": False,
            }

        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning(
                f"EP{episode:02d} — Visual Director v3 attempt {attempt} bad output: {e}"
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
                f"EP{episode:02d} — Visual Director v3 attempt {attempt} error: {e}"
            )
            if attempt < 3:
                time.sleep(2 ** attempt)

    raise RuntimeError(
        f"EP{episode:02d} visual_director_agent failed after 3 attempts: {last_error}"
    )
