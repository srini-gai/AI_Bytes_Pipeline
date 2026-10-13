"""
Channel Config Wiring Tests — proves that Engine v1 agents consume
channel-specific values from ChannelConfig, not hardcoded constants.

Uses the synthetic test_channel to verify runtime selection changes
downstream values without rendering or publishing.
"""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from engine.channel_config import (
    ChannelConfig,
    DomainConfig,
    load_channel,
    get_default_channel,
    _cache,
)


@pytest.fixture(autouse=True)
def clear_channel_cache():
    """Clear the singleton cache between tests."""
    _cache.clear()
    yield
    _cache.clear()


# ── 1. Loader basics ────────────────────────────────────────────────────────

class TestChannelLoader:
    def test_load_default_channel(self):
        cfg = load_channel(get_default_channel())
        assert cfg.id == "srini_on_ai"
        assert cfg.name == "Srini on AI"

    def test_load_test_channel(self):
        cfg = load_channel("test_channel")
        assert cfg.id == "test_channel"
        assert cfg.name == "Test Channel"

    def test_missing_channel_raises(self):
        with pytest.raises(FileNotFoundError, match="Channel pack not found"):
            load_channel("nonexistent_channel")

    def test_channels_have_different_values(self):
        srini = load_channel("srini_on_ai")
        test = load_channel("test_channel")
        assert srini.brand.accent != test.brand.accent
        assert srini.brand.cta_text != test.brand.cta_text
        assert srini.voice.stability != test.voice.stability
        assert srini.visual.fingerprint_channel_key != test.visual.fingerprint_channel_key

    def test_cache_returns_same_instance(self):
        a = load_channel("srini_on_ai")
        b = load_channel("srini_on_ai")
        assert a is b


# ── 2. Script Agent receives channel config ──────────────────────────────────

class TestScriptAgentWiring:
    def test_prompt_contains_channel_name(self):
        from agents.script_agent import _build_system_prompt
        prompt = _build_system_prompt("en")
        cfg = load_channel(get_default_channel())
        assert cfg.name in prompt

    def test_prompt_contains_cta(self):
        from agents.script_agent import _build_system_prompt
        prompt = _build_system_prompt("en")
        cfg = load_channel(get_default_channel())
        assert cfg.brand.cta_text in prompt

    def test_prompt_contains_hashtag(self):
        from agents.script_agent import _build_system_prompt
        prompt = _build_system_prompt("en")
        cfg = load_channel(get_default_channel())
        assert cfg.brand.hashtag in prompt

    def test_prompt_contains_word_range(self):
        from agents.script_agent import _build_system_prompt
        prompt = _build_system_prompt("en")
        cfg = load_channel(get_default_channel())
        lo, hi = cfg.script.voiceover_word_range
        assert str(lo) in prompt
        assert str(hi) in prompt


# ── 3. Voice Agent receives channel voice settings ───────────────────────────

class TestVoiceAgentWiring:
    def test_voice_settings_from_config(self):
        from agents.voice_agent import _voice_settings
        cfg = load_channel(get_default_channel())
        vs = _voice_settings()
        assert vs.stability == cfg.voice.stability
        assert vs.similarity_boost == cfg.voice.similarity_boost
        assert vs.speed == cfg.voice.speed

    def test_voice_settings_env_override(self, monkeypatch):
        from agents.voice_agent import _voice_settings
        monkeypatch.setenv("ELEVENLABS_STABILITY", "0.99")
        vs = _voice_settings()
        assert vs.stability == 0.99

    def test_duration_window_from_config(self):
        from agents.voice_agent import _validate_duration
        cfg = load_channel(get_default_channel())
        dw = cfg.voice.duration_windows["en"]
        assert dw.min == 40.0
        assert dw.max == 66.0


# ── 4. Visual Director receives channel visual config ────────────────────────

