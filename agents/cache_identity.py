"""
cache_identity.py — content-identity helpers for pipeline output caches.

Caches are reused ONLY when the identity of the inputs that produced an output
matches the identity of the current inputs. File existence, size or mtime alone
never justify reuse.

Stale outputs are quarantined (renamed to *.stale_<UTC timestamp>.*), never
deleted, so nothing is lost and a stale artifact can never be mistaken for a
fresh one.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def text_hash(text: str) -> str:
    """SHA-256 (first 16 hex chars) of exact UTF-8 text — the pipeline's narration hash."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def json_identity(obj: object) -> str:
    """Stable SHA-256 (first 16 hex chars) of a JSON-serialisable object."""
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return text_hash(canonical)


def read_meta(path: Path) -> dict | None:
    """Read a cache metadata sidecar; None if missing or unreadable."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Unreadable cache metadata {path.name}: {e}")
        return None


def write_meta(path: Path, data: dict) -> None:
    """Atomically write a cache metadata sidecar."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def quarantine_stale(path: Path, reason: str) -> Path | None:
    """
    Rename a stale cached output out of the way (never delete).
    Returns the new path, or None if the file did not exist.
    """
    if not path.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = path.with_name(f"{path.stem}.stale_{stamp}{path.suffix}")
    path.rename(target)
    logger.warning(f"STALE CACHE: {path.name} -> {target.name} ({reason})")
    return target
