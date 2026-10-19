"""
Production Queue — channel-scoped episode lifecycle tracker.

Storage: one JSON file per channel at queue/<channel_id>/queue.json.
Thread-safe within a single process via file-level locking semantics
(read-modify-write under a single call). Not designed for concurrent
multi-process writes — appropriate for CLI / single-orchestrator use.
"""
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

QUEUE_DIR = Path(__file__).parent


class Status(str, Enum):
    QUEUED = "QUEUED"
    PRODUCING = "PRODUCING"
    QA = "QA"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"


VALID_TRANSITIONS: dict[Status, set[Status]] = {
    Status.QUEUED: {Status.PRODUCING, Status.PAUSED},
    Status.PRODUCING: {Status.QA, Status.FAILED, Status.PAUSED},
    Status.QA: {Status.AWAITING_APPROVAL, Status.FAILED, Status.PAUSED},
    Status.AWAITING_APPROVAL: {Status.APPROVED, Status.FAILED, Status.PAUSED},
    Status.APPROVED: {Status.PUBLISHED, Status.FAILED, Status.PAUSED},
    Status.PUBLISHED: set(),
    Status.FAILED: {Status.QUEUED},
    Status.PAUSED: {Status.QUEUED, Status.PRODUCING, Status.QA, Status.AWAITING_APPROVAL},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class QueueEntry:
    """Single episode queue record."""

    def __init__(
        self,
        channel_id: str,
        episode_id: str,
        topic: str,
        *,
        priority: int = 0,
        status: str = Status.QUEUED.value,
        source: str = "topics.txt",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        final_mp4: Optional[str] = None,
        qa_status: Optional[str] = None,
        approval_status: Optional[str] = None,
        publish_status: Optional[str] = None,
        youtube_video_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
        paused_from: Optional[str] = None,
    ) -> None:
        self.channel_id = channel_id
        self.episode_id = episode_id
        self.topic = topic
        self.priority = priority
        self.status = status
        self.source = source
        self.created_at = created_at or _now_iso()
        self.updated_at = updated_at or self.created_at
        self.final_mp4 = final_mp4
        self.qa_status = qa_status
        self.approval_status = approval_status
        self.publish_status = publish_status
        self.youtube_video_id = youtube_video_id
        self.failure_reason = failure_reason
        self.paused_from = paused_from

    def to_dict(self) -> dict:
        return {
            "channel_id": self.channel_id,
            "episode_id": self.episode_id,
            "topic": self.topic,
            "priority": self.priority,
            "status": self.status,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "final_mp4": self.final_mp4,
            "qa_status": self.qa_status,
            "approval_status": self.approval_status,
            "publish_status": self.publish_status,
            "youtube_video_id": self.youtube_video_id,
            "failure_reason": self.failure_reason,
            "paused_from": self.paused_from,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueueEntry":
        return cls(**data)


class ProductionQueue:
    """Channel-scoped production queue backed by a JSON file."""

    def __init__(self, channel_id: str, base_dir: Optional[Path] = None) -> None:
        self.channel_id = channel_id
        self._base = (base_dir or QUEUE_DIR) / channel_id
        self._base.mkdir(parents=True, exist_ok=True)
        self._path = self._base / "queue.json"
        self._entries: list[QueueEntry] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._entries = [QueueEntry.from_dict(r) for r in raw]
        else:
            self._entries = []

    def _save(self) -> None:
        self._path.write_text(
            json.dumps([e.to_dict() for e in self._entries], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _find(self, episode_id: str) -> Optional[QueueEntry]:
        for e in self._entries:
            if e.episode_id == episode_id:
                return e
        return None

    # ── ID generation ───────────────────────────────────────────────────

    def _next_queue_id(self) -> str:
        """Generate the next queue-scoped ID (q-001, q-002, ...)."""
        max_num = 0
        for e in self._entries:
            if e.episode_id.startswith("q-"):
                try:
                    num = int(e.episode_id[2:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        return f"q-{max_num + 1:03d}"

    @staticmethod
    def _normalize_topic(topic: str) -> str:
        """Normalize topic text for deduplication comparison."""
        return " ".join(topic.lower().split()).strip(" ?!.—–-")

    def _topic_exists(self, topic: str) -> bool:
        norm = self._normalize_topic(topic)
        return any(self._normalize_topic(e.topic) == norm for e in self._entries)

    # ── Import ───────────────────────────────────────────────────────────

    def import_topics(self, topics_file: Path, *, source: str = "topics.txt") -> int:
        """Import topics from a text file. Idempotent — skips duplicate topics."""
        lines = [
            ln.strip()
            for ln in topics_file.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        existing_topics = {self._normalize_topic(e.topic) for e in self._entries}
        added = 0
        for idx, topic in enumerate(lines, start=1):
            if self._normalize_topic(topic) in existing_topics:
                continue
            eid = self._next_queue_id()
            entry = QueueEntry(
                channel_id=self.channel_id,
                episode_id=eid,
                topic=topic,
                priority=len(self._entries) + 1,
                source=source,
            )
            self._entries.append(entry)
            existing_topics.add(self._normalize_topic(topic))
            added += 1
        if added:
            self._save()
            logger.info(f"Imported {added} topics into {self.channel_id} queue")
        return added

    def add_historical(
        self,
        episode_id: str,
        topic: str,
        *,
        status: str = Status.PUBLISHED.value,
        source: str = "historical",
        youtube_video_id: Optional[str] = None,
        final_mp4: Optional[str] = None,
    ) -> bool:
        """Add a historical episode. Idempotent — skips if episode_id exists."""
        if self._find(episode_id) is not None:
            return False
        entry = QueueEntry(
            channel_id=self.channel_id,
            episode_id=episode_id,
            topic=topic,
            status=status,
            source=source,
            youtube_video_id=youtube_video_id,
            final_mp4=final_mp4,
            priority=0,
            qa_status="passed" if status == Status.PUBLISHED.value else None,
            approval_status="approved" if status == Status.PUBLISHED.value else None,
            publish_status="published" if status == Status.PUBLISHED.value else None,
        )
        self._entries.append(entry)
        self._save()
        return True

    # ── Query ────────────────────────────────────────────────────────────

    def list_all(self) -> list[QueueEntry]:
        return list(self._entries)

    def list_by_status(self, status: Status) -> list[QueueEntry]:
        return [e for e in self._entries if e.status == status.value]

    def next_queued(self) -> Optional[QueueEntry]:
        """Return the highest-priority QUEUED entry (lowest priority number)."""
        queued = self.list_by_status(Status.QUEUED)
        if not queued:
            return None
        return min(queued, key=lambda e: e.priority)

    def get(self, episode_id: str) -> Optional[QueueEntry]:
        return self._find(episode_id)

    # ── State transitions ────────────────────────────────────────────────

    def _transition(
        self,
        episode_id: str,
        target: Status,
        **kwargs: object,
    ) -> QueueEntry:
        entry = self._find(episode_id)
        if entry is None:
            raise KeyError(f"Episode {episode_id} not in queue")

        current = Status(entry.status)
        if target not in VALID_TRANSITIONS.get(current, set()):
            raise ValueError(
                f"Invalid transition {current.value} → {target.value} "
                f"for {episode_id}"
            )

        if target == Status.PAUSED:
            entry.paused_from = entry.status
        elif current == Status.PAUSED and entry.paused_from:
            entry.paused_from = None

        entry.status = target.value
        entry.updated_at = _now_iso()
        for k, v in kwargs.items():
            if hasattr(entry, k):
                setattr(entry, k, v)
        self._save()
        logger.info(f"{episode_id} → {target.value}")
        return entry

    def claim_next(self) -> Optional[QueueEntry]:
        """Move the next QUEUED episode to PRODUCING."""
        nxt = self.next_queued()
        if nxt is None:
            return None
        return self._transition(nxt.episode_id, Status.PRODUCING)

    def start_producing(self, episode_id: str) -> QueueEntry:
        return self._transition(episode_id, Status.PRODUCING)

    def mark_qa(self, episode_id: str) -> QueueEntry:
        return self._transition(episode_id, Status.QA)

    def pass_qa(self, episode_id: str, *, final_mp4: Optional[str] = None) -> QueueEntry:
        entry = self._transition(
            episode_id,
            Status.AWAITING_APPROVAL,
            qa_status="passed",
            final_mp4=final_mp4,
        )
        return entry

    def fail_qa(self, episode_id: str, *, reason: str = "") -> QueueEntry:
        return self._transition(
            episode_id,
            Status.FAILED,
            qa_status="failed",
            failure_reason=reason,
        )

    def approve(self, episode_id: str) -> QueueEntry:
        return self._transition(episode_id, Status.APPROVED, approval_status="approved")

    def reject(self, episode_id: str, *, reason: str = "") -> QueueEntry:
        return self._transition(
            episode_id,
            Status.FAILED,
            approval_status="rejected",
            failure_reason=reason,
        )

    def mark_published(self, episode_id: str, *, youtube_video_id: str) -> QueueEntry:
        return self._transition(
            episode_id,
            Status.PUBLISHED,
            publish_status="published",
            youtube_video_id=youtube_video_id,
        )

    def pause(self, episode_id: str) -> QueueEntry:
        return self._transition(episode_id, Status.PAUSED)

    def resume(self, episode_id: str) -> QueueEntry:
        """Resume a PAUSED entry back to its pre-pause state."""
        entry = self._find(episode_id)
        if entry is None:
            raise KeyError(f"Episode {episode_id} not in queue")
        if entry.status != Status.PAUSED.value:
            raise ValueError(f"{episode_id} is not PAUSED (is {entry.status})")
        target = Status(entry.paused_from) if entry.paused_from else Status.QUEUED
        entry.status = target.value
        entry.paused_from = None
        entry.updated_at = _now_iso()
        self._save()
        logger.info(f"{episode_id} resumed → {target.value}")
        return entry

    def retry(self, episode_id: str) -> QueueEntry:
        """Re-queue a FAILED entry."""
        return self._transition(episode_id, Status.QUEUED, failure_reason=None)

    # ── Bulk ─────────────────────────────────────────────────────────────

    def count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self._entries:
            counts[e.status] = counts.get(e.status, 0) + 1
        return counts
