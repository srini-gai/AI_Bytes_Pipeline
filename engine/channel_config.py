"""
Channel configuration loader — reads a channel pack YAML and provides
typed accessors for every agent that needs channel-specific values.

Usage:
    from engine.channel_config import load_channel, ChannelConfig

    cfg = load_channel("srini_on_ai")
    cfg.brand.accent      # "#a78bfa"
    cfg.voice.defaults    # {"stability": 0.42, ...}
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

CHANNELS_DIR = Path(__file__).parent.parent / "channels"

_DEFAULT_CHANNEL = "srini_on_ai"

# Singleton cache — one channel loaded per process lifetime
_cache: dict[str, "ChannelConfig"] = {}


@dataclass(frozen=True)
class BrandConfig:
    bg: str
    accent: str
    accent2: str
    logo: str
    cta_text: str
    hashtag: str
    default_title_pattern: str


@dataclass(frozen=True)
class VoiceDurationWindow:
    min: float
    max: float


@dataclass(frozen=True)
class VoiceConfig:
    model_id: str
    output_format: str
    stability: float
    similarity_boost: float
    style: float
    speed: float
    use_speaker_boost: bool
    env_voice_id_key: str
    duration_windows: dict[str, VoiceDurationWindow]


@dataclass(frozen=True)
class ScriptConfig:
    persona: str
    voiceover_word_range: tuple[int, int]
    voiceover_target_words: int
    tags_always_include: str
    theme_guide: dict[str, dict[str, str]]


@dataclass(frozen=True)
class VisualConfig:
    remotion_composition_id: str
    default_theme: dict[str, str]
    target_min_seconds: float
    target_max_seconds: float
    max_hook_seconds: float
    max_cta_seconds: float
    min_narration_wps: float
    max_narration_wps: float
    weekly_diversity_guideline: dict[str, str]
    fingerprint_channel_key: str


@dataclass(frozen=True)
class PublisherConfig:
    category_id: str
    env_keys: dict[str, dict[str, str]]


@dataclass(frozen=True)
class DomainConfig:
    id: str
    description: str
    content_guidance: str
    visual_guidance: str


@dataclass(frozen=True)
class ChannelConfig:
    id: str
    name: str
    tagline: str
    format: str
    language_default: str
    languages: list[str]
    brand: BrandConfig
    voice: VoiceConfig
    script: ScriptConfig
    visual: VisualConfig
    publisher: PublisherConfig
    domain: DomainConfig

    _raw: dict = field(default_factory=dict, repr=False, compare=False)


def _parse_brand(raw: dict) -> BrandConfig:
    colors = raw.get("colors", {})
    return BrandConfig(
        bg=colors.get("bg", "#050510"),
        accent=colors.get("accent", "#a78bfa"),
        accent2=colors.get("accent2", "#34d399"),
        logo=raw.get("logo", ""),
        cta_text=raw.get("cta_text", ""),
        hashtag=raw.get("hashtag", ""),
        default_title_pattern=raw.get("default_title_pattern", ""),
    )


def _parse_voice(raw: dict) -> VoiceConfig:
    defaults = raw.get("defaults", {})
    dw_raw = raw.get("duration_windows", {})
    duration_windows = {
        lang: VoiceDurationWindow(min=w["min"], max=w["max"])
        for lang, w in dw_raw.items()
    }
    return VoiceConfig(
        model_id=raw.get("model_id", "eleven_multilingual_v2"),
        output_format=raw.get("output_format", "mp3_44100_128"),
        stability=defaults.get("stability", 0.42),
        similarity_boost=defaults.get("similarity_boost", 0.78),
        style=defaults.get("style", 0.0),
        speed=defaults.get("speed", 1.05),
        use_speaker_boost=defaults.get("use_speaker_boost", True),
        env_voice_id_key=raw.get("env_voice_id_key", "ELEVENLABS_VOICE_ID"),
        duration_windows=duration_windows,
    )


def _parse_script(raw: dict) -> ScriptConfig:
    wr = raw.get("voiceover_word_range", [150, 175])
    return ScriptConfig(
        persona=raw.get("persona", ""),
        voiceover_word_range=(wr[0], wr[1]),
        voiceover_target_words=raw.get("voiceover_target_words", 155),
        tags_always_include=raw.get("tags_always_include", ""),
        theme_guide=raw.get("theme_guide", {}),
    )


def _parse_visual(raw: dict) -> VisualConfig:
    gates = raw.get("quality_gates", {})
    pacing = raw.get("narration_pacing", {})
    return VisualConfig(
        remotion_composition_id=raw.get("remotion_composition_id", "AIBytesReel"),
        default_theme=raw.get("default_theme", {}),
        target_min_seconds=gates.get("target_min_seconds", 45.0),
        target_max_seconds=gates.get("target_max_seconds", 60.0),
        max_hook_seconds=gates.get("max_hook_seconds", 4.0),
        max_cta_seconds=gates.get("max_cta_seconds", 3.0),
        min_narration_wps=pacing.get("min_wps", 2.0),
        max_narration_wps=pacing.get("max_wps", 3.2),
        weekly_diversity_guideline=raw.get("weekly_diversity_guideline", {}),
        fingerprint_channel_key=raw.get("fingerprint_channel_key", "ai_bytes"),
    )


def _parse_publisher(raw: dict) -> PublisherConfig:
    return PublisherConfig(
        category_id=raw.get("category_id", "28"),
        env_keys=raw.get("env_keys", {}),
    )


def _parse_domain(raw: dict) -> DomainConfig:
    return DomainConfig(
        id=raw.get("id", "general"),
        description=raw.get("description", ""),
        content_guidance=raw.get("content_guidance", ""),
        visual_guidance=raw.get("visual_guidance", ""),
    )


def load_channel(channel_id: str = _DEFAULT_CHANNEL) -> ChannelConfig:
    """Load a channel pack from channels/<channel_id>/channel.yaml."""
    if channel_id in _cache:
        return _cache[channel_id]

    channel_dir = CHANNELS_DIR / channel_id
    config_path = channel_dir / "channel.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Channel pack not found: {config_path}. "
            f"Available channels: {[d.name for d in CHANNELS_DIR.iterdir() if d.is_dir()]}"
        )

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    logger.info(f"Loaded channel pack: {channel_id} ({raw.get('name', '?')})")

    cfg = ChannelConfig(
        id=raw.get("id", channel_id),
        name=raw.get("name", channel_id),
        tagline=raw.get("tagline", ""),
        format=raw.get("format", "youtube_shorts"),
        language_default=raw.get("language_default", "en"),
        languages=raw.get("languages", ["en"]),
        brand=_parse_brand(raw.get("brand", {})),
        voice=_parse_voice(raw.get("voice", {})),
        script=_parse_script(raw.get("script", {})),
        visual=_parse_visual(raw.get("visual", {})),
        publisher=_parse_publisher(raw.get("publisher", {})),
        domain=_parse_domain(raw.get("domain", {})),
        _raw=raw,
    )
    _cache[channel_id] = cfg
    return cfg


def get_default_channel() -> str:
    """Return the active channel ID (set by orchestrator --channel flag)."""
    return _DEFAULT_CHANNEL


def set_default_channel(channel_id: str) -> None:
    """Set the active channel for this process. Called once by the orchestrator."""
    global _DEFAULT_CHANNEL
    _DEFAULT_CHANNEL = channel_id
