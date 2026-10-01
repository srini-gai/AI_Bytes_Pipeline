"""
providers/base.py — Abstract interfaces for all asset generation providers.

Phase 3A: interface definitions only.
No paid API calls are made anywhere in this module.

Architecture:
    AssetPlanner
        ├── RemotionRenderer          (deterministic — always available)
        ├── ImageGenerationProvider   (abstract)
        │       └── [adapters: phase 3B]
        └── VideoGenerationProvider   (abstract)
                └── [adapters: phase 3B]
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Renderer / asset source taxonomy ─────────────────────────────────────────

class AssetSource(str, Enum):
    """How the visual layer for a scene is produced."""
    REMOTION_ONLY     = "REMOTION_ONLY"      # Fully deterministic — default
    AI_IMAGE          = "AI_IMAGE"           # AI-generated still + Remotion overlay/animation
    GENERATIVE_VIDEO  = "GENERATIVE_VIDEO"   # AI-generated short video clip + Remotion overlay


class GenerationType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


# ── Generation request / result ───────────────────────────────────────────────

@dataclass
class GenerationRequest:
    """
    A provider-neutral generation request.

    Prompt intent is written in English for clarity, but the requested
    generated output must contain NO visible text (enforced via
    `embedded_text_required=False` and provider-level instruction).
    """
    # Identity
    scene_id: str
    episode: int
    week: int
    generation_type: GenerationType

    # Intent
    prompt_intent: str          # English description of visual intent
    language_neutral: bool      # Must be True for all generative assets
    embedded_text_required: bool = False  # Always False — text via Remotion overlay

    # Provider instruction suffix appended to every prompt:
    # "No visible text, letters, numbers, logos, watermarks, UI labels,
    #  subtitles, or signage. Text will be added in post-production."

    # Technical
    aspect_ratio: str = "9:16"            # Shorts always 9:16
    duration_seconds: Optional[float] = None  # Video only; None for images

    # Provider selection (resolved at runtime; None = any available)
    provider: Optional[str] = None
    model:    Optional[str] = None

    # Visual continuity hints (for Remotion overlay compositor)
    entry_direction:       Optional[str] = None   # e.g. "center", "left"
    exit_direction:        Optional[str] = None
    dominant_color_family: Optional[str] = None   # e.g. "dark-purple"
    motion_direction:      Optional[str] = None   # e.g. "push-in"
    transition_intent:     Optional[str] = None


@dataclass
class GenerationResult:
    """Result returned by a provider after a successful generation."""
    asset_path: str            # Absolute path to the generated file
    provider: str
    model: str
    actual_cost_usd: float     # 0.0 during Phase 3A (no paid calls)
    asset_id: str              # Deterministic cache key (SHA-256)
    generation_type: GenerationType
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None


# ── Cache key ─────────────────────────────────────────────────────────────────

def make_cache_key(
    prompt_intent: str,
    provider: str,
    model: str,
    generation_type: GenerationType,
    aspect_ratio: str,
    duration_seconds: Optional[float] = None,
    seed: Optional[int] = None,
) -> str:
    """
    Derive a deterministic cache key from generation intent.

    Key is intentionally NOT derived from scene_id or episode number:
    language-neutral assets with identical intent (EN vs TA) resolve
    to the same cache entry — no duplicate generation cost.

    Key components:
        - normalized prompt (lowercased, stripped)
        - provider
        - model
        - generation type
        - aspect ratio
        - duration (video only)
        - seed (when provider supports deterministic generation)
    """
    normalized_prompt = prompt_intent.strip().lower()

    payload: dict = {
        "prompt": normalized_prompt,
        "provider": provider,
        "model": model,
        "type": generation_type.value,
        "aspect_ratio": aspect_ratio,
    }
    if duration_seconds is not None:
        payload["duration_seconds"] = round(duration_seconds, 2)
    if seed is not None:
        payload["seed"] = seed

    canonical = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ── Abstract provider interfaces ──────────────────────────────────────────────

class VideoGenerationProvider(ABC):
    """
    Abstract interface for all video generation providers.

    Implementations: HiggsfieldAdapter, ImagineArtAdapter (Phase 3B stubs).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'higgsfield', 'imagineart')."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model name for this provider."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if provider credentials are configured and reachable."""
        ...

    @abstractmethod
    def estimate_cost(self, request: GenerationRequest) -> float:
        """
        Return a planning cost estimate in USD for this request.

        This is a PLANNING ESTIMATE, not authoritative pricing.
        Actual cost is recorded on the GenerationResult after generation.
        """
        ...

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        Execute generation and return the result.

        Must NOT be called during Phase 3A.
        Must check is_available() before calling.
        Must save asset to cache directory.
        """
        ...


class ImageGenerationProvider(ABC):
    """
    Abstract interface for all image generation providers.

    Implementations added in Phase 3B.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def default_model(self) -> str: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def estimate_cost(self, request: GenerationRequest) -> float: ...

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult: ...
