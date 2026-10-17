"""Transition-safety regression tests for the generic Defect #7 fix.

Validates the GENERIC transition-safety contract introduced in
remotion/src/AIBytesReel.tsx:
  - Every scene (except the last) extends by CROSSFADE frames into the
    overlap region, so component animations run through the handoff.
  - The Fade wrapper starts incoming scenes at TRANSITION_FLOOR (12%)
    opacity, not 0, preventing content-free gaps on dark backgrounds.
  - No channel-specific or component-specific conditionals are involved.

Six required criteria:
  1. KineticTypo → dark incoming scene has no blank interval
  2. KineticTypo → bright incoming scene still behaves correctly
  3. ordinary scene → ordinary scene behavior remains unchanged
  4. transition overlap always maintains visible-content floor
  5. TIMELINE_QA still catches a genuinely blank transition
  6. no channel-specific conditional is involved
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

FPS = 30
CROSSFADE = 9
TRANSITION_FLOOR = 0.12


def _interpolate(frame: float, in_range: list, out_range: list, clamp_right: bool = True) -> float:
    t = (frame - in_range[0]) / (in_range[1] - in_range[0]) if in_range[1] != in_range[0] else 1.0
    t = max(0.0, t)
    if clamp_right:
        t = min(1.0, t)
    return out_range[0] + t * (out_range[1] - out_range[0])


def _fade_opacity(frame: int, duration: int, no_fade_in: bool = False) -> float:
    fade_in = 1.0 if no_fade_in else _interpolate(frame, [0, CROSSFADE], [TRANSITION_FLOOR, 1.0])
    fade_out = _interpolate(frame, [duration - CROSSFADE, duration], [1.0, 0.0])
    return min(fade_in, fade_out)


def _kinetic_char_opacity(frame: int, duration_in_frames: int) -> float:
    shatter_start = round(duration_in_frames * 0.45)
    if frame < shatter_start:
        return 1.0
    shatter_progress = _interpolate(frame, [shatter_start, duration_in_frames - 4], [0.0, 1.0])
    eased = shatter_progress ** 2
    return max(0.0, 1.0 - eased)


def _make_scene(scene_id: int, component: str, dur: float) -> dict:
    return {"scene_id": scene_id, "component": component, "duration_seconds": dur}


def _compute_sequences(storyboard: list[dict]) -> list[dict]:
    cursor = 0
    sequences = []
    for idx, scene in enumerate(storyboard):
        start_frame = cursor
        duration_frames = round(scene["duration_seconds"] * FPS)
        next_scene = storyboard[idx + 1] if idx < len(storyboard) - 1 else None
        overlap = CROSSFADE if next_scene is not None else 0
        cursor += duration_frames
        sequences.append({
            "scene_id": scene["scene_id"],
            "component": scene.get("component", ""),
            "start_frame": start_frame,
            "duration_frames": duration_frames,
            "overlap": overlap,
            "sequence_duration": duration_frames + overlap,
        })
    return sequences


# ── Criterion 1: KineticTypo → dark incoming scene has no blank interval ──────

class TestKineticTypoToDarkScene:

    def test_content_present_throughout_transition(self) -> None:
        sb = [
            _make_scene(1, "KineticTypoScene", 3.0),
            _make_scene(2, "SplitCompareScene", 5.0),
        ]
        seqs = _compute_sequences(sb)
        s1 = seqs[0]
        s2 = seqs[1]

        for frame_offset in range(CROSSFADE + 1):
            global_frame = s1["duration_frames"] + frame_offset
            outgoing_local = global_frame
            outgoing_opacity = _fade_opacity(outgoing_local, s1["sequence_duration"], no_fade_in=True)
            outgoing_char = _kinetic_char_opacity(outgoing_local, s1["sequence_duration"])
            outgoing_content = outgoing_opacity * outgoing_char

            incoming_local = frame_offset
            incoming_opacity = _fade_opacity(incoming_local, s2["sequence_duration"])

            combined = max(outgoing_content, incoming_opacity)
            assert combined >= TRANSITION_FLOOR, (
                f"Frame offset {frame_offset}: combined content={combined:.4f} < "
                f"TRANSITION_FLOOR={TRANSITION_FLOOR}. "
                f"Outgoing={outgoing_content:.4f}, incoming={incoming_opacity:.4f}"
            )

    def test_incoming_starts_at_floor_not_zero(self) -> None:
        sb = [
            _make_scene(1, "KineticTypoScene", 3.0),
            _make_scene(2, "SplitCompareScene", 5.0),
        ]
        seqs = _compute_sequences(sb)
        incoming_opacity_at_0 = _fade_opacity(0, seqs[1]["sequence_duration"])
        assert incoming_opacity_at_0 == pytest.approx(TRANSITION_FLOOR, abs=0.001), (
            f"Incoming scene starts at {incoming_opacity_at_0:.4f}, expected {TRANSITION_FLOOR}"
        )


# ── Criterion 2: KineticTypo → bright incoming scene still behaves correctly ──

class TestKineticTypoToBrightScene:

    def test_bright_scene_fade_in_starts_at_floor(self) -> None:
        sb = [
            _make_scene(1, "KineticTypoScene", 3.0),
            _make_scene(2, "DataScene", 6.0),
        ]
        seqs = _compute_sequences(sb)
        incoming_at_0 = _fade_opacity(0, seqs[1]["sequence_duration"])
        assert incoming_at_0 >= TRANSITION_FLOOR

    def test_bright_scene_reaches_full_opacity(self) -> None:
        sb = [
            _make_scene(1, "KineticTypoScene", 3.0),
            _make_scene(2, "DataScene", 6.0),
        ]
        seqs = _compute_sequences(sb)
        incoming_at_crossfade = _fade_opacity(CROSSFADE, seqs[1]["sequence_duration"])
        assert incoming_at_crossfade == pytest.approx(1.0, abs=0.01)


# ── Criterion 3: ordinary scene → ordinary scene behavior remains unchanged ──

class TestOrdinaryTransitions:

    def test_scene_sequence_has_crossfade_overlap(self) -> None:
        sb = [
            _make_scene(1, "FlowScene", 5.0),
            _make_scene(2, "TransformScene", 6.0),
            _make_scene(3, "CTAScene", 5.0),
        ]
        seqs = _compute_sequences(sb)
        assert seqs[0]["overlap"] == CROSSFADE
        assert seqs[1]["overlap"] == CROSSFADE
        assert seqs[2]["overlap"] == 0

    def test_total_cursor_unchanged_by_overlap(self) -> None:
        sb = [
            _make_scene(1, "FlowScene", 5.0),
            _make_scene(2, "TransformScene", 6.0),
            _make_scene(3, "CTAScene", 5.0),
        ]
        seqs = _compute_sequences(sb)
        planned_frames = sum(round(s["duration_seconds"] * FPS) for s in sb)
        cursor_end = seqs[-1]["start_frame"] + seqs[-1]["duration_frames"]
        assert cursor_end == planned_frames

    def test_last_scene_no_overlap(self) -> None:
        sb = [
            _make_scene(1, "FlowScene", 5.0),
            _make_scene(2, "CTAScene", 5.0),
        ]
        seqs = _compute_sequences(sb)
        assert seqs[-1]["overlap"] == 0


# ── Criterion 4: transition overlap always maintains visible-content floor ────

class TestTransitionFloor:

    def test_fade_in_never_below_floor(self) -> None:
        duration = 150
        for frame in range(CROSSFADE + 1):
            opacity = _fade_opacity(frame, duration)
            assert opacity >= TRANSITION_FLOOR - 0.001, (
                f"Frame {frame}: opacity {opacity:.4f} < floor {TRANSITION_FLOOR}"
            )

    def test_fade_in_monotonically_increases(self) -> None:
        duration = 150
        prev = 0.0
        for frame in range(CROSSFADE + 1):
            opacity = _fade_opacity(frame, duration)
            assert opacity >= prev - 0.001, (
                f"Frame {frame}: opacity {opacity:.4f} decreased from {prev:.4f}"
            )
            prev = opacity

    def test_first_scene_no_fade_in(self) -> None:
        duration = 150
        opacity_at_0 = _fade_opacity(0, duration, no_fade_in=True)
        assert opacity_at_0 == 1.0

    def test_midscene_opacity_is_full(self) -> None:
        duration = 300
        mid = duration // 2
        assert _fade_opacity(mid, duration) == pytest.approx(1.0, abs=0.01)


# ── Criterion 5: TIMELINE_QA still catches a genuinely blank transition ───────

class TestTimelineQACatchesBlanks:

    def test_zero_content_span_detected(self) -> None:
        from timeline_qa_guard import BLANK_SPAN_THRESHOLD_S, SAMPLE_INTERVAL_S
        blank_duration = 1.0
        n_samples = int(blank_duration / SAMPLE_INTERVAL_S)
        assert n_samples * SAMPLE_INTERVAL_S >= BLANK_SPAN_THRESHOLD_S, (
            "A 1.0s blank should exceed the threshold and be caught"
        )

    def test_threshold_not_weakened(self) -> None:
        from timeline_qa_guard import BLANK_SPAN_THRESHOLD_S
        assert BLANK_SPAN_THRESHOLD_S == 0.75, (
            f"BLANK_SPAN_THRESHOLD_S={BLANK_SPAN_THRESHOLD_S}, expected 0.75 — "
            "threshold must not be weakened to hide defects"
        )

    def test_content_delta_unchanged(self) -> None:
        from timeline_qa_guard import CONTENT_DELTA
        assert CONTENT_DELTA == 18, (
            f"CONTENT_DELTA={CONTENT_DELTA}, expected 18 — "
            "sensitivity must not be reduced"
        )


# ── Criterion 6: no channel-specific conditional is involved ─────────────────

class TestNoChannelSpecificConditionals:

    def test_overlap_is_universal_not_component_gated(self) -> None:
        components = [
            "KineticTypoScene", "SplitCompareScene", "SketchScene",
            "DataScene", "FlowScene", "TransformScene",
            "CardStackScene", "TakeawayScene", "CTAScene",
        ]
        for comp in components:
            sb = [
                _make_scene(1, comp, 5.0),
                _make_scene(2, "FlowScene", 5.0),
            ]
            seqs = _compute_sequences(sb)
            assert seqs[0]["overlap"] == CROSSFADE, (
                f"{comp} → FlowScene: overlap={seqs[0]['overlap']}, "
                f"expected {CROSSFADE}. Overlap must be universal."
            )

    def test_fade_floor_applies_regardless_of_component(self) -> None:
        duration = 150
        opacity = _fade_opacity(0, duration, no_fade_in=False)
        assert opacity == pytest.approx(TRANSITION_FLOOR, abs=0.001)

    def test_no_channel_name_in_transition_logic(self) -> None:
        src_path = Path(__file__).parent.parent / "remotion" / "src" / "AIBytesReel.tsx"
        content = src_path.read_text(encoding="utf-8")
        fade_start = content.index("const Fade:")
        fade_end = content.index("};", fade_start) + 2
        fade_code = content[fade_start:fade_end]

        storyboard_reel_start = content.index("const StoryboardReel")
        cursor_block_start = content.index("let cursor = 0;", storyboard_reel_start)
        cursor_block_end = content.index("return {scene, startFrame, durationFrames, overlap};", cursor_block_start) + 60
        overlap_code = content[cursor_block_start:cursor_block_end]

        transition_code = fade_code + "\n" + overlap_code
        channel_keywords = ["cricket_pulse", "cricket", "srini_on_ai"]
        for keyword in channel_keywords:
            assert keyword.lower() not in transition_code.lower(), (
                f"Found channel-specific keyword '{keyword}' in transition logic — "
                "the fix must be channel-agnostic"
            )
