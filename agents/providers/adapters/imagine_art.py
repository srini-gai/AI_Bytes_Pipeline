"""
adapters/imagine_art.py — ImagineArt image/video generation adapter stub.

Phase 3A: interface definition only — no API calls.
Phase 3B: implement generate() with live ImagineArt API.

Env vars (Phase 3B):
    IMAGINE_ART_API_KEY
    IMAGINE_ART_MODEL   (default: "imagineart-v1")
"""

from __future__ import annotations

import logging
import os

from agents.providers.base import (
    GenerationRequest,
    GenerationResult,
    GenerationType,
    ImageGenerationProvider,
    make_cache_key,
)

logger = logging.getLogger(__name__)

# Planning cost estimates — not authoritative provider pricing.
_IMAGE_COST_USD = 0.06
_VIDEO_COST_PER_SECOND_USD = 0.07


class ImagineArtImageAdapter(ImageGenerationProvider):
    """
    ImagineArt image generation — Phase 3A stub.
    """

    @property
    def name(self) -> str:
        return "imagineart"

    @property
    def default_model(self) -> str:
        return os.getenv("IMAGINE_ART_MODEL", "imagineart-v1")

    def is_available(self) -> bool:
        key = os.getenv("IMAGINE_ART_API_KEY", "")
        return bool(key) and "your-" not in key

    def estimate_cost(self, request: GenerationRequest) -> float:
        return _IMAGE_COST_USD

    def generate(self, request: GenerationRequest) -> GenerationResult:
        raise NotImplementedError(
            "ImagineArtImageAdapter.generate() is not implemented in Phase 3A."
        )
