"""
Multi-dimensional topic scoring for candidate evaluation.

Each dimension returns 0.0–1.0. Final score is a weighted average.
"""
from __future__ import annotations

from dataclasses import dataclass
from topic_director.pillars import ChannelStrategy, ContentPillar
from topic_director.similarity import (
    best_pillar,
    classify_pillar,
    find_nearest_topic,
    tokenize,
)


@dataclass
class TopicScore:
    topic: str
    pillar: str
    difficulty: str
    content_type: str
    channel_fit: float
    novelty: float
    accessibility: float
    shorts_suitability: float
    hook_strength: float
    visual_potential: float
    strategic_balance: float
    total: float
    reason: str
    nearest_existing: str
    nearest_similarity: float


WEIGHTS = {
    "channel_fit": 0.15,
    "novelty": 0.25,
    "accessibility": 0.10,
    "shorts_suitability": 0.15,
    "hook_strength": 0.15,
    "visual_potential": 0.10,
    "strategic_balance": 0.10,
}

DIFFICULTY_KEYWORDS = {
    "beginner": {"what", "basic", "introduction", "intro", "101", "simple",
                 "explain", "fundamentals", "beginner", "overview", "first"},
    "advanced": {"advanced", "architecture", "optimize", "scale", "internal",
                 "deep dive", "under the hood", "implement", "benchmark",
                 "distributed", "fine-tune", "rlhf"},
}

TIMELY_KEYWORDS = {"latest", "new", "update", "release", "announce", "launch",
                   "2025", "2026", "trend", "breaking", "just"}

EXPERIMENTAL_KEYWORDS = {"experimental", "speculative", "future", "predict",
                         "imagine", "next generation", "prototype"}

HOOK_SIGNALS = {"why", "how", "secret", "mistake", "myth", "actually", "really",
                "truth", "never", "always", "wrong", "hidden", "surprising",
                "nobody", "everyone", "stop", "dont", "can't", "impossible"}

VISUAL_SIGNALS = {"visual", "diagram", "flow", "architecture", "pipeline",
                  "process", "step", "layer", "transform", "graph", "map",
                  "compare", "versus", "vs", "before", "after", "build"}


def _score_channel_fit(topic: str, strategy: ChannelStrategy) -> float:
    ranked = classify_pillar(topic, strategy.pillars)
    if not ranked:
        return 0.3
    top_score = ranked[0][1]
    return min(0.3 + top_score * 0.7, 1.0)


def _score_novelty(topic: str, existing_topics: list[str]) -> tuple[float, str, float]:
    if not existing_topics:
        return 1.0, "", 0.0
    nearest, similarity = find_nearest_topic(topic, existing_topics)
    if similarity >= 0.6:
        novelty = 0.1
    elif similarity >= 0.4:
        novelty = 0.5
    elif similarity >= 0.25:
        novelty = 0.75
    else:
        novelty = 1.0
    return novelty, nearest, similarity


def _classify_difficulty(topic: str) -> str:
    tokens = tokenize(topic)
    beginner_hits = len(tokens & DIFFICULTY_KEYWORDS["beginner"])
    advanced_hits = len(tokens & DIFFICULTY_KEYWORDS["advanced"])
    if advanced_hits > beginner_hits:
        return "advanced"
    if beginner_hits > 0:
        return "beginner"
    return "intermediate"


def _score_accessibility(difficulty: str, difficulty_dist: dict[str, int],
                         targets: dict[str, float]) -> float:
    total = sum(difficulty_dist.values()) or 1
    current_ratio = difficulty_dist.get(difficulty, 0) / total
    target_ratio = targets.get(difficulty, 0.33)
    if current_ratio < target_ratio:
        return 0.9
    elif current_ratio < target_ratio * 1.5:
        return 0.6
    return 0.3


def _score_shorts_suitability(topic: str) -> float:
    word_count = len(topic.split())
    if word_count > 12:
        return 0.3
    if word_count > 8:
        return 0.5
    if word_count <= 2:
        return 0.6
    return 0.8


def _score_hook_strength(topic: str) -> float:
    tokens = tokenize(topic)
    hook_hits = len(tokens & HOOK_SIGNALS)
    lower = topic.lower()
    bonus = 0.0
    if lower.startswith("why ") or lower.startswith("how "):
        bonus = 0.2
    if "?" in topic:
        bonus += 0.1
    base = min(hook_hits * 0.2, 0.6)
    return min(base + bonus + 0.3, 1.0)


def _score_visual_potential(topic: str) -> float:
    tokens = tokenize(topic)
    visual_hits = len(tokens & VISUAL_SIGNALS)
    return min(0.4 + visual_hits * 0.15, 1.0)


def _classify_content_type(topic: str) -> str:
    lower = topic.lower()
    if any(kw in lower for kw in TIMELY_KEYWORDS):
        return "TIMELY"
    if any(kw in lower for kw in EXPERIMENTAL_KEYWORDS):
        return "EXPERIMENTAL"
    return "EVERGREEN"


def score_topic(
    topic: str,
    strategy: ChannelStrategy,
    existing_topics: list[str],
    difficulty_dist: dict[str, int],
    pillar_dist: dict[str, int],
) -> TopicScore:
    """Score a single topic candidate across all dimensions."""
    pillar = best_pillar(topic, strategy.pillars)
    difficulty = _classify_difficulty(topic)
    content_type = _classify_content_type(topic)

    channel_fit = _score_channel_fit(topic, strategy)
    novelty, nearest, nearest_sim = _score_novelty(topic, existing_topics)
    accessibility = _score_accessibility(difficulty, difficulty_dist, strategy.difficulty_targets)
    shorts_suit = _score_shorts_suitability(topic)
    hook = _score_hook_strength(topic)
    visual = _score_visual_potential(topic)

    total_pillar = sum(pillar_dist.values()) or 1
    pillar_ratio = pillar_dist.get(pillar, 0) / total_pillar
    strategic_balance = 0.9 if pillar_ratio < 0.2 else (0.5 if pillar_ratio < 0.35 else 0.2)

    dims = {
        "channel_fit": channel_fit,
        "novelty": novelty,
        "accessibility": accessibility,
        "shorts_suitability": shorts_suit,
        "hook_strength": hook,
        "visual_potential": visual,
        "strategic_balance": strategic_balance,
    }
    total = sum(dims[k] * WEIGHTS[k] for k in WEIGHTS)

    reason_parts = []
    if novelty < 0.3:
        reason_parts.append(f"too similar to '{nearest}'")
    if channel_fit > 0.7:
        reason_parts.append(f"strong {pillar} fit")
    if hook > 0.7:
        reason_parts.append("compelling hook")
    if strategic_balance > 0.7:
        reason_parts.append("fills underrepresented pillar")
    reason = "; ".join(reason_parts) if reason_parts else "balanced candidate"

    return TopicScore(
        topic=topic,
        pillar=pillar,
        difficulty=difficulty,
        content_type=content_type,
        channel_fit=channel_fit,
        novelty=novelty,
        accessibility=accessibility,
        shorts_suitability=shorts_suit,
        hook_strength=hook,
        visual_potential=visual,
        strategic_balance=strategic_balance,
        total=total,
        reason=reason,
        nearest_existing=nearest,
        nearest_similarity=nearest_sim,
    )
