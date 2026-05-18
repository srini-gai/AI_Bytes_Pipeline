"""
Phase 5 — Visual Agent
Renders language-agnostic visuals via Remotion headless render.
Output: ep{NN}_visuals.mp4  (1080x1920, 60s, 30fps, no audio — shared across all languages)

If PEXELS_API_KEY is configured, downloads one background clip per scene from Pexels,
stages them into remotion/public/clips/ (so staticFile() can serve them), and passes
clip paths as props to Remotion. Falls back to dark gradient when key is absent.
"""
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import av

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
REMOTION_DIR = PROJECT_ROOT / "remotion"
ENTRY_POINT = "src/index.ts"

NPX = "npx.cmd" if sys.platform == "win32" else "npx"

MIN_DURATION = 58.0
MAX_DURATION = 62.0

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
CLIP_MIN_DURATION = 8  # seconds — all scenes are 7-10s

_DEFAULT_THEME = {
    "name": "energy",
    "accent": "#a78bfa",
    "accent2": "#34d399",
    "overlay": "rgba(5,5,16,0.35)",
    "pexels_mood": "purple neon dark",
}


def _episode_dir(episode: int, week: int) -> Path:
    base = Path(os.getenv("OUTPUT_BASE_PATH", "./output"))
    d = base / f"week_{week:02d}" / f"ep{episode:02d}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _strip_non_ascii(text: str) -> str:
    """Remove emojis and non-ASCII chars so search queries stay clean."""
    return re.sub(r"[^\x00-\x7F]+", " ", text).strip()


_HUMAN_KEYWORDS = frozenset({
    "person", "people", "man", "woman",
    "business", "office", "team", "meeting", "worker",
})


def _is_human_clip(video: dict) -> bool:
    """Return True if the Pexels video URL suggests human/people content."""
    url_lower = video.get("url", "").lower()
    return any(kw in url_lower for kw in _HUMAN_KEYWORDS)


def _clip_queries(script: dict) -> dict[str, str]:
    """Return {scene_key: pexels_search_query} for all 7 scenes."""
    topic = _strip_non_ascii(script.get("topic", "technology"))
    slides = script.get("slides", [{}, {}, {}, {}])

    def heading_kw(idx: int) -> str:
        h = slides[idx].get("heading", "") if idx < len(slides) else ""
        return _strip_non_ascii(h)

    return {
        "hook":    f"{topic} technology dark cinematic abstract no people",
        "concept": "artificial intelligence neural network abstract no people",
        "slide_0": f"{heading_kw(0)} technology abstract no people",
        "slide_1": f"{heading_kw(1)} data flow abstract no people",
        "slide_2": f"{heading_kw(2)} network abstract no people",
        "slide_3": f"{heading_kw(3)} technology future abstract no people",
        "cta":     "technology abstract dark particles no people",
    }


