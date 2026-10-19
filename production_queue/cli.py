"""
Production Queue CLI — manage the channel-scoped episode queue.

Usage:
    python -m queue.cli init [--channel CH] [--topics-file FILE]
    python -m queue.cli list [--channel CH] [--status STATUS]
    python -m queue.cli next [--channel CH]
    python -m queue.cli claim [--channel CH]
    python -m queue.cli show EPISODE_ID [--channel CH]
    python -m queue.cli transition EPISODE_ID STATUS [--channel CH] [--reason TEXT]
    python -m queue.cli approve EPISODE_ID [--channel CH]
    python -m queue.cli reject EPISODE_ID [--channel CH] [--reason TEXT]
    python -m queue.cli publish EPISODE_ID --video-id VID [--channel CH]
    python -m queue.cli pause EPISODE_ID [--channel CH]
    python -m queue.cli resume EPISODE_ID [--channel CH]
    python -m queue.cli retry EPISODE_ID [--channel CH]
    python -m queue.cli stats [--channel CH]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from production_queue.queue import ProductionQueue, Status

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_CHANNEL = "srini_on_ai"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="queue", description="Production Queue CLI")
    p.add_argument("--channel", default=DEFAULT_CHANNEL, help="Channel ID")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Import topics into queue")
    sub.add_parser("list", help="List queue entries").add_argument(
        "--status", choices=[s.value for s in Status], default=None
    )
    sub.add_parser("next", help="Show next queued episode")
    sub.add_parser("claim", help="Claim next queued episode for production")

    show = sub.add_parser("show", help="Show one entry")
    show.add_argument("episode_id")

    trans = sub.add_parser("transition", help="Manually transition status")
    trans.add_argument("episode_id")
    trans.add_argument("status", choices=[s.value for s in Status])
    trans.add_argument("--reason", default="")

    approve = sub.add_parser("approve", help="Approve episode for publishing")
    approve.add_argument("episode_id")

    reject = sub.add_parser("reject", help="Reject episode")
    reject.add_argument("episode_id")
    reject.add_argument("--reason", default="")

    pub = sub.add_parser("publish", help="Mark episode as published")
    pub.add_argument("episode_id")
    pub.add_argument("--video-id", required=True)

    pause_p = sub.add_parser("pause", help="Pause episode")
    pause_p.add_argument("episode_id")

    resume_p = sub.add_parser("resume", help="Resume paused episode")
    resume_p.add_argument("episode_id")

    retry_p = sub.add_parser("retry", help="Re-queue failed episode")
    retry_p.add_argument("episode_id")

    sub.add_parser("stats", help="Show status counts")

    return p


def _print_entry(entry: object) -> None:
    print(json.dumps(entry.to_dict(), indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    q = ProductionQueue(args.channel)

    if args.command == "init":
        topics_file = PROJECT_ROOT / "topics.txt"
        added = q.import_topics(topics_file)
        total = len(q.list_all())
        print(f"Imported {added} new topics ({total} total in {args.channel} queue)")

    elif args.command == "list":
        entries = q.list_all() if args.status is None else q.list_by_status(Status(args.status))
        for e in entries:
            print(f"  {e.episode_id:6s}  {e.status:22s}  {e.topic}")
        print(f"\n{len(entries)} entries")

    elif args.command == "next":
        nxt = q.next_queued()
        if nxt:
            _print_entry(nxt)
        else:
            print("No queued episodes")

    elif args.command == "claim":
        claimed = q.claim_next()
        if claimed:
            print(f"Claimed {claimed.episode_id}: {claimed.topic}")
            _print_entry(claimed)
        else:
            print("Nothing to claim")

    elif args.command == "show":
        entry = q.get(args.episode_id)
        if entry:
            _print_entry(entry)
        else:
            print(f"Episode {args.episode_id} not found")
            return 1

    elif args.command == "approve":
        entry = q.approve(args.episode_id)
        print(f"Approved {entry.episode_id}")

    elif args.command == "reject":
        entry = q.reject(args.episode_id, reason=args.reason)
        print(f"Rejected {entry.episode_id}")

    elif args.command == "publish":
        entry = q.mark_published(args.episode_id, youtube_video_id=args.video_id)
        print(f"Published {entry.episode_id} → {entry.youtube_video_id}")

    elif args.command == "pause":
        entry = q.pause(args.episode_id)
        print(f"Paused {entry.episode_id} (was {entry.paused_from})")

    elif args.command == "resume":
        entry = q.resume(args.episode_id)
        print(f"Resumed {entry.episode_id} → {entry.status}")

    elif args.command == "retry":
        entry = q.retry(args.episode_id)
        print(f"Retried {entry.episode_id} → QUEUED")

    elif args.command == "stats":
        counts = q.count_by_status()
        for status, count in sorted(counts.items()):
            print(f"  {status:22s}  {count}")
        print(f"\n{sum(counts.values())} total")

    elif args.command == "transition":
        target = Status(args.status)
        entry = q.get(args.episode_id)
        if entry is None:
            print(f"Episode {args.episode_id} not found")
            return 1
        updated = q._transition(args.episode_id, target, failure_reason=args.reason or None)
        print(f"{updated.episode_id} → {updated.status}")

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    sys.exit(main())
