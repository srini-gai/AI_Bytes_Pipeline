"""Tests for the orchestrator publisher gate — publish requires explicit --publish flag."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """Set up minimal env so orchestrator can import without crashing."""
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path / "output"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "test")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID_EN", "test")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test-token")
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID", "test")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID_EN", "test")
    monkeypatch.setenv("START_PUBLISH_DATE", "2026-01-01")


def _fake_run_episode_result(episode: int = 1) -> dict:
    return {
        "episode": episode,
        "topic": "Test Topic",
        "langs": {"en": {"final_path": "/tmp/test.mp4"}},
        "errors": [],
    }


class TestPublisherGateDefault:
    """Default (no --publish flag) must never invoke publisher_agent."""

    def test_default_publish_is_false(self):
        """argparse default for --publish is False."""
        import argparse
        # Re-create the parser as orchestrator does
        parser = argparse.ArgumentParser()
        parser.add_argument("--publish", action="store_true", default=False)
        args = parser.parse_args([])
        assert args.publish is False

    def test_run_episode_skips_publisher_when_publish_false(self):
        """_run_episode with publish=False must not call publisher_agent.run."""
        from orchestrator import _run_episode

        with patch("orchestrator.script_agent") as mock_script, \
             patch("orchestrator.voice_agent") as mock_voice, \
             patch("orchestrator.visual_director_agent") as mock_vd, \
             patch("orchestrator.visual_mode_router") as mock_router, \
             patch("orchestrator.visual_agent") as mock_visual, \
             patch("orchestrator.assembly_agent") as mock_assembly, \
             patch("orchestrator.publisher_agent") as mock_publisher:

            mock_script.run.return_value = {
                "script": {"voiceover": "test", "hook": "hook"},
                "output_path": "/tmp/script.json",
            }
            mock_voice.run.return_value = {
                "output_path": "/tmp/voice.mp3",
                "duration": 55.0,
            }
            mock_vd.run.return_value = {
                "storyboard": [{"scene_id": 1, "duration_seconds": 55}],
                "output_path": "/tmp/sb.json",
                "total_duration": 55.0,
            }
            mock_router.route_storyboard.return_value = {
                "episode_mode": "NATIVE",
                "native_beats": 1,
                "generated_beats": 0,
                "routing_issues": [],
            }
            mock_router.has_planner_declared_modes.return_value = True
            mock_visual.run.return_value = {
                "success": True,
                "output_path": "/tmp/visuals.mp4",
                "duration": 55.0,
                "storyboard_planned_duration": 55.0,
                "skipped": False,
                "size_mb": 5.0,
            }
            mock_assembly.run.return_value = {
                "success": True,
                "output_path": "/tmp/final.mp4",
                "duration": 55.0,
            }

            result = _run_episode(
                episode=1, week=1, topic="Test", langs=["en"],
                dry_run=False, publish=False,
            )

            mock_publisher.run.assert_not_called()

    def test_run_episode_calls_publisher_when_publish_true(self):
        """_run_episode with publish=True must call publisher_agent.run."""
        from orchestrator import _run_episode

        with patch("orchestrator.script_agent") as mock_script, \
             patch("orchestrator.voice_agent") as mock_voice, \
             patch("orchestrator.visual_director_agent") as mock_vd, \
             patch("orchestrator.visual_mode_router") as mock_router, \
             patch("orchestrator.visual_agent") as mock_visual, \
             patch("orchestrator.assembly_agent") as mock_assembly, \
             patch("orchestrator.publisher_agent") as mock_publisher:

            mock_script.run.return_value = {
                "script": {"voiceover": "test", "hook": "hook"},
                "output_path": "/tmp/script.json",
            }
            mock_voice.run.return_value = {
                "output_path": "/tmp/voice.mp3",
                "duration": 55.0,
            }
            mock_vd.run.return_value = {
                "storyboard": [{"scene_id": 1, "duration_seconds": 55}],
                "output_path": "/tmp/sb.json",
                "total_duration": 55.0,
            }
            mock_router.route_storyboard.return_value = {
                "episode_mode": "NATIVE",
                "native_beats": 1,
                "generated_beats": 0,
                "routing_issues": [],
            }
            mock_router.has_planner_declared_modes.return_value = True
            mock_visual.run.return_value = {
                "success": True,
                "output_path": "/tmp/visuals.mp4",
                "duration": 55.0,
                "storyboard_planned_duration": 55.0,
                "skipped": False,
                "size_mb": 5.0,
            }
            mock_assembly.run.return_value = {
                "success": True,
                "output_path": "/tmp/final.mp4",
                "duration": 55.0,
            }
            mock_publisher.run.return_value = {
                "video_url": "https://youtube.com/watch?v=test",
                "video_id": "test",
            }

            result = _run_episode(
                episode=1, week=1, topic="Test", langs=["en"],
                dry_run=False, publish=True,
            )

            mock_publisher.run.assert_called_once()


class TestPublisherGateDryRun:
    """Dry run must never invoke publisher_agent."""

    def test_dry_run_skips_publisher(self):
        """dry_run=True skips everything after voice — publisher never called."""
        from orchestrator import _run_episode

        with patch("orchestrator.script_agent") as mock_script, \
             patch("orchestrator.voice_agent") as mock_voice, \
             patch("orchestrator.visual_director_agent") as mock_vd, \
             patch("orchestrator.visual_mode_router") as mock_router, \
             patch("orchestrator.publisher_agent") as mock_publisher:

            mock_script.run.return_value = {
                "script": {"voiceover": "test", "hook": "hook"},
                "output_path": "/tmp/script.json",
            }
            mock_voice.run.return_value = {
                "output_path": "/tmp/voice.mp3",
                "duration": 55.0,
            }
            mock_vd.run.return_value = {
                "storyboard": [{"scene_id": 1, "duration_seconds": 55}],
                "output_path": "/tmp/sb.json",
                "total_duration": 55.0,
            }
            mock_router.route_storyboard.return_value = {
                "episode_mode": "NATIVE",
                "native_beats": 1,
                "generated_beats": 0,
                "routing_issues": [],
            }
            mock_router.has_planner_declared_modes.return_value = True

            result = _run_episode(
                episode=1, week=1, topic="Test", langs=["en"],
                dry_run=True, publish=True,
            )

            mock_publisher.run.assert_not_called()


class TestPublisherGateCLI:
    """CLI argument parsing for --publish flag."""

    def test_no_flag_defaults_false(self):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--publish", action="store_true", default=False)
        args = parser.parse_args([])
        assert args.publish is False

    def test_flag_sets_true(self):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--publish", action="store_true", default=False)
        args = parser.parse_args(["--publish"])
        assert args.publish is True

    def test_missing_flag_with_other_args(self):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--publish", action="store_true", default=False)
        parser.add_argument("--episode", type=int)
        args = parser.parse_args(["--episode", "6"])
        assert args.publish is False
