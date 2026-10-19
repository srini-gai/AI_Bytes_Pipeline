"""
Topic Director CLI — content strategy operations.

Usage:
    python -m topic_director plan [--channel CH] [--count N]
    python -m topic_director recommendations [--channel CH]
    python -m topic_director approve TOPIC [--channel CH] [--run TIMESTAMP]
    python -m topic_director reject TOPIC [--channel CH] [--reason TEXT] [--run TIMESTAMP]
    python -m topic_director history [--channel CH]
    python -m topic_director pillars [--channel CH]
"""
import argparse
import json
import logging
import sys

from topic_director.director import (
    approve_topic,
    get_recommendations,
    list_runs,
    plan,
    reject_topic,
)
from topic_director.pillars import get_strategy

logger = logging.getLogger(__name__)

DEFAULT_CHANNEL = "srini_on_ai"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="topic_director",
        description="Topic Director — channel-scoped content strategy",
    )
    p.add_argument("--channel", default=DEFAULT_CHANNEL, help="Channel ID")
    sub = p.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan", help="Run planning cycle and generate recommendations")
    plan_p.add_argument("--count", type=int, default=5, help="Number of recommendations")

    sub.add_parser("recommendations", help="Show latest recommendations")

    approve_p = sub.add_parser("approve", help="Approve a recommended topic into queue")
    approve_p.add_argument("topic", help="Exact topic text to approve")
    approve_p.add_argument("--run", default=None, help="Planning run timestamp")

    reject_p = sub.add_parser("reject", help="Reject a recommended topic")
    reject_p.add_argument("topic", help="Exact topic text to reject")
    reject_p.add_argument("--reason", default="", help="Rejection reason")
    reject_p.add_argument("--run", default=None, help="Planning run timestamp")

    sub.add_parser("history", help="List planning run history")
    sub.add_parser("pillars", help="Show channel content pillars")

    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "plan":
        result = plan(args.channel, recommend_count=args.count)
        print(f"\n{'='*60}")
        print(f"TOPIC DIRECTOR -- {args.channel}")
        print(f"{'='*60}")
        print(f"Candidates evaluated: {result['candidates_evaluated']}")
        print(f"Duplicates filtered:  {result['duplicates_filtered']}")
        print(f"Candidates scored:    {result['candidates_scored']}")
        print(f"Sequence diversity:   {result['sequence_diversity']}")
        print(f"\nNEXT {result['recommended_count']} RECOMMENDED EPISODES:")
        print(f"{'-'*60}")
        for rec in result["recommendations"]:
            print(f"\n  #{rec['rank']}  {rec['topic']}")
            print(f"      Pillar: {rec['pillar']}")
            print(f"      Type: {rec['content_type']}  |  Difficulty: {rec['difficulty']}")
            print(f"      Score: {rec['score']}")
            print(f"      Reason: {rec['reason']}")
            if rec["nearest_existing"]:
                print(f"      Nearest: \"{rec['nearest_existing']}\" (sim={rec['nearest_similarity']:.2f})")
        if result["rejected_duplicates"]:
            print(f"\n{'-'*60}")
            print("Filtered (too similar to existing):")
            for topic, reason in result["rejected_duplicates"]:
                print(f"  X {topic}")
                print(f"    {reason}")
        print(f"\nRun saved: {result['run_file']}")
        print("Recommendations are NOT queued. Use 'approve' to add to production queue.")

    elif args.command == "recommendations":
        recs = get_recommendations(args.channel)
        if not recs:
            print("No pending recommendations. Run 'plan' first.")
            return 0
        print(f"\nLatest recommendations for {args.channel}:")
        for rec in recs:
            status = ""
            if rec.get("approved"):
                status = f" [APPROVED → {rec.get('queue_id', '?')}]"
            elif rec.get("rejected"):
                status = " [REJECTED]"
            print(f"  #{rec['rank']}  {rec['topic']}{status}")
            print(f"      {rec['pillar']}  |  {rec['content_type']}  |  Score: {rec['total_score']}")

    elif args.command == "approve":
        result = approve_topic(args.channel, args.topic, run_timestamp=args.run)
        print(f"Approved: {result['episode_id']} — {result['topic']}")
        print(f"Status: {result['status']} (in {result['channel_id']} production queue)")

    elif args.command == "reject":
        result = reject_topic(
            args.channel, args.topic, reason=args.reason, run_timestamp=args.run
        )
        print(f"Rejected: {result['topic']}")
        if result["reason"]:
            print(f"Reason: {result['reason']}")

    elif args.command == "history":
        runs = list_runs(args.channel)
        if not runs:
            print(f"No planning runs for {args.channel}")
            return 0
        print(f"\nPlanning history for {args.channel}:")
        for r in runs:
            print(f"  {r['timestamp']}  candidates={r['candidates_evaluated']}  "
                  f"recommended={r['recommended_count']}  status={r['approval_status']}")

    elif args.command == "pillars":
        strategy = get_strategy(args.channel)
        print(f"\nContent pillars for {strategy.display_name}:")
        print(f"Audience: {strategy.audience}")
        print(f"\nDifficulty targets: {strategy.difficulty_targets}")
        print(f"\nPillars:")
        for p in strategy.pillars:
            print(f"  • {p.name}")
            print(f"    {p.description}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
