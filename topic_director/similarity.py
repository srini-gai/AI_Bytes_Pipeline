"""
Lightweight semantic similarity for topic deduplication.

Uses token-overlap (Jaccard) plus keyword matching against content pillars.
No external ML dependencies — designed for ~30–50 topic comparisons.
"""
from __future__ import annotations

import re
from topic_director.pillars import ContentPillar


_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "neither", "each", "every", "all", "any", "few", "more", "most",
    "some", "no", "if", "then", "than", "when", "where", "how", "what",
    "which", "who", "whom", "this", "that", "these", "those", "it", "its",
    "of", "in", "to", "for", "with", "on", "at", "from", "by", "about",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "once", "here", "there",
    "up", "down", "out", "off", "over", "own", "same", "very",
    "just", "also", "now", "only", "still", "already", "even",
    "why", "does", "your", "you", "they", "them", "we", "us",
})


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _STOP_WORDS and len(w) > 1}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def topic_similarity(topic_a: str, topic_b: str) -> float:
    """Return similarity score between 0 and 1 for two topic strings."""
    tokens_a = tokenize(topic_a)
    tokens_b = tokenize(topic_b)
    return jaccard_similarity(tokens_a, tokens_b)


def classify_pillar(topic: str, pillars: list[ContentPillar]) -> list[tuple[str, float]]:
    """Return pillars sorted by relevance score (descending)."""
    topic_lower = topic.lower()
    topic_tokens = tokenize(topic)
    scores: list[tuple[str, float]] = []
    for pillar in pillars:
        # Substring match against raw keywords for multi-word terms
        substr_hits = sum(1 for kw in pillar.keywords if kw in topic_lower)
        # Token overlap for single-word matches
        pillar_tokens = tokenize(" ".join(pillar.keywords))
        token_hits = len(topic_tokens & pillar_tokens)
        # Combine: substring hits weighted higher (they match intent better)
        score = (substr_hits * 2 + token_hits) / max(len(topic_tokens) + len(pillar.keywords), 1)
        scores.append((pillar.name, score))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def best_pillar(topic: str, pillars: list[ContentPillar]) -> str:
    """Return the single best-matching pillar name for a topic."""
    ranked = classify_pillar(topic, pillars)
    if ranked and ranked[0][1] > 0:
        return ranked[0][0]
    return "Uncategorized"


def find_nearest_topic(
    candidate: str,
    existing_topics: list[str],
) -> tuple[str, float]:
    """Find the most similar existing topic and its similarity score."""
    best_topic = ""
    best_score = 0.0
    for existing in existing_topics:
        score = topic_similarity(candidate, existing)
        if score > best_score:
            best_score = score
            best_topic = existing
    return best_topic, best_score
