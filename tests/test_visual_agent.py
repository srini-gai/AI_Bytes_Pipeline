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


def test_clip_queries_all_contain_no_people():
    queries = visual_agent._clip_queries(SAMPLE_SCRIPT)
    for key, q in queries.items():
        assert "no people" in q, f"Query for '{key}' missing 'no people': {q}"


def test_clip_queries_all_contain_abstract():
    queries = visual_agent._clip_queries(SAMPLE_SCRIPT)
    for key, q in queries.items():
        assert "abstract" in q, f"Query for '{key}' missing 'abstract': {q}"


def test_clip_queries_concept_contains_neural_network():
    queries = visual_agent._clip_queries(SAMPLE_SCRIPT)
    assert "neural network" in queries["concept"]


def test_clip_queries_slide1_contains_data_flow():
    queries = visual_agent._clip_queries(SAMPLE_SCRIPT)
    assert "data flow" in queries["slide_1"]


def test_clip_queries_slide2_contains_network():
    queries = visual_agent._clip_queries(SAMPLE_SCRIPT)
    assert "network" in queries["slide_2"]


def test_clip_queries_slide3_contains_future():
    queries = visual_agent._clip_queries(SAMPLE_SCRIPT)
    assert "future" in queries["slide_3"]


def test_clip_queries_cta_contains_particles():
    queries = visual_agent._clip_queries(SAMPLE_SCRIPT)
    assert "particles" in queries["cta"]


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


def test_build_props_passes_diagram_spec():
    spec = {"type": "hub_spoke", "hub": "LLM", "spokes": ["Tool A", "Tool B", "Tool C"]}
    script = {**SAMPLE_SCRIPT, "diagram_spec": spec}
    props = visual_agent._build_props(script)
    assert props["diagram_spec"] == spec


def test_build_props_omits_diagram_spec_when_absent():
    props = visual_agent._build_props(SAMPLE_SCRIPT)
    assert "diagram_spec" not in props


def test_build_props_passes_sketch_spec():
    sketch_spec = {"nodes": [{"id": "a", "label": "A", "x": 0, "y": 0, "shape": "rect"}], "edges": []}
    script = {**SAMPLE_SCRIPT, "diagram_spec": {"type": "sketch"}, "sketch_spec": sketch_spec}
    props = visual_agent._build_props(script)
    assert props["sketch_spec"] == sketch_spec


def test_build_props_omits_sketch_spec_when_absent():
    props = visual_agent._build_props(SAMPLE_SCRIPT)
    assert "sketch_spec" not in props


def test_build_props_passes_data_spec():
    data_spec = {"type": "counter", "title": "Training Data", "counterValue": 45, "counterLabel": "TB of text"}
    script = {**SAMPLE_SCRIPT, "diagram_spec": {"type": "data"}, "data_spec": data_spec}
    props = visual_agent._build_props(script)
    assert props["data_spec"] == data_spec


def test_build_props_omits_data_spec_when_absent():
    props = visual_agent._build_props(SAMPLE_SCRIPT)
    assert "data_spec" not in props


def test_build_props_passes_token_spec():
    token_spec = {
        "sentence": "Hello world how are you",
        "tokens": [{"text": "Hello"}, {"text": "world"}, {"text": "how"}, {"text": "are"}, {"text": "you"}],
    }
    script = {**SAMPLE_SCRIPT, "diagram_spec": {"type": "token"}, "token_spec": token_spec}
    props = visual_agent._build_props(script)
    assert props["token_spec"] == token_spec


def test_build_props_omits_token_spec_when_absent():
    props = visual_agent._build_props(SAMPLE_SCRIPT)
    assert "token_spec" not in props


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


def _fake_scale_to_portrait(src: Path, dst: Path) -> None:
    """Stand-in for ffmpeg during tests — just copies bytes through."""
    dst.write_bytes(src.read_bytes())


@patch("urllib.request.urlopen")
@patch("agents.visual_agent._scale_to_portrait", side_effect=_fake_scale_to_portrait)
def test_fetch_pexels_clip_downloads_and_caches(mock_scale, mock_urlopen, tmp_path):
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
    mock_scale.assert_called_once()

    # scale ran against the raw download, writing the portrait-cropped result to `cached`
    scale_src, scale_dst = mock_scale.call_args[0]
    assert scale_dst == tmp_path / "hook.mp4"
    assert scale_src != scale_dst

    # the intermediate pre-scale download must not be left behind
    assert not scale_src.exists()


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
@patch("agents.visual_agent._scale_to_portrait", side_effect=_fake_scale_to_portrait)
def test_fetch_pexels_clip_picks_highest_resolution(mock_scale, mock_urlopen, tmp_path):
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


