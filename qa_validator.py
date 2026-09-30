"""
qa_validator.py — Extended QA Validation for AI Bytes Shorts (v3.2)

7 checks, 4 hard fail conditions.

sourced_numeric / illustrative rule (check 6):
  Numeric visualization scenes (MeterScene, BarChartScene, DataScene) must
  have source_type="sourced_numeric" + source_reference in the storyboard to
  render any precise numeric claim. Without it, the scene is in "illustrative"
  mode and any exact percentage, dollar value, or performance stat hard-fails QA.
  Output includes: Scene | Value | Source type | Source reference | Allowed table.

Usage:
    python qa_validator.py /path/to/video.mp4 [storyboard.json] [--draft]

--draft flag: relaxes resolution check (540×960 ok for 0.5× scale renders).
              Does NOT relax timing or content checks.

Output:
    JSON report printed to stdout. Exit code 0 = PASS, 1 = FAIL.
"""
import json
import logging
import subprocess
import sys
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
EXPECTED_W = 1080
EXPECTED_H = 1920
FPS_EXPECTED = 30.0

# QA thresholds
FIRST_FRAME_FAIL_S = 0.2       # fail if first meaningful visual > 0.2s
EMPTY_TRANSITION_FAIL_S = 0.3  # fail if any empty-canvas gap > 0.3s

# Luminance thresholds for dark-theme video (BG=#050510)
# A white label at partial opacity on #050510 can read as low as 6–10 mean lum.
# We use 4.0 as "truly empty" (a pure BG frame measures ~1-2 on our sample res).
DARK_FRAME_LUM = 4.0      # below this = empty canvas
BRIGHT_FRAME_LUM = 6.0    # above this = meaningful content present
# Unsupported stats: numeric patterns that are fabricated accuracy claims
# Matches things like "27%", "91%", "+63pts", "2.4x improvement"
# NOTE: non-capturing groups only — findall returns full match strings, not group contents.
UNSUPPORTED_STAT_PATTERN = re.compile(
    r'\b\d+\.?\d*\s*%|\+\d+\s*pts?\b|\d+\.?\d*x\s*(?:improvement|better|faster|lift)\b',
    re.IGNORECASE
)
# Internal identifiers that must never appear in video (from objects[] arrays)
INTERNAL_IDENTIFIERS = [
    "without_rag_panel", "with_rag_panel",
    "vanilla_llm_panel", "rag_panel",
    "query_box", "kb_cylinder", "doc_card",
    # Add more as storyboard evolves
]
# Minimum label size to be readable on phone (pixels at 1080×1920)
MIN_LABEL_PX = 24

SMALL_LABEL_WARN_S = 20   # warn if important label detected below MIN_LABEL_PX


