"""
Visual Director Agent — Phase 2.5
Reads a script JSON and produces a storyboard JSON array.

Each storyboard scene describes what VISUALLY HAPPENS on screen,
decoupled from the slide-card model. The resulting storyboard is
consumed by visual_agent.py which passes it to Remotion for rendering.

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

# ── Storyboard scene schema ───────────────────────────────────────────────────

VALID_SCENE_TYPES = {
    "HOOK", "DEMONSTRATION", "TRANSFORMATION", "FLOW",
    "COMPARISON", "DIAGRAM", "DATA", "ZOOM",
    "SIMULATION", "METAPHOR", "TAKEAWAY", "CTA",
}

VALID_COMPONENTS = {
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
}

# ── Quality gate thresholds ───────────────────────────────────────────────────

MAX_TEXT_CARD_RATIO = 0.30          # no more than 30% pure text-card scenes
MAX_CONSECUTIVE_SAME_TYPE = 2       # at most 2 in a row with same type
MIN_VISUAL_DEMONSTRATIONS = 3       # at least 3 "real" visual scenes
TARGET_MIN_SECONDS = 55.0
TARGET_MAX_SECONDS = 62.0

# Scene types that count as genuine visual demonstrations (not text cards)
DEMONSTRATION_TYPES = {
    "DEMONSTRATION", "TRANSFORMATION", "FLOW",
    "COMPARISON", "DIAGRAM", "DATA", "ZOOM", "SIMULATION",
}

# Scene types that are essentially text cards (penalty in quality gate)
TEXT_CARD_TYPES = {"METAPHOR"}   # only if objects/animation are empty
# HOOK, TAKEAWAY, CTA are structural — not counted as text cards


_SYSTEM_PROMPT = """\
You are the Visual Director for Srini on AI, a YouTube Shorts channel about AI for developers.

Your job: given a script JSON, produce a storyboard JSON array that describes what the viewer
SEES on screen — not what they read. Visuals must complement the narration, not duplicate it.

CORE PRINCIPLE
--------------
Voice EXPLAINS. Visuals DEMONSTRATE.
A viewer with the sound off should grasp the core idea from the animation alone.
If the narration says "tokens become numbers", show: Hello → [Hello] → 15496 — not text.

SCENE SCHEMA
------------
Each scene must be a JSON object with EXACTLY these keys:
{
  "scene_id": <integer, 1-based>,
  "duration_seconds": <float, 2.0–8.0>,
  "narration": "<the portion of the voiceover spoken during this scene>",
  "scene_type": "<one of: HOOK | DEMONSTRATION | TRANSFORMATION | FLOW | COMPARISON | DIAGRAM | DATA | ZOOM | SIMULATION | METAPHOR | TAKEAWAY | CTA>",
  "visual_goal": "<one sentence: what the viewer must understand from this scene visually>",
  "component": "<Remotion component: KineticTypoScene | TokenScene | SketchScene | DataScene | SplitCompareScene | FlowScene | HubSpokeScene | ClusterScene | DialScene | BarChartScene | NumberCounterScene | TakeawayScene | CTAScene>",
  "objects": [<strings — the named visual elements present, e.g. token boxes, arrows, bar labels, node names>],
  "animation": "<brief description of the motion/transition that happens in this scene>",
  "on_screen_text": [<strings — SHORT labels only: max 7 words per item; NEVER a narration sentence; empty [] is fine and encouraged>],
  "data": <object or null — for DataScene/NumberCounterScene: e.g. {"type":"counter","value":128000,"label":"token context window","suffix":"tokens"}>,
  "transition": "<how this scene ends / how the next scene begins, e.g. 'fade', 'slide right', 'zoom out'>"
}

COMPONENT GUIDE
---------------
KineticTypoScene  — HOOK or key punchy statement; large animated text glitch/reveal
TokenScene        — tokenization, text → token boxes → IDs; sentence split animation
SketchScene       — node-edge diagram (pipeline, flow, architecture, process)
DataScene         — bar chart or comparison bars (use "data" field with type "bars" or "comparison")
NumberCounterScene — animating counter counting up to a hero number (use "data" field with type "counter")
SplitCompareScene  — left vs right, before vs after, A vs B
FlowScene         — linear steps with icons
HubSpokeScene     — hub + spoke radial (MCP, agents)
ClusterScene      — semantic groupings
DialScene         — dial/knob (temperature, settings)
BarChartScene     — simple 0-100 bar chart
TakeawayScene     — single bold takeaway line
CTAScene          — creator photo + follow CTA (always LAST scene)

STORY STRUCTURE (60 seconds)
-----------------------------
0–2s     HOOK         — KineticTypoScene — punchy visual hook; one bold statement
2–8s     DEMONSTRATION — show the problem or phenomenon immediately
8–35s    EXPLANATION   — 4–7 short scenes: TRANSFORMATION, DIAGRAM, DATA, FLOW, COMPARISON
35–50s   WHY IT MATTERS — connect to real usage, SIMULATION or COMPARISON
50–57s   TAKEAWAY      — TakeawayScene — one visual summary
57–60s   CTA           — CTAScene — always last

