# Channel Factory Readiness Report

> Generated 2026-10-12. Based on Engine v1 (tag `engine-v1`, commit `8d94e82`).

---

## Summary

The first Channel Pack (`srini_on_ai`) has been extracted from Engine v1.
A typed configuration loader (`engine.channel_config`) can read any channel pack.
The orchestrator accepts `--channel <id>` to select a channel at runtime.
The visual fingerprint system now reads its channel key from config rather than
a hardcoded string. **Zero behavior change** — all existing tests pass at the
same rate as the baseline freeze (429 pass, 20 pre-existing fail, 16 fixture errors).

---

## 1. Channel Pack extracted?

**YES.** `channels/srini_on_ai/channel.yaml` — a single YAML file containing
all channel-specific configuration organized in 5 sections: brand, voice, script,
visual, publisher. One file was chosen over 5 separate files to minimize loader
complexity and keep related data together.

## 2. Channel config loader built?

**YES.** `engine/channel_config.py` — typed dataclass accessors with singleton
caching. `load_channel("srini_on_ai")` returns a `ChannelConfig` with nested
`BrandConfig`, `VoiceConfig`, `ScriptConfig`, `VisualConfig`, `PublisherConfig`.

## 3. CLI channel selection working?

**YES.** `python orchestrator.py --channel srini_on_ai` loads the channel pack
and displays the channel name at startup. Default: `srini_on_ai`.

## 4. Fingerprint system channel-aware via config?

**YES.** The four hardcoded `"ai_bytes"` references in `visual_director_agent.py`
now resolve through `_channel_fingerprint_key()` which reads from the channel
config's `visual.fingerprint_channel_key`. Backward-compatible: falls back to
`"ai_bytes"` if config is unavailable.

Changed locations:
- `_diversity_gate()` — channel parameter default
- `_format_fingerprints_for_prompt()` — channel parameter default
- Both channel-scoped filter expressions
- `approve_episode()` — fingerprint `"channel"` field

## 5. Zero-behavior-change validated?

**YES.** Validated with EP08 frozen storyboard:
- `_channel_fingerprint_key()` → `"ai_bytes"` (identical to hardcoded value)
- Diversity gate against 4 prior fingerprints: PASS
- Fingerprint prompt includes all 5 registered episodes
- EP08 fingerprint `channel` field: `"ai_bytes"`
- Different channel key → gate correctly skips (no matching fingerprints)
- Full test suite: 429 pass, 20 pre-existing fail, 16 fixture errors, **0 new failures**

## 6. CHANNEL vs DOMAIN vs GLOBAL boundaries documented?

**YES.** Classification from the audit:

### CHANNEL-specific (in channel.yaml)
| Data | Source file(s) |
|------|---------------|
| Brand colors (BG/ACCENT/ACCENT2) | visual_agent, 25+ Remotion components |
| Channel name "Srini on AI" | script_agent, visual_director, HookScene, CTAScene |
| CTA text | script_agent, CTAScene |
| Hashtag #SriniOnAI | script_agent |
| Voice B settings (stability, similarity, speed) | voice_agent |
| Voice model + format | voice_agent |
| Duration windows (per-language) | voice_agent |
| Voiceover word range (150-175) | script_agent |
| Theme guide (6 moods × colors) | script_agent |
| Default theme (energy) | visual_agent |
| Remotion composition ID (AIBytesReel) | visual_agent |
| Quality gate thresholds | visual_director_agent |
| Narration pacing (WPS) | visual_director_agent |
| Weekly diversity guideline | visual_mode_router |
| Publisher category, env keys | publisher_agent |
| Default title pattern | publisher_agent |
| Logo file reference | HookScene |
| Fingerprint channel key | visual_director_agent |

### DOMAIN-specific (AI/tech education — NOT in channel pack)
| Data | Location |
|------|----------|
| Diagram routing keywords (AI-specific) | script_agent lines 89-107 |
| YouTube category "Science & Technology" | publisher_agent (also in channel.yaml for override) |
| Topic interpretation rule (AI lens) | CLAUDE.md + memory |

### GLOBAL ENGINE rules (never channel-specific)
| Rule | Location |
|------|----------|
| Voice-first timing (duration gate) | orchestrator |
| Duration validation ranges | assembly_agent |
| 4-level semantic hierarchy | visual_director_agent |
| NATIVE/GENERATED router | visual_mode_router |
| Diversity gates (cross-episode, intra-episode) | visual_director_agent |
| fal budget controls | fal_asset_agent |
| Timeline QA (blank/static/duplication) | timeline_qa_guard |
| Perceptual duplicate QA | timeline_qa_guard |
| Loudness normalization (EBU R128) | assembly_agent |
| Publisher approval gate | publisher_agent |
| Three-hash check | assembly_agent |
| Scene config similarity (6-factor) | visual_director_agent |

## 7. What's wired vs. what's documented-only?

### Wired (reads from channel.yaml at runtime)
- Fingerprint channel key → `visual_director_agent._channel_fingerprint_key()`
- Channel selection → `orchestrator.py --channel`
- All config accessible → `load_channel().brand.accent`, etc.

