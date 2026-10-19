"""Tests for production_queue — Phase 7A queue + 7A.1 reconciliation."""
import json
import pytest
from pathlib import Path

from production_queue.queue import ProductionQueue, QueueEntry, Status, VALID_TRANSITIONS


@pytest.fixture
def tmp_queue(tmp_path: Path) -> ProductionQueue:
    return ProductionQueue("srini_on_ai", base_dir=tmp_path)


@pytest.fixture
def topics_file(tmp_path: Path) -> Path:
    p = tmp_path / "topics.txt"
    p.write_text(
        "How AI Actually Reads Your Text\n"
        "Why Some AI Models Are Smarter Than Others\n"
        "Why AI Hallucinates\n"
        "AI Agents vs Agentic AI\n"
        "How AI Models Are Trained on Trillions of Words\n",
        encoding="utf-8",
    )
    return p


# ── Import tests ─────────────────────────────────────────────────────────

class TestImport:
    def test_import_topics(self, tmp_queue: ProductionQueue, topics_file: Path) -> None:
        added = tmp_queue.import_topics(topics_file)
        assert added == 5
        assert len(tmp_queue.list_all()) == 5
        assert tmp_queue.get("q-001").topic == "How AI Actually Reads Your Text"
        assert tmp_queue.get("q-005").topic == "How AI Models Are Trained on Trillions of Words"

    def test_import_idempotent(self, tmp_queue: ProductionQueue, topics_file: Path) -> None:
        tmp_queue.import_topics(topics_file)
        added_again = tmp_queue.import_topics(topics_file)
        assert added_again == 0
        assert len(tmp_queue.list_all()) == 5

    def test_import_preserves_order(self, tmp_queue: ProductionQueue, topics_file: Path) -> None:
        tmp_queue.import_topics(topics_file)
        entries = tmp_queue.list_all()
        assert entries[0].priority < entries[1].priority < entries[4].priority

    def test_import_sets_channel_id(self, tmp_queue: ProductionQueue, topics_file: Path) -> None:
        tmp_queue.import_topics(topics_file)
        for e in tmp_queue.list_all():
            assert e.channel_id == "srini_on_ai"

    def test_import_all_queued(self, tmp_queue: ProductionQueue, topics_file: Path) -> None:
        tmp_queue.import_topics(topics_file)
        for e in tmp_queue.list_all():
            assert e.status == Status.QUEUED.value

    def test_import_skips_blank_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "topics.txt"
        f.write_text("Topic A\n\n\nTopic B\n", encoding="utf-8")
        q = ProductionQueue("test_ch", base_dir=tmp_path)
        added = q.import_topics(f)
        assert added == 2

    def test_import_uses_queue_ids(self, tmp_queue: ProductionQueue, topics_file: Path) -> None:
        """Queue IDs use q-NNN format, not ep01."""
        tmp_queue.import_topics(topics_file)
        ids = [e.episode_id for e in tmp_queue.list_all()]
        assert all(eid.startswith("q-") for eid in ids)

    def test_import_deduplicates_by_topic_text(self, tmp_path: Path) -> None:
        """Same topic text (normalized) is not imported twice."""
        f = tmp_path / "topics.txt"
        f.write_text("Topic A\nTopic A\ntopic a\n", encoding="utf-8")
        q = ProductionQueue("test_ch", base_dir=tmp_path)
        added = q.import_topics(f)
        assert added == 1


# ── State transition tests ───────────────────────────────────────────────

class TestTransitions:
    def _seeded(self, tmp_path: Path) -> ProductionQueue:
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        f = tmp_path / "topics.txt"
        f.write_text("Test topic\n", encoding="utf-8")
        q.import_topics(f)
        return q

    def _first_id(self, q: ProductionQueue) -> str:
        return q.list_all()[0].episode_id

    def test_full_happy_path(self, tmp_path: Path) -> None:
        q = self._seeded(tmp_path)
        eid = self._first_id(q)
        q.start_producing(eid)
        assert q.get(eid).status == Status.PRODUCING.value

        q.mark_qa(eid)
        assert q.get(eid).status == Status.QA.value

        q.pass_qa(eid, final_mp4="/out/ep01.mp4")
        e = q.get(eid)
        assert e.status == Status.AWAITING_APPROVAL.value
        assert e.final_mp4 == "/out/ep01.mp4"
        assert e.qa_status == "passed"

        q.approve(eid)
        assert q.get(eid).status == Status.APPROVED.value
        assert q.get(eid).approval_status == "approved"

        q.mark_published(eid, youtube_video_id="abc123")
        e = q.get(eid)
        assert e.status == Status.PUBLISHED.value
        assert e.youtube_video_id == "abc123"

    def test_invalid_queued_to_published(self, tmp_path: Path) -> None:
        q = self._seeded(tmp_path)
        eid = self._first_id(q)
        with pytest.raises(ValueError, match="Invalid transition"):
            q.mark_published(eid, youtube_video_id="hack")

    def test_invalid_queued_to_approved(self, tmp_path: Path) -> None:
        q = self._seeded(tmp_path)
        eid = self._first_id(q)
        with pytest.raises(ValueError, match="Invalid transition"):
            q.approve(eid)

    def test_invalid_producing_to_published(self, tmp_path: Path) -> None:
        q = self._seeded(tmp_path)
        eid = self._first_id(q)
        q.start_producing(eid)
        with pytest.raises(ValueError, match="Invalid transition"):
            q.mark_published(eid, youtube_video_id="hack")

    def test_approval_required_before_publish(self, tmp_path: Path) -> None:
        q = self._seeded(tmp_path)
        eid = self._first_id(q)
        q.start_producing(eid)
        q.mark_qa(eid)
        q.pass_qa(eid)
        with pytest.raises(ValueError, match="Invalid transition"):
            q.mark_published(eid, youtube_video_id="hack")

    def test_all_valid_transitions_declared(self) -> None:
        for s in Status:
            assert s in VALID_TRANSITIONS

    def test_published_is_terminal(self) -> None:
        assert VALID_TRANSITIONS[Status.PUBLISHED] == set()