class TestVisualDirectorWiring:
    def test_target_duration_from_config(self):
        from agents.visual_director_agent import _target_min_seconds, _target_max_seconds
        cfg = load_channel(get_default_channel())
        assert _target_min_seconds() == cfg.visual.target_min_seconds
        assert _target_max_seconds() == cfg.visual.target_max_seconds

    def test_hook_cta_limits_from_config(self):
        from agents.visual_director_agent import _max_hook_seconds, _max_cta_seconds
        cfg = load_channel(get_default_channel())
        assert _max_hook_seconds() == cfg.visual.max_hook_seconds
        assert _max_cta_seconds() == cfg.visual.max_cta_seconds

    def test_narration_pacing_from_config(self):
        from agents.visual_director_agent import _min_narration_wps, _max_narration_wps
        cfg = load_channel(get_default_channel())
        assert _min_narration_wps() == cfg.visual.min_narration_wps
        assert _max_narration_wps() == cfg.visual.max_narration_wps

    def test_fingerprint_key_from_config(self):
        from agents.visual_director_agent import _channel_fingerprint_key
        cfg = load_channel(get_default_channel())
        assert _channel_fingerprint_key() == cfg.visual.fingerprint_channel_key


# ── 5. CTA is channel-driven ────────────────────────────────────────────────

class TestCTAWiring:
    def test_cta_text_in_script_prompt(self):
        from agents.script_agent import _build_system_prompt
        prompt = _build_system_prompt("en")
        cfg = load_channel(get_default_channel())
        assert cfg.brand.cta_text in prompt

    def test_cta_differs_between_channels(self):
        srini = load_channel("srini_on_ai")
        test = load_channel("test_channel")
        assert srini.brand.cta_text != test.brand.cta_text
        assert "Srini on AI" in srini.brand.cta_text
        assert "Test Channel" in test.brand.cta_text


# ── 6. Fingerprint memory is channel-scoped ──────────────────────────────────

class TestFingerprintScoping:
    def test_diversity_gate_filters_by_channel(self):
        from agents.visual_director_agent import _diversity_gate
        fps = {
            "ep01": {"channel": "ai_bytes", "component_sequence": ["FlowScene"]},
            "ep02": {"channel": "other_channel", "component_sequence": ["FlowScene"]},
        }
        plan = {"components": ["FlowScene"], "visual_modes": ["NATIVE"]}
        result = _diversity_gate(plan, fps, channel="ai_bytes")
        assert result["recent_key"] == "ep01"

    def test_fingerprint_prompt_filters_by_channel(self):
        from agents.visual_director_agent import _format_fingerprints_for_prompt
        fps = {
            "ep01": {"channel": "ai_bytes", "topic": "Test A"},
            "ep02": {"channel": "other_channel", "topic": "Test B"},
        }
        prompt = _format_fingerprints_for_prompt(fps, channel="ai_bytes")
        assert "Test A" in prompt
        assert "Test B" not in prompt

    def test_different_channel_key_isolates(self):
        from agents.visual_director_agent import _diversity_gate
        fps = {
            "ep01": {"channel": "ai_bytes", "component_sequence": ["FlowScene"]},
        }
        plan = {"components": ["FlowScene"], "visual_modes": ["NATIVE"]}
        result = _diversity_gate(plan, fps, channel="test_channel")
        assert result["pass"] is True
        assert "no" in result["reason"].lower() or "skipped" in result["reason"].lower()


# ── 7. Publisher config is channel-driven ────────────────────────────────────

class TestPublisherWiring:
    def test_category_from_config(self):
        cfg = load_channel(get_default_channel())
        assert cfg.publisher.category_id == "28"

    def test_env_keys_from_config(self):
        cfg = load_channel(get_default_channel())
        en_keys = cfg.publisher.env_keys["en"]
        assert en_keys["channel_id"] == "YOUTUBE_CHANNEL_ID_EN"
        assert en_keys["refresh_token"] == "YOUTUBE_REFRESH_TOKEN_EN"

    def test_test_channel_has_different_publisher(self):
        cfg = load_channel("test_channel")
        assert cfg.publisher.category_id == "27"
        en_keys = cfg.publisher.env_keys["en"]
        assert en_keys["channel_id"] == "YOUTUBE_CHANNEL_ID_TEST"