HARD VISUAL RULES
-----------------
1. NEVER put a narration sentence as on_screen_text. Labels only (1-5 words).
2. At least 70% of explanatory scenes (not HOOK/TAKEAWAY/CTA) must be DEMONSTRATION,
   TRANSFORMATION, DIAGRAM, DATA, COMPARISON, FLOW, ZOOM, or SIMULATION.
3. No more than 2 consecutive scenes with the same scene_type.
4. Every 2–4 seconds something meaningful must visually change (animation must be non-trivial).
5. Avoid empty screens. Transitions ≤ 0.4 seconds.
6. Total duration of all scenes must sum to 57–62 seconds.
7. CTAScene is ALWAYS the last scene and always exactly 3 seconds.

DATA FIELD FORMAT
-----------------
For NumberCounterScene (scene_type DATA, component NumberCounterScene):
  "data": {"type": "counter", "value": <number>, "label": "<what it means>", "suffix": "<optional unit>"}

For DataScene with bars (scene_type DATA or COMPARISON, component DataScene):
  "data": {"type": "bars", "title": "<chart title>", "bars": [{"label": "...", "value": <0-100>}, ...]}

For DataScene comparison (scene_type COMPARISON, component DataScene):
  "data": {"type": "comparison", "title": "...", "bars": [{"label": "old", "value": <n>, "maxValue": <m>}, {"label": "new", "value": <n>, "maxValue": <m>}]}

For TokenScene: leave "data" null; the token details come from the script's token_spec.

