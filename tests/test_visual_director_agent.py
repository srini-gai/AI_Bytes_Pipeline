"""Tests for visual_director_agent Art Director enforcement + fingerprint approval.

The Anthropic client is mocked — no API calls are made.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents import visual_director_agent as vda


RATIONALE = {k: "reason" for k in vda.ART_DIRECTION_RATIONALE_KEYS}
VALID_AD = {
    "id": "cinematic-dark",
    "visual_world": "cinematic dark-tech",
    "rationale": RATIONALE,
}
DURATION_DECISION = {
    "total_seconds": 46.0,
    "rationale": {k: "reason" for k in vda.DURATION_RATIONALE_KEYS},
}
SCRIPT = {"topic": "Test Topic", "concept": "c", "hook": "h", "takeaway": "t", "voiceover": "v"}


def _scene(i: int, component: str, scene_type: str, dur: float, n_beats: int) -> dict:
    return {
        "scene_id": i,
        "duration_seconds": dur,
        "narration": f"narration {i}",
        "scene_type": scene_type,
        "visual_goal": "goal",
        "component": component,
        "objects": [],
        "animation": "moves",
        "on_screen_text": ["LABEL"],
        "transition": "cut",
        "beats": [
            {"start": b, "end": b + 1, "action": "transform", "claim_type": "ILLUSTRATIVE"}
            for b in range(n_beats)
        ],
    }


def _storyboard() -> list[dict]:
    """A storyboard that passes the existing v4 quality gate."""
    scenes = [_scene(1, "KineticTypoScene", "HOOK", 3.0, 2)]
    for i in range(2, 10):
        comp = "TransformScene" if i % 2 else "SplitCompareScene"
        scenes.append(_scene(i, comp, "DEMONSTRATION", 5.0, 2))
    scenes.append(_scene(10, "CTAScene", "CTA", 3.0, 0))
    return scenes


def _response(art_direction: object) -> MagicMock:
    payload = {
        "visual_thesis": {"core_concept": "x"},
        "novelty_assessment": {"similarity_scores": {}},
        "visual_fingerprint": {"visual_thesis": "x"},
        "storyboard": _storyboard(),
        "total_duration_seconds": 46.0,
    }
    if art_direction is not None:
        payload["art_direction"] = art_direction
    payload["duration_decision"] = DURATION_DECISION
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(payload))]
    return msg


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(vda, "FINGERPRINT_PATH", tmp_path / "visual_fingerprints.json")
    monkeypatch.setattr(vda.time, "sleep", lambda s: None)
    return tmp_path


def _mock_client(*responses: MagicMock) -> MagicMock:
    client = MagicMock()
    client.messages.create.side_effect = list(responses)
    return client


# ── Registry ─────────────────────────────────────────────────────────────────

def test_registry_parses_themes_ts():
    registry = vda.load_art_direction_registry()
    assert set(registry) >= {"cinematic-dark", "bright-workspace"}
    assert registry["bright-workspace"]["light_or_dark"] == "light"
    assert registry["cinematic-dark"]["visual_world"]


def test_registry_missing_file_raises(tmp_path):
    with pytest.raises(vda.ArtDirectionError):
        vda.load_art_direction_registry(tmp_path / "nope.ts")


# ── Validation ───────────────────────────────────────────────────────────────

REG = {"cinematic-dark": {}, "bright-workspace": {}}


def test_validate_missing_decision():
    v = vda._validate_art_direction(None, REG, {})
    assert v and v[0].startswith("ART_DIRECTION_MISSING")


def test_validate_no_default_for_empty_dict():
    assert vda._validate_art_direction({}, REG, {})[0].startswith("ART_DIRECTION_MISSING")


def test_validate_unregistered_world():
    ad = {**VALID_AD, "id": "pastel-dream"}
    assert any("UNREGISTERED" in v for v in vda._validate_art_direction(ad, REG, {}))


def test_validate_incomplete_rationale():
    ad = {**VALID_AD, "rationale": {"topic_semantics": "x"}}
    v = vda._validate_art_direction(ad, REG, {})
    assert any("rationale missing" in x and "visual_thesis" in x for x in v)


def test_validate_new_world_required():
    ad = {"id": vda.NEW_WORLD_REQUIRED, "visual_world": "chalkboard"}
    assert vda._validate_art_direction(ad, REG, {})[0].startswith("ART_DIRECTION_NEW_WORLD_REQUIRED")


def test_validate_valid_decision():
    assert vda._validate_art_direction(VALID_AD, REG, {}) == []


def test_validate_repeat_of_most_recent_world_needs_justification():
    fps = {
        "week01_ep01": {"art_direction": {"id": "bright-workspace"}},
        "week01_ep02": {"art_direction": {"id": "cinematic-dark"}},
    }
    assert any("ART_DIRECTION_REPEAT" in v for v in vda._validate_art_direction(VALID_AD, REG, fps))
    justified = {**VALID_AD, "repeat_justification": "deliberate series continuity"}
    assert vda._validate_art_direction(justified, REG, fps) == []


def test_validate_reuse_of_older_world_allowed():
    fps = {
        "week01_ep01": {"art_direction": {"id": "cinematic-dark"}},
        "week01_ep02": {"art_direction": {"id": "bright-workspace"}},
    }
    assert vda._validate_art_direction(VALID_AD, REG, fps) == []


# ── run() enforcement ────────────────────────────────────────────────────────

def test_run_fails_planning_without_art_director_decision(env):
    client = _mock_client(_response(None), _response(None), _response(None))
    with patch.object(vda.anthropic, "Anthropic", return_value=client):
        with pytest.raises(vda.ArtDirectionError):
            vda.run(SCRIPT, episode=3, week=2)

    assert client.messages.create.call_count == 3
    ep_dir = env / "week_02" / "ep03"
    assert not (ep_dir / "ep03_storyboard_EN.json").exists()
    marker = json.loads((ep_dir / "ep03_art_direction_FAILED_EN.json").read_text(encoding="utf-8"))
    assert marker["violations"][0].startswith("ART_DIRECTION_MISSING")


def test_run_new_world_required_stops_immediately(env):
    client = _mock_client(_response({"id": vda.NEW_WORLD_REQUIRED, "visual_world": "chalkboard"}))
    with patch.object(vda.anthropic, "Anthropic", return_value=client):
        with pytest.raises(vda.ArtDirectionError, match="NEW_WORLD_REQUIRED"):
            vda.run(SCRIPT, episode=3, week=2)
    assert client.messages.create.call_count == 1


def test_run_persists_explicit_art_direction_and_clears_marker(env):
    ep_dir = env / "week_02" / "ep03"
    ep_dir.mkdir(parents=True)
    stale = ep_dir / "ep03_art_direction_FAILED_EN.json"
    stale.write_text("{}", encoding="utf-8")

    client = _mock_client(_response(VALID_AD))
    with patch.object(vda.anthropic, "Anthropic", return_value=client):
        out = vda.run(SCRIPT, episode=3, week=2)

    assert out["art_direction"]["id"] == "cinematic-dark"
    doc = json.loads((ep_dir / "ep03_storyboard_EN.json").read_text(encoding="utf-8"))
    assert doc["art_direction"]["id"] == "cinematic-dark"
    assert doc["topic"] == "Test Topic"
    assert not stale.exists()


def test_run_retries_until_art_director_decides(env):
    client = _mock_client(_response(None), _response(VALID_AD))
    with patch.object(vda.anthropic, "Anthropic", return_value=client):
        out = vda.run(SCRIPT, episode=3, week=2)
    assert out["art_direction"]["id"] == "cinematic-dark"
    retry_prompt = client.messages.create.call_args_list[1].kwargs["messages"][0]["content"]
    assert "ART_DIRECTION_MISSING" in retry_prompt


def test_prompt_lists_registered_worlds_without_default(env):
    client = _mock_client(_response(VALID_AD))
    with patch.object(vda.anthropic, "Anthropic", return_value=client):
        vda.run(SCRIPT, episode=3, week=2)
    prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "cinematic-dark" in prompt and "bright-workspace" in prompt
    assert "no default world" in prompt


# ── approve_episode() fingerprint persistence ───────────────────────────────

def _write_doc(env: Path, ad: object) -> Path:
    ep_dir = env / "week_02" / "ep03"
    ep_dir.mkdir(parents=True, exist_ok=True)
    path = ep_dir / "ep03_storyboard_EN.json"
    path.write_text(json.dumps({
        "topic": "Test Topic",
        "art_direction": ad,
        "visual_fingerprint": {"visual_thesis": "x", "dominant_primitives": ["traverse"]},
        "storyboard": _storyboard(),
    }), encoding="utf-8")
    return path


def test_approve_persists_art_direction_fingerprint(env):
    _write_doc(env, VALID_AD)
    out = vda.approve_episode(3, 2, approved_by="srini")

    store = json.loads(vda.FINGERPRINT_PATH.read_text(encoding="utf-8"))
    fp = store["episodes"][out["episode_key"]]
    assert out["episode_key"] == "week02_ep03"
    assert fp["art_direction"]["id"] == "cinematic-dark"
    assert fp["art_direction"]["light_or_dark"] == "dark"
    assert fp["art_direction"]["rationale"] == RATIONALE
    assert fp["component_sequence"][0] == "KineticTypoScene"
    assert fp["approved_by"] == "srini"
    assert fp["visual_thesis"] == "x"


def test_approve_accepts_props_format_string_id(env, tmp_path):
    props = tmp_path / "props.json"
    props.write_text(json.dumps({
        "topic": "Agents", "art_direction": "bright-workspace", "storyboard": _storyboard(),
    }), encoding="utf-8")
    vda.approve_episode(2, 1, source=props)
    fp = json.loads(vda.FINGERPRINT_PATH.read_text(encoding="utf-8"))["episodes"]["week01_ep02"]
    assert fp["art_direction"]["id"] == "bright-workspace"
    assert fp["art_direction"]["visual_world"] == "bright workspace — productivity editorial"


def test_approve_without_art_direction_raises_and_writes_nothing(env):
    _write_doc(env, None)
    with pytest.raises(vda.ArtDirectionError):
        vda.approve_episode(3, 2)
    assert not vda.FINGERPRINT_PATH.exists()


def test_approved_fingerprint_feeds_next_plan_repeat_guard(env):
    _write_doc(env, VALID_AD)
    vda.approve_episode(3, 2)
    fps = vda._load_fingerprints()
    # The next episode choosing the same world without justification is flagged
    v = vda._validate_art_direction(VALID_AD, vda.load_art_direction_registry(), fps)
    assert any("ART_DIRECTION_REPEAT" in x for x in v)
    assert "Art direction: cinematic-dark" in vda._format_fingerprints_for_prompt(fps)


def test_reapproval_moves_episode_to_most_recent(env, tmp_path):
    _write_doc(env, VALID_AD)
    vda.approve_episode(3, 2)
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"art_direction": "bright-workspace", "storyboard": _storyboard()}), encoding="utf-8")
    vda.approve_episode(4, 2, source=other)
    vda.approve_episode(3, 2)
    assert list(vda._load_fingerprints())[-1] == "week02_ep03"


# ── v4 component registry ────────────────────────────────────────────────────

def test_v4_components_are_valid():
    assert {"AgentTraversalScene", "CircularFlowScene"} <= vda.VALID_COMPONENTS
    scenes = _storyboard()
    scenes[4]["component"] = "AgentTraversalScene"
    scenes[6]["component"] = "CircularFlowScene"
    assert not any("invalid component" in v for v in vda._validate_storyboard(scenes, 1))


def test_prompt_documents_v4_components():
    assert "AgentTraversalScene" in vda._SYSTEM_PROMPT
    assert "CircularFlowScene" in vda._SYSTEM_PROMPT


# ── Duration policy (45–60s, no default length) ──────────────────────────────

def test_prompt_has_no_preferred_duration():
    assert "no default length" in vda._SYSTEM_PROMPT
    assert "55–58s" not in vda._SYSTEM_PROMPT  # old fixed 58s template removed


def test_allowed_range_unchanged():
    assert (vda.TARGET_MIN_SECONDS, vda.TARGET_MAX_SECONDS) == (45.0, 60.0)


def test_duration_decision_required():
    v = vda._validate_duration_decision(None, _storyboard())
    assert v and v[0].startswith("DURATION_DECISION_MISSING")


def test_duration_decision_rationale_must_cover_all_factors():
    d = {"total_seconds": 46.0, "rationale": {"content_complexity": "x"}}
    v = vda._validate_duration_decision(d, _storyboard())
    assert any("narration_length" in x and "readability" in x for x in v)


def test_duration_decision_must_match_storyboard_total():
    d = {**DURATION_DECISION, "total_seconds": 55.0}
    assert any("MISMATCH" in x for x in vda._validate_duration_decision(d, _storyboard()))


def test_duration_decision_valid():
    assert vda._validate_duration_decision(DURATION_DECISION, _storyboard()) == []


def _with_narration_words(n_words: int) -> list[dict]:
    scenes = _storyboard()
    per = n_words // len(scenes)
    for s in scenes:
        s["narration"] = " ".join(["word"] * per)
    return scenes


def test_duration_too_short_for_narration_flagged():
    scenes = _with_narration_words(160)  # 160 words in 46s ≈ 3.5 w/s
    assert any("TOO_SHORT" in x for x in vda._validate_duration_decision(DURATION_DECISION, scenes))


def test_duration_too_long_for_narration_flagged():
    scenes = _with_narration_words(60)  # 60 words in 46s ≈ 1.3 w/s
    assert any("TOO_LONG" in x for x in vda._validate_duration_decision(DURATION_DECISION, scenes))


def test_duration_fits_narration():
    scenes = _with_narration_words(110)  # ≈ 2.4 w/s
    assert vda._validate_duration_decision(DURATION_DECISION, scenes) == []


def test_run_retries_when_duration_decision_missing(env):
    bad = _response(VALID_AD)
    payload = json.loads(bad.content[0].text)
    payload.pop("duration_decision")
    bad.content[0].text = json.dumps(payload)
    client = _mock_client(bad, _response(VALID_AD))
    with patch.object(vda.anthropic, "Anthropic", return_value=client):
        out = vda.run(SCRIPT, episode=3, week=2)
    assert client.messages.create.call_count == 2
    assert out["violations"] == []
    doc = json.loads((env / "week_02" / "ep03" / "ep03_storyboard_EN.json").read_text(encoding="utf-8"))
    assert doc["duration_decision"]["total_seconds"] == 46.0