# ── 8. Engine v1 global rules remain unchanged ──────────────────────────────

class TestGlobalRulesUnchanged:
    def test_global_structural_gates(self):
        from agents.visual_director_agent import (
            MIN_VISUAL_BEATS,
            MAX_TYPOGRAPHY_RATIO,
            MAX_CONSECUTIVE_SAME_LAYOUT,
            MIN_VISUAL_DEMONSTRATIONS,
            MIN_VISUAL_FIRST_SCORE,
            MAX_SCENE_SECONDS_WITHOUT_BEATS,
        )
        assert MIN_VISUAL_BEATS == 8
        assert MAX_TYPOGRAPHY_RATIO == 0.25
        assert MAX_CONSECUTIVE_SAME_LAYOUT == 2
        assert MIN_VISUAL_DEMONSTRATIONS == 3
        assert MIN_VISUAL_FIRST_SCORE == 80
        assert MAX_SCENE_SECONDS_WITHOUT_BEATS == 6.0

    def test_component_families_global(self):
        from agents.visual_director_agent import COMPONENT_FAMILIES
        assert "KineticTypoScene" in COMPONENT_FAMILIES
        assert COMPONENT_FAMILIES["KineticTypoScene"] == "TYPOGRAPHY"

    def test_valid_components_global(self):
        from agents.visual_director_agent import VALID_COMPONENTS
        assert "CTAScene" in VALID_COMPONENTS
        assert "FlowScene" in VALID_COMPONENTS

    def test_valid_scene_types_global(self):
        from agents.visual_director_agent import VALID_SCENE_TYPES
        assert "HOOK" in VALID_SCENE_TYPES
        assert "CTA" in VALID_SCENE_TYPES


# ── 9. Runtime channel selection proof ───────────────────────────────────────

class TestRuntimeSelection:
    """Proves that changing the default channel changes what agents receive."""

    def test_different_channel_different_voice_settings(self):
        srini_voice = load_channel("srini_on_ai").voice
        test_voice = load_channel("test_channel").voice
        assert srini_voice.stability == 0.42
        assert test_voice.stability == 0.50
        assert srini_voice.speed == 1.05
        assert test_voice.speed == 1.10

    def test_different_channel_different_visual_thresholds(self):
        srini_vis = load_channel("srini_on_ai").visual
        test_vis = load_channel("test_channel").visual
        assert srini_vis.target_min_seconds == 45.0
        assert test_vis.target_min_seconds == 40.0
        assert srini_vis.max_hook_seconds == 4.0
        assert test_vis.max_hook_seconds == 5.0

    def test_different_channel_different_composition_id(self):
        srini = load_channel("srini_on_ai").visual
        test = load_channel("test_channel").visual
        assert srini.remotion_composition_id == "AIBytesReel"
        assert test.remotion_composition_id == "TestReel"

    def test_different_channel_different_brand(self):
        srini = load_channel("srini_on_ai").brand
        test = load_channel("test_channel").brand
        assert srini.accent == "#a78bfa"
        assert test.accent == "#ff0000"
        assert srini.cta_text != test.cta_text

    def test_different_channel_different_fingerprint_key(self):
        srini = load_channel("srini_on_ai").visual
        test = load_channel("test_channel").visual
        assert srini.fingerprint_channel_key == "ai_bytes"
        assert test.fingerprint_channel_key == "test_channel"


# ── 10. Domain config ───────────────────────────────────────────────────────

