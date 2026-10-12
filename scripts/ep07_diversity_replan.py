"""
EP07 Diversity Re-plan — re-generate storyboard with diversity-aware planning.

Uses locked canonical narration, Voice B (47.7s), and timestamps.
The diversity gate will compare against the EP06 fingerprint and require
different component-family composition or GENERATED beats.

Usage:
    python scripts/ep07_diversity_replan.py                # full: plan + render + assemble
    python scripts/ep07_diversity_replan.py --plan-only     # storyboard only (no render)
    python scripts/ep07_diversity_replan.py --render-only   # render + assemble (storyboard must exist)
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("ep07_replan")

EPISODE = 7
WEEK = 9
EP_DIR = PROJECT_ROOT / "output" / "week_09" / "ep07"
SCRIPT_PATH = EP_DIR / "ep07_script_EN.json"
STORYBOARD_PATH = EP_DIR / "ep07_storyboard_EN.json"
VOICE_PATH = EP_DIR / "ep07_voice_EN.mp3"
VOICE_DURATION = 47.7
ASSET_STAGING = PROJECT_ROOT / "remotion" / "public" / "assets" / "ep07"


def archive_original_storyboard() -> Path | None:
    if not STORYBOARD_PATH.exists():
        return None
    archive = EP_DIR / "ep07_storyboard_EN_pre_diversity.json"
    shutil.copy2(STORYBOARD_PATH, archive)
    logger.info(f"Archived original storyboard -> {archive}")
    STORYBOARD_PATH.unlink()
    logger.info(f"Deleted cached storyboard to force re-generation")
    return archive


def run_visual_director() -> dict:
    from agents.visual_director_agent import run as vda_run

    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    logger.info(f"Running Visual Director v4.2 with diversity gate (voice={VOICE_DURATION}s)")

    result = vda_run(
        script=script,
        episode=EPISODE,
        week=WEEK,
        lang="en",
        voice_duration=VOICE_DURATION,
    )

    if not result.get("success"):
        raise RuntimeError(f"Visual Director failed: {result}")

    scenes = result["storyboard"]
    diversity = result.get("diversity_gate", {})
    logger.info(
        f"Storyboard generated: {len(scenes)} scenes, "
        f"score={result['visual_complexity'].get('visual_first_score', 0)}, "
        f"diversity_pass={diversity.get('pass', 'N/A')}"
    )
    return result


def run_mode_router() -> dict:
    from agents.visual_mode_router import route_storyboard
    summary = route_storyboard(STORYBOARD_PATH)
    logger.info(
        f"Mode routing: {summary['episode_mode']} "
        f"({summary['native_beats']}N / {summary['generated_beats']}G)"
    )
    return summary


def build_beat_map() -> dict | None:
    data = json.loads(STORYBOARD_PATH.read_text(encoding="utf-8"))
    scenes = data.get("storyboard", [])
    generated = [s for s in scenes if s.get("visual_mode") == "GENERATED"]
    if not generated:
        logger.info("No GENERATED beats — skipping beat map / fal generation")
        return None

    hero_images = []
    hero_clips = []
    for s in generated:
        sid = s["scene_id"]
        dur = s.get("duration_seconds", 5.0)
        prompt = s.get("visual_goal", s.get("animation", ""))
        if dur <= 4.0:
            hero_images.append({
                "id": f"i{sid}",
                "scene_id": sid,
                "prompt": prompt,
                "style": "cinematic editorial",
                "negative_prompt": "text, watermark, blurry",
            })
        else:
            hero_clips.append({
                "id": f"v{sid}",
                "scene_id": sid,
                "prompt": prompt,
                "duration_seconds": min(dur, 5.0),
                "style": "cinematic editorial",
            })

    beat_map = {
        "episode": EPISODE,
        "week": WEEK,
        "asset_plan": {
            "hero_images": hero_images,
            "hero_clips": hero_clips,
        },
    }
    beat_map_path = EP_DIR / "ep07_beat_map.json"
    beat_map_path.write_text(json.dumps(beat_map, indent=2), encoding="utf-8")
    logger.info(f"Beat map: {len(hero_images)} images, {len(hero_clips)} clips -> {beat_map_path}")
    return beat_map


def generate_assets(beat_map: dict) -> dict[str, Path]:
    from agents.fal_asset_agent import run as fal_run
    result = fal_run(EPISODE, WEEK, {"beat_map": beat_map})
    if not result.get("success"):
        raise RuntimeError(f"fal asset generation failed: {result}")

    assets: dict[str, Path] = {}
    for asset_id, path_str in result["assets"].items():
        assets[asset_id] = Path(path_str)

    logger.info(
        f"Generated {result.get('generated_count', len(assets))} assets, "
        f"~${result.get('total_cost_usd', 0):.2f}"
    )
    return assets


def stage_assets(assets: dict[str, Path]) -> None:
    ASSET_STAGING.mkdir(parents=True, exist_ok=True)
    for asset_id, src_path in assets.items():
        dest = ASSET_STAGING / f"{asset_id.lower()}{src_path.suffix}"
        shutil.copy2(src_path, dest)
        logger.info(f"Staged {asset_id}: {dest}")


def render_visuals() -> Path:
    from agents.visual_agent import run as visual_run
    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    result = visual_run(script, EPISODE, WEEK, lang="en")
    if not result.get("success"):
        raise RuntimeError(f"Visual render failed: {result}")
    logger.info(f"Visuals rendered: {result['output_path']} ({result.get('size_mb', 0):.1f} MB)")
    return Path(result["output_path"])


def assemble_final() -> Path:
    from agents.assembly_agent import run as assembly_run
    result = assembly_run(episode=EPISODE, week=WEEK, lang="en")
    if not result.get("success"):
        raise RuntimeError(f"Assembly failed: {result}")
    logger.info(f"Final assembled: {result['output_path']}")
    return Path(result["output_path"])


def build_report(
    vda_result: dict,
    routing: dict,
    beat_map: dict | None,
    assets_generated: int,
    fal_cost: float,
    final_path: Path | None,
) -> dict:
    diversity = vda_result.get("diversity_gate", {})
    scenes = vda_result["storyboard"]

    from agents.visual_director_agent import classify_component_families
    comp_seq = [s.get("component", "") for s in scenes]
    families = classify_component_families(comp_seq)

    native_count = sum(1 for s in scenes if s.get("visual_mode") == "NATIVE")
    gen_count = sum(1 for s in scenes if s.get("visual_mode") == "GENERATED")

    report = {
        "root_cause": (
            "EP07 original storyboard was 100% NATIVE with component families "
            "TYPOGRAPHY → TRANSFORMATION → SEQUENCE → DIAGRAM → FLOW_PIPELINE → "
            "DOMAIN → TRANSFORMATION → TAKEAWAY → CTA, highly overlapping EP06's "
            "TYPOGRAPHY → TYPOGRAPHY → TRANSFORMATION → FLOW_PIPELINE → DOMAIN → "
            "COMPARISON → DIAGRAM → FLOW_PIPELINE → TAKEAWAY → CTA. Both episodes "
            "100% NATIVE meant mode couldn't compensate for family similarity. "
            "Diversity gate composite score ~0.57 (MEDIUM) with both NATIVE-dominant "
            "→ FAIL."
        ),
        "files_changed": [
            "agents/visual_director_agent.py — diversity gate + channel-scoped memory + v4.2 planning",
            "tests/test_diversity_gate.py — 13 regression tests (NEW)",
            "output/visual_fingerprints.json — EP06 approved with families + mode_ratio + channel",
            "scripts/ep07_diversity_replan.py — this production script (NEW)",
        ],
        "ep06_fingerprint": {
            "families": "TYPOGRAPHY → TYPOGRAPHY → TRANSFORMATION → FLOW_PIPELINE → DOMAIN → COMPARISON → DIAGRAM → FLOW_PIPELINE → TAKEAWAY → CTA",
            "mode_ratio": {"native": 10, "generated": 0},
            "art_direction": "bright-workspace",
        },
        "original_ep07_fingerprint": {
            "families": "TYPOGRAPHY → TRANSFORMATION → SEQUENCE → DIAGRAM → FLOW_PIPELINE → DOMAIN → TRANSFORMATION → TAKEAWAY → CTA",
            "mode_ratio": {"native": 9, "generated": 0},
            "art_direction": "cinematic-dark",
            "diversity_gate_would_fail": True,
        },
        "revised_ep07_plan": {
            "component_sequence": comp_seq,
            "family_sequence": families,
            "art_direction": vda_result.get("art_direction", {}).get("id", "unknown"),
            "visual_thesis": vda_result.get("visual_thesis", {}).get("core_concept", ""),
        },
        "native_generated_breakdown": {
            "native": native_count,
            "generated": gen_count,
            "episode_mode": routing.get("episode_mode", "unknown"),
        },
        "generated_assets": assets_generated,
        "fal_cost_usd": fal_cost,
        "diversity_gate_result": {
            "pass": diversity.get("pass", False),
            "similarity": diversity.get("similarity", {}),
            "recent_key": diversity.get("recent_key", ""),
            "reason": diversity.get("reason", ""),
        },
        "visual_complexity_score": vda_result.get("visual_complexity", {}).get("visual_first_score", 0),
        "final_preview_path": str(final_path) if final_path else None,
    }

    report_path = EP_DIR / "ep07_diversity_replan_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Report saved -> {report_path}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="EP07 diversity re-plan")
    parser.add_argument("--plan-only", action="store_true", help="Storyboard only")
    parser.add_argument("--render-only", action="store_true", help="Render + assemble only")
    args = parser.parse_args()

    vda_result = None
    routing = {}
    beat_map = None
    assets_generated = 0
    fal_cost = 0.0
    final_path = None

    if not args.render_only:
        print("\n[1/6] Archiving original storyboard...")
        archive_original_storyboard()

        print("[2/6] Running Visual Director with diversity gate...")
        vda_result = run_visual_director()
        print(f"  OK   {len(vda_result['storyboard'])} scenes, "
              f"score={vda_result['visual_complexity'].get('visual_first_score', 0)}")

        print("[3/6] Running visual mode router...")
        routing = run_mode_router()
        print(f"  OK   {routing['episode_mode']} "
              f"({routing['native_beats']}N / {routing['generated_beats']}G)")

        if routing["generated_beats"] > 0:
            print("[4/6] Building beat map for generated assets...")
            beat_map = build_beat_map()
            if beat_map:
                print("[4b/6] Generating fal.ai assets...")
                assets = generate_assets(beat_map)
                assets_generated = len(assets)
                print(f"  OK   {assets_generated} assets generated")
                print("[4c/6] Staging assets for Remotion...")
                stage_assets(assets)
        else:
            print("[4/6] Skipped — no GENERATED beats")

    if args.plan_only:
        if vda_result:
            report = build_report(vda_result, routing, beat_map, assets_generated, fal_cost, None)
            print(f"\n  Plan complete. Report: {EP_DIR / 'ep07_diversity_replan_report.json'}")
        return

    print("\n[5/6] Rendering visuals with Remotion...")
    visuals_path = render_visuals()
    print(f"  OK   {visuals_path}")

    print("[6/6] Assembling final preview...")
    final_path = assemble_final()
    size_mb = final_path.stat().st_size / (1024 * 1024) if final_path.exists() else 0
    print(f"  OK   {final_path} ({size_mb:.1f} MB)")

    if vda_result is None:
        data = json.loads(STORYBOARD_PATH.read_text(encoding="utf-8"))
        vda_result = {
            "storyboard": data.get("storyboard", []),
            "visual_complexity": data.get("visual_complexity", {}),
            "visual_thesis": data.get("visual_thesis", {}),
            "art_direction": data.get("art_direction", {}),
            "diversity_gate": data.get("diversity_gate", {}),
        }
        routing = data.get("visual_mode_routing", {})

    report = build_report(vda_result, routing, beat_map, assets_generated, fal_cost, final_path)

    print(f"\n{'='*60}")
    print(f"  EP07 DIVERSITY RE-PLAN COMPLETE")
    print(f"  Final: {final_path}")
    print(f"  Size: {size_mb:.1f} MB")
    print(f"  Mode: {routing.get('episode_mode', '?')} "
          f"({routing.get('native_beats', '?')}N / {routing.get('generated_beats', '?')}G)")
    print(f"  Score: {report.get('visual_complexity_score', 0)}/100")
    print(f"  Report: {EP_DIR / 'ep07_diversity_replan_report.json'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
