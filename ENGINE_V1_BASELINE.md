# AI Bytes Pipeline — Engine v1 Baseline

> Frozen 2026-10-12. Production contract for the Srini on AI channel.
> Do NOT modify production rules without explicit human approval.

---

## Pipeline Stages

```
topics.txt (human-edited, 7 lines)
  → Script Agent (Claude claude-sonnet-4-20250514)
    → Voice Agent (ElevenLabs eleven_multilingual_v2, Voice B)
      → duration gate (55–65s EN, configurable per lang)
        → Visual Director Agent
          → semantic scenes from narration clauses
          → visual beats from scene semantics
          → channel-scoped creative memory (visual_fingerprints.json)
          → cross-episode diversity gate (family Jaccard + distribution + order)
          → intra-episode repetition gate (config similarity + ABA + family concentration)
          → NATIVE / GENERATED routing (visual_mode_router)
          → fal asset generation (when GENERATED selected)
          → scene_composer (primitive-based composition for NATIVE)
        → Remotion render (npx remotion render, 1080×1920, 30fps)
      → Sound Director → Audio Mixer (deterministic)
      → Assembly Agent
        → Whisper transcription → SRT captions
        → FFmpeg mux (visuals + audio)
        → loudness normalization (EBU R128, -14 LUFS target)
        → three-hash check (canonical == storyboard == voice)
        → voice-visual sync check (±2s tolerance)
      → Timeline QA Guard
        → blank-span detection (dark-theme aware)
        → static-scene detection
        → perceptual duplication detection (8×8 grid, contrast-stretch, ≥92% threshold)
      → Human Review
      → Publisher Agent (YouTube Data API v3, explicit approval required)
```

---

## Non-Negotiable Production Rules (EP04–EP08)

### Script Agent
- Output must parse as valid JSON with all required fields
- Narration text is the canonical source of truth for all downstream agents
- Topic interpretation: always through AI/LLM lens ("tokenomics" = AI tokens, not crypto)

### Voice Agent
- Voice B settings are LOCKED — never change voice ID, model, or stability
- MP3 duration must be 55–65 seconds (EN)
- Voice hash written for cache identity tracking

### Visual Director
- Beats emerge from narration semantics via 4-level hierarchy (episode → scene → beat → animation)
- Planning must not conflate scenes with beats
- Adjacent beats must not hard-cut to the same asset
- No repeated humanoid/robot defaults — vary metaphors per episode concept

### Diversity Gates
- **Cross-episode**: compares current plan's component families against most recent same-channel episode
  - Family Jaccard similarity, distribution distance, order similarity
  - Gate fails when composite similarity is HIGH and both episodes are NATIVE-dominant
  - ONE bounded re-plan on failure, not retry loops
- **Intra-episode**: checks within a single storyboard
  - Same component with ≥70% config similarity → flagged
  - A→B→A return pattern at ≥55% family similarity → flagged
  - Family concentration: >2 content scenes from same family → flagged

### Scene Config Similarity (6-factor weighted)
| Factor | Weight |
|--------|--------|
| Component match | 0.30 |
| Scene type | 0.15 |
| Object count similarity | 0.15 |
| Beat count | 0.10 |
| Data structure | 0.15 |
| Animation style | 0.15 |

### NATIVE / GENERATED Routing
- visual_mode_router decides per scene
- NATIVE: Remotion components (scene_composer pipeline)
- GENERATED: fal API with budget controls
- HYBRID quota is never forced — mode chosen by semantic analysis

### Remotion Components (dark-theme contract)
- Background: `#050510` (BG token)
- Accent: `#a78bfa` (ACCENT token)
- Secondary: `#34d399` (ACCENT2 token)
- All components must have sufficient visual presence at 108×192 downscale (timeline QA sampling resolution)
- Structural anchors required for components with thin SVG elements (PipelineScene, SplitCompareScene)
- Fill opacity minimum ~22% (`0x38`) for node backgrounds on dark themes
- Border/stroke width minimum 3px for visibility at downscale