# ── Failed / retry ───────────────────────────────────────────────────────

class TestFailedRetry:
    def test_retry_requeues(self, tmp_path: Path) -> None:
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        f = tmp_path / "topics.txt"
        f.write_text("Topic\n", encoding="utf-8")
        q.import_topics(f)
        eid = q.list_all()[0].episode_id
        q.start_producing(eid)
        q._transition(eid, Status.FAILED, failure_reason="crash")
        assert q.get(eid).status == Status.FAILED.value

        q.retry(eid)
        e = q.get(eid)
        assert e.status == Status.QUEUED.value
        assert e.failure_reason is None

    def test_fail_stores_reason(self, tmp_path: Path) -> None:
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        f = tmp_path / "topics.txt"
        f.write_text("Topic\n", encoding="utf-8")
        q.import_topics(f)
        eid = q.list_all()[0].episode_id
        q.start_producing(eid)
        q._transition(eid, Status.FAILED, failure_reason="API timeout")
        assert q.get(eid).failure_reason == "API timeout"


# ── Pause / resume ───────────────────────────────────────────────────────

class TestPauseResume:
    def test_pause_and_resume(self, tmp_path: Path) -> None:
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        f = tmp_path / "topics.txt"
        f.write_text("Topic\n", encoding="utf-8")
        q.import_topics(f)
        eid = q.list_all()[0].episode_id
        q.start_producing(eid)
        q.pause(eid)
        e = q.get(eid)
        assert e.status == Status.PAUSED.value
        assert e.paused_from == Status.PRODUCING.value

        q.resume(eid)
        e = q.get(eid)
        assert e.status == Status.PRODUCING.value
        assert e.paused_from is None


# ── Channel isolation ────────────────────────────────────────────────────

class TestChannelIsolation:
    def test_separate_channels(self, tmp_path: Path) -> None:
        f = tmp_path / "topics.txt"
        f.write_text("Topic A\nTopic B\n", encoding="utf-8")

        q1 = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q1.import_topics(f)

        q2 = ProductionQueue("cricket_pulse", base_dir=tmp_path)
        q2.import_topics(f)

        assert len(q1.list_all()) == 2
        assert len(q2.list_all()) == 2

        eid = q1.list_all()[0].episode_id
        q1.start_producing(eid)
        assert q1.get(eid).status == Status.PRODUCING.value
        # cricket_pulse queue has its own q-001
        cp_eid = q2.list_all()[0].episode_id
        assert q2.get(cp_eid).status == Status.QUEUED.value

    def test_channels_have_separate_files(self, tmp_path: Path) -> None:
        ProductionQueue("ch_a", base_dir=tmp_path)
        ProductionQueue("ch_b", base_dir=tmp_path)
        assert (tmp_path / "ch_a" / "queue.json").parent != (tmp_path / "ch_b" / "queue.json").parent


# ── Persistence ──────────────────────────────────────────────────────────

class TestPersistence:
    def test_survives_reload(self, tmp_path: Path) -> None:
        f = tmp_path / "topics.txt"
        f.write_text("Topic A\n", encoding="utf-8")

        q1 = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q1.import_topics(f)
        eid = q1.list_all()[0].episode_id
        q1.start_producing(eid)

        q2 = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        assert len(q2.list_all()) == 1
        assert q2.get(eid).status == Status.PRODUCING.value

    def test_published_youtube_id_persists(self, tmp_path: Path) -> None:
        f = tmp_path / "topics.txt"
        f.write_text("Topic\n", encoding="utf-8")

        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q.import_topics(f)
        eid = q.list_all()[0].episode_id
        q.start_producing(eid)
        q.mark_qa(eid)
        q.pass_qa(eid)
        q.approve(eid)
        q.mark_published(eid, youtube_video_id="yt_abc123")

        q2 = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        assert q2.get(eid).youtube_video_id == "yt_abc123"