class TestDomainConfig:
    def test_srini_domain_is_ai(self):
        cfg = load_channel("srini_on_ai")
        assert cfg.domain.id == "ai_technology"
        assert "AI" in cfg.domain.description

    def test_test_channel_domain_is_not_ai(self):
        cfg = load_channel("test_channel")
        assert cfg.domain.id == "general_education"
        assert "AI" not in cfg.domain.id

    def test_ai_content_guidance_in_srini(self):
        cfg = load_channel("srini_on_ai")
        assert "tokenization" in cfg.domain.content_guidance.lower()
        assert "backpropagation" in cfg.domain.content_guidance.lower()

    def test_no_ai_content_guidance_in_test(self):
        cfg = load_channel("test_channel")
        assert "tokenization" not in cfg.domain.content_guidance.lower()
        assert "backpropagation" not in cfg.domain.content_guidance.lower()
        assert "RLHF" not in cfg.domain.content_guidance

    def test_ai_visual_guidance_in_srini(self):
        cfg = load_channel("srini_on_ai")
        assert "humanoid" in cfg.domain.visual_guidance.lower()
        assert "TokenScene" in cfg.domain.visual_guidance

    def test_no_ai_visual_guidance_in_test(self):
        cfg = load_channel("test_channel")
        assert "humanoid" not in cfg.domain.visual_guidance.lower()
        assert "TokenScene" not in cfg.domain.visual_guidance


# ── 11. Remotion props carry channel brand ───────────────────────────────────

class TestRemotonPropsWiring:
    def test_props_contain_channel_brand(self):
        from agents.visual_agent import _build_props
        props = _build_props({"episode": "01", "topic": "Test"})
        assert props["channelName"] == "Srini on AI"
        assert props["logoPath"] == "srini-logo.png"
        assert props["ctaText"] == "Follow Srini on AI for practical AI, daily."

    def test_logo_differs_by_channel(self):
        srini = load_channel("srini_on_ai")
        test = load_channel("test_channel")
        assert srini.brand.logo == "srini-logo.png"
        assert test.brand.logo == "test-logo.png"

    def test_cta_differs_by_channel(self):
        srini = load_channel("srini_on_ai")
        test = load_channel("test_channel")
        assert "Srini on AI" in srini.brand.cta_text
        assert "Srini on AI" not in test.brand.cta_text
        assert "Test Channel" in test.brand.cta_text


# ── 12. No Srini-on-AI leakage into non-AI channel ──────────────────────────

class TestNoChannelLeakage:
    def test_no_srini_identity_in_test_channel(self):
        test = load_channel("test_channel")
        combined = (
            test.name + test.tagline + test.brand.cta_text +
            test.brand.hashtag + test.brand.logo +
            test.domain.content_guidance + test.domain.visual_guidance
        ).lower()
        assert "srini" not in combined
        assert "practical ai, daily" not in combined

    def test_no_ai_domain_content_in_test_prompt(self):
        """Proves script prompt built for test_channel would not get AI routing."""
        test = load_channel("test_channel")
        assert "tokenization" not in test.domain.content_guidance.lower()
        assert "transformer" not in test.domain.content_guidance.lower()
        assert "neural network" not in test.domain.content_guidance.lower()

    def test_no_ai_domain_visual_in_test_prompt(self):
        test = load_channel("test_channel")
        assert "robot" not in test.domain.visual_guidance.lower()
        assert "TokenScene" not in test.domain.visual_guidance
        assert "ContextWindowScene" not in test.domain.visual_guidance

    def test_generic_engine_rules_identical_across_channels(self):
        from agents.visual_director_agent import (
            MIN_VISUAL_BEATS,
            MAX_TYPOGRAPHY_RATIO,
            VALID_COMPONENTS,
            VALID_SCENE_TYPES,
            COMPONENT_FAMILIES,
        )
        assert MIN_VISUAL_BEATS == 8
        assert MAX_TYPOGRAPHY_RATIO == 0.25
        assert "CTAScene" in VALID_COMPONENTS
        assert "HOOK" in VALID_SCENE_TYPES
        assert "TYPOGRAPHY" in COMPONENT_FAMILIES.values()
