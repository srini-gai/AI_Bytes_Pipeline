"""
regression_guard.py — Per-scene visible-content regression check for AI Bytes Shorts

For each scene in the storyboard, samples one frame at the scene midpoint and
decides whether it shows real content or only background. Fails if:
  - Multiple consecutive scenes render only background
  - Longest visually empty interval > 2.0s
  - Rendered scene count (scenes with content) < expected count

Theme-neutral content test (works for light and dark Art Director worlds):
the frame's dominant luminance is taken as its background; a frame has content
when enough pixels differ clearly from that background. A flat off-white
(bright-workspace) or flat near-black (cinematic-dark) frame is "empty" either way.

The expected scene count comes from the storyboard / render-props file — there
is no hardcoded episode count.

Usage:
    python regression_guard.py <video.mp4> [storyboard_or_props.json]

Exit code 0 = PASS, 1 = FAIL.
"""
import json
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Sample resolution (grayscale)
SAMPLE_W = 108
SAMPLE_H = 192

# A pixel is "content" when its luminance differs from the frame's dominant
# (background) luminance by more than this many levels (0–255 scale)...
CONTENT_DELTA = 16
# ...and a frame has content when at least this share of pixels are content.
MIN_CONTENT_RATIO = 0.005

# Fail if this many consecutive scenes are background-only
CONSECUTIVE_DARK_FAIL = 2

# Fail if longest empty interval exceeds this many seconds
LONGEST_EMPTY_FAIL_S = 2.0

FPS = 30.0


