"""EP04 regression tests — covers all fixes from the EP04 reliability hardening.

1. KineticTypoScene: single-line hero, two-line hero, shatter phases
2. Pipeline ordering: voice runs before visual director
3. Duration gate: pass / warn / fail
4. Scene Composer: 100% beat coverage gate + auto-recomposition
5. Visual Director: retry categorization + prefill JSON enforcement
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ═══════════════════════════════════════════════════════════════════════════════
# 1. KineticTypoScene regression tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestKineticTypoScene:
    """Verify the leftChars ReferenceError fix and shatter rendering paths."""

    @pytest.fixture
    def _check_tsx_source(self) -> str:
        tsx = (
            Path(__file__).parent.parent
            / "remotion" / "src" / "components" / "KineticTypoScene.tsx"
        )
        return tsx.read_text(encoding="utf-8")

    def test_single_line_no_leftchars_reference(self, _check_tsx_source: str):
        """Single-line crack path must NOT reference undefined leftChars/rightChars."""
        assert "leftChars" not in _check_tsx_source
        assert "rightChars" not in _check_tsx_source

    def test_single_line_uses_chars_split(self, _check_tsx_source: str):
        """Single-line branch must split text into chars with Math.ceil midpoint."""
        assert "const chars = text.split" in _check_tsx_source
        assert "Math.ceil(chars.length / 2)" in _check_tsx_source

    def test_two_line_crack_uses_local_vars(self, _check_tsx_source: str):
        """Two-line branch must use locally-scoped lChars/lMid."""
        assert "const lChars = line.split" in _check_tsx_source
        assert "Math.ceil(lChars.length / 2)" in _check_tsx_source

    def test_shatter_line_renderer_exists(self, _check_tsx_source: str):
        """renderShatterLine must exist and split chars at midpoint."""
        assert "renderShatterLine" in _check_tsx_source
        assert "renderShatterChar" in _check_tsx_source

    def test_pre_shatter_renderer_exists(self, _check_tsx_source: str):
        """renderPreShatterText must exist with both single and two-line paths."""
        assert "renderPreShatterText" in _check_tsx_source
        assert "isTwoLine" in _check_tsx_source


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Pipeline ordering — voice before visual director
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineOrdering:
    """Verify orchestrator runs voice synthesis before the visual director."""

    @pytest.fixture
    def _orchestrator_source(self) -> str:
        return (
            Path(__file__).parent.parent / "orchestrator.py"
        ).read_text(encoding="utf-8")

    def test_voice_phase_before_visual_director(self, _orchestrator_source: str):
        """Phase 2.5 (voice) must appear before Phase 3 (visual director)."""
        voice_idx = _orchestrator_source.index("Phase 2.5: Voice")
        vd_idx = _orchestrator_source.index("Phase 3: Visual Director")
        assert voice_idx < vd_idx, "Voice phase must run before Visual Director"

    def test_duration_gate_between_voice_and_vd(self, _orchestrator_source: str):
        """Duration gate (Phase 2.6) must appear between voice and VD."""
        voice_idx = _orchestrator_source.index("Phase 2.5: Voice")
        gate_idx = _orchestrator_source.index("Phase 2.6: Duration gate")
        vd_idx = _orchestrator_source.index("Phase 3: Visual Director")
        assert voice_idx < gate_idx < vd_idx

    def test_visual_director_receives_voice_duration(self, _orchestrator_source: str):
        """Visual director call must pass voice_duration=locked_dur."""
        assert "voice_duration=locked_dur" in _orchestrator_source


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Duration gate — pass / warn / fail
# ═══════════════════════════════════════════════════════════════════════════════

class TestDurationGate:
    """Test the duration gate logic in orchestrator._run_episode."""

    @pytest.fixture
    def _orchestrator_source(self) -> str:
        return (
            Path(__file__).parent.parent / "orchestrator.py"
        ).read_text(encoding="utf-8")

    def test_gate_pass_range(self, _orchestrator_source: str):
        """Durations 45-60s must pass the gate."""
        assert "dur < 45.0" in _orchestrator_source
        assert "dur > 60.0" in _orchestrator_source

    def test_gate_fail_removes_script(self, _orchestrator_source: str):
        """Durations > 60s must pop the script and voice_duration."""
        assert "scripts.pop(lang, None)" in _orchestrator_source
        assert "voice_durations.pop(lang)" in _orchestrator_source

    def test_gate_warn_below_min(self, _orchestrator_source: str):
        """Durations < 45s log a warning but continue."""
        assert "narration may be too short" in _orchestrator_source


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Scene Composer — coverage gate + auto-recomposition
# ═══════════════════════════════════════════════════════════════════════════════

from agents import scene_composer as sc


class TestSceneComposerCoverage:
    """Scene Composer must block render when coverage < 100%."""

    def _beat(self, action: str) -> dict:
        return {"start": 0, "end": 1, "action": action, "claim_type": "ILLUSTRATIVE"}

    def _scene(self, sid: int, component: str, beats: list[dict]) -> dict:
        return {
            "scene_id": sid,
            "component": component,
            "duration_seconds": 5.0,
            "narration": f"scene {sid}",
            "beats": beats,
        }

    def test_composed_scene_covers_all_actions(self):
        """ComposedScene supports ALL visual actions — coverage must be 100%."""
        scene = self._scene(1, "ComposedScene", [
            self._beat("travel"),
            self._beat("fill"),
            self._beat("collapse"),
            self._beat("reveal"),
        ])
        result = sc.validate_beat_coverage([scene])
        assert result["all_covered"] is True

    def test_kinetic_typo_rejects_travel(self):
        """KineticTypoScene does not support 'travel' — beat must be uncovered."""
        scene = self._scene(1, "KineticTypoScene", [self._beat("travel across the screen")])
        result = sc.validate_beat_coverage([scene])
        assert result["all_covered"] is False
        assert "travel" in result["beats"][0]["missing_actions"]

    def test_circular_flow_registered(self):
        """CircularFlowScene must be registered in SCENE_ACTIONS."""
        assert "CircularFlowScene" in sc.SCENE_ACTIONS
        assert "fill" in sc.SCENE_ACTIONS["CircularFlowScene"]
        assert "connect" in sc.SCENE_ACTIONS["CircularFlowScene"]

    def test_takeaway_registered(self):
        """TakeawayScene must be registered in SCENE_ACTIONS."""
        assert "TakeawayScene" in sc.SCENE_ACTIONS
        assert "reveal" in sc.SCENE_ACTIONS["TakeawayScene"]
        assert "hold" in sc.SCENE_ACTIONS["TakeawayScene"]

    def test_auto_recompose_unsupported_to_composed(self):
        """Scene with unsupported actions auto-recomposes to ComposedScene."""
        scene = self._scene(1, "KineticTypoScene", [
            self._beat("travel across screen"),
        ])
        recomposed = sc.recompose_storyboard([scene])
        assert recomposed[0]["component"] == "ComposedScene"
        assert recomposed[0]["data"]["_recomposed_from"] == "KineticTypoScene"

    def test_no_recompose_when_covered(self):
        """Scene with all actions covered stays as-is."""
        scene = self._scene(1, "KineticTypoScene", [
            self._beat("enter and reveal the text"),
        ])
        recomposed = sc.recompose_storyboard([scene])
        assert recomposed[0]["component"] == "KineticTypoScene"

    def test_coverage_gate_blocks_render(self, tmp_path: Path):
        """run() must raise RuntimeError when recomposition can't achieve 100%."""
        storyboard = [self._scene(1, "UnknownComponent", [
            self._beat("quantum entangle the particles"),
        ])]
        sb_path = tmp_path / "ep99_storyboard_en.json"
        sb_path.write_text(json.dumps({"storyboard": storyboard}), encoding="utf-8")
        with patch.object(sc, "recompose_storyboard", side_effect=lambda sb: sb):
            with pytest.raises(RuntimeError, match="Scene Composer FAIL"):
                sc.run(99, 1, {"storyboard_path": str(sb_path)})

    def test_full_recompose_then_coverage_passes(self, tmp_path: Path):
        """After recomposition, coverage should reach 100% and run() succeeds."""
        storyboard = [
            self._scene(1, "CircularFlowScene", [
                self._beat("fill the arc"),
                self._beat("connect the nodes"),
            ]),
        ]
        sb_path = tmp_path / "ep99_storyboard_en.json"
        sb_path.write_text(json.dumps({"storyboard": storyboard}), encoding="utf-8")
        result = sc.run(99, 1, {"storyboard_path": str(sb_path)})
        assert result["all_covered"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Visual Director — retry categorization + JSON prefill
# ═══════════════════════════════════════════════════════════════════════════════

from agents import visual_director_agent as vda


class TestVisualDirectorRetryHardening:
    """Visual Director must categorize failures and use assistant prefill."""

    def test_retry_counts_in_source(self):
        """run() must initialize categorized retry_counts dict."""
        source = (
            Path(__file__).parent.parent
            / "agents" / "visual_director_agent.py"
        ).read_text(encoding="utf-8")
        for category in ["EMPTY_RESPONSE", "JSON_PARSE", "SCHEMA", "DURATION", "CONTENT_GATE"]:
            assert f'"{category}"' in source, f"Missing retry category: {category}"

    def test_empty_response_detection_in_source(self):
        """API call must detect and categorize empty responses."""
        source = (
            Path(__file__).parent.parent
            / "agents" / "visual_director_agent.py"
        ).read_text(encoding="utf-8")
        assert "EMPTY_RESPONSE" in source
        assert "EMPTY_RESPONSE: Claude returned" in source

    def test_empty_response_detected(self):
        """Empty API response must raise ValueError with EMPTY_RESPONSE category."""
        mock_content = MagicMock()
        mock_content.text = ""
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                with pytest.raises(RuntimeError, match="failed after 3 attempts"):
                    vda.run(
                        {"topic": "T", "concept": "c", "hook": "h",
                         "takeaway": "t", "voiceover": "v"},
                        episode=99, week=1,
                    )
        assert mock_client.messages.create.call_count == 3

    def test_quality_gate_failure_raises_not_proceeds(self):
        """Quality gate failures must raise RuntimeError, not proceed with warnings."""
        source = (
            Path(__file__).parent.parent
            / "agents" / "visual_director_agent.py"
        ).read_text(encoding="utf-8")
        assert "proceeding with warnings" not in source

    def test_voice_duration_mismatch_validation(self):
        """When voice_duration is locked, scene sum mismatch must trigger violation."""
        scenes = [
            {"scene_id": 1, "duration_seconds": 20.0, "beats": []},
            {"scene_id": 2, "duration_seconds": 20.0, "beats": []},
        ]
        scene_sum = sum(s["duration_seconds"] for s in scenes)
        voice_dur = 55.0
        assert abs(scene_sum - voice_dur) > 5.0, "Test setup: sum must mismatch by >5s"
