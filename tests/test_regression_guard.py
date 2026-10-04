"""Tests for regression_guard — theme-neutral content detection + storyboard-driven scene count."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import regression_guard as rg

N = rg.SAMPLE_W * rg.SAMPLE_H
LIGHT_BG = 248   # bright-workspace #F7F8FA
DARK_BG = 6      # cinematic-dark #050510


def _frame(bg: int, content_value: int | None = None, content_px: int = 0) -> bytes:
    px = bytearray([bg]) * N
    if content_value is not None:
        px[:content_px] = bytes([content_value]) * content_px
    return bytes(px)


# ── frame_content_stats (pure) ───────────────────────────────────────────────

@pytest.mark.parametrize("bg", [LIGHT_BG, DARK_BG])
def test_flat_background_is_empty_in_both_themes(bg):
    stats = rg.frame_content_stats(_frame(bg))
    assert stats["background_luminance"] == bg
    assert not stats["has_content"]


def test_dark_text_on_light_background_is_content():
    assert rg.frame_content_stats(_frame(LIGHT_BG, 26, N // 20))["has_content"]


def test_light_text_on_dark_background_is_content():
    assert rg.frame_content_stats(_frame(DARK_BG, 230, N // 20))["has_content"]


def test_subtle_background_noise_is_not_content():
    # Gradient-like variation within CONTENT_DELTA of the background
    assert not rg.frame_content_stats(_frame(LIGHT_BG, LIGHT_BG - 8, N // 2))["has_content"]


def test_tiny_speck_below_ratio_is_not_content():
    assert not rg.frame_content_stats(_frame(LIGHT_BG, 20, 10))["has_content"]


# ── load_scenes ──────────────────────────────────────────────────────────────

def test_load_scenes_from_props(tmp_path):
    p = tmp_path / "props.json"
    p.write_text(json.dumps({"art_direction": "bright-workspace", "storyboard": [{}, {}, {}]}), encoding="utf-8")
    scenes, ad = rg.load_scenes(p)
    assert len(scenes) == 3 and ad == "bright-workspace"


def test_load_scenes_from_v4_doc_and_list(tmp_path):
    doc = tmp_path / "doc.json"
    doc.write_text(json.dumps({"art_direction": {"id": "cinematic-dark"}, "storyboard": [{}]}), encoding="utf-8")
    assert rg.load_scenes(doc) == ([{}], "cinematic-dark")
    lst = tmp_path / "list.json"
    lst.write_text(json.dumps([{}, {}]), encoding="utf-8")
    assert rg.load_scenes(lst) == ([{}, {}], None)


def test_no_hardcoded_scene_count():
    assert not hasattr(rg, "EXPECTED_SCENE_COUNT")


# ── run_regression_guard end-to-end (local ffmpeg only) ─────────────────────

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _make_video(path: Path, color: str, box: str | None = None) -> None:
    vf = ["-vf", f"drawbox=x=200:y=700:w=680:h=400:color={box}:t=fill"] if box else []
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", f"color=c={color}:s=1080x1920:d=6:r=30", *vf, str(path)],
        check=True,
    )


def _storyboard(tmp_path: Path, n: int) -> Path:
    p = tmp_path / "sb.json"
    p.write_text(json.dumps({"storyboard": [{"scene_id": i + 1, "duration_seconds": 6 / n} for i in range(n)]}),
                 encoding="utf-8")
    return p


@needs_ffmpeg
@pytest.mark.parametrize("bg,box", [("0xF7F8FA", "0x3B82F6"), ("0x050510", "0xa78bfa")])
def test_content_passes_in_both_themes(tmp_path, bg, box):
    video = tmp_path / "v.mp4"
    _make_video(video, bg, box)
    report = rg.run_regression_guard(video, _storyboard(tmp_path, 3))
    assert report["verdict"] == "PASS"
    assert report["expected_scenes"] == 3 and report["rendered_scenes"] == 3


@needs_ffmpeg
@pytest.mark.parametrize("bg", ["0xF7F8FA", "0x050510"])
def test_blank_render_fails_in_both_themes(tmp_path, bg):
    video = tmp_path / "v.mp4"
    _make_video(video, bg)
    report = rg.run_regression_guard(video, _storyboard(tmp_path, 2))
    assert report["verdict"] == "FAIL"
    assert report["rendered_scenes"] == 0
    assert report["checks"]["scene_count"]["expected"] == 2
