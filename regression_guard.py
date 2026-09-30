"""
regression_guard.py — Per-scene luminance regression check for AI Bytes Shorts

For each scene in the storyboard, samples one frame at the scene midpoint and
measures mean luminance. Fails if:
  - Multiple consecutive scenes render only background (luminance < threshold)
  - Longest visually empty interval > 2.0s
  - Rendered scene count (scenes with content) < expected count

Usage:
    python regression_guard.py <video.mp4> [storyboard.json]

Exit code 0 = PASS, 1 = FAIL.
"""
import json
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Luminance threshold: below this = scene renders only background (#050510 ≈ lum 2)
SCENE_LUM_THRESHOLD = 5.0

# Fail if this many consecutive scenes are dark
CONSECUTIVE_DARK_FAIL = 2

# Fail if longest empty interval exceeds this many seconds
LONGEST_EMPTY_FAIL_S = 2.0

# Expected number of visually rendered scenes (from storyboard)
EXPECTED_SCENE_COUNT = 11

FPS = 30.0


def extract_frame_luminance(video_path: Path, timestamp_s: float) -> float | None:
    """Extract a single frame at timestamp_s and return mean luminance (0–255 scale)."""
    cmd = [
        "ffmpeg",
        "-ss", str(timestamp_s),
        "-i", str(video_path),
        "-frames:v", "1",
        "-vf", "scale=108:192,format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray",
        "pipe:1",
        "-loglevel", "error",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        raw = result.stdout
        frame_size = 108 * 192
        if len(raw) < frame_size:
            return None
        frame_bytes = raw[:frame_size]
        return sum(frame_bytes) / len(frame_bytes)
    except Exception as e:
        logger.warning(f"Frame extract failed at t={timestamp_s:.2f}s: {e}")
        return None


def run_regression_guard(
    video_path: Path,
    storyboard_path: Path | None = None,
) -> dict:
    """
    For each storyboard scene, sample the mid-frame luminance.
    Return a report with per-scene results and overall pass/fail.
    """
    if not video_path.exists():
        return {"error": f"File not found: {video_path}", "verdict": "FAIL"}

    # Load storyboard
    sb_path = storyboard_path or (
        Path(__file__).parent / "remotion" / "src" / "rag_v3_storyboard.json"
    )
    if not sb_path.exists():
        return {"error": f"Storyboard not found: {sb_path}", "verdict": "FAIL"}

    storyboard = json.loads(sb_path.read_text())
    scenes = storyboard.get("storyboard", storyboard if isinstance(storyboard, list) else [])

    logger.info(f"Checking {len(scenes)} scenes in {video_path.name}")

    # Build scene timing table
    current_frame = 0
    scene_timings = []
    for scene in scenes:
        dur_s = scene.get("duration_seconds", 0)
        dur_frames = round(dur_s * FPS)
        start_s = current_frame / FPS
        mid_s = start_s + dur_s / 2
        scene_timings.append({
            "scene_id": scene.get("scene_id", "?"),
            "component": scene.get("component", "?"),
            "start_s": round(start_s, 3),
            "end_s": round(start_s + dur_s, 3),
            "duration_s": round(dur_s, 3),
            "mid_s": round(mid_s, 3),
        })
        current_frame += dur_frames

    # Sample luminance at each scene midpoint
    scene_results = []
    for t in scene_timings:
        lum = extract_frame_luminance(video_path, t["mid_s"])
        has_content = lum is not None and lum >= SCENE_LUM_THRESHOLD
        result = {
            **t,
            "mid_luminance": round(lum, 2) if lum is not None else None,
            "has_content": has_content,
        }
        logger.info(
            f"  {t['scene_id']} @ {t['mid_s']:.2f}s: "
            f"lum={lum:.2f if lum is not None else 'ERR'} "
            f"{'✓' if has_content else '✗ DARK'}"
        )
        scene_results.append(result)

    # Check 1: consecutive dark scenes
    max_consecutive_dark = 0
    consecutive_dark = 0
    consecutive_dark_scenes = []
    worst_run_start = None
    for r in scene_results:
        if not r["has_content"]:
            if consecutive_dark == 0:
                worst_run_start = r["scene_id"]
            consecutive_dark += 1
            consecutive_dark_scenes.append(r["scene_id"])
            max_consecutive_dark = max(max_consecutive_dark, consecutive_dark)
        else:
            consecutive_dark = 0

    consecutive_fail = max_consecutive_dark >= CONSECUTIVE_DARK_FAIL

    # Check 2: longest visually empty interval (continuous time without content)
    # Build a list of empty time ranges based on scene midpoints marked dark
    # (approximate: treat whole scene as empty if midpoint is dark)
    empty_intervals = []
    empty_start = None
    for r in scene_results:
        if not r["has_content"]:
            if empty_start is None:
                empty_start = r["start_s"]
        else:
            if empty_start is not None:
                empty_intervals.append(r["start_s"] - empty_start)
                empty_start = None
    if empty_start is not None:
        empty_intervals.append(scene_timings[-1]["end_s"] - empty_start)

    longest_empty = max(empty_intervals, default=0.0)
    empty_interval_fail = longest_empty > LONGEST_EMPTY_FAIL_S

    # Check 3: expected vs rendered scene count
    rendered_count = sum(1 for r in scene_results if r["has_content"])
    count_fail = rendered_count < EXPECTED_SCENE_COUNT

    # Summary
    total_fail = consecutive_fail or empty_interval_fail or count_fail
    verdict = "FAIL" if total_fail else "PASS"

    dark_scene_ids = [r["scene_id"] for r in scene_results if not r["has_content"]]

    report = {
        "video": str(video_path),
        "verdict": verdict,
        "expected_scenes": EXPECTED_SCENE_COUNT,
        "rendered_scenes": rendered_count,
        "dark_scenes": dark_scene_ids,
        "max_consecutive_dark": max_consecutive_dark,
        "longest_empty_interval_s": round(longest_empty, 3),
        "checks": {
            "consecutive_dark": {
                "fail": consecutive_fail,
                "threshold": CONSECUTIVE_DARK_FAIL,
                "actual": max_consecutive_dark,
                "description": f"Max {CONSECUTIVE_DARK_FAIL} consecutive dark scenes allowed",
            },
            "longest_empty": {
                "fail": empty_interval_fail,
                "threshold_s": LONGEST_EMPTY_FAIL_S,
                "actual_s": round(longest_empty, 3),
                "description": f"Longest empty interval ≤{LONGEST_EMPTY_FAIL_S}s",
            },
            "scene_count": {
                "fail": count_fail,
                "expected": EXPECTED_SCENE_COUNT,
                "actual": rendered_count,
                "description": f"All {EXPECTED_SCENE_COUNT} scenes must have visible content",
            },
        },
        "scene_results": scene_results,
    }

    return report


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(
            "Usage: python regression_guard.py <video.mp4> [storyboard.json]",
            file=sys.stderr,
        )
        sys.exit(1)

    video_path = Path(args[0])
    storyboard_path = Path(args[1]) if len(args) > 1 else None

    report = run_regression_guard(video_path, storyboard_path)
    print(json.dumps(report, indent=2))

    verdict = report.get("verdict", "FAIL")
    if verdict == "PASS":
        logger.info("✓ REGRESSION GUARD PASSED — all scenes render content")
        sys.exit(0)
    else:
        logger.error(
            f"✗ REGRESSION GUARD FAILED — "
            f"{report.get('rendered_scenes')}/{report.get('expected_scenes')} scenes rendered, "
            f"longest empty: {report.get('longest_empty_interval_s')}s"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
