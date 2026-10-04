# AI Bytes Pipeline — Current State Handoff

> Last updated: 2026-10-04
> Known-good commit: `1e7ab9d` (main)
> Dev environment: Claude Code (cloud container)

---

## Architecture

Python CLI pipeline + Remotion (Node.js) renderer for YouTube Shorts.

```
topics.txt → orchestrator.py
  → script_agent.py    (Claude API → JSON script)
  → voice_agent.py     (ElevenLabs TTS → MP3)
  → visual_agent.py    (Visual Director v4 → storyboard JSON → Remotion render → MP4)
  → assembly_agent.py  (FFmpeg/MoviePy merge voice+visuals, Whisper subtitle sync)
  → publisher_agent.py (YouTube Data API v3 upload)
```

Remotion renders at 1080x1920 (9:16 Shorts), 30fps. Props passed via `--props <json>`.

### Key Files to Read First in Next Session

```
CLAUDE.md                              # Project rules and standards
docs/CURRENT_STATE.md                  # This file
remotion/src/themes.ts                 # Art direction manifest system
remotion/src/AIBytesReel.tsx           # Main composition + scene routing
remotion/src/types.ts                  # Props schema (AIBytesReelProps)
output/week_01/ep02/ep02_props.json    # EP02 approved props (gitignored)
agents/visual_agent.py                 # Visual Director v4
agents/voice_agent.py                  # Voice B settings
```

---

## Visual Director v4

**Status: ACTIVE — current pipeline version.**

Creative visual reasoning pipeline that produces storyboard JSON with per-scene `component`, `beats`, `objects`, `animation`, and `on_screen_text`. Drives Remotion rendering. Does NOT use templates or hardcoded scene sequences.

---

## Art Direction System

**Status: COMPLETE and APPROVED.**

`remotion/src/themes.ts` defines a 14+ dimension `ArtDirection` interface:
- palette (12 color tokens), typography (2 font families), depth (glow, shadow, border-radius)
- overlay, transitions, zones, character colors (chatbot/agent), item colors, split-compare overrides
- `light_or_dark` flag for conditional structural styling

Two manifests ship:
| ID | Name | Episodes |
|----|------|----------|
| `cinematic-dark` | Cinematic Dark | EP00 RAG, EP01 Tokens |
| `bright-workspace` | Bright Workspace — Productivity Editorial | EP02 Agents vs Chatbots |

Flow: `ep_props.json` `"art_direction"` string → `getArtDirection()` → full manifest → passed through `StoryboardReel` → `renderStoryboardScene` → individual components via `artDirection` prop. All components fall back to dark-tech defaults when no art direction is passed.

**No default world (2026-10-04).** `bright-workspace` is EP02-specific. Every new episode's Visual Director plan must contain an explicit `art_direction` decision (registered id + visual_world + rationale); planning fails otherwise and `visual_agent` refuses to render. `getArtDirection()` throws on unknown ids. After approval, run `scripts/approve_episode.py` to persist the art-direction fingerprint to `visual_fingerprints.json`. See `skills/VISUAL_DIRECTOR.md` → Art Director.

---

## Episode Status

### EP00 — RAG (Reference)
- Art direction: `cinematic-dark` (implicit — no `art_direction` field needed)
- Status: Complete reference episode

### EP01 — Tokens v4.1 (Reference)
- Art direction: `cinematic-dark`
- Latest render: `output/week_01/ep01/ep01_visuals_v41_tokens_native.mp4`
- Status: Complete reference episode, token-native visual storytelling

### EP02 — AI Agents vs Chatbots (IN PROGRESS)
- Art direction: `bright-workspace` (set in `ep02_props.json`)
- Latest approved render: `output/week_01/ep02/ep02_visuals_v4_artdir.mp4`
- Visual structure: **APPROVED 2026-10-04** — do not redesign unless a concrete defect is found
- 10 scenes, 45s total, all components consuming bright-workspace manifest
- Voice/audio: NOT YET PRODUCED
- Assembly: NOT YET DONE
- Publishing: NOT YET DONE

**Next phase: voice/audio production and audiovisual polish.**

---

## Components (Remotion)