# ── Query / claim ────────────────────────────────────────────────────────

class TestQueryClaim:
    def test_next_queued_returns_first(self, tmp_path: Path) -> None:
        f = tmp_path / "topics.txt"
        f.write_text("A\nB\nC\n", encoding="utf-8")
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q.import_topics(f)
        nxt = q.next_queued()
        assert nxt.episode_id == "q-001"

    def test_claim_moves_to_producing(self, tmp_path: Path) -> None:
        f = tmp_path / "topics.txt"
        f.write_text("A\nB\n", encoding="utf-8")
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q.import_topics(f)
        claimed = q.claim_next()
        assert claimed.episode_id == "q-001"
        assert claimed.status == Status.PRODUCING.value
        claimed2 = q.claim_next()
        assert claimed2.episode_id == "q-002"

    def test_claim_returns_none_when_empty(self, tmp_path: Path) -> None:
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        assert q.claim_next() is None

    def test_count_by_status(self, tmp_path: Path) -> None:
        f = tmp_path / "topics.txt"
        f.write_text("A\nB\nC\n", encoding="utf-8")
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q.import_topics(f)
        eid = q.list_all()[0].episode_id
        q.start_producing(eid)
        counts = q.count_by_status()
        assert counts["QUEUED"] == 2
        assert counts["PRODUCING"] == 1


# ── Historical / reconciliation ──────────────────────────────────────────

class TestHistorical:
    def test_add_historical_published(self, tmp_path: Path) -> None:
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        added = q.add_historical(
            "week_01-ep05", "Token Economics",
            youtube_video_id="PLFnI4rcU9I",
        )
        assert added is True
        e = q.get("week_01-ep05")
        assert e.status == Status.PUBLISHED.value
        assert e.youtube_video_id == "PLFnI4rcU9I"
        assert e.approval_status == "approved"

    def test_add_historical_idempotent(self, tmp_path: Path) -> None:
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q.add_historical("week_01-ep05", "Token Economics", youtube_video_id="PLFnI4rcU9I")
        added = q.add_historical("week_01-ep05", "Token Economics", youtube_video_id="PLFnI4rcU9I")
        assert added is False
        assert len(q.list_all()) == 1

    def test_topic_dedup_prevents_reimport(self, tmp_path: Path) -> None:
        """A topic already in the queue (from historical) should not be re-imported."""
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q.add_historical("week_09-ep06", "How RAG Actually Reduces AI Hallucinations", youtube_video_id="2k8jOtSdKuc")

        f = tmp_path / "topics.txt"
        f.write_text("How RAG Actually Reduces AI Hallucinations\nBrand New Topic\n", encoding="utf-8")
        added = q.import_topics(f)
        assert added == 1
        assert len(q.list_all()) == 2
        new_entry = q.get("q-001")
        assert new_entry.topic == "Brand New Topic"

    def test_published_topic_not_requeued(self, tmp_path: Path) -> None:
        """An already-published topic must not appear as QUEUED."""
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q.add_historical("week_02-ep03", "Hallucination explained", youtube_video_id="_ftXPR8sZIc")

        f = tmp_path / "topics.txt"
        f.write_text("Hallucination explained\n", encoding="utf-8")
        added = q.import_topics(f)
        assert added == 0
        assert len(q.list_by_status(Status.QUEUED)) == 0

    def test_id_collision_prevention(self, tmp_path: Path) -> None:
        """Queue IDs (q-NNN) never collide with historical IDs (week_NN-epNN)."""
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q.add_historical("week_01-ep01", "RAG basics", youtube_video_id="abc")
        f = tmp_path / "topics.txt"
        f.write_text("New topic\n", encoding="utf-8")
        q.import_topics(f)
        ids = [e.episode_id for e in q.list_all()]
        assert "week_01-ep01" in ids
        assert "q-001" in ids
        assert len(ids) == len(set(ids))

    def test_reconciliation_preserves_channel_isolation(self, tmp_path: Path) -> None:
        q1 = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q1.add_historical("week_01-ep01", "RAG", youtube_video_id="abc")

        q2 = ProductionQueue("cricket_pulse", base_dir=tmp_path)
        q2.add_historical("week_01-ep01", "Cricket Swing", youtube_video_id="xyz")

        assert q1.get("week_01-ep01").topic == "RAG"
        assert q2.get("week_01-ep01").topic == "Cricket Swing"

    def test_reconciliation_reload_persistence(self, tmp_path: Path) -> None:
        q = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        q.add_historical("week_09-ep06", "RAG Hallucinations", youtube_video_id="2k8jOtSdKuc")
        f = tmp_path / "topics.txt"
        f.write_text("New topic\n", encoding="utf-8")
        q.import_topics(f)

        q2 = ProductionQueue("srini_on_ai", base_dir=tmp_path)
        assert len(q2.list_all()) == 2
        assert q2.get("week_09-ep06").status == Status.PUBLISHED.value
        assert q2.get("q-001").status == Status.QUEUED.value
