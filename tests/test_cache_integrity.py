"""Cache-integrity tests: stale voice / visual / final outputs are never reused.

All external services (ElevenLabs, Remotion, ffmpeg, Whisper) are mocked —
no API calls are made.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents import assembly_agent, voice_agent, visual_agent
from agents.cache_identity import text_hash

EP, WK = 2, 1
NARRATION = "You ask, it answers. Agents complete."
OLD_NARRATION = "This is how prompt engineering works."


@pytest.fixture
def ep_dir(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "dummy")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID_EN", "dummy-voice")
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    d = tmp_path / "week_01" / "ep02"
    d.mkdir(parents=True)
    return d


def _stale_files(d: Path, stem: str) -> list[Path]:
    return sorted(d.glob(f"{stem}.stale_*"))


# ── Voice cache ──────────────────────────────────────────────────────────────

def _mock_tts(mock_cls: MagicMock) -> MagicMock:
    client = MagicMock()
    client.text_to_speech.convert.return_value = [b"NEW-AUDIO"]
    mock_cls.return_value = client
    return client


@patch.object(voice_agent, "_validate_duration", return_value=45.0)
@patch.object(voice_agent, "ElevenLabs")
def test_voice_mp3_without_hash_is_stale_and_regenerated(mock_cls, _dur, ep_dir):
    client = _mock_tts(mock_cls)
    mp3 = ep_dir / "ep02_voice_EN.mp3"
    mp3.write_bytes(b"OLD-PROMPT-ENGINEERING-AUDIO")

    out = voice_agent.run({"voiceover": NARRATION}, EP, WK, lang="en")

    client.text_to_speech.convert.assert_called_once()
    assert mp3.read_bytes() == b"NEW-AUDIO"
    assert (ep_dir / "ep02_voice_hash_EN.txt").read_text(encoding="utf-8") == text_hash(NARRATION)
    stale = _stale_files(ep_dir, "ep02_voice_EN")
    assert len(stale) == 1 and stale[0].read_bytes() == b"OLD-PROMPT-ENGINEERING-AUDIO"
    assert out["voice_source_hash"] == text_hash(NARRATION)


@patch.object(voice_agent, "_validate_duration", return_value=45.0)
@patch.object(voice_agent, "ElevenLabs")
def test_voice_mp3_with_mismatched_hash_is_stale_and_regenerated(mock_cls, _dur, ep_dir):
    client = _mock_tts(mock_cls)
    (ep_dir / "ep02_voice_EN.mp3").write_bytes(b"OLD")
    (ep_dir / "ep02_voice_hash_EN.txt").write_text(text_hash(OLD_NARRATION), encoding="utf-8")

    voice_agent.run({"voiceover": NARRATION}, EP, WK, lang="en")

    client.text_to_speech.convert.assert_called_once()
    assert (ep_dir / "ep02_voice_hash_EN.txt").read_text(encoding="utf-8") == text_hash(NARRATION)
    assert len(_stale_files(ep_dir, "ep02_voice_EN")) == 1
    assert len(_stale_files(ep_dir, "ep02_voice_hash_EN")) == 1


@patch.object(voice_agent, "_validate_duration", return_value=45.0)
@patch.object(voice_agent, "ElevenLabs")
def test_voice_cache_reused_only_on_matching_hash(mock_cls, _dur, ep_dir):
    client = _mock_tts(mock_cls)
    mp3 = ep_dir / "ep02_voice_EN.mp3"
    mp3.write_bytes(b"MATCHING-AUDIO")
    (ep_dir / "ep02_voice_hash_EN.txt").write_text(text_hash(NARRATION), encoding="utf-8")

    out = voice_agent.run({"voiceover": NARRATION}, EP, WK, lang="en")

    client.text_to_speech.convert.assert_not_called()
    assert out["skipped"] is True
    assert mp3.read_bytes() == b"MATCHING-AUDIO"
    assert not _stale_files(ep_dir, "ep02_voice_EN")


@patch.object(voice_agent, "_validate_duration", side_effect=ValueError("too short"))
@patch.object(voice_agent, "ElevenLabs")
def test_voice_hash_not_written_when_generated_audio_fails_validation(mock_cls, _dur, ep_dir):
    _mock_tts(mock_cls)
    with pytest.raises(RuntimeError):
        voice_agent.run({"voiceover": NARRATION}, EP, WK, lang="en")
    assert not (ep_dir / "ep02_voice_hash_EN.txt").exists()


# ── Visual cache ─────────────────────────────────────────────────────────────

SCRIPT = {"episode": "02", "topic": "AI Agents vs Chatbots", "voiceover": NARRATION, "slides": []}


def _write_storyboard(d: Path, narration: str = NARRATION) -> None:
    (d / "ep02_storyboard_EN.json").write_text(json.dumps({
        "art_direction": {"id": "bright-workspace"},
        "storyboard": [{"scene_id": 1, "component": "KineticTypoScene", "duration_seconds": 45.0,
                        "narration": narration, "on_screen_text": ["X"], "objects": []}],
    }), encoding="utf-8")


@pytest.fixture
def render_mocks():
    with patch.object(visual_agent, "_render") as render, \
         patch.object(visual_agent, "_validate_output", return_value=45.0), \
         patch.object(visual_agent, "_generate_video_scenes", return_value=({}, None)):
        render.side_effect = lambda out, props, ep: out.write_bytes(b"0" * 200_000)
        yield render


def test_visual_without_metadata_is_stale_and_rerendered(ep_dir, render_mocks):
    _write_storyboard(ep_dir)
    mp4 = ep_dir / "ep02_visuals.mp4"
    mp4.write_bytes(b"OLD" * 100_000)

    out = visual_agent.run(SCRIPT, EP, WK, lang="en")

    render_mocks.assert_called_once()
    assert out["skipped"] is False
    assert len(_stale_files(ep_dir, "ep02_visuals")) == 1
    meta = json.loads((ep_dir / "ep02_visuals.meta.json").read_text(encoding="utf-8"))
    assert meta["visual_identity"] == out["visual_identity"]
    assert meta["art_direction"] == "bright-workspace"
    props = json.loads((ep_dir / "ep02_render_props.json").read_text(encoding="utf-8"))
    assert props["voiceover"] == NARRATION and props["art_direction"] == "bright-workspace"


def test_visual_cache_reused_only_on_matching_identity(ep_dir, render_mocks):
    _write_storyboard(ep_dir)
    visual_agent.run(SCRIPT, EP, WK, lang="en")
    render_mocks.reset_mock()

    out = visual_agent.run(SCRIPT, EP, WK, lang="en")

    render_mocks.assert_not_called()
    assert out["skipped"] is True


def test_visual_rerendered_when_storyboard_changes(ep_dir, render_mocks):
    _write_storyboard(ep_dir)
    first = visual_agent.run(SCRIPT, EP, WK, lang="en")
    render_mocks.reset_mock()

    _write_storyboard(ep_dir, narration="A different narration.")
    script = {**SCRIPT, "voiceover": "A different narration."}
    second = visual_agent.run(script, EP, WK, lang="en")

    render_mocks.assert_called_once()
    assert second["visual_identity"] != first["visual_identity"]
    assert len(_stale_files(ep_dir, "ep02_visuals")) == 1


# ── Assembly cache ───────────────────────────────────────────────────────────

def _assembly_inputs(d: Path, voice_hash: str | None, visual_identity: str | None) -> None:
    (d / "ep02_visuals.mp4").write_bytes(b"V" * 600_000)
    (d / "ep02_voice_EN.mp3").write_bytes(b"A" * 1000)
    if voice_hash:
        (d / "ep02_voice_hash_EN.txt").write_text(voice_hash, encoding="utf-8")
    if visual_identity:
        (d / "ep02_visuals.meta.json").write_text(json.dumps({"visual_identity": visual_identity}), encoding="utf-8")


@pytest.fixture
def assembly_mocks():
    container = MagicMock(duration=45_000_000)
    with patch.object(assembly_agent, "_transcribe", return_value=[]), \
         patch.object(assembly_agent, "_write_srt"), \
         patch.object(assembly_agent.av, "open", return_value=container), \
         patch.object(assembly_agent, "_validate_output", return_value=45.0), \
         patch.object(assembly_agent, "_ffmpeg") as ffmpeg:
        ffmpeg.side_effect = lambda *args, **kw: Path(args[-1]).write_bytes(b"F" * 600_000)
        yield ffmpeg


def test_final_without_metadata_is_stale_and_reassembled(ep_dir, assembly_mocks):
    _assembly_inputs(ep_dir, text_hash(NARRATION), "vis123")
    (ep_dir / "ep02_final_EN.mp4").write_bytes(b"OLD-FINAL" * 100_000)

    out = assembly_agent.run(EP, WK, lang="en")

    assembly_mocks.assert_called_once()
    assert out["skipped"] is False
    assert len(_stale_files(ep_dir, "ep02_final_EN")) == 1
    meta = json.loads((ep_dir / "ep02_final_EN.meta.json").read_text(encoding="utf-8"))
    assert meta == {**meta, "voice_source_hash": text_hash(NARRATION), "visual_identity": "vis123"}


def test_final_reused_only_when_both_identities_match(ep_dir, assembly_mocks):
    _assembly_inputs(ep_dir, text_hash(NARRATION), "vis123")
    assembly_agent.run(EP, WK, lang="en")
    assembly_mocks.reset_mock()

    out = assembly_agent.run(EP, WK, lang="en")

    assembly_mocks.assert_not_called()
    assert out["skipped"] is True


@pytest.mark.parametrize("changed", ["voice", "visual"])
def test_final_reassembled_when_an_input_identity_changes(ep_dir, assembly_mocks, changed):
    _assembly_inputs(ep_dir, text_hash(NARRATION), "vis123")
    assembly_agent.run(EP, WK, lang="en")
    assembly_mocks.reset_mock()

    if changed == "voice":
        (ep_dir / "ep02_voice_hash_EN.txt").write_text(text_hash("new narration"), encoding="utf-8")
    else:
        (ep_dir / "ep02_visuals.meta.json").write_text(json.dumps({"visual_identity": "vis999"}), encoding="utf-8")

    out = assembly_agent.run(EP, WK, lang="en")
    assembly_mocks.assert_called_once()
    assert out["skipped"] is False


def test_final_never_reused_when_input_identity_unknown(ep_dir, assembly_mocks):
    _assembly_inputs(ep_dir, voice_hash=None, visual_identity="vis123")
    assembly_agent.run(EP, WK, lang="en")
    assembly_mocks.reset_mock()

    assembly_agent.run(EP, WK, lang="en")
    assembly_mocks.assert_called_once()
