# Pipeline Skill — AI Bytes

> Agent orchestration rules, retry logic, and error handling patterns.

---

## Standard Agent Signature

Every agent in `agents/` must follow this exact signature:

```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def run(episode: int, week: int, input_data: dict) -> dict:
    """
    Args:
        episode: Episode number (1-7)
        week: Week number (auto-detected or --week flag)
        input_data: Dict passed from previous agent or orchestrator

    Returns:
        {"success": True, "output_path": str}

    Raises:
        Exception on unrecoverable failure (orchestrator catches + retries)
    """
    try:
        # do work
        logger.info(f"EP{episode:02d} — agent completed")
        return {"success": True, "output_path": str(path)}
    except Exception as e:
        logger.error(f"EP{episode:02d} — agent failed: {e}")
        raise
```

---

## Retry Pattern (all API calls)

```python
import time
import logging

logger = logging.getLogger(__name__)

def call_with_retry(fn, *args, max_retries: int = 3, **kwargs):
    """Exponential backoff retry wrapper."""
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Failed after {max_retries} attempts: {e}")
                raise
            wait = 2 ** attempt
            logger.warning(f"Attempt {attempt} failed ({e}), retrying in {wait}s...")
            time.sleep(wait)
```

---

## Output Directory Pattern

```python
from pathlib import Path

def get_episode_dir(episode: int, week: int, base: str = "./output") -> Path:
    """Returns and creates the episode output directory."""
    path = Path(base) / f"week_{week:02d}" / f"ep{episode:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_episode_file(episode: int, week: int, suffix: str, base: str = "./output") -> Path:
    """Returns the path for an episode file."""
    ep_dir = get_episode_dir(episode, week, base)
    return ep_dir / f"ep{episode:02d}_{suffix}"
```

---

## Validation Helpers

```python
import subprocess

def validate_mp3_duration(path: Path, min_sec: float = 55, max_sec: float = 65) -> float:
    """Validate MP3 duration is within acceptable range. Returns duration."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True
    )
    duration = float(result.stdout.strip())
    if not (min_sec <= duration <= max_sec):
        raise ValueError(f"MP3 duration {duration:.1f}s outside range {min_sec}–{max_sec}s")
    return duration

def validate_mp4(path: Path, expected_w: int = 1080, expected_h: int = 1920,
                 min_sec: float = 58, max_sec: float = 62,
                 require_audio: bool = True) -> dict:
    """Validate MP4 resolution, duration, and audio track."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,duration",
         "-of", "default=noprint_wrappers=1", str(path)],
        capture_output=True, text=True, check=True
    )
    info = dict(line.split("=") for line in result.stdout.strip().splitlines() if "=" in line)
    w, h = int(info.get("width", 0)), int(info.get("height", 0))
    if w != expected_w or h != expected_h:
        raise ValueError(f"Resolution {w}x{h} != expected {expected_w}x{expected_h}")
    duration = float(info.get("duration", 0))
    if not (min_sec <= duration <= max_sec):
        raise ValueError(f"Duration {duration:.1f}s outside range {min_sec}–{max_sec}s")
    return {"width": w, "height": h, "duration": duration}
```

---

## Orchestrator Error Handling

```python
failed_episodes = []

for i, topic in enumerate(topics):
    ep = i + 1
    try:
        result = run_episode(ep, week, topic)
        logger.info(f"EP{ep:02d} — SUCCESS: {result}")
    except Exception as e:
        logger.error(f"EP{ep:02d} — FAILED: {e}")
        failed_episodes.append(ep)

# Retry failed episodes once
for ep in failed_episodes:
    try:
        result = run_episode(ep, week, topics[ep - 1])
        logger.info(f"EP{ep:02d} — RETRY SUCCESS")
        failed_episodes.remove(ep)
    except Exception as e:
        logger.error(f"EP{ep:02d} — RETRY FAILED: {e}")

logger.info(f"Pipeline complete: {7 - len(failed_episodes)}/7 episodes published")
```

---

## Logging Setup

```python
import logging
from pathlib import Path

def setup_logging(log_file: str = "orchestrator.log") -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ]
    )
```
