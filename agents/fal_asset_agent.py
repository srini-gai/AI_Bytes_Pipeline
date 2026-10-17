"""
fal_asset_agent.py — Generate hero visuals via fal.ai APIs.

Supports:
    - Still images via fal-ai/nano-banana-2
    - Image-to-video via minimax/h3-max/image-to-video

Standard agent signature:
    run(episode, week, input_data) -> dict
"""

from __future__ import annotations

import base64
import logging
import os
import time
from pathlib import Path
from typing import Any

import fal_client
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

IMAGE_MODEL = "fal-ai/nano-banana-2"
VIDEO_MODEL = "minimax/h3-max/image-to-video"

IMAGE_SIZE_9_16 = {"width": 768, "height": 1344}
IMAGE_SIZE_9_16_SMALL = {"width": 480, "height": 848}

COST_PER_IMAGE = 0.01
COST_PER_VIDEO_SRC = 0.01
COST_PER_VIDEO_480P = 0.15
BUDGET_LIMIT_USD = 1.00


def _get_key() -> str:
    """Lazy-load FAL_KEY from environment at call time."""
    key = os.getenv("FAL_KEY", "")
    if not key:
        raise RuntimeError("FAL_KEY not set in .env — cannot call fal.ai APIs")
    return key


def _ensure_key() -> None:
    os.environ["FAL_KEY"] = _get_key()


def startup_check() -> str:
    """Report FAL_KEY status without exposing the key."""
    key = os.getenv("FAL_KEY", "")
    status = "FAL_KEY configured" if key else "FAL_KEY missing"
    logger.info(status)
    return status


def connectivity_check() -> dict[str, Any]:
    """Validate fal.ai API connectivity without generating paid media."""
    _ensure_key()
    try:
        result = fal_client.subscribe(
            "fal-ai/nano-banana-2",
            arguments={
                "prompt": "a simple blue gradient background, abstract, minimal",
                "image_size": {"width": 256, "height": 256},
                "num_images": 1,
                "enable_safety_checker": False,
            },
        )
        images = result.get("images", [])
        ok = len(images) > 0
        request_id = result.get("request_id", "unknown")
        logger.info(f"fal connectivity check: {'PASS' if ok else 'FAIL'} (request_id={request_id})")
        return {"ok": ok, "request_id": request_id}
    except Exception as e:
        logger.error(f"fal connectivity check FAIL: {e}")
        return {"ok": False, "error": str(e)}


def _episode_dir(episode: int, week: int) -> Path:
    base = Path(os.getenv("OUTPUT_BASE_PATH", "./output"))
    d = base / f"week_{week:02d}" / f"ep{episode:02d}" / "assets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _download_asset(
    url: str, output_path: Path, asset_id: str, timeout: int = 60, retries: int = 3,
) -> Path:
    """Download a generated asset URL with retries. Never re-generates."""
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"fal download [{asset_id}] attempt {attempt}/{retries}")
            resp = httpx.get(url, follow_redirects=True, timeout=timeout)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
            kb = output_path.stat().st_size / 1024
            logger.info(f"fal download [{asset_id}] saved: {output_path.name} ({kb:.0f} KB)")
            return output_path
        except Exception as e:
            logger.warning(f"fal download [{asset_id}] attempt {attempt} failed: {e}")
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def generate_image(
    prompt: str,
    output_path: Path,
    asset_id: str = "",
    size: dict[str, int] | None = None,
    retries: int = 3,
) -> tuple[Path, float]:
    """Generate a still image. Returns (path, estimated_cost).

    Generation and download have separate retry loops: a download failure
    never triggers another paid generation call.
    """
    _ensure_key()
    sz = size or IMAGE_SIZE_9_16
    image_url: str | None = None
    request_id: str = "unknown"
    generation_calls = 0

    for attempt in range(1, retries + 1):
        try:
            if image_url is None:
                logger.info(
                    f"fal image gen [{asset_id}] attempt {attempt}/{retries} "
                    f"model={IMAGE_MODEL} size={sz['width']}x{sz['height']}"
                )
                generation_calls += 1
                result = fal_client.subscribe(
                    IMAGE_MODEL,
                    arguments={
                        "prompt": prompt,
                        "image_size": sz,
                        "num_images": 1,
                        "enable_safety_checker": False,
                    },
                )
                images = result.get("images", [])
                if not images:
                    raise RuntimeError("fal returned no images")
                image_url = images[0].get("url", "")
                if not image_url:
                    raise RuntimeError("fal returned image with no URL")
                request_id = result.get("request_id", "unknown")
                logger.info(
                    f"fal image [{asset_id}] generated: request_id={request_id} "
                    f"est_cost=${COST_PER_IMAGE:.2f} gen_calls={generation_calls}"
                )

            _download_asset(image_url, output_path, asset_id, timeout=60)
            return output_path, COST_PER_IMAGE

        except Exception as e:
            logger.warning(f"fal image [{asset_id}] attempt {attempt} failed: {e}")
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)

    raise RuntimeError("unreachable")