@patch("urllib.request.urlopen")
@patch("agents.visual_agent._scale_to_portrait", side_effect=_fake_scale_to_portrait)
def test_fetch_pexels_clip_includes_portrait_orientation(mock_scale, mock_urlopen, tmp_path):
    search_resp = MagicMock()
    search_resp.read.return_value = _make_pexels_response()
    search_resp.__enter__ = lambda s: s
    search_resp.__exit__ = MagicMock(return_value=False)

    dl_resp = MagicMock()
    dl_resp.read.return_value = b"0" * 100_000
    dl_resp.__enter__ = lambda s: s
    dl_resp.__exit__ = MagicMock(return_value=False)

    mock_urlopen.side_effect = [search_resp, dl_resp]

    visual_agent.fetch_pexels_clip("abstract tech", 8, "key", tmp_path, "hook.mp4")

    search_call = mock_urlopen.call_args_list[0][0][0]
    search_url = search_call.full_url if hasattr(search_call, "full_url") else str(search_call)
    assert "orientation=portrait" in search_url


@patch("urllib.request.urlopen")
@patch("agents.visual_agent._scale_to_portrait", side_effect=_fake_scale_to_portrait)
def test_fetch_pexels_clip_skips_human_clips(mock_scale, mock_urlopen, tmp_path):
    """First result has human URL; second is clean — should download the clean one."""
    resp = MagicMock()
    resp.read.return_value = json.dumps({
        "videos": [
            {
                "id": 1,
                "url": "https://www.pexels.com/video/business-team-meeting-1234/",
                "video_files": [{"link": "https://cdn.pexels.com/human.mp4", "width": 1920, "height": 1080}],
            },
            {
                "id": 2,
                "url": "https://www.pexels.com/video/abstract-technology-5678/",
                "video_files": [{"link": "https://cdn.pexels.com/clean.mp4", "width": 1920, "height": 1080}],
            },
        ]
    }).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)

    dl_resp = MagicMock()
    dl_resp.read.return_value = b"0" * 100_000
    dl_resp.__enter__ = lambda s: s
    dl_resp.__exit__ = MagicMock(return_value=False)

    mock_urlopen.side_effect = [resp, dl_resp]
    visual_agent.fetch_pexels_clip("abstract technology", 8, "key", tmp_path, "hook.mp4")

    download_call = mock_urlopen.call_args_list[1][0][0]
    dl_url = download_call.full_url if hasattr(download_call, "full_url") else str(download_call)
    assert "clean.mp4" in dl_url
    assert "human.mp4" not in dl_url


@patch("urllib.request.urlopen")
@patch("agents.visual_agent._scale_to_portrait", side_effect=_fake_scale_to_portrait)
def test_fetch_pexels_clip_falls_back_if_all_human(mock_scale, mock_urlopen, tmp_path):
    """If every result is human-flagged, falls back to first result rather than failing."""
    resp = MagicMock()
    resp.read.return_value = json.dumps({
        "videos": [
            {
                "id": 1,
                "url": "https://www.pexels.com/video/business-people-1234/",
                "video_files": [{"link": "https://cdn.pexels.com/human1.mp4", "width": 1920, "height": 1080}],
            },
        ]
    }).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)

    dl_resp = MagicMock()
    dl_resp.read.return_value = b"0" * 100_000
    dl_resp.__enter__ = lambda s: s
    dl_resp.__exit__ = MagicMock(return_value=False)

    mock_urlopen.side_effect = [resp, dl_resp]
    visual_agent.fetch_pexels_clip("abstract technology", 8, "key", tmp_path, "hook.mp4")

    download_call = mock_urlopen.call_args_list[1][0][0]
    dl_url = download_call.full_url if hasattr(download_call, "full_url") else str(download_call)
    assert "human1.mp4" in dl_url


# ── _scale_to_portrait ────────────────────────────────────────────────────────

def test_portrait_scale_filter_crops_to_fill():
    assert visual_agent.PORTRAIT_SCALE_FILTER == (
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    )


