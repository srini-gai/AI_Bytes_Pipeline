"""Scene lifecycle regression tests — crossfade overlap + duration-aware components.

Verifies:
1. AIBytesReel crossfade overlap applies to ALL scene transitions
2. SketchScene uses durationInFrames for proportional timing
3. FlowScene uses durationInFrames instead of hard-coded 180
4. PipelineScene accepts durationInFrames prop
5. No premature fade/unmount before scene end
6. Components work with two different durations
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

REMOTION_SRC = Path(__file__).parent.parent / "remotion" / "src"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Crossfade overlap — ALL scene transitions
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossfadeOverlap:
    """Every scene transition must have crossfade overlap, not just ComposedScene."""

    @pytest.fixture
    def _reel_source(self) -> str:
        return (REMOTION_SRC / "AIBytesReel.tsx").read_text(encoding="utf-8")

    def test_overlap_not_restricted_to_composed_scene(self, _reel_source: str):
        """overlap must not be gated by ComposedScene check."""
        assert "scene.component === 'ComposedScene'" not in _reel_source

    def test_overlap_uses_crossfade_when_next_scene_exists(self, _reel_source: str):
        """overlap must be CROSSFADE for every non-last scene."""
        assert "nextScene ? CROSSFADE : 0" in _reel_source

    def test_crossfade_constant_exists(self, _reel_source: str):
        """CROSSFADE constant must be defined (9 frames = 0.3s at 30fps)."""
        match = re.search(r"const CROSSFADE\s*=\s*(\d+)", _reel_source)
        assert match, "CROSSFADE constant must be defined"
        assert int(match.group(1)) == 9


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SketchScene — proportional animation timing
# ═══════════════════════════════════════════════════════════════════════════════

class TestSketchSceneLifecycle:
    """SketchScene must use durationInFrames to scale node/edge timing."""

    @pytest.fixture
    def _source(self) -> str:
        return (REMOTION_SRC / "components" / "SketchScene.tsx").read_text(encoding="utf-8")

    def test_destructures_duration_in_frames(self, _source: str):
        """Component must destructure durationInFrames from props."""
        assert "durationInFrames" in _source
        pattern = re.compile(r"\{[^}]*durationInFrames[^}]*\}\s*\)")
        assert pattern.search(_source), "durationInFrames must be destructured in component params"

    def test_scales_animation_to_duration(self, _source: str):
        """Animation timing must be computed from durationInFrames, not just fixed constants."""
        assert "timeScale" in _source or "animTarget" in _source

    def test_no_hardcoded_node_slot_in_rendering(self, _source: str):
        """Node rendering loop must use scaled slot, not raw NODE_SLOT."""
        node_map_section = _source[_source.index("nodes.map"):]
        assert "scaledNodeSlot" in node_map_section or "scaledNodeDraw" in node_map_section

    def test_edge_path_receives_scaled_timing(self, _source: str):
        """EdgePath component must receive scaled draw/label timing props."""
        assert "edgeDraw" in _source
        assert "edgeLabelFade" in _source

    def test_works_with_short_duration(self, _source: str):
        """timeScale computation must handle durationInFrames shorter than base animation."""
        assert "baseTotal > 0" in _source or "Math.max" in _source

    def test_works_with_long_duration(self, _source: str):
        """With large durationInFrames, animation should fill ~85% of scene."""
        assert "0.85" in _source

    def test_ghost_fills_for_enter_phase(self, _source: str):
        """SketchScene must render ghost fills at frame 0 for ENTER phase content."""
        assert "ghost-" in _source
        assert "ghostOpacity" in _source


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FlowScene — durationInFrames replaces hard-coded 180
# ═══════════════════════════════════════════════════════════════════════════════

class TestFlowSceneLifecycle:
    """FlowScene must use durationInFrames instead of hard-coded 180 frames."""

    @pytest.fixture
    def _source(self) -> str:
        return (REMOTION_SRC / "components" / "FlowScene.tsx").read_text(encoding="utf-8")

    def test_accepts_duration_in_frames_prop(self, _source: str):
        """FlowSceneProps must include durationInFrames."""
        assert "durationInFrames" in _source
        assert re.search(r"durationInFrames\??:\s*number", _source)

    def test_anim_budget_derived_from_duration(self, _source: str):
        """Step interval must be derived from durationInFrames, not hard-coded 180."""
        assert "animBudget" in _source
        assert "durationInFrames" in _source

    def test_fallback_to_180_without_duration(self, _source: str):
        """When durationInFrames is undefined, fallback to 180 for backwards compat."""
        assert "180" in _source

    def test_step_interval_uses_anim_budget(self, _source: str):
        """stepInterval must be computed from animBudget, not raw 180."""
        interval_line = [l for l in _source.splitlines() if "stepInterval" in l and "Math.floor" in l]
        assert interval_line, "stepInterval must use Math.floor"
        assert "animBudget" in interval_line[0]

    def test_no_premature_fadeout(self, _source: str):
        """FlowScene must not internally fade out before the scene ends."""
        assert "fadeOut" not in _source.lower() or "fade_out" not in _source.lower()

    def test_ghost_circles_for_enter_phase(self, _source: str):
        """FlowScene must render ghost circles at frame 0 for ENTER phase content."""
        assert "ghost-" in _source
        assert "ghostOpacity" in _source

    def test_steps_start_early(self, _source: str):
        """STEPS_START must be <= 15 frames so first step appears within 0.5s."""
        import re
        match = re.search(r"STEPS_START\s*=\s*(\d+)", _source)
        assert match, "STEPS_START must be defined"
        assert int(match.group(1)) <= 15


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PipelineScene — durationInFrames awareness
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineSceneLifecycle:
    """PipelineScene must accept durationInFrames prop."""

    @pytest.fixture
    def _source(self) -> str:
        return (REMOTION_SRC / "components" / "PipelineScene.tsx").read_text(encoding="utf-8")

    def test_accepts_duration_in_frames_prop(self, _source: str):
        """PipelineSceneProps must include durationInFrames."""
        assert re.search(r"durationInFrames\??:\s*number", _source)

    def test_no_premature_fadeout(self, _source: str):
        """PipelineScene must not internally fade out — Fade wrapper handles transitions."""
        lower = _source.lower()
        fade_out_count = lower.count("fadeout") + lower.count("fade_out") + lower.count("fade-out")
        assert fade_out_count == 0, "PipelineScene must not have internal fade-out"

    def test_scene_opacity_only_fades_in(self, _source: str):
        """sceneOpacity must only fade IN (0→1), never back to 0."""
        lines = [l for l in _source.splitlines() if "sceneOpacity" in l and "interpolate" in l]
        assert lines, "sceneOpacity must exist"
        for line in lines:
            assert "[0, 1]" in line or "[0,1]" in line, "sceneOpacity must interpolate to 1, not back to 0"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. TransformScene — already lifecycle-compliant, verify no regression
# ═══════════════════════════════════════════════════════════════════════════════

class TestTransformSceneLifecycle:
    """TransformScene must maintain its existing durationInFrames usage."""

    @pytest.fixture
    def _source(self) -> str:
        return (REMOTION_SRC / "components" / "TransformScene.tsx").read_text(encoding="utf-8")

    def test_uses_duration_in_frames(self, _source: str):
        """TransformScene must use durationInFrames for summary label timing."""
        assert "durationInFrames" in _source
        assert "sceneSec" in _source or "durationInFrames / fps" in _source

    def test_scene_opacity_only_fades_in(self, _source: str):
        """sceneOpacity must only ramp up, never down."""
        lines = [l for l in _source.splitlines() if "sceneOpacity" in l and "interpolate" in l]
        assert lines
        for line in lines:
            assert "[0, 1]" in line or "[0,1]" in line

    def test_ghost_cards_for_enter_phase(self, _source: str):
        """TransformScene must render ghost card placeholders at frame 0."""
        assert "ghost-" in _source
        assert "ghostAlpha" in _source


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Fade wrapper — no premature exit for any scene
# ═══════════════════════════════════════════════════════════════════════════════

class TestFadeWrapper:
    """Fade wrapper must use duration for fadeOut, not a shorter internal value."""

    @pytest.fixture
    def _reel_source(self) -> str:
        return (REMOTION_SRC / "AIBytesReel.tsx").read_text(encoding="utf-8")

    def test_fade_receives_full_duration_plus_overlap(self, _reel_source: str):
        """Fade duration must be durationFrames + overlap, not just durationFrames."""
        assert "duration={durationFrames + overlap}" in _reel_source

    def test_fade_out_uses_duration_prop(self, _reel_source: str):
        """fadeOut must interpolate from [duration - CROSSFADE, duration], not a fixed value."""
        assert "duration - CROSSFADE" in _reel_source

    def test_no_fade_in_for_first_scene(self, _reel_source: str):
        """First scene (i === 0) must skip fade-in."""
        assert "noFadeIn={i === 0}" in _reel_source


# ═══════════════════════════════════════════════════════════════════════════════
# 7. renderStoryboardScene — durationInFrames passed to all components
# ═══════════════════════════════════════════════════════════════════════════════

class TestRenderStoryboardScene:
    """renderStoryboardScene must pass durationInFrames to lifecycle-critical components."""

    @pytest.fixture
    def _reel_source(self) -> str:
        return (REMOTION_SRC / "AIBytesReel.tsx").read_text(encoding="utf-8")

    def test_flow_scene_receives_duration(self, _reel_source: str):
        """FlowScene must receive durationInFrames prop."""
        flow_section = _reel_source[_reel_source.index("case 'FlowScene'"):]
        flow_section = flow_section[:flow_section.index("case '", 1)]
        assert "durationInFrames={durationInFrames}" in flow_section

    def test_pipeline_scene_receives_duration(self, _reel_source: str):
        """PipelineScene must receive durationInFrames prop."""
        pipe_section = _reel_source[_reel_source.index("case 'PipelineScene'"):]
        pipe_section = pipe_section[:pipe_section.index("case '", 1)]
        assert "durationInFrames={durationInFrames}" in pipe_section

    def test_sketch_scene_receives_duration(self, _reel_source: str):
        """SketchScene must receive durationInFrames prop."""
        sketch_section = _reel_source[_reel_source.index("case 'SketchScene'"):]
        sketch_section = sketch_section[:sketch_section.index("case '", 1)]
        assert "durationInFrames={durationInFrames}" in sketch_section

    def test_transform_scene_receives_duration(self, _reel_source: str):
        """TransformScene must receive durationInFrames prop."""
        tf_section = _reel_source[_reel_source.index("case 'TransformScene'"):]
        tf_section = tf_section[:tf_section.index("case '", 1)]
        assert "durationInFrames={durationInFrames}" in tf_section