def generate_video(
    prompt: str,
    source_image_path: Path,
    output_path: Path,
    asset_id: str = "",
    retries: int = 3,
) -> tuple[Path, float]:
    """Generate a video clip via image-to-video. Returns (path, estimated_cost).

    Generation and download have separate retry loops: a download failure
    never triggers another paid generation call.
    """
    _ensure_key()

    with open(source_image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    ext = source_image_path.suffix.lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    data_uri = f"data:{mime};base64,{img_b64}"
    video_url: str | None = None
    generation_calls = 0

    for attempt in range(1, retries + 1):
        try:
            if video_url is None:
                logger.info(
                    f"fal video gen [{asset_id}] attempt {attempt}/{retries} "
                    f"model={VIDEO_MODEL} resolution=480p"
                )
                generation_calls += 1
                result = fal_client.subscribe(
                    VIDEO_MODEL,
                    arguments={
                        "prompt": prompt,
                        "image_url": data_uri,
                    },
                )
                video = result.get("video", {})
                video_url = video.get("url", "")
                if not video_url:
                    raise RuntimeError("fal returned video with no URL")
                request_id = result.get("request_id", "unknown")
                logger.info(
                    f"fal video [{asset_id}] generated: request_id={request_id} "
                    f"est_cost=${COST_PER_VIDEO_480P:.2f} gen_calls={generation_calls}"
                )

            _download_asset(video_url, output_path, asset_id, timeout=120)
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(
                f"fal video [{asset_id}] saved: {output_path.name} ({size_mb:.1f} MB)"
            )
            return output_path, COST_PER_VIDEO_480P

        except Exception as e:
            logger.warning(f"fal video [{asset_id}] attempt {attempt} failed: {e}")
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)

    raise RuntimeError("unreachable")


def run(episode: int, week: int, input_data: dict[str, Any]) -> dict[str, Any]:
    """Generate all hero assets for an episode from a beat map.

    Args:
        episode: Episode number
        week: Week number
        input_data: Must contain 'beat_map' with asset_plan

    Returns:
        {"success": True, "assets": {...}, "total_cost_usd": float, "generation_log": [...]}
    """
    _ensure_key()
    beat_map = input_data["beat_map"]
    asset_plan = beat_map["asset_plan"]
    out_dir = _episode_dir(episode, week)

    assets: dict[str, str] = {}
    generation_log: list[dict[str, Any]] = []
    total_cost = 0.0

    def _check_budget(next_cost: float, asset_id: str) -> None:
        nonlocal total_cost
        if total_cost + next_cost > BUDGET_LIMIT_USD:
            raise RuntimeError(
                f"BUDGET GATE: cumulative ${total_cost:.2f} + next ${next_cost:.2f} "
                f"exceeds ${BUDGET_LIMIT_USD:.2f} limit. Stopping before {asset_id}."
            )

    # Generate still images
    for img_spec in asset_plan.get("hero_images", []):
        img_id = img_spec["id"]
        img_path = out_dir / f"{img_id.lower()}.png"

        if img_path.exists():
            logger.info(f"EP{episode:02d} asset {img_id} cached: {img_path}")
            assets[img_id] = str(img_path)
            generation_log.append({"asset_id": img_id, "status": "cached"})
            continue

        _check_budget(COST_PER_IMAGE, img_id)
        _, cost = generate_image(img_spec["prompt"], img_path, asset_id=img_id)
        total_cost += cost
        assets[img_id] = str(img_path)
        generation_log.append({
            "asset_id": img_id, "model": IMAGE_MODEL, "type": "image",
            "resolution": f"{IMAGE_SIZE_9_16['width']}x{IMAGE_SIZE_9_16['height']}",
            "est_cost_usd": cost, "status": "generated",
        })

    # Generate source images for videos, then videos
    for vid_spec in asset_plan.get("hero_videos", []):
        vid_id = vid_spec["id"]
        src_img_path = out_dir / f"{vid_id.lower()}_src.png"
        vid_path = out_dir / f"{vid_id.lower()}.mp4"

        if vid_path.exists():
            logger.info(f"EP{episode:02d} asset {vid_id} cached: {vid_path}")
            assets[vid_id] = str(vid_path)
            generation_log.append({"asset_id": vid_id, "status": "cached"})
            continue

        # Generate source image if needed
        if not src_img_path.exists():
            _check_budget(COST_PER_VIDEO_SRC, f"{vid_id}_src")
            _, src_cost = generate_image(
                vid_spec["prompt"], src_img_path,
                asset_id=f"{vid_id}_src", size=IMAGE_SIZE_9_16_SMALL,
            )
            total_cost += src_cost
            generation_log.append({
                "asset_id": f"{vid_id}_src", "model": IMAGE_MODEL, "type": "image",
                "resolution": f"{IMAGE_SIZE_9_16_SMALL['width']}x{IMAGE_SIZE_9_16_SMALL['height']}",
                "est_cost_usd": src_cost, "status": "generated",
            })

        # Generate video from source image
        _check_budget(COST_PER_VIDEO_480P, vid_id)
        _, vid_cost = generate_video(
            vid_spec["prompt"], src_img_path, vid_path, asset_id=vid_id,
        )
        total_cost += vid_cost
        assets[vid_id] = str(vid_path)
        generation_log.append({
            "asset_id": vid_id, "model": VIDEO_MODEL, "type": "video",
            "resolution": "480p", "est_cost_usd": vid_cost, "status": "generated",
        })

    logger.info(
        f"EP{episode:02d} fal assets complete: {len(assets)} assets, "
        f"total_cost=${total_cost:.2f}"
    )

    return {
        "success": True,
        "assets": assets,
        "total_cost_usd": total_cost,
        "generation_log": generation_log,
    }
