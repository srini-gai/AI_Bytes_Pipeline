"""Tests for visual_agent — Pexels HTTP calls and file-system helpers are mocked."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from io import BytesIO

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents import visual_agent


# ── _clip_queries ─────────────────────────────────────────────────────────────

SAMPLE_SCRIPT = {
    "topic": "RAG",
    "slides": [
        {"icon": "🧠", "heading": "The Problem", "body": "LLMs hallucinate."},
        {"icon": "📚", "heading": "The Fix", "body": "RAG fetches real docs."},
        {"icon": "⚡", "heading": "How It Works", "body": "Retrieve, inject, answer."},
        {"icon": "🎯", "heading": "Use Cases", "body": "Support bots, doc Q&A."},
    ],
    "theme": {
        "name": "danger",
        "accent": "#ff3333",
        "accent2": "#ff6600",
        "overlay": "rgba(20,0,0,0.45)",
        "pexels_mood": "dark technology dramatic",
    },
}


def test_clip_queries_returns_7_keys():
    queries = visual_agent._clip_queries(SAMPLE_SCRIPT)
    assert set(queries.keys()) == {"hook", "concept", "slide_0", "slide_1", "slide_2", "slide_3", "cta"}


def test_clip_queries_hook_contains_topic():
    queries = visual_agent._clip_queries(SAMPLE_SCRIPT)
    assert "RAG" in queries["hook"]
    assert "technology" in queries["hook"]


def test_clip_queries_concept_fixed():
    queries = visual_agent._clip_queries(SAMPLE_SCRIPT)
    assert "artificial intelligence" in queries["concept"]


def test_clip_queries_slides_contain_heading_words():
    queries = visual_agent._clip_queries(SAMPLE_SCRIPT)
    assert "Problem" in queries["slide_0"]
    assert "Fix" in queries["slide_1"]


def test_clip_queries_strips_emojis():
    script = {**SAMPLE_SCRIPT, "topic": "RAG 🤖"}
    queries = visual_agent._clip_queries(script)
    assert "🤖" not in queries["hook"]


# ── _build_props ──────────────────────────────────────────────────────────────

def test_build_props_no_clips():
    props = visual_agent._build_props(SAMPLE_SCRIPT)
    assert "clips" not in props
    assert props["topic"] == "RAG"
    assert len(props["slides"]) == 4


def test_build_props_with_clips():
    clips = {"hook": "clips/hook.mp4", "concept": "clips/concept.mp4"}
    props = visual_agent._build_props(SAMPLE_SCRIPT, clips=clips)
    assert props["clips"] == clips


def test_build_props_empty_clips_dict_omitted():
    props = visual_agent._build_props(SAMPLE_SCRIPT, clips={})
    assert "clips" not in props


# ── fetch_pexels_clip ─────────────────────────────────────────────────────────

def _make_pexels_response(width: int = 1920, height: int = 1080) -> bytes:
    return json.dumps({
        "videos": [
            {
                "id": 1,
                "video_files": [
                    {"link": "https://cdn.pexels.com/clip.mp4", "width": width, "height": height, "quality": "hd"},
                    {"link": "https://cdn.pexels.com/clip_sd.mp4", "width": 640, "height": 360, "quality": "sd"},
                ],
            }
        ]
    }).encode()


@patch("urllib.request.urlopen")
def test_fetch_pexels_clip_downloads_and_caches(mock_urlopen, tmp_path):
    search_resp = MagicMock()
    search_resp.read.return_value = _make_pexels_response()
    search_resp.__enter__ = lambda s: s
    search_resp.__exit__ = MagicMock(return_value=False)

    dl_resp = MagicMock()
    dl_resp.read.return_value = b"0" * 100_000  # 100 KB fake clip
    dl_resp.__enter__ = lambda s: s
    dl_resp.__exit__ = MagicMock(return_value=False)

    mock_urlopen.side_effect = [search_resp, dl_resp]

    path = visual_agent.fetch_pexels_clip(
        query="test query",
        min_duration=8,
        api_key="test-key",
        clips_dir=tmp_path,
        filename="hook.mp4",
    )

    assert path == tmp_path / "hook.mp4"
    assert path.exists()
    assert path.stat().st_size == 100_000


@patch("urllib.request.urlopen")
def test_fetch_pexels_clip_uses_cache(mock_urlopen, tmp_path):
    # Pre-write a cached file
    cached = tmp_path / "hook.mp4"
    cached.write_bytes(b"0" * 100_000)

    path = visual_agent.fetch_pexels_clip(
        query="test query",
        min_duration=8,
        api_key="test-key",
        clips_dir=tmp_path,
        filename="hook.mp4",
    )

    assert path == cached
    mock_urlopen.assert_not_called()


@patch("urllib.request.urlopen")
def test_fetch_pexels_clip_picks_highest_resolution(mock_urlopen, tmp_path):
    """Best file should be the one with largest width*height."""
    search_resp = MagicMock()
    search_resp.read.return_value = json.dumps({
        "videos": [
            {
                "id": 1,
                "video_files": [
                    {"link": "https://cdn.pexels.com/sd.mp4", "width": 640, "height": 360},
                    {"link": "https://cdn.pexels.com/hd.mp4", "width": 1920, "height": 1080},
                    {"link": "https://cdn.pexels.com/4k.mp4", "width": 3840, "height": 2160},
                ],
            }
        ]
    }).encode()
    search_resp.__enter__ = lambda s: s
    search_resp.__exit__ = MagicMock(return_value=False)

    dl_resp = MagicMock()
    dl_resp.read.return_value = b"0" * 100_000
    dl_resp.__enter__ = lambda s: s
    dl_resp.__exit__ = MagicMock(return_value=False)

    mock_urlopen.side_effect = [search_resp, dl_resp]

    visual_agent.fetch_pexels_clip("q", 8, "key", tmp_path, "hook.mp4")

    # Second call (download) should be for the 4K URL
    download_call = mock_urlopen.call_args_list[1][0][0]
    download_url = download_call.full_url if hasattr(download_call, "full_url") else str(download_call)
    assert "4k.mp4" in download_url


@patch("urllib.request.urlopen")
def test_fetch_pexels_clip_raises_on_no_results(mock_urlopen, tmp_path):
    resp = MagicMock()
    resp.read.return_value = json.dumps({"videos": []}).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = resp

    with pytest.raises(RuntimeError, match="No Pexels results"):
        visual_agent.fetch_pexels_clip("nothing found", 8, "key", tmp_path, "hook.mp4")


# ── _stage_clips_to_public ────────────────────────────────────────────────────

def test_stage_clips_to_public_copies_files(tmp_path):
    src_dir = tmp_path / "clips"
    src_dir.mkdir()
    (src_dir / "hook.mp4").write_bytes(b"fakevideo")

    public_dir = tmp_path / "public" / "clips"
    staged = visual_agent._stage_clips_to_public(
        {"hook": str(src_dir / "hook.mp4")}, public_dir
    )

    assert staged == {"hook": "clips/hook.mp4"}
    assert (public_dir / "hook.mp4").exists()
    assert (public_dir / "hook.mp4").read_bytes() == b"fakevideo"


def test_stage_clips_creates_directory(tmp_path):
    src_dir = tmp_path / "clips"
    src_dir.mkdir()
    (src_dir / "cta.mp4").write_bytes(b"x" * 1000)

    public_dir = tmp_path / "nonexistent" / "clips"
    visual_agent._stage_clips_to_public({"cta": str(src_dir / "cta.mp4")}, public_dir)
    assert public_dir.exists()


# ── _fetch_all_clips ──────────────────────────────────────────────────────────

@patch("agents.visual_agent.fetch_pexels_clip")
def test_fetch_all_clips_returns_all_scenes(mock_fetch, tmp_path):
    mock_fetch.side_effect = lambda query, min_dur, key, clips_dir, filename: (
        clips_dir / filename
    )
    (tmp_path / "clips").mkdir()

    clips = visual_agent._fetch_all_clips(SAMPLE_SCRIPT, tmp_path, "test-key")
    assert set(clips.keys()) == {"hook", "concept", "slide_0", "slide_1", "slide_2", "slide_3", "cta"}


@patch("agents.visual_agent.fetch_pexels_clip")
def test_fetch_all_clips_skips_failed_scenes(mock_fetch, tmp_path):
    def side_effect(query, min_dur, key, clips_dir, filename):
        if "hook" in filename:
            raise RuntimeError("network error")
        return clips_dir / filename

    mock_fetch.side_effect = side_effect
    clips = visual_agent._fetch_all_clips(SAMPLE_SCRIPT, tmp_path, "test-key")

    assert "hook" not in clips
    assert "concept" in clips
