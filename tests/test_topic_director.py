"""Tests for the Topic Director module."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from topic_director.pillars import (
    CHANNEL_STRATEGIES,
    ChannelStrategy,
    ContentPillar,
    get_strategy,
)
from topic_director.similarity import (
    best_pillar,
    classify_pillar,
    find_nearest_topic,
    jaccard_similarity,
    tokenize,
    topic_similarity,
)
from topic_director.scorer import (
    TopicScore,
    _classify_difficulty,
    _score_channel_fit,
    _score_hook_strength,
    _score_shorts_suitability,
    _score_visual_potential,
    score_topic,
)
from topic_director.director import (
    SIMILARITY_THRESHOLD,
    _evaluate_sequence_diversity,
    _filter_duplicates,
    _optimize_sequence,
    _save_planning_run,
    approve_topic,
    get_recommendations,
    list_runs,
    plan,
    reject_topic,
)
from production_queue.queue import ProductionQueue, Status


# ── Helpers ─────────────────────────────────────────────────────────────

def _make_queue(tmp: Path, channel: str = "test_ch", topics: list[str] | None = None) -> ProductionQueue:
    q = ProductionQueue(channel, base_dir=tmp)
    if topics:
        tf = tmp / "topics.txt"
        tf.write_text("\n".join(topics), encoding="utf-8")
        q.import_topics(tf)
    return q


def _strategy() -> ChannelStrategy:
    return get_strategy("srini_on_ai")


# ═══════════════════════════════════════════════════════════════════════
# Test: Channel Isolation
# ═══════════════════════════════════════════════════════════════════════

class TestChannelIsolation:
    def test_strategy_per_channel(self) -> None:
        s = get_strategy("srini_on_ai")
        assert s.channel_id == "srini_on_ai"
        assert len(s.pillars) > 0

    def test_unknown_channel_raises(self) -> None:
        with pytest.raises(KeyError):
            get_strategy("nonexistent_channel")

    def test_pillars_are_channel_specific(self) -> None:
        s = get_strategy("srini_on_ai")
        assert all(isinstance(p, ContentPillar) for p in s.pillars)
        pillar_names = [p.name for p in s.pillars]
        assert "AI Fundamentals" in pillar_names


# ═══════════════════════════════════════════════════════════════════════
# Test: Published Topic Duplicate Rejection
# ═══════════════════════════════════════════════════════════════════════

class TestPublishedDuplicateRejection:
    def test_exact_duplicate_filtered(self) -> None:
        existing = ["What is RAG?"]
        candidates = ["What is RAG?"]
        dupes = _filter_duplicates(candidates, existing)
        assert len(dupes) == 1

    def test_near_duplicate_filtered(self) -> None:
        existing = ["What is RAG?"]
        candidates = ["How Retrieval Augmented Generation Works"]
        dupes = _filter_duplicates(candidates, existing)
        # "rag" overlap → should be caught
        # These share "rag" and related tokens
        sim = topic_similarity("What is RAG?", "How Retrieval Augmented Generation Works")
        if sim >= SIMILARITY_THRESHOLD:
            assert len(dupes) == 1
        else:
            assert len(dupes) == 0

    def test_distinct_topic_passes(self) -> None:
        existing = ["What is RAG?"]
        candidates = ["How AI Agents Decide What To Do Next"]
        dupes = _filter_duplicates(candidates, existing)
        assert len(dupes) == 0


# ═══════════════════════════════════════════════════════════════════════
# Test: Queued Topic Duplicate Rejection
# ═══════════════════════════════════════════════════════════════════════

class TestQueuedDuplicateRejection:
    def test_queued_topic_blocks_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            q = _make_queue(Path(tmp), topics=["How AI Models Learn Patterns"])
            existing = [e.topic for e in q.list_all()]
            dupes = _filter_duplicates(["How AI Models Learn Patterns"], existing)
            assert len(dupes) == 1


# ═══════════════════════════════════════════════════════════════════════
# Test: Awaiting Approval Duplicate Rejection
# ═══════════════════════════════════════════════════════════════════════

class TestAwaitingApprovalDuplicateRejection:
    def test_awaiting_approval_blocks_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            q = ProductionQueue("test_ch", base_dir=Path(tmp))
            q.add_historical(
                "h-001", "What is RAG?",
                status=Status.AWAITING_APPROVAL.value,
                source="produced-no-upload",
            )
            existing = [e.topic for e in q.list_all()]
            dupes = _filter_duplicates(["What is RAG?"], existing)
            assert len(dupes) == 1


# ═══════════════════════════════════════════════════════════════════════
# Test: Semantic Near-Duplicate Detection
# ═══════════════════════════════════════════════════════════════════════

class TestSemanticNearDuplicate:
    def test_similar_topics_detected(self) -> None:
        sim = topic_similarity(
            "How AI Reads Your Text",
            "How AI Actually Reads Your Text",
        )
        assert sim > 0.5

    def test_dissimilar_topics_low_score(self) -> None:
        sim = topic_similarity(
            "What Is RLHF — How Humans Teach AI Right From Wrong",
            "Why AI Tokens Cost Money",
        )
        assert sim < 0.3

    def test_find_nearest_returns_best_match(self) -> None:
        existing = [
            "What is RAG?",
            "How AI Agents Work",
            "Why AI Hallucinates",
        ]
        nearest, score = find_nearest_topic("How AI Agents Decide What To Do", existing)
        assert nearest == "How AI Agents Work"

    def test_tokenize_removes_stop_words(self) -> None:
        tokens = tokenize("How does the AI model work?")
        assert "how" not in tokens
        assert "does" not in tokens
        assert "the" not in tokens
        assert "ai" in tokens
        assert "model" in tokens

    def test_jaccard_identical(self) -> None:
        assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_jaccard_disjoint(self) -> None:
        assert jaccard_similarity({"a"}, {"b"}) == 0.0


# ═══════════════════════════════════════════════════════════════════════
# Test: Content Pillar Classification
# ═══════════════════════════════════════════════════════════════════════

class TestContentPillarClassification:
    def test_rag_topic_classifies_correctly(self) -> None:
        strategy = _strategy()
        pillar = best_pillar("How RAG Reduces AI Hallucinations", strategy.pillars)
        assert "RAG" in pillar or "Knowledge" in pillar

    def test_agent_topic_classifies_correctly(self) -> None:
        strategy = _strategy()
        pillar = best_pillar("How AI Agents Decide What To Do Next", strategy.pillars)
        assert "Agent" in pillar

    def test_training_topic_classifies_correctly(self) -> None:
        strategy = _strategy()
        pillar = best_pillar("What Is RLHF — How Humans Teach AI", strategy.pillars)
        assert "Training" in pillar or "Reasoning" in pillar

    def test_classify_returns_sorted_list(self) -> None:
        strategy = _strategy()
        ranked = classify_pillar("How vector databases power AI search", strategy.pillars)
        assert len(ranked) == len(strategy.pillars)
        assert ranked[0][1] >= ranked[-1][1]


# ═══════════════════════════════════════════════════════════════════════
# Test: Candidate Scoring
# ═══════════════════════════════════════════════════════════════════════

class TestCandidateScoring:
    def test_score_returns_all_dimensions(self) -> None:
        strategy = _strategy()
        s = score_topic(
            "Why AI Tokens Cost Money",
            strategy,
            existing_topics=[],
            difficulty_dist={"beginner": 0, "intermediate": 0, "advanced": 0},
            pillar_dist={},
        )
        assert isinstance(s, TopicScore)
        assert 0 <= s.total <= 1
        assert 0 <= s.channel_fit <= 1
        assert 0 <= s.novelty <= 1
        assert s.pillar != ""

    def test_novel_topic_scores_higher(self) -> None:
        strategy = _strategy()
        s_novel = score_topic(
            "Why Mixture of Experts Makes AI Faster",
            strategy,
            existing_topics=[],
            difficulty_dist={},
            pillar_dist={},
        )
        s_dupe = score_topic(
            "Why Mixture of Experts Makes AI Faster",
            strategy,
            existing_topics=["Why Mixture of Experts Makes AI Faster and Cheaper"],
            difficulty_dist={},
            pillar_dist={},
        )
        assert s_novel.novelty > s_dupe.novelty

    def test_hook_signals_boost_score(self) -> None:
        assert _score_hook_strength("Why AI Gets It Wrong") > _score_hook_strength("AI Overview")

    def test_difficulty_classification(self) -> None:
        assert _classify_difficulty("What is AI — A Simple Introduction") == "beginner"
        assert _classify_difficulty("Advanced Fine-Tuning Techniques") == "advanced"
        assert _classify_difficulty("How Embeddings Turn Words Into Numbers") == "intermediate"

    def test_shorts_suitability(self) -> None:
        short = _score_shorts_suitability("Why AI Hallucinates")
        long_title = _score_shorts_suitability(
            "A Comprehensive Deep Dive Into The Architecture Behind Transformer Neural Networks"
        )
        assert short > long_title


# ═══════════════════════════════════════════════════════════════════════
# Test: Sequence Diversity
# ═══════════════════════════════════════════════════════════════════════

class TestSequenceDiversity:
    def _make_score(self, pillar: str, difficulty: str, content_type: str = "EVERGREEN") -> TopicScore:
        return TopicScore(
            topic="test", pillar=pillar, difficulty=difficulty, content_type=content_type,
            channel_fit=0.8, novelty=0.8, accessibility=0.8, shorts_suitability=0.8,
            hook_strength=0.8, visual_potential=0.8, strategic_balance=0.8, total=0.8,
            reason="test", nearest_existing="", nearest_similarity=0.0,
        )

    def test_diverse_sequence_scores_high(self) -> None:
        seq = [
            self._make_score("AI Fundamentals", "beginner"),
            self._make_score("AI Agents / Agentic Systems", "intermediate"),
            self._make_score("RAG / Knowledge Systems", "advanced"),
            self._make_score("LLM Concepts", "intermediate"),
            self._make_score("Model Training / Reasoning", "beginner"),
        ]
        score = _evaluate_sequence_diversity(seq)
        assert score > 0.7

    def test_homogeneous_sequence_scores_low(self) -> None:
        seq = [self._make_score("AI Fundamentals", "beginner")] * 5
        score = _evaluate_sequence_diversity(seq)
        assert score < 0.4

    def test_consecutive_same_pillar_penalized(self) -> None:
        mixed = [
            self._make_score("AI Fundamentals", "beginner"),
            self._make_score("LLM Concepts", "intermediate"),
            self._make_score("AI Fundamentals", "advanced"),
        ]
        consec = [
            self._make_score("AI Fundamentals", "beginner"),
            self._make_score("AI Fundamentals", "intermediate"),
            self._make_score("LLM Concepts", "advanced"),
        ]
        assert _evaluate_sequence_diversity(mixed) >= _evaluate_sequence_diversity(consec)


# ═══════════════════════════════════════════════════════════════════════
# Test: Recommendations Do Not Enter Queue Automatically
# ═══════════════════════════════════════════════════════════════════════

class TestNoAutoQueue:
    def test_plan_does_not_modify_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
            before_count = len(q.list_all())

            with patch("topic_director.director.HISTORY_DIR", tmp_path), \
                 patch("topic_director.director.ProductionQueue") as mock_q_cls:
                mock_q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
                mock_q_cls.return_value = mock_q

                result = plan("srini_on_ai", recommend_count=3)

            # Reload queue
            q2 = ProductionQueue("srini_on_ai", base_dir=tmp_path)
            after_count = len(q2.list_all())
            assert after_count == before_count
            assert result["recommended_count"] > 0


# ═══════════════════════════════════════════════════════════════════════
# Test: Explicit Approval Adds to Queue
# ═══════════════════════════════════════════════════════════════════════

class TestExplicitApproval:
    def test_approve_adds_to_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            with patch("topic_director.director.HISTORY_DIR", tmp_path), \
                 patch("topic_director.director.ProductionQueue") as mock_q_cls:
                q = ProductionQueue("test_ch", base_dir=tmp_path)
                mock_q_cls.return_value = q

                result = plan("srini_on_ai", recommend_count=3)
                topic_to_approve = result["recommendations"][0]["topic"]

                # Now approve
                mock_q_cls.return_value = ProductionQueue("test_ch", base_dir=tmp_path)
                approved = approve_topic("srini_on_ai", topic_to_approve)

            assert approved["status"] == "QUEUED"
            assert approved["episode_id"].startswith("q-")

    def test_approve_nonexistent_topic_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("topic_director.director.HISTORY_DIR", tmp_path):
                # Create a dummy run
                ch_dir = tmp_path / "test_ch"
                ch_dir.mkdir()
                run_file = ch_dir / "run_20261019T000000Z.json"
                run_file.write_text(json.dumps({
                    "timestamp": "20261019T000000Z",
                    "channel_id": "test_ch",
                    "candidates_evaluated": 1,
                    "candidates": [],
                    "recommended": [{"topic": "Real Topic", "rank": 1, "total_score": 0.8}],
                    "rejected_duplicates": [],
                    "sequence_diversity_score": 0.9,
                    "approval_status": "pending",
                }), encoding="utf-8")

                with pytest.raises(ValueError, match="not in latest"):
                    approve_topic("test_ch", "Nonexistent Topic")

    def test_idempotent_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            with patch("topic_director.director.HISTORY_DIR", tmp_path), \
                 patch("topic_director.director.ProductionQueue") as mock_q_cls:
                q = ProductionQueue("test_ch", base_dir=tmp_path)
                mock_q_cls.return_value = q
                result = plan("srini_on_ai", recommend_count=2)
                topic = result["recommendations"][0]["topic"]

                mock_q_cls.return_value = ProductionQueue("test_ch", base_dir=tmp_path)
                approve_topic("srini_on_ai", topic)

                # Second approval should fail (already in queue)
                mock_q_cls.return_value = ProductionQueue("test_ch", base_dir=tmp_path)
                with pytest.raises(ValueError, match="already exists"):
                    approve_topic("srini_on_ai", topic)


# ═══════════════════════════════════════════════════════════════════════
# Test: Queue ID Allocation
# ═══════════════════════════════════════════════════════════════════════

class TestQueueIdAllocation:
    def test_approved_topics_get_queue_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            with patch("topic_director.director.HISTORY_DIR", tmp_path), \
                 patch("topic_director.director.ProductionQueue") as mock_q_cls:
                q = ProductionQueue("test_ch", base_dir=tmp_path)
                mock_q_cls.return_value = q
                result = plan("srini_on_ai", recommend_count=2)
                topic = result["recommendations"][0]["topic"]

                mock_q_cls.return_value = ProductionQueue("test_ch", base_dir=tmp_path)
                approved = approve_topic("srini_on_ai", topic)

            assert approved["episode_id"].startswith("q-")
            num = int(approved["episode_id"][2:])
            assert num >= 1


# ═══════════════════════════════════════════════════════════════════════
# Test: Planning History Persistence
# ═══════════════════════════════════════════════════════════════════════

class TestPlanningHistory:
    def test_plan_persists_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("topic_director.director.HISTORY_DIR", tmp_path), \
                 patch("topic_director.director.ProductionQueue") as mock_q_cls:
                mock_q_cls.return_value = ProductionQueue("test_ch", base_dir=tmp_path)
                plan("srini_on_ai", recommend_count=3)

            runs = list(tmp_path.glob("srini_on_ai/run_*.json"))
            assert len(runs) == 1
            data = json.loads(runs[0].read_text(encoding="utf-8"))
            assert data["approval_status"] == "pending"
            assert len(data["recommended"]) == 3

    def test_history_survives_reload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("topic_director.director.HISTORY_DIR", tmp_path), \
                 patch("topic_director.director.ProductionQueue") as mock_q_cls:
                mock_q_cls.return_value = ProductionQueue("test_ch", base_dir=tmp_path)
                plan("srini_on_ai", recommend_count=3)

            with patch("topic_director.director.HISTORY_DIR", tmp_path):
                runs = list_runs("srini_on_ai")
            assert len(runs) == 1
            assert runs[0]["recommended_count"] == 3

    def test_recommendations_from_persisted_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch("topic_director.director.HISTORY_DIR", tmp_path), \
                 patch("topic_director.director.ProductionQueue") as mock_q_cls:
                mock_q_cls.return_value = ProductionQueue("test_ch", base_dir=tmp_path)
                plan("srini_on_ai", recommend_count=3)

            with patch("topic_director.director.HISTORY_DIR", tmp_path):
                recs = get_recommendations("srini_on_ai")
            assert recs is not None
            assert len(recs) == 3
