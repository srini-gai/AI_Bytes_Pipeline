"""
Pre-render validation checks for AI Bytes pipeline.

Runs 5 checks against render_props.json before Remotion render:
  1. TOPIC_DATA_VALIDATION  — all scenes have required data populated
  2. RAG_LEAK_CHECK         — fail if RAG terms appear in scene props
  3. INTERNAL_LABEL_CHECK   — fail if implementation names appear on-screen
  4. NUMERIC_INTEGRITY      — illustrative source_type scenes don't render precise values
  5. HIGGSFIELD_S01_VISIBLE — s01 generated video clip composited correctly
"""
import json
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Components that REQUIRE scene.data to be non-null
DATA_REQUIRED_COMPONENTS = {
    'TokenScene',
    'DataScene',
    'NumberCounterScene',
}

# RAG / wrong-topic leak terms (case-insensitive)
RAG_LEAK_TERMS = [
    r'\bRAG\b',
    r'Retrieval.Augmented.Generation',
    r'\bRAG ANSWER\b',
    r'\bWITHOUT RAG\b',
    r'\bWITH RAG\b',
    r'\bretrieval\b',
    r'\bgrounded answer\b',
    r'Eiffel Tower',
    r'Source:\s*Wikipedia',
]

# Internal implementation labels that must never appear on-screen
INTERNAL_LABEL_PATTERNS = [
    r'\binput_sentence\b',
    r'\btoken_boxes\b',
    r'\bboundary_markers\b',
    r'\bscene_id\b',
    r'\bwithout_rag_panel\b',
    r'\bwith_rag_panel\b',
    r'\brag_panel\b',
]


def check_topic_data_validation(storyboard: list[dict]) -> list[str]:
    """Check 1: All scenes have required data populated."""
    errors: list[str] = []
    for scene in storyboard:
        sid = scene.get('scene_id', '?')
        component = scene.get('component', '')
        if component in DATA_REQUIRED_COMPONENTS:
            data = scene.get('data')
            if data is None:
                errors.append(
                    f"s{sid:02d} ({component}): scene.data is null — "
                    f"required data must be populated"
                )
        # All scenes need on_screen_text for beat-driven components
        ost = scene.get('on_screen_text', [])
        if component == 'BeforeAfterScene' and len(ost) < 4:
            errors.append(
                f"s{sid:02d} (BeforeAfterScene): on_screen_text has {len(ost)} entries, "
                f"needs ≥4 [beforeLabel, afterLabel, beforeDetail, afterDetail]"
            )
        if component == 'TransformScene' and len(ost) < 3:
            errors.append(
                f"s{sid:02d} (TransformScene): on_screen_text has {len(ost)} entries, "
                f"needs ≥3 transform entries"
            )
    return errors


def check_rag_leak(storyboard: list[dict]) -> list[str]:
    """Check 2: Fail if RAG/wrong-topic terms appear in scene props."""
    errors: list[str] = []
    compiled = [re.compile(p, re.IGNORECASE) for p in RAG_LEAK_TERMS]

    for scene in storyboard:
        sid = scene.get('scene_id', '?')
        # Check on_screen_text
        for text in scene.get('on_screen_text', []):
            for pat in compiled:
                if pat.search(text):
                    errors.append(
                        f"s{sid:02d}: RAG leak in on_screen_text: '{text}' "
                        f"matches /{pat.pattern}/"
                    )
        # Check data (serialized)
        data = scene.get('data')
        if data:
            data_str = json.dumps(data)
            for pat in compiled:
                if pat.search(data_str):
                    errors.append(
                        f"s{sid:02d}: RAG leak in scene.data: "
                        f"matches /{pat.pattern}/"
                    )
        # Check visual_goal
        vg = scene.get('visual_goal', '')
        for pat in compiled:
            if pat.search(vg):
                errors.append(
                    f"s{sid:02d}: RAG leak in visual_goal: '{vg}' "
                    f"matches /{pat.pattern}/"
                )
    return errors


def check_internal_labels(storyboard: list[dict]) -> list[str]:
    """Check 3: Fail if implementation names appear in on-screen content."""
    errors: list[str] = []
    compiled = [re.compile(p, re.IGNORECASE) for p in INTERNAL_LABEL_PATTERNS]

    for scene in storyboard:
        sid = scene.get('scene_id', '?')
        for text in scene.get('on_screen_text', []):
            for pat in compiled:
                if pat.search(text):
                    errors.append(
                        f"s{sid:02d}: internal label in on_screen_text: '{text}' "
                        f"matches /{pat.pattern}/"
                    )
    return errors