### EP02 Art-Direction-Wired Components (all 8 scene types + characters)
| Component | Art Direction | Notes |
|-----------|--------------|-------|
| KineticTypoScene | Fully wired | Hook/kinetic text |
| TransformScene | Fully wired | Before/after transforms |
| SplitCompareScene | Fully wired | Side-by-side comparison (beat-driven + legacy modes) |
| AgentTraversalScene | Fully wired | Kanban zones + agent character |
| CircularFlowScene | Fully wired | 4-quadrant reasoning wheel |
| CardStackScene | Fully wired | Stacked task cards |
| TakeawayScene | Fully wired | Scatter-converge word tokens |
| CTAScene | Fully wired | Key takeaway + CTA |
| CharacterUtils | Fully wired | ChatbotCharacter + AgentCharacter with themed state colors |

### Recently Created (v4)
- `AgentTraversalScene.tsx` — kanban-lane agent traversal
- `CircularFlowScene.tsx` — Plan/Act/Observe/Adjust reasoning wheel
- `CharacterUtils.tsx` — reusable ChatbotCharacter and AgentCharacter SVG components

---

## Asset Planner

**Status: EXISTS but scoring must NOT be changed.**
- `agents/asset_planner_agent.py` — scores scenes for external asset needs
- Do NOT modify Asset Planner scoring logic
- Do NOT couple Asset Planner directly to Higgsfield

## Higgsfield

**Status: DO NOT USE.**
- `agents/providers/adapters/higgsfield.py` exists but is frozen
- Decision: Do NOT call Higgsfield again. No new generation expense.
- Any previously cached Higgsfield clip must be reused, never regenerated.

---

## ElevenLabs Voice B Settings

Voice agent: `agents/voice_agent.py`, model `eleven_multilingual_v2`.

Default (Voice B approved baseline):
```
stability=0.42, similarity_boost=0.78, style=0.0, speed=1.05, speaker_boost=True
```

Per-beat tuning guidance is documented in `voice_agent.py` comments (lines 75-91).
Voice ID loaded from `ELEVENLABS_VOICE_ID` in `.env`. Do NOT change Voice B settings.

---

## Tests and QA Guards

### Unit Tests (`tests/`)
- `test_script_agent.py`, `test_voice_agent.py`, `test_visual_agent.py`
- `test_assembly_agent.py`, `test_publisher_agent.py`, `test_orchestrator.py`
- `test_asset_planner.py`

### Pre-Render Checks
- `scripts/pre_render_checks.py` — validates props JSON before Remotion render
- TypeScript: `npx tsc --noEmit` in `remotion/` — zero errors as of `1e7ab9d`

### Render QA
- Keyframe extraction via ffmpeg + visual inspection of 10 scene samples
- Resolution check: 1080x1920, duration check against storyboard sum

---

## Unresolved Issues

1. **SplitCompareScene legacy mode**: Panel sub-component still uses module-level FONT constant instead of `fontFamily` from art direction. Minor — only affects legacy (non-beat-driven) mode.
2. **SplitCompareScene beat-mode verdict border**: Still hardcoded `rgba(255,68,68,0.4)` — should derive from `ad?.palette.danger`.
3. **TransformScene**: `textColor` is declared but unused — agent reported no hardcoded white text to replace. Verify in next visual pass.

---

## Exact Next Recommended Task

**EP02 voice/audio production:**
1. Generate EP02 voice narration using Voice B settings (do NOT call ElevenLabs until ready)
2. Whisper-align narration to visual beats
3. Assembly agent: merge voice + visuals
4. Add music/SFX layer
5. Final audiovisual QA
6. Stop for review before publishing

---

## Environment and Security

- **Dev environment**: Claude Code (cloud container)
- **VPS runtime**: `/root/ai_bytes_pipeline` on Hostinger VPS 187.127.151.27 (Ubuntu 22.04)
- **Production secrets**: `/opt/aibytes/.env` on VPS — NEVER commit `.env`
- **Git-ignored**: `output/`, `.env`, `node_modules/`, rendered MP4s
- **Generated artifacts** (rendered videos, voice MP3s, QA frames) may exist only on VPS or in `output/` locally — they are NOT in Git
- API keys load from `.env` via `python-dotenv` — never hardcode, never log, never print

---

## Standing Constraints (Carry Forward)

- Do NOT publish to YouTube without explicit approval
- Do NOT redesign EP02 visuals — approved baseline locked
- Do NOT call Higgsfield — no new generation expense
- Do NOT change Voice B settings
- Do NOT change Asset Planner scoring
- Do NOT modify RAG or Tokens episodes
- Do NOT expose or commit `.env` or API secrets
- Pipeline must not stop on single episode failure — log error, continue
