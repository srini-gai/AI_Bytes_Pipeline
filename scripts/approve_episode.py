"""
Persist an approved episode's visual + art-direction fingerprint.

Run ONLY after a human has approved the episode visuals. The fingerprint is
written to $OUTPUT_BASE_PATH/visual_fingerprints.json and is read by the
Visual Director's novelty guard and Art Director repeat guard when planning
future episodes.

Usage:
    python scripts/approve_episode.py --week 1 --episode 2
    python scripts/approve_episode.py --week 1 --episode 2 \
        --source output/week_01/ep02/ep02_props_FINALSTRUCT.json --approved-by srini
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import visual_director_agent  # noqa: E402

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--episode", type=int, required=True)
    parser.add_argument("--lang", default="en")
    parser.add_argument("--source", type=Path, default=None,
                        help="storyboard doc or render-props JSON (default: ep storyboard file)")
    parser.add_argument("--approved-by", default="human")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        out = visual_director_agent.approve_episode(
            args.episode, args.week, lang=args.lang, source=args.source, approved_by=args.approved_by,
        )
    except Exception as e:
        logger.error(f"Approval failed: {e}")
        return 1
    logger.info(f"Fingerprint {out['episode_key']} persisted -> {out['output_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