### Assembly Agent
- Canonical narration is the authoritative caption text
- THREE_HASH_CHECK: canonical text hash == storyboard text hash == voice text hash
- VOICE_VISUAL_SYNC: |voice_duration - visual_duration| ≤ 2.0s
- Loudness normalization: EBU R128, target -14 LUFS, TP ≤ -1.0 dBTP
- Output: 1080×1920 MP4, 58–62s duration window (or voice-matched)

### Timeline QA Guard
- Blank-span detection: samples frames at 2fps, 108×192 resolution, dark-theme aware
- Static-scene detection: consecutive frames with <5% pixel change
- Perceptual duplication: 8×8 grid (64 cells), contrast-stretch normalization
  - Maps [min, max] luminance → [0, 255] (skip if spread < 8 levels)
  - Samples 3 frames per scene from middle portion, averages fingerprints
  - Non-adjacent scene pairs flagged at ≥92% similarity threshold
- All three checks must PASS for assembly to succeed

### Publisher Agent
- YouTube video ID must be returned and logged
- Publishing requires explicit human approval — never auto-publish
- Publisher gate validates all upstream checks before allowing upload

---

## Visual Fingerprint Store

**Path:** `output/visual_fingerprints.json`
**Version:** v4.1
**Channel:** `ai_bytes` (Srini on AI)

### Registered Episodes (as of freeze)

| Key | Topic | Art Direction | Approved |
|-----|-------|---------------|----------|
| week01_ep02 | AI Agents vs Chatbots | bright-workspace | 2026-10-06 |
| week01_ep03 | Why AI Hallucinates | cinematic-dark | 2026-10-08 |
| week09_ep06 | How RAG Reduces Hallucinations | bright-workspace | 2026-10-11 |
| week09_ep07 | Function Calling Explained | cinematic-dark | 2026-10-11 |
| week09_ep08 | Context Window Explained | cinematic-dark | 2026-10-12 |

### Art Direction Registry
- `bright-workspace` — bright workspace, productivity editorial, light theme
- `cinematic-dark` — deep void with neon accents, dark theme

---

## Component Family Taxonomy

| Family | Components |
|--------|-----------|
| TYPOGRAPHY | KineticTypoScene |
| FLOW_PIPELINE | FlowScene, PipelineScene, DataFlowScene, CircularFlowScene, AgentTraversalScene |
| DIAGRAM | SketchScene, NetworkBuildScene, HubSpokeScene, LayerRevealScene |
| TRANSFORMATION | TransformScene, BeforeAfterScene |
| COMPARISON | SplitCompareScene |
| SEQUENCE | CardStackScene, ClusterScene, TimelineScene |
| DATA | DataScene, NumberCounterScene |
| DOMAIN | ContextWindowScene, TokenScene, TokenStreamScene |
| GENERATED_EDITORIAL | (fal-generated editorial assets) |
| TAKEAWAY | TakeawayScene |
| CTA | CTAScene |

---

## Security Constraints

- Never expose or commit `.env` or API secrets
- Never hardcode or log FAL_KEY
- Never publish to YouTube without explicit human approval
- Never change Voice B settings
- Never discuss cryptocurrency, crypto token supply, Bitcoin, token vesting, crypto investing
- Do not use "tokenomics" in titles unless explicitly qualified as AI token economics

---

## File Structure (production-critical)

```
agents/
  script_agent.py          # Claude-powered script generation
  voice_agent.py           # ElevenLabs TTS
  visual_director_agent.py # Planning + diversity gates + fingerprinting
  visual_mode_router.py    # NATIVE/GENERATED routing
  visual_agent.py          # Remotion render orchestration
  scene_composer.py        # Primitive-based NATIVE composition
  fal_asset_agent.py       # GENERATED asset pipeline (fal API)
  assembly_agent.py        # FFmpeg mux + loudness norm + validation
  publisher_agent.py       # YouTube upload with approval gate
  storyboard_qa.py         # Storyboard structural validation
timeline_qa_guard.py       # Post-render QA (blank/static/duplication)
orchestrator.py            # Master pipeline runner
output/
  visual_fingerprints.json # Channel-scoped creative memory
  week_NN/ep_NN/           # Per-episode artifacts
remotion/
  src/components/           # Remotion scene components
```

---

## Engine v1 Freeze Date

**2026-10-12** — All production hardening through EP08 is complete.
No architectural changes beyond this point without explicit human approval.
