"""
storyboard_qa.py — Generic QA checks for visual storyboards.

Runs pre-render validation on storyboard JSON to catch perceptual
defects before paid asset generation.
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def check_adjacent_asset_repetition(
    storyboard: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flag adjacent visual beats that reuse the same source asset with a hard cut.

    Two adjacent beats must NOT create a hard scene transition back to the same
    source asset unless the second treatment represents a genuinely different
    semantic state. A crop/pan/zoom alone does not qualify as a new visual beat.

    Returns a list of findings (empty = pass).
    """
    findings: list[dict[str, Any]] = []

    for i in range(1, len(storyboard)):
        prev = storyboard[i - 1]
        curr = storyboard[i]

        prev_src = _extract_asset_id(prev)
        curr_src = _extract_asset_id(curr)

        if prev_src is None or curr_src is None:
            continue

        if prev_src != curr_src:
            continue

        prev_motion = _extract_motion(prev)
        curr_motion = _extract_motion(curr)
        prev_component = prev.get("component", "")
        curr_component = curr.get("component", "")

        if prev_component != curr_component:
            continue

        finding = {
            "type": "ADJACENT_ASSET_REPETITION",
            "beat_a": prev.get("scene_id"),
            "beat_b": curr.get("scene_id"),
            "asset_id": curr_src,
            "motion_a": prev_motion,
            "motion_b": curr_motion,
            "message": (
                f"VB{prev.get('scene_id')} and VB{curr.get('scene_id')} share "
                f"asset '{curr_src}' with a hard scene boundary. "
                f"Motions: {prev_motion} → {curr_motion}. "
                f"Consider: (1) merge into one continuous beat, "
                f"(2) add a meaningful overlay/reveal, "
                f"(3) use a different asset, or "
                f"(4) verify the semantic transformation is sufficient."
            ),
        }
        findings.append(finding)
        logger.warning(f"ADJACENT_ASSET_REPETITION: {finding['message']}")

    return findings


def _extract_asset_id(scene: dict[str, Any]) -> str | None:
    """Extract the source asset identifier from a storyboard scene."""
    data = scene.get("data", {})
    if not isinstance(data, dict):
        return None
    src = data.get("src", "")
    if not src:
        beat_meta = scene.get("beat_meta", {})
        if isinstance(beat_meta, dict):
            return beat_meta.get("asset_ref")
        return None
    return Path(src).stem


def _extract_motion(scene: dict[str, Any]) -> str:
    """Extract the motion type from a storyboard scene."""
    data = scene.get("data", {})
    if isinstance(data, dict):
        return data.get("motion", "none")
    return "none"


def run_qa(storyboard_path: Path) -> dict[str, Any]:
    """Run all storyboard QA checks. Returns structured results."""
    storyboard_data = json.loads(storyboard_path.read_text(encoding="utf-8"))
    scenes = storyboard_data.get("storyboard", [])

    results: dict[str, Any] = {
        "storyboard_path": str(storyboard_path),
        "total_beats": len(scenes),
        "checks": {},
    }

    adj_findings = check_adjacent_asset_repetition(scenes)
    results["checks"]["ADJACENT_ASSET_REPETITION"] = {
        "status": "PASS" if not adj_findings else "FAIL",
        "findings": adj_findings,
    }

    total_duration = sum(s.get("duration_seconds", 0) for s in scenes)
    results["total_duration_s"] = total_duration

    results["overall"] = "PASS" if all(
        c["status"] == "PASS" for c in results["checks"].values()
    ) else "FAIL"

    return results
