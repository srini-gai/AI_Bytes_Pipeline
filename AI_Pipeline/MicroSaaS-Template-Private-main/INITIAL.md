# INITIAL.md — AI Bytes Pipeline

> Product definition for Claude Code. Run `/generate-prp INITIAL.md` after filling this in.

---

## PRODUCT

**Name:** AI Bytes Pipeline

**Tagline:** Automated YouTube Shorts factory — one topics.txt, seven reels live every week.

**Description:**
A fully automated content production and publishing pipeline that takes a weekly list of 7 AI concept topics and produces 7 complete YouTube Shorts — each with AI-generated script, ElevenLabs voiceover, Remotion motion video, FFmpeg assembly with burned-in captions, and auto-scheduled YouTube upload. No manual steps after topics.txt is saved. Runs on Hostinger VPS (187.127.151.27).

**Type:** Local automation tool + VPS pipeline. No SaaS frontend. No payments. No auth.

---

## PROBLEM IT SOLVES

Content creators building a daily AI education channel (AI Bytes) need to produce 7 reels every week consistently. Manual production takes 2+ hours per reel. This pipeline reduces that to 5 minutes of human input — edit topics.txt, run orchestrator, done.

---

## TECH STACK

### Backend / Pipeline
- **Language:** Python 3.11
- **Orchestrator:** orchestrator.py — reads topics.txt, runs all agents per topic sequentially
- **Task queue:** None needed — sequential execution per topic is sufficient
- **Logging:** Python logging → orchestrator.log

### Agent Stack
| Agent | File | Tool / API |
|-------|------|-----------|
| Script Agent | agents/script_agent.py | Anthropic Claude API (claude-sonnet-4-20250514) |
| Voice Agent | agents/voice_agent.py | ElevenLabs v1 TTS API |
| Visual Agent | agents/visual_agent.py | Remotion (Node.js, headless render) |
| Assembly Agent | agents/assembly_agent.py | FFmpeg + MoviePy + OpenAI Whisper |
| Publisher Agent | agents/publisher_agent.py | YouTube Data API v3 (OAuth2) |

### Database
- **None** — file-based output only
- Output stored in `/output/week_NN/ep_NN_*/` folder structure

### Frontend
- **None** — CLI tool only
- Input: `topics.txt`
- Output: MP4 files + YouTube upload confirmation logs

### Deployment
- **VPS:** Hostinger KVM2 — 187.127.151.27
- **OS:** Ubuntu 22.04
- **Process manager:** systemd service or cron job (Sunday 6am IST)
- **Node.js:** Required for Remotion rendering
- **Python:** 3.11 via venv

### External APIs
- `ANTHROPIC_API_KEY` — Claude API for script generation
- `ELEVENLABS_API_KEY` — ElevenLabs TTS
- `ELEVENLABS_VOICE_ID` — fixed voice ID (brand consistency)
- `YOUTUBE_CLIENT_ID` — OAuth2
- `YOUTUBE_CLIENT_SECRET` — OAuth2
- `YOUTUBE_REFRESH_TOKEN` — pre-authorised token

### Payments
- **None** — personal tool, no monetisation layer

---

## PROJECT STRUCTURE

```
aibytes-pipeline/
├── CLAUDE.md                    # Claude Code instructions
├── INITIAL.md                   # This file
├── topics.txt                   # 7 lines, one topic per line — human edits weekly
├── orchestrator.py              # Master runner — loops topics, calls all agents
├── orchestrator.log             # Auto-generated run log
├── .env                         # All API keys
├── requirements.txt
├── package.json                 # Remotion dependency
│
├── agents/
│   ├── script_agent.py          # Topic → structured JSON script
│   ├── voice_agent.py           # Script JSON → MP3 via ElevenLabs
│   ├── visual_agent.py          # Script JSON → MP4 via Remotion
│   ├── assembly_agent.py        # MP3 + MP4 → final 1080x1920 MP4 with captions
│   └── publisher_agent.py       # Final MP4 → YouTube scheduled upload
│
├── remotion/
│   ├── src/
│   │   ├── Root.tsx             # Remotion composition root
│   │   ├── AIBytesReel.tsx      # Main reel component (dark theme, particles, animations)
│   │   └── components/
│   │       ├── HookScene.tsx
│   │       ├── ConceptScene.tsx
│   │       ├── SlideScene.tsx
│   │       └── CTAScene.tsx
│   └── package.json
│
├── output/
│   └── week_01/
│       ├── ep01/
│       │   ├── ep01_script.json
│       │   ├── ep01_voice.mp3
│       │   ├── ep01_visuals.mp4
│       │   ├── ep01_captions.srt
│       │   └── ep01_final.mp4
│       └── ep02/ ...
│
└── skills/
    ├── CONTENT.md               # AI Bytes content rules, hook formulas, script patterns
    ├── PIPELINE.md              # Agent orchestration rules, retry logic, error handling
    └── YOUTUBE.md               # YouTube API patterns, scheduling, metadata rules
```

