"""
timeline_qa_guard.py — Full-timeline visual QA for AI Bytes Shorts.

Two checks:

1. BLANK-SPAN CHECK
   Sample every 0.5s across the video. Detect contiguous spans > 0.75s where
   the frame has no meaningful visual content (theme-aware: cinematic-dark bg
   is near-black, bright-workspace bg is near-white). Background texture,
   subtle glow, and faint scattered elements do NOT count as content.

2. STATIC-SCENE CHECK
   For scenes > 5s, sample at 1s intervals and compute frame-to-frame pixel
   difference. Flag any 2s+ window with < 1% pixel change. Explicit hold
   intervals (takeaway_hold, cta_hold, hold) are exempt.

Usage:
    python timeline_qa_guard.py <video.mp4> <storyboard.json>

Exit code 0 = PASS, 1 = FAIL.
"""
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────

SAMPLE_W = 108
SAMPLE_H = 192
FRAME_SIZE = SAMPLE_W * SAMPLE_H

SAMPLE_INTERVAL_S = 0.5
BLANK_SPAN_THRESHOLD_S = 0.75

# Content detection: a pixel is "content" when its luminance differs from
# the dominant background by more than CONTENT_DELTA levels.
CONTENT_DELTA = 18

# Dark themes need a higher content ratio because faint glows can produce
# a small pixel delta without being perceptually meaningful.
MIN_CONTENT_RATIO_DARK = 0.020
MIN_CONTENT_RATIO_LIGHT = 0.008

# Static-scene check
STATIC_MIN_SCENE_DURATION_S = 5.0
STATIC_SAMPLE_INTERVAL_S = 1.0
STATIC_CHANGE_THRESHOLD = 0.01  # 1% pixel change
STATIC_WINDOW_S = 2.0

# Hold-type scenes are exempt from static check
HOLD_SCENE_TYPES = {"TAKEAWAY", "CTA"}
HOLD_COMPONENTS = {"TakeawayScene", "CTAScene"}

FPS = 30.0


# ── Frame extraction ──────────────────────────────────────────────────────