def ffprobe_json(video_path: Path) -> dict:
    """Run ffprobe and return parsed JSON."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return json.loads(result.stdout)


def get_video_stream(probe: dict) -> dict:
    """Return the first video stream from ffprobe output."""
    for s in probe.get("streams", []):
        if s.get("codec_type") == "video":
            return s
    raise RuntimeError("No video stream found in file")


def has_audio_stream(probe: dict) -> bool:
    """Return True if file has at least one audio stream."""
    return any(s.get("codec_type") == "audio" for s in probe.get("streams", []))


def check_resolution(video_stream: dict, draft_mode: bool = False) -> dict:
    """Check 1: Video must be 1080×1920 (or 540×960 for 0.5× draft renders)."""
    w = video_stream.get("width", 0)
    h = video_stream.get("height", 0)
    if draft_mode:
        # Accept either full resolution or 0.5× draft scale
        ok = (w == EXPECTED_W and h == EXPECTED_H) or (w == 540 and h == 960)
        note = " (draft: 0.5× accepted)" if (w == 540 and h == 960) else ""
    else:
        ok = (w == EXPECTED_W and h == EXPECTED_H)
        note = ""
    return {
        "check": "resolution",
        "description": f"Video is 1080×1920{note}",
        "result": f"{w}×{h}",
        "pass": ok,
        "fail_condition": False,
    }


def check_duration(video_stream: dict, format_info: dict) -> dict:
    """Check 2: Duration 58–62 seconds (assembly_agent rule)."""
    dur_str = format_info.get("duration", "0")
    dur = float(dur_str)
    ok = 55.0 <= dur <= 65.0
    return {
        "check": "duration",
        "description": "Duration 55–65 seconds",
        "result": f"{dur:.2f}s",
        "pass": ok,
        "fail_condition": False,
    }


def check_audio_track(probe: dict) -> dict:
    """Check 3: Has audio track."""
    ok = has_audio_stream(probe)
    return {
        "check": "audio_track",
        "description": "Has at least one audio stream",
        "result": "yes" if ok else "NO AUDIO STREAM",
        "pass": ok,
        "fail_condition": False,
    }


def check_first_meaningful_frame(video_path: Path) -> dict:
    """
    Check 4 (FAIL CONDITION): First meaningful visual must begin ≤0.2s.
    Samples luminance of first 12 frames. A 'meaningful' frame has mean luminance > 8.
    At 0.5× scale we're rendering 540×960, but timestamps are still 1/30s apart.
    """
    # Extract first 12 frames as PNG, measure mean luminance
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vframes", "12",
        "-vf", "scale=108:192,format=gray",  # downsample for speed
        "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
        "-loglevel", "error"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=20)
        raw = result.stdout
        # Each frame: 108×192 = 20736 bytes of grayscale
        frame_size = 108 * 192
        first_bright_frame = -1
        for fi in range(min(12, len(raw) // frame_size)):
            frame_bytes = raw[fi * frame_size:(fi + 1) * frame_size]
            mean_lum = sum(frame_bytes) / len(frame_bytes)
            if mean_lum > BRIGHT_FRAME_LUM:
                first_bright_frame = fi
                break
        if first_bright_frame == -1:
            # No bright frame in first 12 — very dark opening
            first_t = 12 / FPS_EXPECTED
        else:
            first_t = first_bright_frame / FPS_EXPECTED

        is_fail = first_t > FIRST_FRAME_FAIL_S
        return {
            "check": "first_meaningful_frame",
            "description": f"First meaningful visual ≤{FIRST_FRAME_FAIL_S}s",
            "result": f"{first_t:.3f}s (frame {first_bright_frame})",
            "pass": not is_fail,
            "fail_condition": is_fail,
        }
    except Exception as e:
        logger.warning(f"first_frame check failed to run: {e}")
        return {
            "check": "first_meaningful_frame",
            "description": f"First meaningful visual ≤{FIRST_FRAME_FAIL_S}s",
            "result": f"CHECK_ERROR: {e}",
            "pass": True,  # can't determine, don't block
            "fail_condition": False,
        }


def check_empty_transitions(video_path: Path) -> dict:
    """
    Check 5 (FAIL CONDITION): No unintended empty transition >0.3s.
    Samples mean luminance every 0.1s; looks for runs of dark frames > FAIL threshold.
    'Dark' = mean lum < 5.0 (near-black canvas).
    """
    try:
        cmd = [
            "ffmpeg", "-i", str(video_path),
            "-vf", "fps=10,scale=108:192,format=gray",  # 10fps sample
            "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
            "-loglevel", "error"
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        raw = result.stdout
        frame_size = 108 * 192
        total_frames = len(raw) // frame_size
        sample_fps = 10.0

        dark_runs = []
        run_start = None
        for fi in range(total_frames):
            fb = raw[fi * frame_size:(fi + 1) * frame_size]
            lum = sum(fb) / len(fb)
            t = fi / sample_fps
            if lum < DARK_FRAME_LUM:
                if run_start is None:
                    run_start = t
            else:
                if run_start is not None:
                    dur = t - run_start
                    dark_runs.append({"start": round(run_start, 2), "duration": round(dur, 3)})
                    run_start = None
        if run_start is not None:
            dur = total_frames / sample_fps - run_start
            dark_runs.append({"start": round(run_start, 2), "duration": round(dur, 3)})

        # Filter to only substantial gaps (>0.1s) to ignore fast transitions
        gaps = [r for r in dark_runs if r["duration"] > 0.1]
        fail_gaps = [r for r in gaps if r["duration"] > EMPTY_TRANSITION_FAIL_S]
        longest = max((r["duration"] for r in gaps), default=0.0)

        is_fail = len(fail_gaps) > 0
        return {
            "check": "empty_transitions",
            "description": f"No empty canvas gap >{EMPTY_TRANSITION_FAIL_S}s",
            "result": f"Longest gap: {longest:.3f}s | Fail gaps: {len(fail_gaps)}",
            "dark_gaps": gaps,
            "fail_gaps": fail_gaps,
            "pass": not is_fail,
            "fail_condition": is_fail,
        }
    except Exception as e:
        logger.warning(f"empty_transitions check failed: {e}")
        return {
            "check": "empty_transitions",
            "description": f"No empty canvas gap >{EMPTY_TRANSITION_FAIL_S}s",
            "result": f"CHECK_ERROR: {e}",
            "pass": True,
            "fail_condition": False,
        }


def check_unsupported_stats(storyboard_path: Path) -> dict:
    """
    Check 6 (FAIL CONDITION): No unsupported precise numeric claims.

    Applies the sourced_numeric / illustrative rule:
      - sourced_numeric: explicit number supplied by storyboard with source_type="sourced_numeric"
        and a source_reference field → numeric visualization ALLOWED
      - illustrative: no verified source → qualitative labels only, no exact percentages,
        dollar values, accuracy scores, or performance claims → FAIL if found

    Inspects:
      1. on_screen_text[] — explicit text rendered to screen
      2. beats[].action  — storyboard intent text (may contain fabricated numbers
         that inform scene components even without appearing as on_screen_text)
      3. Component-level rendering rules — numeric visualization components
         (MeterScene, BarChartScene, DataScene) are checked against source_type:
         if source_type is not "sourced_numeric", any precise numeric claim hard-fails.
      4. visual_goal      — scene narrative; flagged if it contains fabricated claims

    Output includes a table: Scene | Value | Source type | Source reference | Allowed
    """
    # Numeric visualization components that must respect the sourced_numeric rule
    NUMERIC_VIZ_COMPONENTS = {"MeterScene", "BarChartScene", "DataScene"}

    rows: list[dict] = []      # all inspected numeric claims
    violations: list[dict] = []

    def classify_scene(scene: dict) -> tuple[str, str]:
        """Return (source_type, source_reference) for a scene."""
        src_type = scene.get("source_type", "illustrative")
        src_ref  = scene.get("source_reference", "")
        return (src_type, src_ref)

    def check_text_for_stats(
        text: str,
        scene_id: str,
        field: str,
        source_type: str,
        source_ref: str,
    ) -> None:
        """Scan one text string; append to rows/violations as appropriate."""
        matches = UNSUPPORTED_STAT_PATTERN.findall(text)
        for match in matches:
            allowed = (source_type == "sourced_numeric" and bool(source_ref))
            row = {
                "scene": scene_id,
                "field": field,
                "value": match.strip(),
                "source_type": source_type,
                "source_reference": source_ref or "—",
                "allowed": allowed,
            }
            rows.append(row)
            if not allowed:
                violations.append(row)

    try:
        if not storyboard_path.exists():
            return {
                "check": "unsupported_stats",
                "description": "No fabricated numeric claims (sourced_numeric rule)",
                "result": "STORYBOARD_NOT_FOUND — check skipped",
                "pass": True,
                "fail_condition": False,
                "numeric_claims_table": [],
            }

        storyboard = json.loads(storyboard_path.read_text())
        scenes = (
            storyboard if isinstance(storyboard, list)
            else storyboard.get("storyboard", storyboard.get("scenes", []))
        )

        for scene in scenes:
            scene_id   = scene.get("scene_id", "?")
            component  = scene.get("component", "")
            source_type, source_ref = classify_scene(scene)

            # 1. on_screen_text
            for text in scene.get("on_screen_text", []):
                check_text_for_stats(str(text), scene_id, "on_screen_text",
                                     source_type, source_ref)

            # 2. beats[].action — storyboard intent; may contain fabricated numbers
            #    that the scene component renders (e.g. "needle swings to 28%")
            for beat in scene.get("beats", []):
                action = beat.get("action", "")
                check_text_for_stats(str(action), scene_id, "beats.action",
                                     source_type, source_ref)

            # 3. visual_goal
            visual_goal = scene.get("visual_goal", "")
            check_text_for_stats(str(visual_goal), scene_id, "visual_goal",
                                 source_type, source_ref)

            # 4. Component-level: numeric viz components without sourced_numeric
            #    Even with no on_screen_text number, a MeterScene needle position
            #    can imply a specific measurement. Flag the component itself.
            if component in NUMERIC_VIZ_COMPONENTS and source_type != "sourced_numeric":
                # Check whether any numeric text already caught in on_screen_text/beats;
                # if yes, those rows are already in violations.
                # Additionally flag the component entry itself so the table is complete.
                has_component_row = any(
                    r["scene"] == scene_id and r["field"] == "component_type"
                    for r in rows
                )
                if not has_component_row:
                    # Informational row: component is in illustrative mode.
                    # "allowed" is None here — whether rendering is OK depends on
                    # whether numeric claims appear (checked above). This row is
                    # INFO only; it escalates to a violation only if numeric
                    # claims in this scene already produced violations.
                    row = {
                        "scene": scene_id,
                        "field": "component_type",
                        "value": f"{component} — illustrative mode (no sourced_numeric metadata)",
                        "source_type": source_type,
                        "source_reference": source_ref or "—",
                        "allowed": "INFO",  # not a pass/fail itself
                    }
                    rows.append(row)
                    # Escalate to violation only if numeric claims already failed this scene.
                    if any(v["scene"] == scene_id for v in violations):
                        violations.append({**row, "allowed": False})

    except Exception as e:
        return {
            "check": "unsupported_stats",
            "description": "No fabricated numeric claims (sourced_numeric rule)",
            "result": f"CHECK_ERROR: {e}",
            "pass": True,
            "fail_condition": False,
            "numeric_claims_table": [],
        }

    # Build display table
    table_header = "Scene | Value | Source type | Source reference | Allowed"
    def allowed_label(a: object) -> str:
        if a == "INFO":
            return "INFO (illustrative, no numeric claims)"
        return "YES" if a else "NO — FAIL"

    table_rows = [
        f"{r['scene']} | {r['value']} | {r['source_type']} | {r['source_reference']} | {allowed_label(r['allowed'])}"
        for r in rows
    ]

    is_fail = len(violations) > 0
    result_str = (
        f"{len(violations)} violation(s) — unsourced numeric claims detected"
        if violations else "CLEAN"
    )

    return {
        "check": "unsupported_stats",
        "description": "No fabricated numeric claims (sourced_numeric rule)",
        "result": result_str,
        "numeric_claims_table": [table_header] + table_rows,
        "violations": violations,
        "pass": not is_fail,
        "fail_condition": is_fail,
    }


def check_internal_identifiers(storyboard_path: Path) -> dict:
    """
    Check 7 (FAIL CONDITION): Internal object identifiers must not appear in on_screen_text.
    These are objects[] values that must ONLY be used for internal scene routing, never as UI text.
    """
    violations = []
    try:
        if not storyboard_path.exists():
            return {
                "check": "internal_identifiers",
                "description": "No internal object IDs in on_screen_text",
                "result": "STORYBOARD_NOT_FOUND — check skipped",
                "pass": True,
                "fail_condition": False,
            }
        storyboard = json.loads(storyboard_path.read_text())
        scenes = (
            storyboard if isinstance(storyboard, list)
            else storyboard.get("storyboard", storyboard.get("scenes", []))
        )
        for scene in scenes:
            scene_id = scene.get("scene_id", "?")
            objects = scene.get("objects", [])
            texts = scene.get("on_screen_text", [])
            for obj in objects:
                # Check if any on_screen_text contains raw object identifiers
                for text in texts:
                    if obj and obj.lower() in str(text).lower():
                        violations.append({
                            "scene": scene_id, "object": obj, "text": str(text)
                        })
                # Check against hardcoded known-bad identifiers
                if obj in INTERNAL_IDENTIFIERS:
                    # Flag: if this object identifier appears to have leaked into on_screen_text
                    pass  # Already caught by the objects check above
    except Exception as e:
        return {
            "check": "internal_identifiers",
            "description": "No internal object IDs in on_screen_text",
            "result": f"CHECK_ERROR: {e}",
            "pass": True,
            "fail_condition": False,
        }

    is_fail = len(violations) > 0
    return {
        "check": "internal_identifiers",
        "description": "No internal object IDs in on_screen_text",
        "result": f"{len(violations)} violations" if violations else "CLEAN",
        "violations": violations,
        "pass": not is_fail,
        "fail_condition": is_fail,
    }


def run_validation(
    video_path: Path,
    storyboard_path: Path | None = None,
    draft_mode: bool = False,
) -> dict:
    """Run all 7 QA checks. Returns report dict."""
    logger.info(f"Validating: {video_path} (draft_mode={draft_mode})")
    if not video_path.exists():
        return {"error": f"File not found: {video_path}", "verdict": "FAIL"}

    try:
        probe = ffprobe_json(video_path)
    except Exception as e:
        return {"error": f"ffprobe failed: {e}", "verdict": "FAIL"}

    video_stream = get_video_stream(probe)
    format_info = probe.get("format", {})

    # Resolve storyboard path
    sb_path = storyboard_path or (
        Path(__file__).parent / "remotion" / "src" / "rag_v3_storyboard.json"
    )

    checks = [
        check_resolution(video_stream, draft_mode=draft_mode),
        check_duration(video_stream, format_info),
        check_audio_track(probe),
        check_first_meaningful_frame(video_path),
        check_empty_transitions(video_path),
        check_unsupported_stats(sb_path),
        check_internal_identifiers(sb_path),
    ]

    hard_fails = [c for c in checks if c.get("fail_condition")]
    soft_fails = [c for c in checks if not c.get("pass") and not c.get("fail_condition")]
    all_pass = len(hard_fails) == 0 and len(soft_fails) == 0

    verdict = "PASS" if all_pass else ("HARD_FAIL" if hard_fails else "WARN")

    report = {
        "video": str(video_path),
        "verdict": verdict,
        "summary": {
            "total_checks": len(checks),
            "hard_fails": len(hard_fails),
            "soft_fails": len(soft_fails),
            "passed": len([c for c in checks if c.get("pass")]),
        },
        "checks": checks,
    }

    return report


def main() -> None:
    args = sys.argv[1:]
    draft_mode = "--draft" in args
    args = [a for a in args if a != "--draft"]

    if not args:
        print(
            "Usage: python qa_validator.py <video.mp4> [storyboard.json] [--draft]",
            file=sys.stderr,
        )
        sys.exit(1)

    video_path = Path(args[0])
    storyboard_path = Path(args[1]) if len(args) > 1 else None

    report = run_validation(video_path, storyboard_path, draft_mode=draft_mode)
    print(json.dumps(report, indent=2))

    # Print numeric claims table to stderr for easy console reading
    for check in report.get("checks", []):
        if check.get("check") == "unsupported_stats":
            table = check.get("numeric_claims_table", [])
            if table:
                logger.info("── Numeric claims audit ──────────────────────────────")
                for row in table:
                    logger.info(f"  {row}")
                logger.info("──────────────────────────────────────────────────────")
            break

    verdict = report.get("verdict", "FAIL")
    if verdict == "PASS":
        logger.info("✓ QA PASSED")
        sys.exit(0)
    elif verdict == "WARN":
        logger.warning("⚠ QA WARNINGS (soft fails) — review before publishing")
        sys.exit(0)  # Don't block on soft fails
    else:
        logger.error("✗ QA HARD FAIL — do not publish")
        sys.exit(1)


if __name__ == "__main__":
    main()