def fetch_pexels_clip(
    query: str,
    min_duration: int,
    api_key: str,
    clips_dir: Path,
    filename: str,
) -> Path:
    """
    Download the highest-resolution Pexels video clip for query.
    Caches to clips_dir/filename — skips download if the file already exists.
    Retries network errors 3x with exponential backoff.
    """
    cached = clips_dir / filename
    if cached.exists() and cached.stat().st_size > 50_000:
        logger.info(f"Clip cache hit: {filename}")
        return cached

    clips_dir.mkdir(parents=True, exist_ok=True)

    params = urllib.parse.urlencode({
        "query": query,
        "per_page": 10,
        "min_duration": min_duration,
        "orientation": "portrait",
    })
    search_url = f"{PEXELS_SEARCH_URL}?{params}"

    # Search — read key at call time so dotenv order doesn't matter
    pexels_key = os.getenv("PEXELS_API_KEY", api_key)
    logger.debug(f"Pexels key first 8 chars: {pexels_key[:8]!r}")

    data: dict | None = None
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(
                search_url,
                headers={
                    "Authorization": pexels_key,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            break
        except (urllib.error.URLError, OSError) as e:
            last_error = e
            logger.warning(f"Pexels search '{query}' attempt {attempt}/3: {e}")
            if attempt < 3:
                time.sleep(2 ** attempt)

    if data is None:
        raise RuntimeError(f"Pexels search failed for '{query}': {last_error}")

    videos = data.get("videos", [])
    if not videos:
        raise RuntimeError(f"No Pexels results for query: '{query}'")

    # Skip clips whose Pexels URL indicates human/people content
    clean_videos = [v for v in videos if not _is_human_clip(v)]
    if not clean_videos:
        logger.warning(
            f"All {len(videos)} Pexels results for '{query}' matched human filter — using first result"
        )
        clean_videos = videos

    video_files = clean_videos[0].get("video_files", [])
    if not video_files:
        raise RuntimeError(f"No downloadable files for '{query}'")

    best = max(video_files, key=lambda f: f.get("width", 0) * f.get("height", 0))
    download_url = best["link"]
    logger.info(
        f"Downloading clip '{query}' "
        f"({best.get('width')}x{best.get('height')}) -> {filename}"
    )

    # Download — CDN also requires a browser User-Agent to avoid 403
    _UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    for attempt in range(1, 4):
        try:
            dl_req = urllib.request.Request(download_url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(dl_req, timeout=120) as resp:
                cached.write_bytes(resp.read())
            logger.info(f"Clip saved: {filename} ({cached.stat().st_size // 1024} KB)")
            return cached
        except (urllib.error.URLError, OSError) as e:
            last_error = e
            # WinError 10054 = connection reset by peer — CDN drops long downloads;
            # wait 30s to let the connection settle before retrying.
            winerror = getattr(e, "winerror", None) or getattr(getattr(e, "reason", None), "winerror", None)
            if winerror == 10054:
                wait = 30
                logger.warning(
                    f"Pexels download '{filename}' attempt {attempt}/3: WinError 10054 "
                    f"(connection reset) — waiting {wait}s before retry"
                )
            else:
                wait = 2 ** attempt
                logger.warning(f"Pexels download '{filename}' attempt {attempt}/3: {e}")
            if attempt < 3:
                time.sleep(wait)

    raise RuntimeError(f"Pexels download failed for '{query}': {last_error}")


def _fetch_all_clips(script: dict, ep_dir: Path, api_key: str) -> dict[str, str]:
    """
    Download all 7 scene clips from Pexels.
    Returns {scene_key: absolute_path}. Failed scenes are skipped with a warning.
    """
    clips_dir = ep_dir / "clips"
    clips: dict[str, str] = {}
    for scene_key, query in _clip_queries(script).items():
        filename = f"{scene_key}.mp4"
        try:
            path = fetch_pexels_clip(query, CLIP_MIN_DURATION, api_key, clips_dir, filename)
            clips[scene_key] = str(path.resolve())
        except Exception as e:
            logger.warning(f"Clip fetch failed for '{scene_key}': {e} — scene will use dark background")
    return clips


def _stage_clips_to_public(clips: dict[str, str], public_clips_dir: Path) -> dict[str, str]:
    """
    Copy downloaded clips into remotion/public/clips/ so Remotion's HTTP server
    can serve them via staticFile() during headless rendering.
    Returns {scene_key: "clips/<scene_key>.mp4"} (public-relative paths).
    """
    public_clips_dir.mkdir(parents=True, exist_ok=True)
    staged: dict[str, str] = {}
    for scene_key, abs_path in clips.items():
        dst = public_clips_dir / f"{scene_key}.mp4"
        shutil.copy2(abs_path, dst)
        staged[scene_key] = f"clips/{scene_key}.mp4"
        logger.info(f"Staged {scene_key} -> remotion/public/clips/{scene_key}.mp4")
    return staged


def _build_props(script: dict, clips: dict[str, str] | None = None) -> dict:
    """Map script JSON fields to AIBytesReel composition props."""
    slides = [
        {
            "icon": s.get("icon", "💡"),
            "heading": s.get("heading", ""),
            "body": s.get("body", ""),
        }
        for s in script.get("slides", [])
    ]
    props: dict = {
        "episode": script.get("episode", "01"),
        "topic": script.get("topic", ""),
        "title": script.get("title", ""),
        "hook": script.get("hook", ""),
        "concept": script.get("concept", ""),
        "slides": slides,
        "voiceover": script.get("voiceover", ""),
        "takeaway": script.get("takeaway", ""),
        "tags": script.get("tags", ""),
        "theme": script.get("theme", _DEFAULT_THEME),
    }
    if script.get("diagram_spec"):
        props["diagram_spec"] = script["diagram_spec"]
    if clips:
        props["clips"] = clips
    return props


def _validate_output(path: Path, episode: int) -> float:
    """
    Check the rendered MP4:
      - File exists and is non-trivial
      - Video stream is 1080x1920
      - Duration is 58-62 seconds
    Returns duration in seconds.
    """
    if not path.exists() or path.stat().st_size < 100_000:
        raise RuntimeError(
            f"EP{episode:02d} output missing or too small: {path}"
        )

    container = av.open(str(path))
    try:
        video_streams = list(container.streams.video)
        if not video_streams:
            raise RuntimeError(f"EP{episode:02d} output has no video stream: {path}")

        vs = video_streams[0]
        width = vs.codec_context.width
        height = vs.codec_context.height
        if width != 1080 or height != 1920:
            raise RuntimeError(
                f"EP{episode:02d} output is {width}x{height} — expected 1080x1920"
            )

        if container.duration is not None and container.duration > 0:
            duration = float(container.duration) / 1_000_000
        elif vs.duration and vs.time_base:
            duration = float(vs.duration * vs.time_base)
        else:
            raise RuntimeError(f"EP{episode:02d} could not determine output duration")
    finally:
        container.close()

    if not (MIN_DURATION <= duration <= MAX_DURATION):
        raise RuntimeError(
            f"EP{episode:02d} output duration {duration:.1f}s outside {MIN_DURATION}-{MAX_DURATION}s window"
        )

    return duration


def _render(output_path: Path, props: dict, episode: int) -> None:
    """
    Run npx remotion render and raise RuntimeError on failure.
    Props are written to a temp JSON file to avoid Windows CLI quoting issues.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(props, tmp, ensure_ascii=False)
        props_file = tmp.name

    try:
        cmd = [
            NPX, "remotion", "render",
            ENTRY_POINT,
            "AIBytesReel",
            str(output_path.resolve()),
            f"--props={props_file}",
            "--codec", "h264",
            "--image-format", "jpeg",
            "--jpeg-quality", "90",
            "--concurrency", "4",
            "--log", "verbose",
        ]

        logger.info(f"EP{episode:02d} render cmd: {' '.join(cmd[:5])} ...")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(REMOTION_DIR),
                capture_output=True,
                text=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"EP{episode:02d} Remotion render timed out after 10 minutes")

        if result.returncode != 0:
            stderr_tail = result.stderr[-3000:] if result.stderr else "(no stderr)"
            raise RuntimeError(
                f"EP{episode:02d} Remotion exited {result.returncode}:\n{stderr_tail}"
            )
    finally:
        Path(props_file).unlink(missing_ok=True)


def run(script: dict, episode: int, week: int) -> dict:
    """
    Render Remotion composition for this episode (language-agnostic).
    Downloads Pexels background clips if PEXELS_API_KEY is configured.
    Retries once on failure. Validates 1080x1920 and 58-62s duration via PyAV.

    Returns:
        {"success": True, "output_path": str, "duration": float,
         "render_time": float, "size_mb": float, "skipped": bool}
    """
    ep_dir = _episode_dir(episode, week)
    output_path = ep_dir / f"ep{episode:02d}_visuals.mp4"

    if output_path.exists() and output_path.stat().st_size > 100_000:
        logger.info(f"EP{episode:02d} visuals already rendered — skipping")
        return {
            "success": True,
            "output_path": str(output_path),
            "skipped": True,
            "message": "Visuals already rendered - skipping.",
        }

    # Fetch Pexels background clips if API key is configured
    staged_clips: dict[str, str] | None = None
    if PEXELS_API_KEY:
        logger.info(f"EP{episode:02d} fetching Pexels background clips")
        try:
            raw_clips = _fetch_all_clips(script, ep_dir, PEXELS_API_KEY)
            if raw_clips:
                staged_clips = _stage_clips_to_public(
                    raw_clips, REMOTION_DIR / "public" / "clips"
                )
                logger.info(f"EP{episode:02d} staged {len(staged_clips)}/7 clips for Remotion")
        except Exception as e:
            logger.warning(f"EP{episode:02d} Pexels integration failed — rendering without clips: {e}")
    else:
        logger.info(f"EP{episode:02d} PEXELS_API_KEY not set — rendering with dark gradient background")

    props = _build_props(script, clips=staged_clips)
    last_error: Exception | None = None

    for attempt in range(1, 3):  # max 2 attempts
        t0 = time.monotonic()
        try:
            logger.info(f"EP{episode:02d} starting Remotion render (attempt {attempt}/2)")
            _render(output_path, props, episode)
            duration = _validate_output(output_path, episode)
            render_time = time.monotonic() - t0

            logger.info(
                f"EP{episode:02d} render complete in {render_time:.1f}s — "
                f"duration={duration:.1f}s size={output_path.stat().st_size/1_048_576:.1f}MB"
            )
            return {
                "success": True,
                "output_path": str(output_path),
                "skipped": False,
                "duration": duration,
                "render_time": round(render_time, 1),
                "size_mb": round(output_path.stat().st_size / 1_048_576, 1),
            }

        except RuntimeError as e:
            last_error = e
            render_time = time.monotonic() - t0
            logger.warning(
                f"EP{episode:02d} render attempt {attempt} failed after {render_time:.1f}s: {e}"
            )
            if output_path.exists():
                output_path.unlink()
            if attempt < 2:
                logger.info(f"EP{episode:02d} retrying render in 5s...")
                time.sleep(5)

    raise RuntimeError(
        f"EP{episode:02d} visual_agent failed after 2 attempts: {last_error}"
    )