@patch("agents.visual_agent.subprocess.run")
def test_scale_to_portrait_invokes_ffmpeg_with_filter(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    src = tmp_path / "raw.mp4"
    dst = tmp_path / "out.mp4"

    visual_agent._scale_to_portrait(src, dst)

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == visual_agent.FFMPEG
    assert "-vf" in cmd
    assert cmd[cmd.index("-vf") + 1] == visual_agent.PORTRAIT_SCALE_FILTER
    assert str(src) in cmd
    assert str(dst) in cmd


@patch("agents.visual_agent.subprocess.run")
def test_scale_to_portrait_raises_on_ffmpeg_failure(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=1, stderr="Invalid data found")
    with pytest.raises(RuntimeError, match="ffmpeg portrait scale failed"):
        visual_agent._scale_to_portrait(tmp_path / "raw.mp4", tmp_path / "out.mp4")


@patch("agents.visual_agent.subprocess.run", side_effect=visual_agent.subprocess.TimeoutExpired(cmd="ffmpeg", timeout=120))
def test_scale_to_portrait_raises_on_timeout(mock_run, tmp_path):
    with pytest.raises(RuntimeError, match="timed out"):
        visual_agent._scale_to_portrait(tmp_path / "raw.mp4", tmp_path / "out.mp4")


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


# ── _collect_disk_clips ───────────────────────────────────────────────────────

def test_collect_disk_clips_returns_existing_clips(tmp_path):
    clips_dir = tmp_path / "clips"
    clips_dir.mkdir()
    (clips_dir / "concept.mp4").write_bytes(b"0" * 100_000)
    (clips_dir / "hook.mp4").write_bytes(b"0" * 100_000)

    result = visual_agent._collect_disk_clips(clips_dir, ["hook", "concept", "cta"])
    assert set(result.keys()) == {"hook", "concept"}


def test_collect_disk_clips_ignores_small_files(tmp_path):
    clips_dir = tmp_path / "clips"
    clips_dir.mkdir()
    (clips_dir / "concept.mp4").write_bytes(b"x" * 1_000)  # too small

    result = visual_agent._collect_disk_clips(clips_dir, ["concept"])
    assert result == {}


def test_collect_disk_clips_returns_empty_when_dir_missing(tmp_path):
    clips_dir = tmp_path / "clips"  # does not exist
    result = visual_agent._collect_disk_clips(clips_dir, ["hook", "concept"])
    assert result == {}


def test_collect_disk_clips_returns_empty_when_no_clips(tmp_path):
    clips_dir = tmp_path / "clips"
    clips_dir.mkdir()
    result = visual_agent._collect_disk_clips(clips_dir, ["hook", "concept"])
    assert result == {}


# ── run() disk-reuse behavior ─────────────────────────────────────────────────

@patch("agents.visual_agent._render")
@patch("agents.visual_agent._validate_output", return_value=60.0)
@patch("agents.visual_agent._stage_clips_to_public")
def test_run_ta_reuses_cached_clips_without_pexels_key(
    mock_stage, mock_validate, mock_render, tmp_path, monkeypatch
):
    """TA render must stage cached EN clips even when PEXELS_API_KEY is not set."""
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)

    ep_dir = tmp_path / "week_01" / "ep01"
    clips_dir = ep_dir / "clips"
    clips_dir.mkdir(parents=True)
    for scene in ("hook", "concept", "slide_0", "slide_1", "slide_2", "slide_3", "cta"):
        (clips_dir / f"{scene}.mp4").write_bytes(b"0" * 100_000)

    mock_stage.return_value = {"hook": "clips/hook.mp4", "concept": "clips/concept.mp4"}
    mock_render.side_effect = lambda out, props, ep: out.write_bytes(b"0" * 200_000)

    visual_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="ta")

    mock_stage.assert_called_once()
    staged_arg = mock_stage.call_args[0][0]
    assert "concept" in staged_arg


@patch("agents.visual_agent.fetch_pexels_clip")
@patch("agents.visual_agent._render")
@patch("agents.visual_agent._validate_output", return_value=60.0)
@patch("agents.visual_agent._stage_clips_to_public")
def test_run_ta_skips_pexels_when_all_clips_cached(
    mock_stage, mock_validate, mock_render, mock_fetch, tmp_path, monkeypatch
):
    """When all clips are on disk, Pexels must not be called even if key is set."""
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("PEXELS_API_KEY", "test-pexels-key")

    ep_dir = tmp_path / "week_01" / "ep01"
    clips_dir = ep_dir / "clips"
    clips_dir.mkdir(parents=True)
    for scene in ("hook", "concept", "slide_0", "slide_1", "slide_2", "slide_3", "cta"):
        (clips_dir / f"{scene}.mp4").write_bytes(b"0" * 100_000)

    mock_stage.return_value = {s: f"clips/{s}.mp4" for s in
                               ("hook", "concept", "slide_0", "slide_1", "slide_2", "slide_3", "cta")}
    mock_render.side_effect = lambda out, props, ep: out.write_bytes(b"0" * 200_000)

    visual_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="ta")

    mock_fetch.assert_not_called()


@patch("agents.visual_agent.fetch_pexels_clip")
@patch("agents.visual_agent._render")
@patch("agents.visual_agent._validate_output", return_value=60.0)
@patch("agents.visual_agent._stage_clips_to_public")
def test_run_downloads_only_missing_clips(
    mock_stage, mock_validate, mock_render, mock_fetch, tmp_path, monkeypatch
):
    """Only scenes absent from disk should trigger a Pexels download."""
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("PEXELS_API_KEY", "test-pexels-key")

    ep_dir = tmp_path / "week_01" / "ep01"
    clips_dir = ep_dir / "clips"
    clips_dir.mkdir(parents=True)
    # Pre-populate only concept and hook — the other 5 must be downloaded
    for scene in ("concept", "hook"):
        (clips_dir / f"{scene}.mp4").write_bytes(b"0" * 100_000)

    def fake_fetch(query, min_dur, key, clips_dir, filename):
        p = clips_dir / filename
        p.write_bytes(b"0" * 100_000)
        return p

    mock_fetch.side_effect = fake_fetch
    mock_render.side_effect = lambda out, props, ep: out.write_bytes(b"0" * 200_000)
    mock_stage.return_value = {}

    visual_agent.run(SAMPLE_SCRIPT, episode=1, week=1, lang="en")

    fetched_scenes = {call_args[0][4].replace(".mp4", "") for call_args in mock_fetch.call_args_list}
    assert "concept" not in fetched_scenes
    assert "hook" not in fetched_scenes
    assert fetched_scenes == {"slide_0", "slide_1", "slide_2", "slide_3", "cta"}


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