def load_scenes(sb_path: Path) -> tuple[list[dict], str | None]:
    """
    Load scenes from a storyboard doc, a bare storyboard list, or render props.
    Returns (scenes, art_direction_id_or_None).
    """
    data = json.loads(sb_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, None
    scenes = data.get("storyboard", [])
    ad = data.get("art_direction")
    ad_id = ad.get("id") if isinstance(ad, dict) else ad
    return (scenes if isinstance(scenes, list) else []), (str(ad_id) if ad_id else None)


def frame_content_stats(pixels: bytes) -> dict:
    """
    Theme-neutral content measure for one grayscale frame.
    Background = most common luminance; content = pixels far from it.
    """
    histogram = [0] * 256
    for value in pixels:
        histogram[value] += 1
    background = max(range(256), key=histogram.__getitem__)
    lo, hi = background - CONTENT_DELTA, background + CONTENT_DELTA
    content_px = sum(count for value, count in enumerate(histogram) if value < lo or value > hi)
    ratio = content_px / len(pixels) if pixels else 0.0
    return {
        "mean_luminance": sum(v * c for v, c in enumerate(histogram)) / len(pixels) if pixels else 0.0,
        "background_luminance": background,
        "content_ratio": ratio,
        "has_content": ratio >= MIN_CONTENT_RATIO,
    }


def extract_frame(video_path: Path, timestamp_s: float) -> bytes | None:
    """Extract one grayscale frame at timestamp_s as raw bytes."""
    cmd = [
        "ffmpeg",
        "-ss", str(timestamp_s),
        "-i", str(video_path),
        "-frames:v", "1",
        "-vf", f"scale={SAMPLE_W}:{SAMPLE_H},format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray",
        "pipe:1",
        "-loglevel", "error",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        frame_size = SAMPLE_W * SAMPLE_H
        if len(result.stdout) < frame_size:
            return None
        return result.stdout[:frame_size]
    except Exception as e:
        logger.warning(f"Frame extract failed at t={timestamp_s:.2f}s: {e}")
        return None


def run_regression_guard(
    video_path: Path,
    storyboard_path: Path | None = None,
) -> dict:
    """
    For each storyboard scene, test the mid-frame for visible content.
    Return a report with per-scene results and overall pass/fail.
    """
    if not video_path.exists():
        return {"error": f"File not found: {video_path}", "verdict": "FAIL"}

    if storyboard_path is None:
        storyboard_path = Path(__file__).parent / "remotion" / "src" / "rag_v3_storyboard.json"
        logger.warning(
            f"No storyboard given — using RAG reference storyboard {storyboard_path.name}. "
            f"Pass the episode's storyboard or render props for any other episode."
        )
    if not storyboard_path.exists():
        return {"error": f"Storyboard not found: {storyboard_path}", "verdict": "FAIL"}

    scenes, art_direction = load_scenes(storyboard_path)
    if not scenes:
        return {"error": f"No scenes in {storyboard_path}", "verdict": "FAIL"}
    expected_count = len(scenes)

    logger.info(
        f"Checking {expected_count} scenes in {video_path.name} "
        f"(art_direction={art_direction or 'legacy/none'})"
    )

    # Build scene timing table
    current_frame = 0
    scene_timings = []
    for scene in scenes:
        dur_s = scene.get("duration_seconds", 0)
        dur_frames = round(dur_s * FPS)
        start_s = current_frame / FPS
        scene_timings.append({
            "scene_id": scene.get("scene_id", "?"),
            "component": scene.get("component", "?"),
            "start_s": round(start_s, 3),
            "end_s": round(start_s + dur_s, 3),
            "duration_s": round(dur_s, 3),
            "mid_s": round(start_s + dur_s / 2, 3),
        })
        current_frame += dur_frames

    # Test each scene midpoint for content
    scene_results = []
    for t in scene_timings:
        pixels = extract_frame(video_path, t["mid_s"])
        stats = frame_content_stats(pixels) if pixels else None
        has_content = bool(stats and stats["has_content"])
        scene_results.append({
            **t,
            "mid_luminance": round(stats["mean_luminance"], 2) if stats else None,
            "background_luminance": stats["background_luminance"] if stats else None,
            "content_ratio": round(stats["content_ratio"], 4) if stats else None,
            "has_content": has_content,
        })
        ratio_str = f"{stats['content_ratio']:.3f}" if stats else "ERR"
        logger.info(
            f"  {t['scene_id']} @ {t['mid_s']:.2f}s: content={ratio_str} "
            f"{'✓' if has_content else '✗ EMPTY'}"
        )

    # Check 1: consecutive background-only scenes
    max_consecutive_dark = 0
    consecutive_dark = 0
    for r in scene_results:
        if not r["has_content"]:
            consecutive_dark += 1
            max_consecutive_dark = max(max_consecutive_dark, consecutive_dark)
        else:
            consecutive_dark = 0
    consecutive_fail = max_consecutive_dark >= CONSECUTIVE_DARK_FAIL

    # Check 2: longest visually empty interval
    # (approximate: treat whole scene as empty if its midpoint is empty)
    empty_intervals = []
    empty_start = None
    for r in scene_results:
        if not r["has_content"]:
            if empty_start is None:
                empty_start = r["start_s"]
        elif empty_start is not None:
            empty_intervals.append(r["start_s"] - empty_start)
            empty_start = None
    if empty_start is not None:
        empty_intervals.append(scene_timings[-1]["end_s"] - empty_start)
    longest_empty = max(empty_intervals, default=0.0)
    empty_interval_fail = longest_empty > LONGEST_EMPTY_FAIL_S

    # Check 3: expected (from storyboard) vs rendered scene count
    rendered_count = sum(1 for r in scene_results if r["has_content"])
    count_fail = rendered_count < expected_count

    verdict = "FAIL" if (consecutive_fail or empty_interval_fail or count_fail) else "PASS"

    return {
        "video": str(video_path),
        "storyboard": str(storyboard_path),
        "art_direction": art_direction,
        "verdict": verdict,
        "expected_scenes": expected_count,
        "rendered_scenes": rendered_count,
        "dark_scenes": [r["scene_id"] for r in scene_results if not r["has_content"]],
        "max_consecutive_dark": max_consecutive_dark,
        "longest_empty_interval_s": round(longest_empty, 3),
        "checks": {
            "consecutive_dark": {
                "fail": consecutive_fail,
                "threshold": CONSECUTIVE_DARK_FAIL,
                "actual": max_consecutive_dark,
                "description": f"Max {CONSECUTIVE_DARK_FAIL} consecutive background-only scenes allowed",
            },
            "longest_empty": {
                "fail": empty_interval_fail,
                "threshold_s": LONGEST_EMPTY_FAIL_S,
                "actual_s": round(longest_empty, 3),
                "description": f"Longest empty interval ≤{LONGEST_EMPTY_FAIL_S}s",
            },
            "scene_count": {
                "fail": count_fail,
                "expected": expected_count,
                "actual": rendered_count,
                "description": f"All {expected_count} storyboard scenes must have visible content",
            },
        },
        "scene_results": scene_results,
    }


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(
            "Usage: python regression_guard.py <video.mp4> [storyboard_or_props.json]",
            file=sys.stderr,
        )
        sys.exit(1)

    video_path = Path(args[0])
    storyboard_path = Path(args[1]) if len(args) > 1 else None

    report = run_regression_guard(video_path, storyboard_path)
    print(json.dumps(report, indent=2))

    if report.get("verdict") == "PASS":
        logger.info("✓ REGRESSION GUARD PASSED — all scenes render content")
        sys.exit(0)
    logger.error(
        f"✗ REGRESSION GUARD FAILED — "
        f"{report.get('rendered_scenes')}/{report.get('expected_scenes')} scenes rendered, "
        f"longest empty: {report.get('longest_empty_interval_s')}s"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