OUTPUT FORMAT
-------------
Return a JSON object with EXACTLY this structure — no markdown fences, no explanation:
{
  "storyboard": [<array of scene objects>],
  "total_duration_seconds": <float>,
  "visual_summary": "<one line describing the visual journey of this episode>"
}
"""


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

    # ── CTA must be last ──────────────────────────────────────────────────────
    last = scenes[-1]
    if last.get("component") != "CTAScene":
        violations.append("Last scene must be CTAScene")

    # ── Schema completeness ───────────────────────────────────────────────────
    required_keys = {
        "scene_id", "duration_seconds", "narration", "scene_type",
        "visual_goal", "component", "objects", "animation", "on_screen_text", "transition"
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
        # Narration text must not appear verbatim in on_screen_text
        narration = scene.get("narration", "")
        for label in scene.get("on_screen_text", []):
            if len(label.split()) > 10:
                violations.append(
                    f"Scene {i+1} on_screen_text label too long (>10 words): '{label}'"
                )
            if narration and label.lower() in narration.lower() and len(label.split()) > 5:
                violations.append(
                    f"Scene {i+1} on_screen_text appears to duplicate narration: '{label}'"
                )

    # ── Text-card ratio (non-structural scenes only) ──────────────────────────
    structural = {"HOOK", "TAKEAWAY", "CTA"}
    explanatory = [s for s in scenes if s.get("scene_type") not in structural]
    if explanatory:
        text_cards = [
            s for s in explanatory
            if s.get("scene_type") == "METAPHOR"
            and not s.get("objects") and not s.get("animation")
        ]
        ratio = len(text_cards) / len(explanatory)
        if ratio > MAX_TEXT_CARD_RATIO:
            violations.append(
                f"Text-card ratio {ratio:.0%} exceeds {MAX_TEXT_CARD_RATIO:.0%} limit"
            )

    # ── Visual demonstration count ────────────────────────────────────────────
    demo_count = sum(
        1 for s in explanatory if s.get("scene_type") in DEMONSTRATION_TYPES
    )
    if demo_count < MIN_VISUAL_DEMONSTRATIONS:
        violations.append(
            f"Only {demo_count} visual demonstrations — need at least {MIN_VISUAL_DEMONSTRATIONS}"
        )

    # ── Consecutive same scene_type ───────────────────────────────────────────
    for i in range(len(scenes) - MAX_CONSECUTIVE_SAME_TYPE):
        window_types = [
            scenes[i + j].get("scene_type") for j in range(MAX_CONSECUTIVE_SAME_TYPE + 1)
        ]
        if len(set(window_types)) == 1 and window_types[0] not in {"HOOK", "CTA"}:
            violations.append(
                f"Scene {i+1}–{i+MAX_CONSECUTIVE_SAME_TYPE+1}: "
                f"{MAX_CONSECUTIVE_SAME_TYPE+1} consecutive '{window_types[0]}' scenes"
            )

    return violations


def _print_storyboard_summary(scenes: list, episode: int) -> None:
    """Print a human-readable storyboard table to stdout (used by dry-run)."""
    print(f"\n{'─'*90}")
    print(f"  EP{episode:02d} STORYBOARD ({len(scenes)} scenes)")
    print(f"{'─'*90}")
    print(f"  {'#':>2}  {'T':>5}  {'Type':<16}  {'Component':<22}  Visual action")
    print(f"{'─'*90}")
    cumulative = 0.0
    for s in scenes:
        dur = s.get("duration_seconds", 0)
        end = cumulative + dur
        comp = s.get("component", "?")
        stype = s.get("scene_type", "?")
        anim = s.get("animation", "")[:45]
        print(
            f"  {s.get('scene_id', '?'):>2}  "
            f"{cumulative:>4.1f}s  "
            f"{stype:<16}  {comp:<22}  {anim}"
        )
        cumulative = end
    print(f"{'─'*90}")
    print(f"  Total: {cumulative:.1f}s\n")


def run(
    script: dict,
    episode: int,
    week: int,
    lang: str = "en",
    dry_run: bool = False,
) -> dict:
    """
    Generate a visual storyboard from a script JSON.

    Args:
        script:   Script dict from script_agent (must contain voiceover, topic, concept, etc.)
        episode:  Episode number
        week:     Week number
        lang:     Language code (storyboard is lang-agnostic for visuals, but saved per lang)
        dry_run:  If True, prints storyboard summary and exits without saving

    Returns:
        {"success": True, "output_path": str, "storyboard": list, "total_duration": float}
    """
    lang = lang.lower()
    output_path = _episode_dir(episode, week) / f"ep{episode:02d}_storyboard_{lang.upper()}.json"

    # Cache check — skip Claude call if storyboard already on disk
    if output_path.exists():
        try:
            cached = json.loads(output_path.read_text(encoding="utf-8"))
            scenes = cached.get("storyboard", [])
            violations = _validate_storyboard(scenes, episode)
            if not violations:
                logger.info(
                    f"EP{episode:02d} — storyboard already on disk "
                    f"({len(scenes)} scenes) — skipping Visual Director"
                )
                if dry_run:
                    _print_storyboard_summary(scenes, episode)
                return {
                    "success": True,
                    "output_path": str(output_path),
                    "storyboard": scenes,
                    "total_duration": cached.get("total_duration_seconds", 0),
                    "skipped": True,
                }
            else:
                logger.warning(
                    f"EP{episode:02d} — cached storyboard failed quality gate: "
                    f"{violations} — regenerating"
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

    # Pass diagram/token spec so Visual Director can make informed scene choices
    if script.get("token_spec"):
        user_msg += f"Token spec (for TokenScene): {json.dumps(script['token_spec'])}\n\n"
    if script.get("sketch_spec"):
        user_msg += f"Sketch spec (for SketchScene): {json.dumps(script['sketch_spec'])}\n\n"
    if script.get("data_spec"):
        user_msg += f"Data spec (for DataScene): {json.dumps(script['data_spec'])}\n\n"

    user_msg += "Generate the storyboard JSON now."

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            logger.info(
                f"EP{episode:02d} — Visual Director Claude call (attempt {attempt}/3)"
            )

            response = client.messages.create(
                model=MODEL,
                max_tokens=3000,
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
                    f"EP{episode:02d} — storyboard quality gate failed (attempt {attempt}): "
                    f"{'; '.join(violations)}"
                )
                if attempt < 3:
                    # Give Claude feedback on what it got wrong
                    user_msg_retry = (
                        user_msg
                        + f"\n\nYour previous storyboard FAILED the quality gate:\n"
                        + "\n".join(f"- {v}" for v in violations)
                        + "\n\nPlease fix these issues and regenerate the storyboard."
                    )
                    user_msg = user_msg_retry
                    time.sleep(2 ** attempt)
                    continue
                # 3rd attempt still failing — log violations and continue anyway
                logger.error(
                    f"EP{episode:02d} — storyboard still has violations after 3 attempts; "
                    f"proceeding with warnings: {violations}"
                )

            # Normalise scene IDs to be sequential
            for i, scene in enumerate(scenes):
                scene["scene_id"] = i + 1

            result_data = {
                "storyboard": scenes,
                "total_duration_seconds": data.get(
                    "total_duration_seconds",
                    round(sum(s.get("duration_seconds", 0) for s in scenes), 2)
                ),
                "visual_summary": data.get("visual_summary", ""),
                "violations": violations,
            }

            if not dry_run:
                output_path.write_text(
                    json.dumps(result_data, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                logger.info(
                    f"EP{episode:02d} — storyboard saved ({len(scenes)} scenes) "
                    f"-> {output_path}"
                )

            if dry_run:
                _print_storyboard_summary(scenes, episode)

            return {
                "success": True,
                "output_path": str(output_path),
                "storyboard": scenes,
                "total_duration": result_data["total_duration_seconds"],
                "violations": violations,
                "skipped": False,
            }

        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning(
                f"EP{episode:02d} — Visual Director attempt {attempt} bad output: {e}"
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
                f"EP{episode:02d} — Visual Director attempt {attempt} error: {e}"
            )
            if attempt < 3:
                time.sleep(2 ** attempt)

    raise RuntimeError(
        f"EP{episode:02d} visual_director_agent failed after 3 attempts: {last_error}"
    )