### Documented-only (channel.yaml captures the value; agent still reads its own constant)
These are the remaining wiring points. Each is a one-line change in the agent
to read from `cfg.X` instead of a module-level constant, but the user's
instruction was "configuration extraction only" — no agent refactoring.

| Agent | Constant | Channel config path |
|-------|----------|-------------------|
| script_agent | `_SYSTEM_PROMPT_BASE` (persona) | `cfg.script.persona` |
| script_agent | THEME GUIDE block | `cfg.script.theme_guide` |
| script_agent | voiceover word range | `cfg.script.voiceover_word_range` |
| script_agent | CTA text, hashtag | `cfg.brand.cta_text`, `cfg.brand.hashtag` |
| voice_agent | `MODEL_ID` | `cfg.voice.model_id` |
| voice_agent | `_voice_settings()` defaults | `cfg.voice.stability`, etc. |
| voice_agent | `MIN_DURATION`, `MAX_DURATION` | `cfg.voice.duration_windows[lang]` |
| visual_agent | `_DEFAULT_THEME` | `cfg.visual.default_theme` |
| visual_agent | composition ID "AIBytesReel" | `cfg.visual.remotion_composition_id` |
| visual_director | system prompt "Srini on AI" | `cfg.name` |
| visual_director | quality gate thresholds | `cfg.visual.target_min_seconds`, etc. |
| visual_director | narration WPS | `cfg.visual.min_narration_wps`, etc. |
| visual_mode_router | weekly diversity guideline | `cfg.visual.weekly_diversity_guideline` |
| publisher_agent | `CATEGORY_ID` | `cfg.publisher.category_id` |
| publisher_agent | env key lookups | `cfg.publisher.env_keys[lang]` |
| publisher_agent | default title | `cfg.brand.default_title_pattern` |
| Remotion components | BG/ACCENT/ACCENT2 fallbacks | Props from Python pipeline (already works via visual_agent theme) |

## 8. Remotion component strategy

The 25+ Remotion components have hardcoded color fallback defaults (`#050510`,
`#a78bfa`, `#34d399`). These are **fallbacks** — the Python pipeline already
passes accent colors through Remotion props via the `theme` object. The correct
strategy for channel B is:

1. Channel B's `channel.yaml` defines its own colors
2. Python pipeline reads `cfg.brand.accent` and passes to Remotion via props
3. Remotion fallbacks only fire if props are missing (shouldn't happen)

**No TSX changes needed** for color support. The only Remotion components that
need channel-specific changes for a new channel are:
- `HookScene.tsx` — logo file path (`staticFile('srini-logo.png')`)
- `CTAScene.tsx` — CTA text fallback

## 9. What's needed to add Channel B?

1. Create `channels/<channel_b_id>/channel.yaml` with channel B values
2. Wire the "documented-only" agents to read from config (see table in item 7)
3. Add channel B's logo to `remotion/public/`
4. Add channel B's ElevenLabs voice ID and YouTube credentials to `.env`
5. Run: `python orchestrator.py --channel <channel_b_id>`

Estimated wiring effort: ~2-3 hours for all agent constants.

## 10. Existing episodes preserved?

**YES.** All 5 registered fingerprints remain unchanged:
- week01_ep02, week01_ep03, week09_ep06, week09_ep07, week09_ep08
- All carry `"channel": "ai_bytes"` as before
- `visual_fingerprints.json` untouched

## 11. PyYAML dependency added?

**YES.** `PyYAML>=6.0` added to `requirements.txt`.

## 12. Files created/modified

### New files
| File | Purpose |
|------|---------|
| `channels/srini_on_ai/channel.yaml` | Channel pack — all Srini on AI config |
| `engine/__init__.py` | Engine package marker |
| `engine/channel_config.py` | Typed YAML loader with caching |

### Modified files
| File | Change |
|------|--------|
| `orchestrator.py` | Added `--channel` flag, loads channel config at startup |
| `agents/visual_director_agent.py` | `_channel_fingerprint_key()` resolver; 4 hardcoded `"ai_bytes"` replaced with config lookup |
| `requirements.txt` | Added `PyYAML>=6.0` |

### NOT modified (by design)
- No agent `run()` signatures changed
- No Remotion components changed
- No test files changed
- `visual_fingerprints.json` unchanged
- `.env` unchanged

---

## Architecture After Extraction

```
channels/
  srini_on_ai/
    channel.yaml          ← Channel Pack (values)
engine/
  __init__.py
  channel_config.py       ← Loader (types + caching)
orchestrator.py           ← --channel flag → load_channel()
agents/
  visual_director_agent.py ← reads fingerprint key from config
  (all other agents)       ← constants documented, not yet wired
```

---

## Conclusion

The Channel Pack extraction is complete. `Srini on AI` is now a named,
loadable configuration rather than values scattered across 10+ source files.
Engine v1 behavior is unchanged. Adding a second channel requires creating
another `channel.yaml` and wiring the remaining agent constants — a bounded,
low-risk task with no architectural changes to the engine.