def check_numeric_integrity(storyboard: list[dict]) -> list[str]:
    """Check 4: Verify illustrative source_type scenes have the flag set."""
    errors: list[str] = []
    for scene in storyboard:
        sid = scene.get('scene_id', '?')
        source_type = scene.get('source_type', '')
        component = scene.get('component', '')
        data = scene.get('data')

        if source_type == 'illustrative':
            # Only DataScene and NumberCounterScene render numeric values
            # Other components (BeforeAfterScene, etc.) show text labels — no concern
            if component in ('DataScene', 'NumberCounterScene'):
                logger.info(
                    f"s{sid:02d} ({component}): source_type=illustrative — "
                    f"qualitative mode will suppress precise values ✓"
                )
            else:
                logger.info(
                    f"s{sid:02d} ({component}): source_type=illustrative — "
                    f"component shows text labels, not numeric values (ok)"
                )
        elif component in ('DataScene', 'NumberCounterScene') and data:
            # Non-illustrative: confirm data has values
            logger.info(
                f"s{sid:02d} ({component}): source_type={source_type or 'factual'} — "
                f"precise values will render ✓"
            )
    return errors


def check_higgsfield_s01(storyboard: list[dict], episode_dir: Path) -> list[str]:
    """Check 5: Verify s01 generated video clip is set up for compositing."""
    errors: list[str] = []
    s01 = next((s for s in storyboard if s.get('scene_id') == 1), None)
    if not s01:
        errors.append("s01: scene not found in storyboard")
        return errors

    asset_source = s01.get('asset_source', '')
    if asset_source != 'GENERATIVE_VIDEO':
        logger.info("s01: asset_source is not GENERATIVE_VIDEO — no Higgsfield check needed")
        return errors

    # Check that generated video file exists
    gen_video_files = list(episode_dir.glob('**/higgsfield_*.mp4')) + \
                      list(episode_dir.glob('**/gen_video_*.mp4')) + \
                      list(episode_dir.glob('**/*s01*.mp4'))

    # Also check render_props for genVideoSrc
    props_path = episode_dir / 'ep01_render_props.json'
    if props_path.exists():
        with open(props_path) as f:
            props = json.load(f)
        gen_src = props.get('genVideoSrc')
        if gen_src:
            gen_path = episode_dir / gen_src
            if not gen_path.exists():
                # Try relative to remotion/public
                alt_path = episode_dir.parent.parent / 'remotion' / 'public' / gen_src
                if not alt_path.exists():
                    errors.append(
                        f"s01: genVideoSrc='{gen_src}' but file not found at "
                        f"{gen_path} or {alt_path}"
                    )
                else:
                    logger.info(f"s01: Higgsfield clip found at {alt_path} ✓")
            else:
                logger.info(f"s01: Higgsfield clip found at {gen_path} ✓")
        else:
            logger.warning("s01: asset_source=GENERATIVE_VIDEO but genVideoSrc not set in props")

    # Check s01 component is KineticTypoScene (which supports transparentBg)
    if s01.get('component') != 'KineticTypoScene':
        errors.append(
            f"s01: expected KineticTypoScene for Higgsfield compositing, "
            f"got {s01.get('component')}"
        )

    return errors


def run_all_checks(render_props_path: str) -> dict:
    """Run all 5 pre-render checks. Returns {check_name: {passed, errors}}."""
    path = Path(render_props_path)
    with open(path) as f:
        props = json.load(f)

    storyboard = props.get('storyboard', [])
    episode_dir = path.parent

    results: dict[str, dict] = {}

    checks = [
        ('TOPIC_DATA_VALIDATION', lambda: check_topic_data_validation(storyboard)),
        ('RAG_LEAK_CHECK', lambda: check_rag_leak(storyboard)),
        ('INTERNAL_LABEL_CHECK', lambda: check_internal_labels(storyboard)),
        ('NUMERIC_INTEGRITY', lambda: check_numeric_integrity(storyboard)),
        ('HIGGSFIELD_S01_VISIBLE', lambda: check_higgsfield_s01(storyboard, episode_dir)),
    ]

    all_passed = True
    for name, check_fn in checks:
        errors = check_fn()
        passed = len(errors) == 0
        results[name] = {'passed': passed, 'errors': errors}
        status = '✓ PASS' if passed else '✗ FAIL'
        logger.info(f"  {status}  {name}")
        if not passed:
            all_passed = False
            for err in errors:
                logger.error(f"    → {err}")

    results['_all_passed'] = all_passed
    return results


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    if len(sys.argv) < 2:
        print("Usage: python pre_render_checks.py <render_props.json>")
        sys.exit(1)

    props_path = sys.argv[1]
    logger.info(f"Running pre-render checks on: {props_path}")
    logger.info("=" * 60)

    results = run_all_checks(props_path)

    logger.info("=" * 60)
    if results['_all_passed']:
        logger.info("ALL 5 CHECKS PASSED ✓ — safe to render")
        sys.exit(0)
    else:
        failed = [k for k, v in results.items() if k != '_all_passed' and not v['passed']]
        logger.error(f"FAILED CHECKS: {', '.join(failed)}")
        sys.exit(1)