def _extract_frame(video_path: Path, timestamp_s: float) -> Optional[bytes]:
    cmd = [
        "ffmpeg",
        "-ss", f"{timestamp_s:.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-vf", f"scale={SAMPLE_W}:{SAMPLE_H},format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray",
        "pipe:1",
        "-loglevel", "error",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        if len(result.stdout) < FRAME_SIZE:
            return None
        return result.stdout[:FRAME_SIZE]
    except Exception as e:
        logger.warning(f"Frame extract failed at t={timestamp_s:.2f}s: {e}")
        return None


def _frame_has_content(pixels: bytes, is_dark_theme: bool) -> tuple[bool, float]:
    histogram = [0] * 256
    for value in pixels:
        histogram[value] += 1
    background = max(range(256), key=histogram.__getitem__)
    lo = background - CONTENT_DELTA
    hi = background + CONTENT_DELTA
    content_px = sum(
        count for value, count in enumerate(histogram)
        if value < lo or value > hi
    )
    ratio = content_px / FRAME_SIZE
    threshold = MIN_CONTENT_RATIO_DARK if is_dark_theme else MIN_CONTENT_RATIO_LIGHT
    return ratio >= threshold, ratio


def _frame_diff_ratio(a: bytes, b: bytes) -> float:
    changed = sum(1 for x, y in zip(a, b) if abs(x - y) > CONTENT_DELTA)
    return changed / FRAME_SIZE


# ── Storyboard loading ────────────────────────────────────────────────────

def _load_storyboard(sb_path: Path) -> tuple[list[dict], bool]:
    data = json.loads(sb_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, True
    scenes = data.get("storyboard", [])
    ad = data.get("art_direction", {})
    ad_id = ad.get("id", "") if isinstance(ad, dict) else str(ad or "")
    is_dark = "dark" in ad_id.lower() or "cinematic" in ad_id.lower()
    if not ad_id:
        is_dark = True
    return scenes, is_dark


# ── Blank-span check ─────────────────────────────────────────────────────

def check_blank_spans(
    video_path: Path,
    is_dark_theme: bool,
    duration_s: float,
    scenes: list[dict],
) -> dict:
    timestamps = []
    t = 0.0
    while t <= duration_s:
        timestamps.append(round(t, 3))
        t += SAMPLE_INTERVAL_S

    sample_results = []
    for ts in timestamps:
        pixels = _extract_frame(video_path, ts)
        if pixels is None:
            sample_results.append({"t": ts, "has_content": False, "ratio": 0.0})
            continue
        has_content, ratio = _frame_has_content(pixels, is_dark_theme)
        sample_results.append({"t": ts, "has_content": has_content, "ratio": round(ratio, 4)})

    # Find contiguous blank spans
    blank_spans = []
    span_start = None
    for sr in sample_results:
        if not sr["has_content"]:
            if span_start is None:
                span_start = sr["t"]
        else:
            if span_start is not None:
                span_end = sr["t"]
                span_dur = span_end - span_start
                if span_dur >= BLANK_SPAN_THRESHOLD_S:
                    scene_id = _scene_at_time(scenes, span_start)
                    blank_spans.append({
                        "start_s": round(span_start, 3),
                        "end_s": round(span_end, 3),
                        "duration_s": round(span_dur, 3),
                        "scene_id": scene_id,
                    })
                span_start = None
    if span_start is not None:
        span_end = timestamps[-1] + SAMPLE_INTERVAL_S
        span_dur = span_end - span_start
        if span_dur >= BLANK_SPAN_THRESHOLD_S:
            blank_spans.append({
                "start_s": round(span_start, 3),
                "end_s": round(span_end, 3),
                "duration_s": round(span_dur, 3),
                "scene_id": _scene_at_time(scenes, span_start),
            })

    return {
        "verdict": "FAIL" if blank_spans else "PASS",
        "blank_spans": blank_spans,
        "total_blank_s": round(sum(s["duration_s"] for s in blank_spans), 3),
        "samples_taken": len(timestamps),
        "samples_with_content": sum(1 for s in sample_results if s["has_content"]),
        "theme": "dark" if is_dark_theme else "light",
    }


def _scene_at_time(scenes: list[dict], t: float) -> str:
    cursor = 0.0
    for s in scenes:
        dur = s.get("duration_seconds", 0)
        if cursor <= t < cursor + dur:
            return f"s{s.get('scene_id', '?'):02d}" if isinstance(s.get("scene_id"), int) else str(s.get("scene_id", "?"))
        cursor += dur
    return "?"


# ── Static-scene check ───────────────────────────────────────────────────

def check_static_scenes(
    video_path: Path,
    scenes: list[dict],
) -> dict:
    cursor = 0.0
    scene_timings = []
    for s in scenes:
        dur = s.get("duration_seconds", 0)
        scene_timings.append({
            "scene_id": s.get("scene_id", "?"),
            "component": s.get("component", "?"),
            "scene_type": s.get("scene_type", "?"),
            "start_s": cursor,
            "end_s": cursor + dur,
            "duration_s": dur,
            "beats": s.get("beats", []),
        })
        cursor += dur

    static_violations = []
    for st in scene_timings:
        if st["duration_s"] < STATIC_MIN_SCENE_DURATION_S:
            continue
        if st["scene_type"] in HOLD_SCENE_TYPES:
            continue
        if st["component"] in HOLD_COMPONENTS:
            continue

        # Check for explicit hold beats or final-state beats
        has_hold_beat = any(
            any(kw in (b.get("action", "") + " " + b.get("focus", "")).lower()
                for kw in ("hold", "lock", "stay", "remain", "visible", "pulse"))
            for b in st["beats"]
        )

        # Sample at 1s intervals within this scene
        sample_times = []
        t = st["start_s"] + 0.5
        while t < st["end_s"] - 0.3:
            sample_times.append(t)
            t += STATIC_SAMPLE_INTERVAL_S

        if len(sample_times) < 3:
            continue

        frames_data = []
        for ts in sample_times:
            px = _extract_frame(video_path, ts)
            frames_data.append((ts, px))

        # Check for static windows — only flag if the window falls outside
        # all beat boundaries (dead time) or has no beats at all.
        window_samples = int(STATIC_WINDOW_S / STATIC_SAMPLE_INTERVAL_S)

        def _window_covered_by_beat(w_start: float, w_end: float) -> bool:
            local_mid = ((w_start + w_end) / 2) - st["start_s"]
            for b in st["beats"]:
                if b.get("start", 0) <= local_mid <= b.get("end", 0):
                    return True
            return False

        for i in range(len(frames_data) - window_samples):
            window_static = True
            for j in range(i, i + window_samples):
                if frames_data[j][1] is None or frames_data[j + 1][1] is None:
                    window_static = False
                    break
                diff = _frame_diff_ratio(frames_data[j][1], frames_data[j + 1][1])
                if diff >= STATIC_CHANGE_THRESHOLD:
                    window_static = False
                    break

            if not window_static:
                continue
            if has_hold_beat:
                continue

            window_start = frames_data[i][0]
            window_end = frames_data[i + window_samples][0]

            if _window_covered_by_beat(window_start, window_end):
                continue

            sid = st["scene_id"]
            sid_str = f"s{sid:02d}" if isinstance(sid, int) else str(sid)
            static_violations.append({
                "scene_id": sid_str,
                "component": st["component"],
                "window_start_s": round(window_start, 3),
                "window_end_s": round(window_end, 3),
                "duration_s": round(window_end - window_start, 3),
            })

    return {
        "verdict": "FAIL" if static_violations else "PASS",
        "static_violations": static_violations,
        "scenes_checked": sum(
            1 for st in scene_timings
            if st["duration_s"] >= STATIC_MIN_SCENE_DURATION_S
            and st["scene_type"] not in HOLD_SCENE_TYPES
            and st["component"] not in HOLD_COMPONENTS
        ),
    }


# ── Combined guard ───────────────────────────────────────────────────────

def run_timeline_qa(
    video_path: Path,
    storyboard_path: Path,
) -> dict:
    if not video_path.exists():
        return {"error": f"Video not found: {video_path}", "verdict": "FAIL"}
    if not storyboard_path.exists():
        return {"error": f"Storyboard not found: {storyboard_path}", "verdict": "FAIL"}

    scenes, is_dark = _load_storyboard(storyboard_path)
    if not scenes:
        return {"error": "No scenes in storyboard", "verdict": "FAIL"}

    total_dur = sum(s.get("duration_seconds", 0) for s in scenes)

    logger.info(
        f"Timeline QA: {video_path.name}, {len(scenes)} scenes, "
        f"{'dark' if is_dark else 'light'} theme, {total_dur:.1f}s planned"
    )

    blank_report = check_blank_spans(video_path, is_dark, total_dur, scenes)
    static_report = check_static_scenes(video_path, scenes)

    overall = "PASS"
    if blank_report["verdict"] == "FAIL":
        overall = "FAIL"
    if static_report["verdict"] == "FAIL":
        overall = "FAIL"

    report = {
        "video": str(video_path),
        "storyboard": str(storyboard_path),
        "verdict": overall,
        "blank_span_check": blank_report,
        "static_scene_check": static_report,
    }

    if overall == "PASS":
        logger.info("TIMELINE_QA=PASS — no blank spans or static violations")
    else:
        blanks = blank_report.get("blank_spans", [])
        statics = static_report.get("static_violations", [])
        logger.error(
            f"TIMELINE_QA=FAIL — "
            f"{len(blanks)} blank span(s), {len(statics)} static violation(s)"
        )
        for b in blanks:
            logger.error(
                f"  BLANK: {b['start_s']:.1f}–{b['end_s']:.1f}s "
                f"({b['duration_s']:.1f}s) in {b['scene_id']}"
            )
        for sv in statics:
            logger.error(
                f"  STATIC: {sv['window_start_s']:.1f}–{sv['window_end_s']:.1f}s "
                f"({sv['duration_s']:.1f}s) in {sv['scene_id']} ({sv['component']})"
            )

    return report


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        print(
            "Usage: python timeline_qa_guard.py <video.mp4> <storyboard.json>",
            file=sys.stderr,
        )
        sys.exit(1)

    video_path = Path(args[0])
    storyboard_path = Path(args[1])

    report = run_timeline_qa(video_path, storyboard_path)
    print(json.dumps(report, indent=2))

    sys.exit(0 if report.get("verdict") == "PASS" else 1)


if __name__ == "__main__":
    main()
