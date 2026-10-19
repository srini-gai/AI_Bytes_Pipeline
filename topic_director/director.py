"""
Topic Director — generates, scores, and ranks topic candidates
for a channel, then recommends the next N episodes.

Reads the production queue for historical awareness.
Persists planning runs for auditability.
Does NOT add topics to the production queue automatically.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from production_queue.queue import ProductionQueue
from topic_director.pillars import ChannelStrategy, get_strategy
from topic_director.scorer import TopicScore, score_topic
from topic_director.similarity import (
    best_pillar,
    find_nearest_topic,
    topic_similarity,
)

logger = logging.getLogger(__name__)

HISTORY_DIR = Path(__file__).parent


# ── Candidate pool ──────────────────────────────────────────────────────

CANDIDATE_POOL: dict[str, list[str]] = {
    "srini_on_ai": [
        "What Is a Transformer — The Architecture Behind Every LLM",
        "How Attention Mechanisms Let AI Focus on What Matters",
        "Why AI Gets Confused by Long Conversations — Context Window Limits",
        "What Happens When You Send a Prompt to an LLM",
        "How Vector Databases Power AI Search",
        "Why Smaller AI Models Are Getting Smarter — Distillation Explained",
        "What Is Chain-of-Thought Reasoning in AI",
        "How AI Agents Decide What To Do Next — Planning and ReAct",
        "Why Fine-Tuning Changes How an AI Thinks",
        "How Embeddings Turn Words Into Numbers AI Understands",
        "What Is RLHF — How Humans Teach AI Right From Wrong",
        "Why AI Tokens Cost Money — The Economics of Inference",
        "How Multi-Agent Systems Solve Complex Problems Together",
        "What Is Prompt Engineering — and Does It Actually Work",
        "How AI Guardrails Prevent Dangerous Outputs",
        "Why Mixture of Experts Makes AI Faster and Cheaper",
        "How Retrieval Augmented Generation Keeps AI Grounded in Facts",
        "What Is an AI Benchmark — and Why Should You Care",
        "How Semantic Search Finds Meaning Not Just Keywords",
        "Why Temperature and Top-P Change How AI Writes",
    ],
}


def _get_existing_topics(queue: ProductionQueue) -> list[str]:
    return [e.topic for e in queue.list_all()]


def _build_distributions(
    existing_topics: list[str],
    strategy: ChannelStrategy,
) -> tuple[dict[str, int], dict[str, int]]:
    """Build difficulty and pillar distributions from existing topics."""
    from topic_director.scorer import _classify_difficulty

    difficulty_dist: dict[str, int] = {"beginner": 0, "intermediate": 0, "advanced": 0}
    pillar_dist: dict[str, int] = {p.name: 0 for p in strategy.pillars}

    for topic in existing_topics:
        diff = _classify_difficulty(topic)
        difficulty_dist[diff] = difficulty_dist.get(diff, 0) + 1
        pil = best_pillar(topic, strategy.pillars)
        pillar_dist[pil] = pillar_dist.get(pil, 0) + 1

    return difficulty_dist, pillar_dist


# ── Duplicate filtering ─────────────────────────────────────────────────

SIMILARITY_THRESHOLD = 0.35


def _filter_duplicates(
    candidates: list[str],
    existing_topics: list[str],
) -> list[tuple[str, str, float]]:
    """Return (candidate, nearest_existing, similarity) for near-duplicates."""
    dupes: list[tuple[str, str, float]] = []
    for c in candidates:
        nearest, sim = find_nearest_topic(c, existing_topics)
        if sim >= SIMILARITY_THRESHOLD:
            dupes.append((c, nearest, sim))
    return dupes


# ── Sequence diversity ──────────────────────────────────────────────────

def _evaluate_sequence_diversity(scored: list[TopicScore]) -> float:
    """Return 0–1 score for how diverse a sequence of topics is."""
    if len(scored) <= 1:
        return 1.0

    penalties = 0.0
    max_penalties = 0.0

    # Pillar diversity
    pillars = [s.pillar for s in scored]
    unique_pillars = len(set(pillars))
    max_penalties += 1.0
    if unique_pillars < len(scored) * 0.6:
        penalties += 0.5
    if unique_pillars <= 2:
        penalties += 0.5

    # Consecutive same-pillar
    for i in range(1, len(pillars)):
        max_penalties += 0.3
        if pillars[i] == pillars[i - 1]:
            penalties += 0.3

    # Difficulty spread
    diffs = [s.difficulty for s in scored]
    unique_diffs = len(set(diffs))
    max_penalties += 0.5
    if unique_diffs == 1:
        penalties += 0.5
    elif unique_diffs == 2 and len(scored) >= 4:
        penalties += 0.2

    # Content type spread
    types = [s.content_type for s in scored]
    max_penalties += 0.3
    if len(set(types)) == 1 and len(scored) >= 4:
        penalties += 0.3

    if max_penalties == 0:
        return 1.0
    return max(0.0, 1.0 - penalties / max_penalties)


def _optimize_sequence(scored: list[TopicScore], top_n: int) -> list[TopicScore]:
    """Select top_n from scored, optimizing for both score and sequence diversity."""
    if len(scored) <= top_n:
        return scored

    # Start with the highest-scored topic
    selected: list[TopicScore] = [scored[0]]
    remaining = list(scored[1:])

    while len(selected) < top_n and remaining:
        best_idx = 0
        best_combined = -1.0
        for i, candidate in enumerate(remaining):
            trial = selected + [candidate]
            diversity = _evaluate_sequence_diversity(trial)
            combined = candidate.total * 0.6 + diversity * 0.4
            if combined > best_combined:
                best_combined = combined
                best_idx = i
        selected.append(remaining.pop(best_idx))

    return selected


# ── Planning run ────────────────────────────────────────────────────────

def _save_planning_run(
    channel_id: str,
    candidates: list[TopicScore],
    recommended: list[TopicScore],
    rejected: list[tuple[str, str]],
    diversity_score: float,
) -> Path:
    """Persist a planning run for auditability."""
    channel_dir = HISTORY_DIR / channel_id
    channel_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_file = channel_dir / f"run_{timestamp}.json"

    data = {
        "timestamp": timestamp,
        "channel_id": channel_id,
        "candidates_evaluated": len(candidates),
        "candidates": [
            {
                "topic": c.topic,
                "pillar": c.pillar,
                "difficulty": c.difficulty,
                "content_type": c.content_type,
                "total_score": round(c.total, 3),
                "channel_fit": round(c.channel_fit, 3),
                "novelty": round(c.novelty, 3),
                "accessibility": round(c.accessibility, 3),
                "shorts_suitability": round(c.shorts_suitability, 3),
                "hook_strength": round(c.hook_strength, 3),
                "visual_potential": round(c.visual_potential, 3),
                "strategic_balance": round(c.strategic_balance, 3),
                "nearest_existing": c.nearest_existing,
                "nearest_similarity": round(c.nearest_similarity, 3),
                "reason": c.reason,
            }
            for c in candidates
        ],
        "recommended": [
            {
                "rank": i + 1,
                "topic": r.topic,
                "pillar": r.pillar,
                "difficulty": r.difficulty,
                "content_type": r.content_type,
                "total_score": round(r.total, 3),
                "reason": r.reason,
                "nearest_existing": r.nearest_existing,
                "nearest_similarity": round(r.nearest_similarity, 3),
            }
            for i, r in enumerate(recommended)
        ],
        "rejected_duplicates": [
            {"topic": t, "reason": r} for t, r in rejected
        ],
        "sequence_diversity_score": round(diversity_score, 3),
        "approval_status": "pending",
    }

    run_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Planning run saved: {run_file}")
    return run_file


def _load_latest_run(channel_id: str) -> Optional[dict]:
    channel_dir = HISTORY_DIR / channel_id
    if not channel_dir.exists():
        return None
    runs = sorted(channel_dir.glob("run_*.json"), reverse=True)
    if not runs:
        return None
    return json.loads(runs[0].read_text(encoding="utf-8"))


def _load_run_by_timestamp(channel_id: str, timestamp: str) -> Optional[dict]:
    run_file = HISTORY_DIR / channel_id / f"run_{timestamp}.json"
    if not run_file.exists():
        return None
    return json.loads(run_file.read_text(encoding="utf-8"))


def list_runs(channel_id: str) -> list[dict]:
    channel_dir = HISTORY_DIR / channel_id
    if not channel_dir.exists():
        return []
    runs = []
    for f in sorted(channel_dir.glob("run_*.json"), reverse=True):
        data = json.loads(f.read_text(encoding="utf-8"))
        runs.append({
            "timestamp": data["timestamp"],
            "candidates_evaluated": data["candidates_evaluated"],
            "recommended_count": len(data["recommended"]),
            "approval_status": data.get("approval_status", "unknown"),
        })
    return runs


# ── Main planning operations ────────────────────────────────────────────

def plan(
    channel_id: str = "srini_on_ai",
    recommend_count: int = 5,
) -> dict:
    """
    Run a full planning cycle:
    1. Load channel strategy and production queue
    2. Generate ~15 candidates
    3. Filter duplicates
    4. Score remaining candidates
    5. Optimize sequence for diversity
    6. Return top N recommendations (NOT added to queue)
    """
    strategy = get_strategy(channel_id)
    queue = ProductionQueue(channel_id)
    existing_topics = _get_existing_topics(queue)

    # Get candidate pool
    pool = CANDIDATE_POOL.get(channel_id, [])
    if not pool:
        raise ValueError(f"No candidate pool defined for channel '{channel_id}'")

    # Filter near-duplicates
    dupes = _filter_duplicates(pool, existing_topics)
    dupe_topics = {d[0] for d in dupes}
    rejected = [(t, f"too similar to '{nearest}' (sim={sim:.2f})") for t, nearest, sim in dupes]
    filtered = [t for t in pool if t not in dupe_topics]

    # Build distributions from existing history
    difficulty_dist, pillar_dist = _build_distributions(existing_topics, strategy)

    # Score all surviving candidates
    scored = []
    for topic in filtered:
        s = score_topic(topic, strategy, existing_topics, difficulty_dist, pillar_dist)
        scored.append(s)

    # Sort by total score descending
    scored.sort(key=lambda s: s.total, reverse=True)

    # Optimize sequence for diversity
    recommended = _optimize_sequence(scored, recommend_count)
    diversity = _evaluate_sequence_diversity(recommended)

    # Persist planning run
    run_file = _save_planning_run(channel_id, scored, recommended, rejected, diversity)

    return {
        "channel_id": channel_id,
        "candidates_evaluated": len(pool),
        "duplicates_filtered": len(rejected),
        "candidates_scored": len(scored),
        "recommended_count": len(recommended),
        "sequence_diversity": round(diversity, 3),
        "run_file": str(run_file),
        "recommendations": [
            {
                "rank": i + 1,
                "topic": r.topic,
                "pillar": r.pillar,
                "difficulty": r.difficulty,
                "content_type": r.content_type,
                "score": round(r.total, 3),
                "reason": r.reason,
                "nearest_existing": r.nearest_existing,
                "nearest_similarity": round(r.nearest_similarity, 3),
            }
            for i, r in enumerate(recommended)
        ],
        "rejected_duplicates": rejected,
    }


def get_recommendations(channel_id: str = "srini_on_ai") -> Optional[list[dict]]:
    """Return the latest pending recommendations for a channel."""
    run = _load_latest_run(channel_id)
    if not run:
        return None
    return run.get("recommended", [])


def approve_topic(
    channel_id: str,
    topic: str,
    *,
    run_timestamp: Optional[str] = None,
) -> dict:
    """
    Approve a specific topic from a planning run into the production queue.
    Returns the new queue entry details.
    """
    # Load the run
    if run_timestamp:
        run = _load_run_by_timestamp(channel_id, run_timestamp)
    else:
        run = _load_latest_run(channel_id)

    if not run:
        raise ValueError(f"No planning run found for {channel_id}")

    # Verify topic is in recommendations
    rec_topics = [r["topic"] for r in run["recommended"]]
    if topic not in rec_topics:
        raise ValueError(f"Topic '{topic}' not in latest recommendations")

    # Add to production queue
    queue = ProductionQueue(channel_id)

    # Check if already in queue
    if queue._topic_exists(topic):
        raise ValueError(f"Topic '{topic}' already exists in production queue")

    eid = queue._next_queue_id()
    from production_queue.queue import QueueEntry
    entry = QueueEntry(
        channel_id=channel_id,
        episode_id=eid,
        topic=topic,
        priority=len(queue._entries) + 1,
        source="topic_director",
    )
    queue._entries.append(entry)
    queue._save()
    logger.info(f"Approved topic into queue: {eid} — {topic}")

    # Update run file approval status
    run_ts = run["timestamp"]
    run_file = HISTORY_DIR / channel_id / f"run_{run_ts}.json"
    for rec in run["recommended"]:
        if rec["topic"] == topic:
            rec["approved"] = True
            rec["queue_id"] = eid
            break
    all_approved = all(r.get("approved") for r in run["recommended"])
    run["approval_status"] = "fully_approved" if all_approved else "partially_approved"
    run_file.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "episode_id": eid,
        "topic": topic,
        "channel_id": channel_id,
        "status": "QUEUED",
    }


def reject_topic(
    channel_id: str,
    topic: str,
    *,
    reason: str = "",
    run_timestamp: Optional[str] = None,
) -> dict:
    """Reject a topic from a planning run (does not add to queue)."""
    if run_timestamp:
        run = _load_run_by_timestamp(channel_id, run_timestamp)
    else:
        run = _load_latest_run(channel_id)

    if not run:
        raise ValueError(f"No planning run found for {channel_id}")

    rec_topics = [r["topic"] for r in run["recommended"]]
    if topic not in rec_topics:
        raise ValueError(f"Topic '{topic}' not in latest recommendations")

    run_ts = run["timestamp"]
    run_file = HISTORY_DIR / channel_id / f"run_{run_ts}.json"
    for rec in run["recommended"]:
        if rec["topic"] == topic:
            rec["rejected"] = True
            rec["rejection_reason"] = reason
            break
    run_file.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"topic": topic, "status": "rejected", "reason": reason}
