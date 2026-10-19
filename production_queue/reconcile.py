"""
Backlog reconciliation — discovers historical episodes from output/,
cross-references against topics.txt, and builds a properly classified queue.

Run once to initialize, idempotent on subsequent runs.

Usage:
    python -m production_queue.reconcile [--channel srini_on_ai]
"""
import json
import logging
from pathlib import Path
from typing import Optional

from production_queue.queue import ProductionQueue, Status

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"


def _discover_historical_episodes(output_dir: Path) -> list[dict]:
    """Scan output/ for AI Bytes episodes with upload receipts."""
    episodes: list[dict] = []
    for receipt_path in sorted(output_dir.rglob("*upload_EN.json")):
        if "cricket" in str(receipt_path):
            continue
        try:
            data = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        video_id = data.get("video_id", "")
        title = data.get("title", "")
        privacy = data.get("privacy", "unknown")
        if not video_id:
            continue

        is_archive = "_archive" in str(receipt_path) or "quarantine" in str(receipt_path)

        # Navigate to the real episode and week directories
        if is_archive:
            # e.g. output/week_01/ep02/_archive_prompt_engineering/ep02_upload_EN.json
            ep_dir = receipt_path.parent.parent  # ep02/
            week_dir = ep_dir.parent             # week_01/
        else:
            ep_dir = receipt_path.parent
            week_dir = ep_dir.parent

        is_standalone = ep_dir == output_dir or not ep_dir.name.startswith("ep")

        # Derive a stable historical ID
        if is_standalone:
            hist_id = f"standalone-{receipt_path.stem.replace('_upload_EN', '')}"
        else:
            hist_id = f"{week_dir.name}-{ep_dir.name}"
            if is_archive:
                hist_id += "-archive"

        # Get topic from script if available (check receipt dir for archives)
        topic = title
        script_dir = receipt_path.parent if is_archive else ep_dir
        script_candidates = list(script_dir.glob("*script_EN.json"))
        if not script_candidates:
            script_candidates = list(ep_dir.glob("*script_EN.json"))
        if script_candidates:
            try:
                script_data = json.loads(script_candidates[0].read_text(encoding="utf-8"))
                topic = script_data.get("topic", title)
            except (json.JSONDecodeError, OSError):
                pass

        final_mp4: Optional[str] = None
        for mp4 in ep_dir.glob("*final_EN.mp4"):
            final_mp4 = str(mp4)
            break

        episodes.append({
            "hist_id": hist_id,
            "topic": topic,
            "title": title,
            "video_id": video_id,
            "privacy": privacy,
            "final_mp4": final_mp4,
            "is_archive": is_archive,
            "is_standalone": is_standalone,
            "week": week_dir.name if not is_standalone else None,
            "receipt_path": str(receipt_path),
        })

    return episodes


def _discover_produced_no_upload(output_dir: Path) -> list[dict]:
    """Find episodes with final_EN.mp4 but no upload receipt."""
    produced: list[dict] = []
    for final in sorted(output_dir.rglob("*final_EN.mp4")):
        if "cricket" in str(final):
            continue
        if "_archive" in str(final) or "quarantine" in str(final):
            continue
        ep_dir = final.parent
        if list(ep_dir.glob("*upload_EN.json")):
            continue

        week_dir = ep_dir.parent
        hist_id = f"{week_dir.name}-{ep_dir.name}"

        topic = "?"
        for sf in ep_dir.glob("*script_EN.json"):
            try:
                topic = json.loads(sf.read_text(encoding="utf-8")).get("topic", "?")
            except (json.JSONDecodeError, OSError):
                pass
            break
        if topic == "?":
            for sb in ep_dir.glob("*storyboard_EN.json"):
                try:
                    topic = json.loads(sb.read_text(encoding="utf-8")).get("topic", "?")
                except (json.JSONDecodeError, OSError):
                    pass
                break

        produced.append({
            "hist_id": hist_id,
            "topic": topic,
            "final_mp4": str(final),
            "week": week_dir.name,
        })

    return produced


def reconcile(channel_id: str = "srini_on_ai") -> dict:
    """Run full reconciliation and return summary."""
    q = ProductionQueue(channel_id)

    # 1. Import historical published episodes
    published_eps = _discover_historical_episodes(OUTPUT_DIR)
    hist_added = 0
    for ep in published_eps:
        status = Status.PUBLISHED.value
        source = "historical-archive" if ep["is_archive"] else "historical"
        if ep["is_standalone"]:
            source = "standalone-upload"
        added = q.add_historical(
            episode_id=ep["hist_id"],
            topic=ep["topic"],
            status=status,
            source=source,
            youtube_video_id=ep["video_id"],
            final_mp4=ep["final_mp4"],
        )
        if added:
            hist_added += 1

    # 2. Import produced-but-not-uploaded episodes
    produced_eps = _discover_produced_no_upload(OUTPUT_DIR)
    prod_added = 0
    for ep in produced_eps:
        added = q.add_historical(
            episode_id=ep["hist_id"],
            topic=ep["topic"],
            status=Status.AWAITING_APPROVAL.value,
            source="produced-no-upload",
            final_mp4=ep["final_mp4"],
        )
        if added:
            prod_added += 1

    # 3. Import topics.txt — only genuinely new topics
    topics_file = PROJECT_ROOT / "topics.txt"
    new_added = 0
    if topics_file.exists():
        # Check which topics.txt entries are already covered
        existing_norms = {q._normalize_topic(e.topic) for e in q.list_all()}
        lines = [ln.strip() for ln in topics_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        for topic in lines:
            if q._normalize_topic(topic) in existing_norms:
                continue
            eid = q._next_queue_id()
            from production_queue.queue import QueueEntry
            entry = QueueEntry(
                channel_id=channel_id,
                episode_id=eid,
                topic=topic,
                priority=len(q._entries) + 1,
                source="topics.txt",
            )
            q._entries.append(entry)
            existing_norms.add(q._normalize_topic(topic))
            new_added += 1
        if new_added:
            q._save()

    counts = q.count_by_status()
    return {
        "historical_published_added": hist_added,
        "produced_not_uploaded_added": prod_added,
        "new_topics_added": new_added,
        "total_queue_size": len(q.list_all()),
        "status_counts": counts,
    }


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="srini_on_ai")
    args = parser.parse_args()

    result = reconcile(args.channel)
    print(json.dumps(result, indent=2))
