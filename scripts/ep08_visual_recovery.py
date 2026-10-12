"""
EP08 Visual Recovery — ONE bounded re-render with revised storyboard.

Runs:
  1. visual_agent.run() — renders with revised storyboard (no ContextWindowScene/TokenScene duplication)
  2. assembly_agent.run() — merges voice + visuals
  3. timeline_qa_guard.run_timeline_qa() — validates including perceptual duplication check
"""
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("ep08_recovery")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import visual_agent, assembly_agent
from timeline_qa_guard import run_timeline_qa


EPISODE = 8
WEEK = 9


def main() -> None:
    ep_dir = Path("output/week_09/ep08")
    script_path = ep_dir / "ep08_script_EN.json"
    storyboard_path = ep_dir / "ep08_storyboard_EN.json"
    voice_path = ep_dir / "ep08_voice_EN.mp3"

    script = json.loads(script_path.read_text(encoding="utf-8"))
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))

    logger.info("=" * 60)
    logger.info("EP08 VISUAL RECOVERY — ONE BOUNDED RE-RENDER")
    logger.info("=" * 60)
    logger.info(f"Components: {[s['component'] for s in storyboard['storyboard']]}")

    # ── Step 1: Render visuals ──
    logger.info("Step 1: Rendering visuals with revised storyboard...")
    vis_result = visual_agent.run(script, EPISODE, WEEK)
    if not vis_result.get("success"):
        logger.error(f"Visual render failed: {vis_result}")
        sys.exit(1)
    visuals_path = vis_result["output_path"]
    logger.info(f"Visuals rendered: {visuals_path}")
    if vis_result.get("skipped"):
        logger.warning("CACHE HIT — visuals were not re-rendered. Delete ep08_visuals.meta.json to force.")

    # ── Step 2: Assembly ──
    logger.info("Step 2: Running assembly agent...")
    asm_result = assembly_agent.run(EPISODE, WEEK, lang="en")
    if not asm_result.get("success"):
        logger.error(f"Assembly failed: {asm_result}")
        sys.exit(1)
    final_path = asm_result["output_path"]
    logger.info(f"Assembly complete: {final_path}")

    # ── Step 3: Timeline QA (includes duplication check) ──
    logger.info("Step 3: Running timeline QA with perceptual duplication check...")
    qa_result = run_timeline_qa(Path(final_path), storyboard_path)
    logger.info(f"Timeline QA verdict: {qa_result.get('verdict', 'UNKNOWN')}")
    if qa_result.get("duplication_check"):
        dup = qa_result["duplication_check"]
        logger.info(f"Duplication check: pass={dup.get('pass')}, pairs_flagged={dup.get('flagged_pairs', 0)}")

    # ── Report ──
    logger.info("=" * 60)
    logger.info("EP08 VISUAL RECOVERY COMPLETE")
    logger.info(f"Final: {final_path}")
    logger.info(f"QA verdict: {qa_result.get('verdict')}")
    logger.info("=" * 60)

    report = {
        "visuals": vis_result,
        "assembly": asm_result,
        "timeline_qa": qa_result,
    }
    report_path = ep_dir / "ep08_recovery_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
