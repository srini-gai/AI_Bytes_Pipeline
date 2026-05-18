"""
AI Bytes Pipeline Orchestrator
Reads topics.txt, runs all agents for each episode across configured languages.

Usage:
    python orchestrator.py                                  # all episodes, all langs from .env
    python orchestrator.py --episode 1                      # single episode, all langs
    python orchestrator.py --lang en                        # all episodes, English only
    python orchestrator.py --episode 3 --lang ta            # single episode, Tamil only
    python orchestrator.py --dry-run                        # script + voice only, skip visual/assembly/publish
    python orchestrator.py --week 2                         # override week number
    python orchestrator.py --lang ta --topics-file topics_ta.txt  # Tamil batch with separate topics file
"""
import argparse
import json
import logging
import os
import subprocess
import sys
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from agents import (
    assembly_agent,
    publisher_agent,
    script_agent,
    visual_agent,
    voice_agent,
)

TOPICS_FILE = Path(__file__).parent / "topics.txt"
OUTPUT_BASE = Path(os.getenv("OUTPUT_BASE_PATH", "./output"))

logger = logging.getLogger("orchestrator")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.FileHandler("orchestrator.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def _auto_week() -> int:
    """
    Calculate the current week number from START_PUBLISH_DATE.
    Week 1 = the week containing the start date.
    Falls back to 1 if the env var is absent or unparseable.
    """
    start_raw = os.getenv("START_PUBLISH_DATE", "")
    if not start_raw:
        return 1
    try:
        start = date.fromisoformat(start_raw)
        delta = (date.today() - start).days
        return max(1, delta // 7 + 1)
    except ValueError:
        logger.warning(f"Invalid START_PUBLISH_DATE '{start_raw}' — defaulting to week 1")
        return 1


def _load_topics(topics_file: Path | None = None) -> list[str]:
    path = topics_file if topics_file is not None else TOPICS_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Create it with one topic per line."
        )
    topics = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not topics:
        raise ValueError(f"{path.name} is empty — add at least one topic.")
    return topics


def _load_script_from_disk(episode: int, week: int, lang: str) -> dict | None:
    """Return the saved script dict if it exists on disk, else None."""
    script_path = (
        OUTPUT_BASE
        / f"week_{week:02d}"
        / f"ep{episode:02d}"
        / f"ep{episode:02d}_script_{lang.upper()}.json"
    )
    if not script_path.exists():
        return None
    try:
        return json.loads(script_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _configured_langs() -> list[str]:
    raw = os.getenv("LANGUAGES", "en")
    return [lang.strip().lower() for lang in raw.split(",") if lang.strip()]


def _validate_config(langs: list[str]) -> list[str]:
    """Return a list of missing/malformed configuration items."""
    issues: list[str] = []

    if not os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-ant-"):
        issues.append("ANTHROPIC_API_KEY missing or malformed")
    if not os.getenv("ELEVENLABS_API_KEY", "").startswith("sk_"):
        issues.append("ELEVENLABS_API_KEY missing or malformed")

    yt_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
    if not yt_token or "your-" in yt_token:
        issues.append("YOUTUBE_REFRESH_TOKEN not configured (required for publishing)")

    for lang in langs:
        vid_key = f"ELEVENLABS_VOICE_ID_{lang.upper()}"
        if not os.getenv(vid_key, "") or "your-" in os.getenv(vid_key, ""):
            issues.append(f"{vid_key} not configured")
        ch_key = f"YOUTUBE_CHANNEL_ID_{lang.upper()}"
        if not os.getenv(ch_key, "") or "your-" in os.getenv(ch_key, ""):
            issues.append(f"{ch_key} not configured (required for publishing)")

    return issues


def _run_episode(
    episode: int, week: int, topic: str, langs: list[str], dry_run: bool
) -> dict:
    """
    Run the full pipeline for one episode across all requested languages.

    Never raises — all agent errors are caught and stored in result["errors"].
    Returns:
        {"episode": int, "topic": str, "langs": dict, "errors": list[str]}
    """
    result: dict = {"episode": episode, "topic": topic, "langs": {}, "errors": []}

    print(f"\n{'='*60}")
    print(f"EP{episode:02d} - {topic}")
    print(f"{'='*60}")
    logger.info(f"EP{episode:02d} starting — topic: {topic!r}")

    # ── Phase 2: Script (per lang) ─────────────────────────────────────────────
    # Load from disk first so re-runs never burn an API call unnecessarily.
    scripts: dict[str, dict] = {}
    for lang in langs:
        cached = _load_script_from_disk(episode, week, lang)
        if cached is not None:
            scripts[lang] = cached
            print(f"\n[EP{episode:02d}][{lang.upper()}] Script already on disk — skipping generation")
            logger.info(f"EP{episode:02d} [{lang.upper()}] script loaded from disk")
            continue

        print(f"\n[EP{episode:02d}][{lang.upper()}] Generating script...")
        try:
            out = script_agent.run(topic, episode, week, lang=lang)
            scripts[lang] = out["script"]
            print(f"  OK   Script -> {out['output_path']}")
            logger.info(f"EP{episode:02d} [{lang.upper()}] script saved -> {out['output_path']}")
        except Exception as e:
            msg = f"script_agent [{lang.upper()}]: {e}"
            result["errors"].append(msg)
            logger.error(f"EP{episode:02d} {msg}")
            print(f"  FAIL {msg}")

    # ── Phase 3: Voice (per lang) ──────────────────────────────────────────────
    for lang in langs:
        if lang not in scripts:
            continue
        print(f"\n[EP{episode:02d}][{lang.upper()}] Synthesising voice...")
        try:
            out = voice_agent.run(scripts[lang], episode, week, lang=lang)
            if out.get("skipped"):
                print(f"  SKIP Voice already exists")
            else:
                dur = out.get("duration", 0)
                print(f"  OK   Voice -> {out['output_path']} ({dur:.1f}s)")
            logger.info(f"EP{episode:02d} [{lang.upper()}] voice done -> {out.get('output_path', '')}")
        except Exception as e:
            msg = f"voice_agent [{lang.upper()}]: {e}"
            result["errors"].append(msg)
            logger.error(f"EP{episode:02d} {msg}")
            print(f"  FAIL {msg}")
            # Drop this lang so downstream phases don't attempt it
            scripts.pop(lang, None)

    # Dry-run ends after voice
    if dry_run:
        print(f"\n[EP{episode:02d}] Dry run complete — script + voice only")
        logger.info(f"EP{episode:02d} dry run complete")
        return result

    # ── Phase 5: Visual render (language-agnostic, run once) ───────────────────
    reference_lang = "en" if "en" in scripts else next(iter(scripts), None)
    visual_ok = False

    if reference_lang:
        print(f"\n[EP{episode:02d}] Rendering visuals...")
        try:
            out = visual_agent.run(scripts[reference_lang], episode, week, lang=reference_lang)
            visual_ok = True
            if out.get("skipped"):
                print(f"  SKIP {out.get('message', 'Visuals already rendered')}")
            else:
                mb = out.get("size_mb", "?")
                dur = out.get("duration", 0)
                print(f"  OK   Visuals -> {out['output_path']} ({mb} MB, {dur:.1f}s)")
            logger.info(f"EP{episode:02d} visuals done -> {out.get('output_path', '')}")
        except Exception as e:
            msg = f"visual_agent: {e}"
            result["errors"].append(msg)
            logger.error(f"EP{episode:02d} {msg}")
            print(f"  FAIL {msg}")
    else:
        print(f"\n[EP{episode:02d}] No scripts available — skipping visual render")
        logger.warning(f"EP{episode:02d} no scripts available, visual render skipped")

    # ── Phase 6: Assembly + captions (per lang) ────────────────────────────────
    if visual_ok:
        for lang in langs:
            if lang not in scripts:
                continue
            print(f"\n[EP{episode:02d}][{lang.upper()}] Assembling final video...")
            try:
                out = assembly_agent.run(episode, week, lang=lang)
                if out.get("skipped"):
                    print(f"  SKIP {out.get('message', 'Already assembled')}")
                else:
                    mb = out.get("size_mb", "?")
                    dur = out.get("duration", 0)
                    print(f"  OK   Final -> {out['output_path']} ({mb} MB, {dur:.1f}s)")
                logger.info(f"EP{episode:02d} [{lang.upper()}] assembly done -> {out.get('output_path', '')}")
                result["langs"].setdefault(lang, {})["final_path"] = out["output_path"]
            except Exception as e:
                msg = f"assembly_agent [{lang.upper()}]: {e}"
                result["errors"].append(msg)
                logger.error(f"EP{episode:02d} {msg}")
                print(f"  FAIL {msg}")

    # ── Phase 7: Publish (per lang) ────────────────────────────────────────────
    for lang in langs:
        if lang not in scripts:
            continue
        if lang not in result["langs"]:
            continue  # assembly failed or was skipped
        print(f"\n[EP{episode:02d}][{lang.upper()}] Publishing to YouTube...")
        try:
            out = publisher_agent.run(scripts[lang], episode, week, lang=lang)
            if out.get("skipped"):
                print(f"  SKIP Already published -> {out['video_url']}")
            else:
                sched = out.get("scheduled_publish") or "immediately"
                print(f"  OK   Published -> {out['video_url']} (scheduled: {sched})")
            logger.info(f"EP{episode:02d} [{lang.upper()}] published -> {out.get('video_url', '')}")
            result["langs"].setdefault(lang, {})["video_url"] = out["video_url"]
        except Exception as e:
            msg = f"publisher_agent [{lang.upper()}]: {e}"
            result["errors"].append(msg)
            logger.error(f"EP{episode:02d} {msg}")
            print(f"  FAIL {msg}")

    return result


def _print_summary(all_results: list[dict], dry_run: bool) -> None:
    total = len(all_results)
    n_errors = sum(1 for r in all_results if r.get("errors") or r.get("fatal"))

    print(f"\n{'='*60}")
    print(f"Pipeline {'(dry run) ' if dry_run else ''}complete — {total} episode(s) processed")
    print(f"{'='*60}")

    for r in sorted(all_results, key=lambda x: x["episode"]):
        ep = r["episode"]
        if r.get("fatal"):
            print(f"  EP{ep:02d}  FATAL   {r['fatal']}")
        elif r.get("errors"):
            errs = "; ".join(r["errors"])
            print(f"  EP{ep:02d}  WARN ({len(r['errors'])})  {errs}")
        else:
            urls = [
                f"[{lang.upper()}] {info.get('video_url', 'no url')}"
                for lang, info in r.get("langs", {}).items()
            ]
            detail = " | ".join(urls) if urls else ("dry-run ok" if dry_run else "ok")
            print(f"  EP{ep:02d}  OK      {detail}")

    print()
    if n_errors:
        logger.warning(f"Pipeline complete — {n_errors}/{total} episode(s) had errors")
    else:
        logger.info(f"Pipeline complete — {total}/{total} episodes ok")


def sync_from_git() -> None:
    """Pull latest code and topics from GitHub before running."""
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            logger.info(f"Git pull successful: {result.stdout.strip()}")
        else:
            logger.warning(f"Git pull failed: {result.stderr.strip()} — continuing with existing files")
    except Exception as e:
        logger.warning(f"Git pull error: {e} — continuing with existing files")


def main() -> None:
    _setup_logging()
    sync_from_git()

    parser = argparse.ArgumentParser(description="AI Bytes Pipeline Orchestrator")
    parser.add_argument("--episode", type=int, help="Run only this episode number (1-based)")
    parser.add_argument("--lang", help="Comma-separated language codes, e.g. 'en' or 'en,ta'")
    parser.add_argument("--week", type=int, help="Week number (default: auto from START_PUBLISH_DATE)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run script + voice only; skip visual, assembly, and publish",
    )
    parser.add_argument(
        "--topics-file",
        help="Path to a topics file (default: topics.txt). Use for language-specific batches.",
    )
    args = parser.parse_args()

    week = args.week if args.week is not None else _auto_week()
    langs = (
        [lang.strip().lower() for lang in args.lang.split(",")]
        if args.lang
        else _configured_langs()
    )

    print(f"\nAI Bytes Pipeline")
    print(f"  Date     : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Week     : {week}")
    print(f"  Languages: {', '.join(l.upper() for l in langs)}")
    if args.dry_run:
        print(f"  Mode     : DRY RUN (script + voice only)")
    logger.info(
        f"Pipeline starting — week={week} langs={langs} "
        f"dry_run={args.dry_run} episode={args.episode}"
    )

    # Config validation — hard-stop on any issue for a full run
    issues = _validate_config(langs)
    if issues:
        print("\nConfiguration issues:")
        for issue in issues:
            print(f"  WARN {issue}")
        if not args.dry_run:
            print("\nFix the above issues in .env before running the pipeline.")
            sys.exit(1)
        else:
            print("\n(Dry run — continuing despite issues)\n")

    topics_path = Path(args.topics_file) if args.topics_file else None
    topics = _load_topics(topics_path)
    topics_label = args.topics_file if args.topics_file else "topics.txt"
    print(f"\n  Topics   : {len(topics)} loaded from {topics_label}")
    for i, t in enumerate(topics, 1):
        print(f"    {i}. {t}")

    if args.episode is not None:
        idx = args.episode - 1
        if idx < 0 or idx >= len(topics):
            print(f"\nError: --episode {args.episode} out of range (1-{len(topics)})")
            sys.exit(1)
        episodes = [(args.episode, topics[idx])]
    else:
        episodes = [(i + 1, topic) for i, topic in enumerate(topics)]

    # ── First pass ─────────────────────────────────────────────────────────────
    all_results: list[dict] = []
    failed_episodes: list[tuple[int, str]] = []

    for episode, topic in episodes:
        try:
            result = _run_episode(episode, week, topic, langs, dry_run=args.dry_run)
            all_results.append(result)
            if result["errors"]:
                failed_episodes.append((episode, topic))
        except Exception as e:
            logger.error(f"EP{episode:02d} FATAL: {e}", exc_info=True)
            print(f"\nFATAL EP{episode:02d}: {e}")
            traceback.print_exc()
            all_results.append({
                "episode": episode,
                "topic": topic,
                "fatal": str(e),
                "langs": {},
                "errors": [],
            })
            failed_episodes.append((episode, topic))

    # ── Retry pass (once, full runs only) ──────────────────────────────────────
    if failed_episodes and not args.dry_run:
        print(f"\n--- Retrying {len(failed_episodes)} episode(s) with errors ---")
        logger.info(f"Retry pass for episodes: {[ep for ep, _ in failed_episodes]}")

        for episode, topic in failed_episodes:
            all_results = [r for r in all_results if r["episode"] != episode]
            try:
                result = _run_episode(episode, week, topic, langs, dry_run=False)
                all_results.append(result)
                status = "succeeded" if not result["errors"] else "still has errors"
                logger.info(f"EP{episode:02d} retry {status}")
            except Exception as e:
                logger.error(f"EP{episode:02d} retry FATAL: {e}", exc_info=True)
                print(f"\nRETRY FATAL EP{episode:02d}: {e}")
                all_results.append({
                    "episode": episode,
                    "topic": topic,
                    "fatal": f"retry: {e}",
                    "langs": {},
                    "errors": [],
                })

    _print_summary(all_results, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
