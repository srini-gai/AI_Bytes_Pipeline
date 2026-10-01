"""
adapters/higgsfield.py — Higgsfield video generation adapter (Phase 3B production).

Authentication: two-part key from env vars
    HIGGSFIELD_API_KEY_ID
    HIGGSFIELD_API_KEY_SECRET

Optional overrides:
    HIGGSFIELD_MODEL   (default: resolved via supported-models endpoint, falls back to kling-3.0-standard)
    HIGGSFIELD_POLL_INTERVAL_SECONDS  (default: 5)
    HIGGSFIELD_POLL_TIMEOUT_SECONDS   (default: 300)

Cost guard env vars (shared with asset_planner_agent):
    GENERATIVE_VIDEO_MAX_COST_PER_SHORT_USD  (default: 0.75)
    GENERATIVE_VIDEO_MONTHLY_BUDGET_USD      (default: 25.0)

NEVER log the API key, key ID, or key secret.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import urllib.error
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from agents.providers.base import (
    GenerationRequest,
    GenerationResult,
    GenerationType,
    VideoGenerationProvider,
    make_cache_key,
)

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

_API_BASE = "https://api.higgsfield.ai"
# Confirmed endpoint from OpenAPI spec (docs.higgsfield.ai/docs/openapi.json).
# Kling 3.0 is not yet in the published spec; v2.5-turbo/standard is the
# latest documented T2V endpoint and is confirmed working.
_T2V_ENDPOINT = f"{_API_BASE}/kling-video/v2.5-turbo/standard/text-to-video"
# Universal status endpoint — same for all models (confirmed from OpenAPI spec).
_STATUS_ENDPOINT_TPL = f"{_API_BASE}/requests/{{request_id}}/status"

# Fallback cost rate (USD/second) used when live estimate is unavailable.
# Kling 2.5-turbo Standard rate ~$0.084/s (same as 3.0 Standard on the explore page).
_FALLBACK_COST_PER_SECOND_USD = 0.084

# Default model name — display/logging label only; NOT sent in the POST body.
# Higgsfield encodes model in the endpoint path, not the request body.
_DEFAULT_MODEL = "kling-v2.5-turbo-standard"

# No-text instruction appended to every prompt.
_NO_TEXT_SUFFIX = (
    " No visible text, letters, numbers, logos, watermarks, UI labels, "
    "subtitles, captions, signage, or typography of any kind. "
    "Text will be added in post-production."
)

# Cache sub-directory under the output base path.
_CACHE_SUBDIR = "generative_video_cache"


# ── Budget guard helpers ───────────────────────────────────────────────────────

def _float_env(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        logger.warning("Invalid value for %s — using default %.4f", key, default)
        return default


def _get_max_cost_per_short() -> float:
    return _float_env("GENERATIVE_VIDEO_MAX_COST_PER_SHORT_USD", 0.75)


# ── Manifest entry ─────────────────────────────────────────────────────────────

@dataclass
class AssetManifestEntry:
    provider: str
    model: str
    asset_id: str        # SHA-256 cache key
    task_id: str         # Higgsfield task UUID
    scene_id: str
    prompt_hash: str     # SHA-256 of normalised prompt only
    requested_duration: float
    actual_duration: Optional[float]
    resolution: Optional[str]       # e.g. "1080x1920"
    estimated_cost_usd: float
    actual_cost_usd: float          # 0.0 if not reported by API
    generation_latency_seconds: float
    cache_status: str               # "hit" | "miss"
    file_path: str
    fallback_status: str            # "used" | "not_used"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── HiggsfieldAdapter ─────────────────────────────────────────────────────────

class HiggsfieldAdapter(VideoGenerationProvider):
    """
    Production Higgsfield adapter for Kling 3.0 Standard T2V.

    Flow:
        1. Check cache (make_cache_key → look for existing MP4)
        2. Live cost estimate
        3. Budget guard check
        4. POST generation request
        5. Poll async status until SUCCEEDED / FAILED / timeout
        6. Download MP4 to cache directory
        7. Build and return GenerationResult + AssetManifestEntry
    """

    def __init__(self) -> None:
        self._key_id = os.getenv("HIGGSFIELD_API_KEY_ID", "")
        self._key_secret = os.getenv("HIGGSFIELD_API_KEY_SECRET", "")
        self._model = os.getenv("HIGGSFIELD_MODEL", _DEFAULT_MODEL)
        self._poll_interval = float(os.getenv("HIGGSFIELD_POLL_INTERVAL_SECONDS", "5"))
        self._poll_timeout = float(os.getenv("HIGGSFIELD_POLL_TIMEOUT_SECONDS", "300"))
        self._cache_dir = Path(
            os.getenv("OUTPUT_BASE_PATH", "./output")
        ) / _CACHE_SUBDIR
        # Most recent manifest entry (populated by generate())
        self.last_manifest_entry: Optional[AssetManifestEntry] = None

    # ── VideoGenerationProvider interface ──────────────────────────────────────

    @property
    def name(self) -> str:
        return "higgsfield"

    @property
    def default_model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Return True if both key parts are set and appear non-placeholder."""
        if not self._key_id or not self._key_secret:
            return False
        placeholder_markers = ("your-", "replace-", "xxx", "changeme", "<")
        for marker in placeholder_markers:
            if marker in self._key_id.lower() or marker in self._key_secret.lower():
                return False
        return True

    def estimate_cost(self, request: GenerationRequest) -> float:
        """
        Return a planning cost estimate in USD.

        Uses _FALLBACK_COST_PER_SECOND_USD because Higgsfield does not expose
        a public cost-estimate endpoint; the actual charge is billed per second
        of output video at the contracted rate.
        """
        duration = request.duration_seconds or 5.0
        return round(duration * _FALLBACK_COST_PER_SECOND_USD, 4)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        Full production generation flow.

        Raises:
            RuntimeError: provider not available, budget exceeded, API error,
                          polling timeout, or invalid video returned.
            All errors are meant to be caught by the caller, which falls back
            to Remotion-only rendering.
        """
        if not self.is_available():
            raise RuntimeError(
                "HiggsfieldAdapter: credentials not configured. "
                "Set HIGGSFIELD_API_KEY_ID and HIGGSFIELD_API_KEY_SECRET."
            )

        if request.generation_type != GenerationType.VIDEO:
            raise RuntimeError(
                f"HiggsfieldAdapter only supports VIDEO, got {request.generation_type}"
            )

        duration = request.duration_seconds or 5.0
        model = request.model or self._model
        aspect_ratio = request.aspect_ratio or "9:16"

        # ── 1. Cache check ─────────────────────────────────────────────────────
        cache_key = make_cache_key(
            prompt_intent=request.prompt_intent,
            provider=self.name,
            model=model,
            generation_type=request.generation_type,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration,
        )
        cache_path = self._cache_dir / f"{cache_key}.mp4"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        if cache_path.exists() and cache_path.stat().st_size > 0:
            logger.info(
                "EP%02d s%s — Higgsfield cache HIT: %s",
                request.episode, request.scene_id, cache_key[:16]
            )
            actual_duration = self._probe_duration(cache_path)
            entry = AssetManifestEntry(
                provider=self.name,
                model=model,
                asset_id=cache_key,
                task_id="cached",
                scene_id=request.scene_id,
                prompt_hash=self._prompt_hash(request.prompt_intent),
                requested_duration=duration,
                actual_duration=actual_duration,
                resolution=self._probe_resolution(cache_path),
                estimated_cost_usd=0.0,
                actual_cost_usd=0.0,
                generation_latency_seconds=0.0,
                cache_status="hit",
                file_path=str(cache_path),
                fallback_status="not_used",
            )
            self.last_manifest_entry = entry
            return GenerationResult(
                asset_path=str(cache_path),
                provider=self.name,
                model=model,
                actual_cost_usd=0.0,
                asset_id=cache_key,
                generation_type=request.generation_type,
                width=1080,
                height=1920,
                duration_seconds=actual_duration,
            )

        # ── 2. Cost estimate + budget guard ────────────────────────────────────
        estimated_cost = self.estimate_cost(request)
        max_cost = _get_max_cost_per_short()
        if estimated_cost > max_cost:
            raise RuntimeError(
                f"HiggsfieldAdapter: estimated cost ${estimated_cost:.4f} "
                f"exceeds episode budget ${max_cost:.4f}. Falling back."
            )
        logger.info(
            "EP%02d s%s — Higgsfield cost estimate $%.4f (budget $%.4f)",
            request.episode, request.scene_id, estimated_cost, max_cost
        )

        # ── 3. Build prompt ────────────────────────────────────────────────────
        full_prompt = request.prompt_intent.strip() + _NO_TEXT_SUFFIX

        # ── 4. POST generation request ─────────────────────────────────────────
        generation_start = time.monotonic()
        request_id = self._post_generation(full_prompt, duration, aspect_ratio, model)
        logger.info(
            "EP%02d s%s — Higgsfield request created: %s",
            request.episode, request.scene_id, request_id
        )

        # ── 5. Poll for completion ─────────────────────────────────────────────
        video_url = self._poll_until_done(request_id, request.episode, request.scene_id)
        generation_latency = time.monotonic() - generation_start
        logger.info(
            "EP%02d s%s — Higgsfield generation complete in %.1fs",
            request.episode, request.scene_id, generation_latency
        )

        # ── 6. Download MP4 ────────────────────────────────────────────────────
        self._download_file(video_url, cache_path)
        logger.info(
            "EP%02d s%s — Higgsfield asset saved: %s",
            request.episode, request.scene_id, cache_path
        )

        # ── 7. Probe and record ────────────────────────────────────────────────
        actual_duration = self._probe_duration(cache_path)
        resolution = self._probe_resolution(cache_path)

        entry = AssetManifestEntry(
            provider=self.name,
            model=model,
            asset_id=cache_key,
            task_id=request_id,
            scene_id=request.scene_id,
            prompt_hash=self._prompt_hash(request.prompt_intent),
            requested_duration=duration,
            actual_duration=actual_duration,
            resolution=resolution,
            estimated_cost_usd=estimated_cost,
            actual_cost_usd=0.0,   # Higgsfield does not return actual cost per call
            generation_latency_seconds=round(generation_latency, 2),
            cache_status="miss",
            file_path=str(cache_path),
            fallback_status="not_used",
        )
        self.last_manifest_entry = entry

        return GenerationResult(
            asset_path=str(cache_path),
            provider=self.name,
            model=model,
            actual_cost_usd=0.0,
            asset_id=cache_key,
            generation_type=request.generation_type,
            width=1080,
            height=1920,
            duration_seconds=actual_duration,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _auth_header(self) -> str:
        """Return the Authorization header value. Never logged."""
        return f"Key {self._key_id}:{self._key_secret}"

    def _post_generation(
        self,
        prompt: str,
        duration: float,
        aspect_ratio: str,   # kept in signature for caller compat; not sent in body
        model: str,          # kept in signature for caller compat; encoded in endpoint path
    ) -> str:
        """POST to T2V endpoint; return request_id string.

        Confirmed request schema (OpenAPI spec):
            prompt          str        required
            duration        int enum   [5, 10]  seconds
            cfg_scale       float      0..1     default 0.5
            negative_prompt str        optional

        Model and aspect_ratio are NOT accepted in the request body.
        Aspect ratio is set implicitly by the prompt for Kling 2.5-turbo Standard.
        """
        # Kling 2.5-turbo Standard accepts 5 or 10 seconds; clamp to nearest valid value.
        duration_int = 5 if int(round(duration)) <= 7 else 10
        payload = {
            "prompt": prompt,
            "duration": duration_int,
            "cfg_scale": 0.5,
            "negative_prompt": (
                "text, letters, numbers, words, captions, subtitles, "
                "watermark, logo, branding, UI, interface, typography, "
                "signage, labels"
            ),
        }
        body_bytes = json.dumps(payload).encode()
        req = urllib.request.Request(
            _T2V_ENDPOINT,
            data=body_bytes,
            headers={
                "Authorization": self._auth_header(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode(errors="replace")
            raise RuntimeError(
                f"Higgsfield T2V POST failed: HTTP {exc.code} — {body_text[:400]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Higgsfield T2V POST network error: {exc.reason}") from exc

        # Confirmed response shape (OpenAPI spec RequestStatus):
        # {"status": "queued", "request_id": "<uuid>", "status_url": "...", ...}
        request_id = data.get("request_id") or data.get("id")
        if not request_id:
            raise RuntimeError(
                f"Higgsfield T2V response missing request_id: {json.dumps(data)[:400]}"
            )
        return str(request_id)

    def _poll_until_done(self, request_id: str, episode: int, scene_id: str) -> str:
        """Poll universal status endpoint until request completes; return video URL.

        Confirmed status values (OpenAPI spec RequestStatus.status enum):
            queued | in_progress | nsfw | failed | completed | canceled

        Confirmed response shape on completion:
            {"status": "completed", "request_id": "...", "video": {"url": "..."}}
        """
        status_url = _STATUS_ENDPOINT_TPL.format(request_id=request_id)
        deadline = time.monotonic() + self._poll_timeout
        attempt = 0

        while time.monotonic() < deadline:
            attempt += 1
            req = urllib.request.Request(
                status_url,
                headers={
                    "Authorization": self._auth_header(),
                    "Accept": "application/json",
                },
                method="GET",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())
            except (urllib.error.URLError, urllib.error.HTTPError) as exc:
                logger.warning(
                    "EP%02d s%s — Higgsfield poll attempt %d failed: %s",
                    episode, scene_id, attempt, exc
                )
                time.sleep(self._poll_interval)
                continue

            # Confirmed: status is at the root of the response object.
            status = (data.get("status") or "").lower()

            logger.info(
                "EP%02d s%s — Higgsfield poll %d: status=%s",
                episode, scene_id, attempt, status
            )

            if status == "completed":
                # Confirmed shape: {"video": {"url": "..."}}
                video_obj = data.get("video") or {}
                video_url = video_obj.get("url")
                if not video_url:
                    raise RuntimeError(
                        f"Higgsfield request {request_id} completed but no video URL: "
                        f"{json.dumps(data)[:400]}"
                    )
                return str(video_url)

            if status in ("failed", "nsfw", "canceled"):
                error_msg = data.get("error") or status
                raise RuntimeError(
                    f"Higgsfield request {request_id} ended with status={status}: {error_msg}"
                )

            # Still queued or in_progress — wait and retry
            time.sleep(self._poll_interval)

        raise RuntimeError(
            f"Higgsfield request {request_id} timed out after {self._poll_timeout:.0f}s "
            f"({attempt} polls)"
        )

    def _download_file(self, url: str, dest: Path) -> None:
        """Download URL to dest path."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ai-bytes-pipeline/1.0"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                dest.write_bytes(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            raise RuntimeError(
                f"Higgsfield download failed for {url}: {exc}"
            ) from exc
        if dest.stat().st_size == 0:
            dest.unlink(missing_ok=True)
            raise RuntimeError(f"Higgsfield downloaded file is empty: {dest}")

    def _probe_duration(self, path: Path) -> Optional[float]:
        """Use PyAV (or fallback to ffprobe) to get video duration in seconds."""
        try:
            import av  # type: ignore[import-untyped]
            with av.open(str(path)) as container:
                return float(container.duration / av.time_base) if container.duration else None
        except Exception as exc:
            logger.warning("Could not probe duration for %s: %s", path, exc)
            return None

    def _probe_resolution(self, path: Path) -> Optional[str]:
        """Return 'WxH' string for the first video stream."""
        try:
            import av  # type: ignore[import-untyped]
            with av.open(str(path)) as container:
                for stream in container.streams.video:
                    return f"{stream.width}x{stream.height}"
        except Exception as exc:
            logger.warning("Could not probe resolution for %s: %s", path, exc)
        return None

    @staticmethod
    def _prompt_hash(prompt_intent: str) -> str:
        import hashlib
        return hashlib.sha256(prompt_intent.strip().lower().encode()).hexdigest()
