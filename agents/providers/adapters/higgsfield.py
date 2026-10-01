"""
adapters/higgsfield.py — Higgsfield video generation adapter stub.

Phase 3A: interface definition only — no API calls.
Phase 3B: implement generate() with live Higgsfield API.

Env vars (Phase 3B):
    HIGGSFIELD_API_KEY
    HIGGSFIELD_MODEL   (default: "higgsfield-v1")
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from agents.providers.base import (
    GenerationRequest,
    GenerationResult,
    GenerationType,
    VideoGenerationProvider,
    make_cache_key,
)

logger = logging.getLogger(__name__)

# Planning cost estimate per second of video — not authoritative provider pricing.
# Update when actual Higgsfield pricing is confirmed.
_COST_PER_SECOND_USD = 0.08


class HiggsfieldAdapter(VideoGenerationProvider):
    """
    Higgsfield video generation — Phase 3A stub.

    generate() raises NotImplementedError until Phase 3B.
    estimate_cost() returns a planning estimate only.
    is_available() checks for API key presence.
    """

    @property
    def name(self) -> str:
        return "higgsfield"

    @property
    def default_model(self) -> str:
        return os.getenv("HIGGSFIELD_MODEL", "higgsfield-v1")

    def is_available(self) -> bool:
        key = os.getenv("HIGGSFIELD_API_KEY", "")
        return bool(key) and "your-" not in key

    def estimate_cost(self, request: GenerationRequest) -> float:
        """Planning estimate only — not authoritative."""
        duration = request.duration_seconds or 4.0
        return round(duration * _COST_PER_SECOND_USD, 4)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        raise NotImplementedError(
            "HiggsfieldAdapter.generate() is not implemented in Phase 3A. "
            "Integrate live API in Phase 3B."
        )