---

## AGENTS — DETAILED SPEC

### Agent 1 — Script Agent (`script_agent.py`)
**Input:** topic string (e.g. "What is RAG?")
**Output:** structured JSON saved to `ep_NN_script.json`

```json
{
  "episode": "01",
  "topic": "What is RAG?",
  "title": "This Is How AI Reads YOUR Documents",
  "hook": "Your AI is lying to you. Here is why.",
  "concept": "Retrieval-Augmented Generation",
  "slides": [
    {"icon": "🧠", "heading": "The Problem", "body": "LLMs only know training data..."},
    {"icon": "📚", "heading": "The Fix", "body": "RAG fetches your docs at query time..."},
    {"icon": "⚡", "heading": "How It Works", "body": "Query → Embed → Search → Retrieve → Answer"},
    {"icon": "🎯", "heading": "Use Cases", "body": "Support bots, doc Q&A, internal KB..."}
  ],
  "voiceover": "Full 130-word narration script ready for ElevenLabs...",
  "takeaway": "RAG = LLM + Your Data. No fine-tuning needed.",
  "tags": "#AIBytes #RAG #LLM #GenerativeAI",
  "youtube_title": "This Is How AI Reads YOUR Documents 🧠 #Shorts",
  "youtube_description": "Full description with hashtags...",
  "scheduled_publish": "2026-05-12T02:30:00Z"
}
```

**Rules:**
- Hook must be under 8 words, creates curiosity or shock
- Voiceover must be 120–140 words (fits 60 seconds at 0.95 speed)
- Always output valid JSON, no markdown wrapping
- Retry up to 3 times on malformed JSON

---

### Agent 2 — Voice Agent (`voice_agent.py`)
**Input:** `ep_NN_script.json` → reads `voiceover` field
**Output:** `ep_NN_voice.mp3`

**Rules:**
- ElevenLabs model: `eleven_multilingual_v2`
- Voice ID: hardcoded from `ELEVENLABS_VOICE_ID` env var — never changes
- Stability: 0.5, Similarity boost: 0.75, Speed: 0.95
- Retry 3 times with exponential backoff on API error
- Validate MP3 duration is between 55–65 seconds before proceeding

---

### Agent 3 — Visual Agent (`visual_agent.py`)
**Input:** `ep_NN_script.json`
**Output:** `ep_NN_visuals.mp4` (1080x1920, 60 seconds, 30fps, no audio)

**Rules:**
- Uses Remotion to render `AIBytesReel` composition
- Passes script JSON as props to Remotion component
- Dark theme: background `#050510`, accent `#a78bfa`, secondary `#34d399`
- Scene timing matches voiceover pacing from script JSON
- Renders headlessly via `npx remotion render` CLI command
- Output must be exactly 60 seconds

**Remotion scenes:**
| Scene | Duration | Content |
|-------|----------|---------|
| Hook | 0–7s | Word-by-word text reveal, particle bg |
| Concept | 7–15s | Glowing orb, concept title animation |
| Slides 1–4 | 15–50s | Each slide 8–9s, slide-in transitions |
| CTA | 50–60s | Takeaway card + follow button |

---

### Agent 4 — Assembly Agent (`assembly_agent.py`)
**Input:** `ep_NN_voice.mp3` + `ep_NN_visuals.mp4`
**Output:** `ep_NN_final.mp4` (1080x1920, 30fps, with burned-in captions)

**Steps:**
1. Transcribe MP3 → SRT using OpenAI Whisper (local, `base` model)
2. Merge video + audio via FFmpeg
3. Burn SRT captions into video (font: Montserrat Bold, size 18, white + black outline)
4. Validate output: resolution 1080x1920, duration 58–62s, has audio track
5. Save final MP4

**FFmpeg command pattern:**
```bash
ffmpeg -i ep_visuals.mp4 -i ep_voice.mp3 \
  -vf "subtitles=ep_captions.srt:force_style='FontName=Montserrat,FontSize=18,
       PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'" \
  -c:v libx264 -c:a aac -shortest ep_final.mp4
```

---

### Agent 5 — Publisher Agent (`publisher_agent.py`)
**Input:** `ep_NN_final.mp4` + `ep_NN_script.json`
**Output:** YouTube video ID + scheduled publish confirmation

**Rules:**
- Uses YouTube Data API v3
- OAuth2 with pre-authorised refresh token (no browser flow needed on VPS)
- Upload as `#Shorts` — title must end with `#Shorts`
- Set `privacyStatus: "private"` then schedule via `publishAt`
- Schedule: one reel per day, 8:00am IST (02:30 UTC), starting next Monday
- Tags pulled from script JSON
- Log video ID and scheduled time to orchestrator.log

