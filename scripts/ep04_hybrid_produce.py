"""
EP04 Hybrid Production — fal.ai assets + Remotion assembly.

Usage:
    python scripts/ep04_hybrid_produce.py              # generate assets + render + assemble
    python scripts/ep04_hybrid_produce.py --assets-only # generate assets only
    python scripts/ep04_hybrid_produce.py --render-only # render + assemble (assets must exist)
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("ep04_hybrid")

EPISODE = 4
WEEK = 1
EP_DIR = PROJECT_ROOT / "output" / "week_01" / "ep04"
ASSET_STAGING = PROJECT_ROOT / "remotion" / "public" / "assets" / "ep04"
BEAT_MAP_PATH = EP_DIR / "ep04_beat_map.json"
STORYBOARD_PATH = EP_DIR / "ep04_hybrid_storyboard_EN.json"
SCRIPT_PATH = EP_DIR / "ep04_script_EN.json"
VOICE_PATH = EP_DIR / "ep04_voice_EN.mp3"


def generate_assets() -> dict[str, Path]:
    """Generate fal.ai assets and return {asset_id: local_path}."""
    from agents.fal_asset_agent import run as fal_run

    beat_map = json.loads(BEAT_MAP_PATH.read_text(encoding="utf-8"))
    result = fal_run(EPISODE, WEEK, {"beat_map": beat_map})

    if not result.get("success"):
        raise RuntimeError(f"fal asset generation failed: {result}")

    assets: dict[str, Path] = {}
    for asset_id, path_str in result["assets"].items():
        assets[asset_id] = Path(path_str)

    logger.info(
        f"Generated {result['generated_count']} assets, "
        f"~${result['cost_estimate_usd']:.2f}"
    )
    return assets


def stage_assets(assets: dict[str, Path]) -> None:
    """Copy generated assets to remotion/public/assets/ep04/ for rendering."""
    ASSET_STAGING.mkdir(parents=True, exist_ok=True)

    for asset_id, src_path in assets.items():
        ext = src_path.suffix
        dest = ASSET_STAGING / f"{asset_id.lower()}{ext}"
        shutil.copy2(src_path, dest)
        logger.info(f"Staged {asset_id}: {dest}")


def verify_assets() -> bool:
    """Check all required assets exist in staging directory."""
    required = ["v1.mp4", "v2.mp4", "i1.png", "i2.png", "i3.png", "i4.png"]
    missing = [f for f in required if not (ASSET_STAGING / f).exists()]
    if missing:
        logger.error(f"Missing staged assets: {missing}")
        return False
    logger.info(f"All {len(required)} assets verified in {ASSET_STAGING}")
    return True


def render_visuals() -> Path:
    """Render EP04 visuals with Remotion using hybrid storyboard."""
    storyboard = json.loads(STORYBOARD_PATH.read_text(encoding="utf-8"))
    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))

    # Build Remotion props
    total_dur = sum(s["duration_seconds"] for s in storyboard["storyboard"])
    total_frames = round(total_dur * 30)

    props = {
        "episode": script["episode"],
        "topic": script["topic"],
        "hook": script["hook"],
        "concept": script.get("concept", ""),
        "slides": script.get("slides", []),
        "takeaway": script["takeaway"],
        "storyboard": storyboard["storyboard"],
        "art_direction": storyboard.get("art_direction", {}).get("id"),
    }

    props_path = EP_DIR / "ep04_hybrid_props.json"
    props_path.write_text(json.dumps(props, indent=2), encoding="utf-8")

    output_path = EP_DIR / "ep04_hybrid_visuals.mp4"

    cmd = [
        "npx.cmd" if sys.platform == "win32" else "npx",
        "remotion", "render",
        "src/index.ts", "AIBytesReel",
        str(output_path),
        f"--props={props_path}",
        f"--frames=0-{total_frames - 1}",
        "--codec=h264",
        "--crf=18",
    ]

    logger.info(f"Rendering: {' '.join(cmd[:6])}...")
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT / "remotion"),
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        logger.error(f"Remotion render failed:\n{result.stderr[-2000:]}")
        raise RuntimeError("Remotion render failed")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"Visuals rendered: {output_path} ({size_mb:.1f} MB)")
    return output_path


def assemble_final(visuals_path: Path) -> Path:
    """Merge voice + visuals into final preview."""
    output_path = EP_DIR / "ep04_hybrid_final_EN.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(visuals_path),
        "-i", str(VOICE_PATH),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

    logger.info("Assembling final preview...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        logger.error(f"FFmpeg assembly failed:\n{result.stderr[-1000:]}")
        raise RuntimeError("FFmpeg assembly failed")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"Final preview: {output_path} ({size_mb:.1f} MB)")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="EP04 hybrid production")
    parser.add_argument("--assets-only", action="store_true", help="Generate assets only")
    parser.add_argument("--render-only", action="store_true", help="Render + assemble only")
    args = parser.parse_args()

    if not args.render_only:
        print("\n[1/4] Generating fal.ai assets...")
        assets = generate_assets()
        print(f"  OK   {len(assets)} assets generated")

        print("[2/4] Staging assets for Remotion...")
        stage_assets(assets)
        print(f"  OK   Assets staged to {ASSET_STAGING}")

    if args.assets_only:
        print("\n✓ Assets ready. Run with --render-only to render.")
        return

    if not verify_assets():
        print("\n✗ Missing assets. Run without --render-only first.")
        sys.exit(1)

    print("\n[3/4] Rendering with Remotion...")
    visuals = render_visuals()
    print(f"  OK   {visuals}")

    print("[4/4] Assembling final preview...")
    final = assemble_final(visuals)
    print(f"  OK   {final}")

    size_mb = final.stat().st_size / (1024 * 1024)
    print(f"\n{'='*60}")
    print(f"  EP04 HYBRID PREVIEW READY")
    print(f"  Path: {final}")
    print(f"  Size: {size_mb:.1f} MB")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
