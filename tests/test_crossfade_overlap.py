"""Regression tests for ComposedScene crossfade overlap in AIBytesReel.

Validates that the StoryboardReel timing logic produces correct Sequence
parameters: consecutive ComposedScene scenes overlap by exactly CROSSFADE
frames, total duration is unchanged, and non-ComposedScene transitions
are unaffected.

The logic under test lives in remotion/src/AIBytesReel.tsx (StoryboardReel).
These tests mirror that logic in Python against real storyboard data.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

FPS = 30
CROSSFADE = 9  # must match AIBytesReel.tsx constant


def _compute_sequences(storyboard: list[dict]) -> list[dict]:
    """Mirror the StoryboardReel timing logic from AIBytesReel.tsx."""
    cursor = 0
    sequences = []
    for idx, scene in enumerate(storyboard):
        start_frame = cursor
        duration_frames = round(scene["duration_seconds"] * FPS)
        next_scene = storyboard[idx + 1] if idx < len(storyboard) - 1 else None
        overlap = (
            CROSSFADE
            if scene.get("component") == "ComposedScene"
            and next_scene is not None
            and next_scene.get("component") == "ComposedScene"
            else 0
        )
        cursor += duration_frames
        sequences.append(
            {
                "scene_id": scene["scene_id"],
                "component": scene.get("component", ""),
                "start_frame": start_frame,
                "duration_frames": duration_frames,
                "overlap": overlap,
                "sequence_duration": duration_frames + overlap,
            }
        )
    return sequences


@pytest.fixture()
def ep03_storyboard() -> list[dict]:
    sb_path = (
        Path(__file__).parent.parent
        / "output"
        / "week_01"
        / "ep03"
        / "ep03_storyboard_composed.json"
    )
    if not sb_path.exists():
        pytest.skip("EP03 composed storyboard not found")
    doc = json.loads(sb_path.read_text(encoding="utf-8"))
    return doc["storyboard"]


@pytest.fixture()
def sequences(ep03_storyboard: list[dict]) -> list[dict]:
    return _compute_sequences(ep03_storyboard)


# ── 1. ComposedScene → ComposedScene overlap = exactly CROSSFADE ────────────

def test_composed_to_composed_overlap_equals_crossfade(sequences: list[dict]) -> None:
    for i, seq in enumerate(sequences):
        if i + 1 >= len(sequences):
            continue
        nxt = sequences[i + 1]
        if seq["component"] == "ComposedScene" and nxt["component"] == "ComposedScene":
            assert seq["overlap"] == CROSSFADE, (
                f"S{seq['scene_id']:02d}→S{nxt['scene_id']:02d}: "
                f"overlap={seq['overlap']} but expected {CROSSFADE}"
            )


# ── 2. Total episode duration unchanged ─────────────────────────────────────

def test_total_duration_unchanged(ep03_storyboard: list[dict], sequences: list[dict]) -> None:
    planned_frames = sum(round(s["duration_seconds"] * FPS) for s in ep03_storyboard)
    cursor_end = sequences[-1]["start_frame"] + sequences[-1]["duration_frames"]
    assert cursor_end == planned_frames, (
        f"Cursor advanced to {cursor_end} frames but planned {planned_frames}. "
        "Overlap must not shift the cursor — it only extends the Sequence."
    )


# ── 3. Outgoing scene does not persist beyond intended overlap ──────────────

def test_outgoing_scene_ends_at_overlap(sequences: list[dict]) -> None:
    for seq in sequences:
        if seq["overlap"] > 0:
            expected_end = seq["start_frame"] + seq["duration_frames"] + CROSSFADE
            actual_end = seq["start_frame"] + seq["sequence_duration"]
            assert actual_end == expected_end, (
                f"S{seq['scene_id']:02d}: Sequence end {actual_end} != "
                f"expected {expected_end} (start + duration + CROSSFADE)"
            )
            assert seq["sequence_duration"] == seq["duration_frames"] + CROSSFADE


# ── 4. Incoming scene begins during the overlap ────────────────────────────

def test_incoming_scene_starts_during_overlap(sequences: list[dict]) -> None:
    for i, seq in enumerate(sequences):
        if seq["overlap"] == 0:
            continue
        nxt = sequences[i + 1]
        outgoing_end = seq["start_frame"] + seq["sequence_duration"]
        incoming_start = nxt["start_frame"]
        overlap_frames = outgoing_end - incoming_start
        assert overlap_frames == CROSSFADE, (
            f"S{seq['scene_id']:02d}→S{nxt['scene_id']:02d}: "
            f"actual overlap={overlap_frames} frames, expected {CROSSFADE}"
        )
        assert incoming_start < outgoing_end, (
            f"Incoming scene S{nxt['scene_id']:02d} must start before "
            f"outgoing scene S{seq['scene_id']:02d} ends"
        )


# ── 5. Non-ComposedScene transitions have zero overlap ─────────────────────

def test_non_composed_transitions_unchanged(sequences: list[dict]) -> None:
    for i, seq in enumerate(sequences):
        if i + 1 >= len(sequences):
            continue
        nxt = sequences[i + 1]
        both_composed = (
            seq["component"] == "ComposedScene"
            and nxt["component"] == "ComposedScene"
        )
        if not both_composed:
            assert seq["overlap"] == 0, (
                f"S{seq['scene_id']:02d} ({seq['component']}) → "
                f"S{nxt['scene_id']:02d} ({nxt['component']}): "
                f"overlap should be 0 for non-ComposedScene transitions, "
                f"got {seq['overlap']}"
            )


# ── 6. Last ComposedScene has no overlap (no scene to crossfade into) ──────

def test_last_composed_scene_no_overlap(sequences: list[dict]) -> None:
    composed = [s for s in sequences if s["component"] == "ComposedScene"]
    if not composed:
        pytest.skip("No ComposedScene in storyboard")
    last = composed[-1]
    last_idx = sequences.index(last)
    if last_idx + 1 < len(sequences):
        nxt = sequences[last_idx + 1]
        if nxt["component"] != "ComposedScene":
            assert last["overlap"] == 0, (
                f"Last ComposedScene S{last['scene_id']:02d} → "
                f"non-Composed S{nxt['scene_id']:02d} should have overlap=0"
            )


# ── Synthetic storyboard tests (framework-independent) ─────────────────────

def _make_scene(scene_id: int, component: str, dur: float) -> dict:
    return {"scene_id": scene_id, "component": component, "duration_seconds": dur}


class TestSyntheticStoryboards:
    """Tests that don't depend on EP03 output files."""

    def test_three_consecutive_composed(self) -> None:
        sb = [
            _make_scene(1, "KineticTypoScene", 5.0),
            _make_scene(2, "ComposedScene", 8.0),
            _make_scene(3, "ComposedScene", 6.0),
            _make_scene(4, "ComposedScene", 7.0),
            _make_scene(5, "CTAScene", 5.0),
        ]
        seqs = _compute_sequences(sb)
        assert seqs[0]["overlap"] == 0      # Kinetic → Composed
        assert seqs[1]["overlap"] == CROSSFADE  # Composed → Composed
        assert seqs[2]["overlap"] == CROSSFADE  # Composed → Composed
        assert seqs[3]["overlap"] == 0      # Composed → CTA
        assert seqs[4]["overlap"] == 0      # CTA (last)

    def test_no_composed_scenes(self) -> None:
        sb = [
            _make_scene(1, "KineticTypoScene", 5.0),
            _make_scene(2, "FlowScene", 8.0),
            _make_scene(3, "CTAScene", 5.0),
        ]
        seqs = _compute_sequences(sb)
        assert all(s["overlap"] == 0 for s in seqs)

    def test_single_composed_scene(self) -> None:
        sb = [
            _make_scene(1, "KineticTypoScene", 5.0),
            _make_scene(2, "ComposedScene", 8.0),
            _make_scene(3, "CTAScene", 5.0),
        ]
        seqs = _compute_sequences(sb)
        assert all(s["overlap"] == 0 for s in seqs)

    def test_cursor_never_shifts(self) -> None:
        sb = [
            _make_scene(1, "ComposedScene", 8.0),
            _make_scene(2, "ComposedScene", 6.0),
            _make_scene(3, "ComposedScene", 7.0),
        ]
        seqs = _compute_sequences(sb)
        planned = sum(round(s["duration_seconds"] * FPS) for s in sb)
        cursor_end = seqs[-1]["start_frame"] + seqs[-1]["duration_frames"]
        assert cursor_end == planned

    def test_overlap_window_exact(self) -> None:
        sb = [
            _make_scene(1, "ComposedScene", 4.0),
            _make_scene(2, "ComposedScene", 4.0),
        ]
        seqs = _compute_sequences(sb)
        s1_end = seqs[0]["start_frame"] + seqs[0]["sequence_duration"]
        s2_start = seqs[1]["start_frame"]
        assert s1_end - s2_start == CROSSFADE