---

## ORCHESTRATOR SPEC (`orchestrator.py`)

**Input:** `topics.txt` — 7 lines, one topic per line
**Flags:**
- `--dry-run` — runs script + voice agents only, skips visual + assembly + publisher
- `--week N` — manually set week number (default: auto-detect from date)
- `--episode N` — run only a single episode number

**Flow:**
```
read topics.txt → split into list of 7
create output/week_NN/ folder
for each topic:
    run script_agent → validate JSON
    run voice_agent → validate MP3 duration
    run visual_agent → validate MP4
    run assembly_agent → validate final MP4
    run publisher_agent → log video ID
    log success + YouTube URL
log total: X/7 episodes published
```

**Error handling:**
- If any agent fails → log error → skip to next episode (don't stop pipeline)
- Retry failed episodes at end of run
- Send summary to orchestrator.log

---

## CONTENT RULES (for script_agent)

### Hook formulas (rotate weekly):
1. "Your [thing] is [surprising claim]. Here is why."
2. "This Is How You [desirable outcome]"
3. "[Number] seconds to understand [complex concept]"
4. "Stop [wrong thing]. Do this instead."
5. "What nobody tells you about [topic]"

### Topic bank — first 7 weeks:
```
Week 1: What is RAG?, Prompt Engineering, AI Agents, Vector Databases, Fine-tuning vs RAG, Chain of Thought, Second Brain
Week 2: MCP Protocol, LangChain, Embeddings explained, Hallucination, Temperature parameter, Few-shot prompting, LLM evaluation
Week 3: Claude vs GPT vs Gemini, Local LLMs with Ollama, AI for founders, Cursor AI, Vibe coding, AI observability, $0 AI stack
```

---

## ENVIRONMENT VARIABLES

```env
# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# ElevenLabs
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...

# YouTube OAuth2
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REFRESH_TOKEN=...
YOUTUBE_CHANNEL_ID=...

# Pipeline config
OUTPUT_BASE_PATH=/home/aibytes/output
PUBLISH_TIME_UTC=02:30
START_PUBLISH_DATE=2026-05-12
```

---

## CUSTOM SKILLS TO ADD (from claude-skills)

Copy these into `skills/` folder from your private claude-skills repo:

| Skill | Source path | Why |
|-------|-------------|-----|
| content-creator | `marketing-skill/content-creator/` | Script hook formulas, content frameworks |
| senior-architect | `engineering-team/senior-architect/` | Pipeline architecture review |
| python-expert | `engineering-team/` | Python best practices for agents |

---

## BUILD PHASES

| Phase | What gets built | Claude Code prompt trigger |
|-------|----------------|---------------------------|
| 1 | Scaffold + .env + requirements.txt + topics.txt | "Build Phase 1: project scaffold" |
| 2 | script_agent.py — Claude API → JSON output | "Build Phase 2: script agent" |
| 3 | voice_agent.py — ElevenLabs → MP3 | "Build Phase 3: voice agent" |
| 4 | Remotion setup + AIBytesReel.tsx component | "Build Phase 4: Remotion visual component" |
| 5 | visual_agent.py — Remotion headless render → MP4 | "Build Phase 5: visual agent" |
| 6 | assembly_agent.py — Whisper + FFmpeg + captions | "Build Phase 6: assembly agent" |
| 7 | publisher_agent.py — YouTube API v3 upload + schedule | "Build Phase 7: publisher agent" |
| 8 | orchestrator.py — full pipeline + --dry-run flag + logging | "Build Phase 8: orchestrator" |
| 9 | VPS deployment — systemd service + cron Sunday 6am IST | "Build Phase 9: VPS deploy" |

---

## ACCEPTANCE CRITERIA

- [ ] `python orchestrator.py --dry-run` generates 7 scripts + 7 MP3s without errors
- [ ] `python orchestrator.py` produces 7 final MP4s (1080x1920, ~60s each)
- [ ] All 7 reels uploaded to YouTube as private with correct scheduled times
- [ ] orchestrator.log shows success for all 7 episodes
- [ ] Full run completes in under 45 minutes on VPS
- [ ] `--dry-run` flag skips visual + assembly + publisher safely
- [ ] Failed episodes are retried and logged, pipeline does not crash

---

## WHAT THIS IS NOT

- Not a SaaS product — no frontend UI, no auth, no payments
- Not a real-time system — batch job runs once per week
- Not a multi-user tool — personal pipeline for AI Bytes channel only

---

*AI Bytes Pipeline — One topics.txt. Seven reels. Every Sunday.*
