# PRP: AI Bytes Pipeline

> Implementation blueprint for sequential agent build — one topics.txt, seven reels live every week.

---

## METADATA

| Field | Value |
|-------|-------|
| **Product** | AI Bytes Pipeline |
| **Type** | Local automation tool + VPS pipeline |
| **Version** | 1.0 |
| **Created** | 2026-05-10 |
| **Complexity** | High |
| **Target VPS** | Hostinger KVM2 — 187.127.151.27 (Ubuntu 22.04) |
| **Schedule** | Cron — Sunday 6:00 AM IST (00:30 UTC) |

---

## PRODUCT OVERVIEW

**Description:** A fully automated content production and publishing pipeline. The operator edits `topics.txt` with 7 AI concept topics once per week. The pipeline produces 7 complete YouTube Shorts — AI-generated script → ElevenLabs voiceover → Remotion motion video → FFmpeg captioned assembly → auto-scheduled YouTube upload. Zero manual steps after `topics.txt` is saved.

**Value Proposition:** Reduces 14+ hours of manual video production per week to 5 minutes of human input + ~45 minutes of automated pipeline execution.

**MVP Scope:**
- [ ] `orchestrator.py` reads `topics.txt` and drives all agents sequentially
- [ ] `script_agent.py` generates structured JSON scripts via Claude API
- [ ] `voice_agent.py` produces 60-second MP3s via ElevenLabs TTS
- [ ] `visual_agent.py` renders 1080x1920 silent MP4s via Remotion (headless)
- [ ] `assembly_agent.py` transcribes, merges audio+video, burns in captions via FFmpeg
- [ ] `publisher_agent.py` uploads to YouTube and schedules publish at 8:00 AM IST
- [ ] `--dry-run` flag skips visual + assembly + publisher
- [ ] Full run completes in under 45 minutes on VPS
- [ ] Failed episodes are logged and retried; pipeline never crashes

---

## TECH STACK

| Layer | Technology | Skill Reference |
|-------|------------|-----------------|
| Orchestration | Python 3.11 — `orchestrator.py` | `skills/senior-architect` |
| Script generation | Anthropic Claude API (`claude-sonnet-4-20250514`) | `skills/content-creator` |
| Voice synthesis | ElevenLabs TTS v2 (`eleven_multilingual_v2`) | — |
| Video rendering | Remotion (Node.js, headless `npx remotion render`) | — |
| Video assembly | FFmpeg + MoviePy + OpenAI Whisper (local, `base` model) | `skills/senior-backend` |
| Publishing | YouTube Data API v3 (OAuth2, pre-authorised refresh token) | — |
| Config | `python-dotenv` → `.env` | — |
| Logging | Python `logging` → `orchestrator.log` | — |
| Deployment | systemd service + cron on Ubuntu 22.04 | — |
| Content strategy | Hook formulas, script patterns | `skills/video-content-strategist` |

**No database. No frontend. No auth layer. No payments.**

---

## PIPELINE ARCHITECTURE

```
topics.txt (7 lines)
        │
        ▼
orchestrator.py ──► for each topic (1–7):
        │
        ├── script_agent.py   ──► ep_NN_script.json
        │         Claude API → structured JSON
        │
        ├── voice_agent.py    ──► ep_NN_voice.mp3
        │         ElevenLabs → 60s MP3 @ 0.95 speed
        │
        ├── visual_agent.py   ──► ep_NN_visuals.mp4
        │         Remotion headless → 1080x1920 silent MP4
        │
        ├── assembly_agent.py ──► ep_NN_final.mp4
        │         Whisper → SRT → FFmpeg merge + caption burn
        │
        └── publisher_agent.py ──► YouTube video ID + schedule
                  YouTube Data API v3 → scheduled 8AM IST

output/week_NN/ep_NN/
    ├── ep_NN_script.json
    ├── ep_NN_voice.mp3
    ├── ep_NN_visuals.mp4
    ├── ep_NN_captions.srt
    └── ep_NN_final.mp4
```

---

## FILE STRUCTURE

```
aibytes-pipeline/
├── CLAUDE.md
├── INITIAL.md
├── topics.txt                    # 7 lines — human edits weekly
├── orchestrator.py               # Master runner
├── orchestrator.log              # Auto-generated
├── .env                          # All secrets
├── requirements.txt
├── package.json                  # Remotion dep
│
├── agents/
│   ├── script_agent.py
│   ├── voice_agent.py
│   ├── visual_agent.py
│   ├── assembly_agent.py
│   └── publisher_agent.py
│
├── remotion/
│   ├── package.json
│   └── src/
│       ├── Root.tsx
│       ├── AIBytesReel.tsx
│       └── components/
│           ├── HookScene.tsx
│           ├── ConceptScene.tsx
│           ├── SlideScene.tsx
│           └── CTAScene.tsx
│
├── output/
│   └── week_NN/
│       └── ep_NN/
│           ├── ep_NN_script.json
│           ├── ep_NN_voice.mp3
│           ├── ep_NN_visuals.mp4
│           ├── ep_NN_captions.srt
│           └── ep_NN_final.mp4
│
└── skills/
    ├── content-creator
    ├── senior-architect
    ├── senior-backend
    └── video-content-strategist
```

---

## AGENTS — FULL SPEC

### Agent 0 — Orchestrator (`orchestrator.py`)

**Skill:** `skills/senior-architect`

**Input:** `topics.txt` — 7 lines, one topic per line

**CLI flags:**
| Flag | Behaviour |
|------|-----------|
| `--dry-run` | Runs script + voice agents only; skips visual, assembly, publisher |
| `--week N` | Override week number (default: auto-detect from date) |
| `--episode N` | Run only a single episode number |

**Flow:**
```
read topics.txt → validate 7 lines
create output/week_NN/ folder
for each topic (i, topic):
    ep = i + 1
    script_agent.run(ep, week, topic)  → validate JSON
    voice_agent.run(ep, week, script)  → validate MP3 55–65s
    [if not --dry-run]:
        visual_agent.run(ep, week, script) → validate MP4 60s
        assembly_agent.run(ep, week)       → validate final MP4
        publisher_agent.run(ep, week)      → log video ID
    log success
retry any failed episodes
log total: X/7 episodes published
```

**Error handling:** Failed episode → log error → skip to next → retry at end. Pipeline never crashes on single episode failure.

**Agent signature (all agents follow this):**
```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def run(episode: int, week: int, input_data: dict) -> dict:
    """Standard agent signature."""
    try:
        # work here
        logger.info(f"EP{episode:02d} — agent completed")
        return {"success": True, "output_path": str(path)}
    except Exception as e:
        logger.error(f"EP{episode:02d} — agent failed: {e}")
        raise
```

---

### Agent 1 — Script Agent (`agents/script_agent.py`)

**Skill:** `skills/content-creator`, `skills/video-content-strategist`

**Input:** `topic: str` (e.g. `"What is RAG?"`)
**Output:** `output/week_NN/ep_NN/ep_NN_script.json`

**Claude API config:**
- Model: `claude-sonnet-4-20250514`
- Max retries: 3 (exponential backoff)
- Parse: `json.loads()` — retry on `JSONDecodeError`

**Output schema:**
```json
{
  "episode": "01",
  "topic": "What is RAG?",
  "title": "This Is How AI Reads YOUR Documents",
  "hook": "Your AI is lying to you. Here is why.",
  "concept": "Retrieval-Augmented Generation",
  "slides": [
    {"icon": "🧠", "heading": "The Problem", "body": "LLMs only know training data..."},
    {"icon": "📚", "heading": "The Fix",     "body": "RAG fetches your docs at query time..."},
    {"icon": "⚡", "heading": "How It Works","body": "Query → Embed → Search → Retrieve → Answer"},
    {"icon": "🎯", "heading": "Use Cases",   "body": "Support bots, doc Q&A, internal KB..."}
  ],
  "voiceover": "Full 130-word narration script ready for ElevenLabs...",
  "takeaway": "RAG = LLM + Your Data. No fine-tuning needed.",
  "tags": "#AIBytes #RAG #LLM #GenerativeAI",
  "youtube_title": "This Is How AI Reads YOUR Documents 🧠 #Shorts",
  "youtube_description": "Full description with hashtags...",
  "scheduled_publish": "2026-05-12T02:30:00Z"
}
```

**Content rules:**
| Rule | Constraint |
|------|-----------|
| Hook | Under 8 words, creates curiosity or shock |
| Voiceover | 120–140 words (fits 60 seconds at 0.95 speed) |
| Slides | Exactly 4 slides |
| Output | Valid JSON only — no markdown wrapping |
| YouTube title | Must end with `#Shorts` |
| Retry | 3 times on malformed JSON |

**Hook formulas (rotate weekly):**
1. `"Your [thing] is [surprising claim]. Here is why."`
2. `"This Is How You [desirable outcome]"`
3. `"[Number] seconds to understand [complex concept]"`
4. `"Stop [wrong thing]. Do this instead."`
5. `"What nobody tells you about [topic]"`

---

### Agent 2 — Voice Agent (`agents/voice_agent.py`)

**Input:** `ep_NN_script.json` → reads `voiceover` field
**Output:** `ep_NN_voice.mp3`

**ElevenLabs config:**
| Parameter | Value |
|-----------|-------|
| Model | `eleven_multilingual_v2` |
| Voice ID | `ELEVENLABS_VOICE_ID` env var (never hardcoded) |
| Stability | `0.5` |
| Similarity boost | `0.75` |
| Speed | `0.95` |
| Retry | 3 times, exponential backoff |

**Validation:** MP3 duration must be 55–65 seconds before returning success. Raise `ValueError` if outside range.

---

### Agent 3 — Visual Agent (`agents/visual_agent.py`)

**Input:** `ep_NN_script.json`
**Output:** `ep_NN_visuals.mp4` (1080×1920, 60 seconds, 30fps, no audio)

**Remotion config:**
- Render command: `npx remotion render AIBytesReel ep_NN_visuals.mp4 --props='<json>'`
- Theme: `background #050510`, `accent #a78bfa`, `secondary #34d399`
- Output must be exactly 60 seconds

**Scene timing:**
| Scene | Time | Content |
|-------|------|---------|
| `HookScene` | 0–7s | Word-by-word text reveal, particle background |
| `ConceptScene` | 7–15s | Glowing orb, concept title animation |
| `SlideScene ×4` | 15–50s | Each slide 8–9s, slide-in transitions |
| `CTAScene` | 50–60s | Takeaway card + follow button |

**Remotion components:**
| Component | File | Role |
|-----------|------|------|
| Root | `remotion/src/Root.tsx` | Composition registration |
| AIBytesReel | `remotion/src/AIBytesReel.tsx` | Main composition, dark theme, particles |
| HookScene | `components/HookScene.tsx` | Word-by-word reveal |
| ConceptScene | `components/ConceptScene.tsx` | Glowing orb + title |
| SlideScene | `components/SlideScene.tsx` | Icon + heading + body card |
| CTAScene | `components/CTAScene.tsx` | Takeaway + follow CTA |

**Rules:** No `any` type in TypeScript. Props typed from script JSON schema.

---

### Agent 4 — Assembly Agent (`agents/assembly_agent.py`)

**Input:** `ep_NN_voice.mp3` + `ep_NN_visuals.mp4`
**Output:** `ep_NN_final.mp4` (1080×1920, 30fps, burned-in captions, audio track)

**Steps:**
1. Transcribe MP3 → SRT using OpenAI Whisper local (`base` model)
2. Save SRT to `ep_NN_captions.srt`
3. Merge video + audio + burn captions via FFmpeg:

```bash
ffmpeg -i ep_NN_visuals.mp4 -i ep_NN_voice.mp3 \
  -vf "subtitles=ep_NN_captions.srt:force_style='FontName=Montserrat,FontSize=18,\
       PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'" \
  -c:v libx264 -c:a aac -shortest ep_NN_final.mp4
```

**Output validation:**
| Check | Constraint |
|-------|-----------|
| Resolution | 1080×1920 |
| Duration | 58–62 seconds |
| Audio track | Must be present |
| File size | Must be > 0 bytes |

---

### Agent 5 — Publisher Agent (`agents/publisher_agent.py`)

**Input:** `ep_NN_final.mp4` + `ep_NN_script.json`
**Output:** YouTube video ID + scheduled publish confirmation logged to `orchestrator.log`

**YouTube API config:**
- API: YouTube Data API v3
- Auth: OAuth2 refresh token (no browser flow on VPS)
- Upload privacy: `"private"` then schedule via `publishAt`
- One reel per day at 08:00 IST (02:30 UTC), starting next Monday from run date

**Metadata from script JSON:**
| YouTube field | Source |
|--------------|--------|
| Title | `youtube_title` (must end with `#Shorts`) |
| Description | `youtube_description` |
| Tags | `tags` (split by space) |
| Scheduled time | `scheduled_publish` |
| Category | `22` (People & Blogs) |

**Log format:**
```
EP01 — YouTube ID: xXxXxXxXxXx — Scheduled: 2026-05-12T02:30:00Z
```

---

## PHASE EXECUTION PLAN

### Phase 1 — Project Scaffold
**Prompt:** `"Build Phase 1: project scaffold"`

**Deliverables:**
- `topics.txt` — 7 example topics (Week 1 bank)
- `.env` — all keys with placeholder values
- `requirements.txt` — anthropic, elevenlabs, moviepy, openai-whisper, google-api-python-client, google-auth-oauthlib, python-dotenv
- `package.json` — Remotion dependency
- `agents/` — empty `__init__.py` files
- `output/` — `.gitkeep`
- `skills/` — existing symlinks intact

**Validation:**
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
npm install
python -c "import anthropic, elevenlabs, moviepy, whisper; print('OK')"
```

---

### Phase 2 — Script Agent
**Prompt:** `"Build Phase 2: script agent"`

**Deliverables:** `agents/script_agent.py`

**Validation:**
```bash
python -c "from agents.script_agent import run; r = run(1, 1, 'What is RAG?'); print(r)"
# Must print valid dict with success=True and script.json path
# Inspect output/week_01/ep_01/ep_01_script.json — validate JSON schema
```

---

### Phase 3 — Voice Agent
**Prompt:** `"Build Phase 3: voice agent"`

**Deliverables:** `agents/voice_agent.py`

**Validation:**
```bash
python -c "from agents.voice_agent import run; r = run(1, 1, {}); print(r)"
# ep_01_voice.mp3 must exist and be 55–65 seconds
```

---

### Phase 4 — Remotion Visual Component
**Prompt:** `"Build Phase 4: Remotion visual component"`

**Deliverables:**
- `remotion/src/Root.tsx`
- `remotion/src/AIBytesReel.tsx`
- `remotion/src/components/HookScene.tsx`
- `remotion/src/components/ConceptScene.tsx`
- `remotion/src/components/SlideScene.tsx`
- `remotion/src/components/CTAScene.tsx`
- `remotion/package.json`

**Validation:**
```bash
cd remotion && npm install
npx remotion studio   # opens preview — verify dark theme renders
```

---

### Phase 5 — Visual Agent
**Prompt:** `"Build Phase 5: visual agent"`

**Deliverables:** `agents/visual_agent.py`

**Validation:**
```bash
python -c "from agents.visual_agent import run; r = run(1, 1, {}); print(r)"
# ep_01_visuals.mp4 must exist, be 1080x1920, and 60 seconds
ffprobe output/week_01/ep_01/ep_01_visuals.mp4
```

---

### Phase 6 — Assembly Agent
**Prompt:** `"Build Phase 6: assembly agent"`

**Deliverables:** `agents/assembly_agent.py`

**Validation:**
```bash
python -c "from agents.assembly_agent import run; r = run(1, 1, {}); print(r)"
# ep_01_final.mp4 must exist, be 1080x1920, 58–62s, with audio
ffprobe output/week_01/ep_01/ep_01_final.mp4
```

---

### Phase 7 — Publisher Agent
**Prompt:** `"Build Phase 7: publisher agent"`

**Deliverables:** `agents/publisher_agent.py`

**Validation:**
```bash
python -c "from agents.publisher_agent import run; r = run(1, 1, {}); print(r)"
# Must log video ID and scheduled time to orchestrator.log
# Verify in YouTube Studio → Content → Scheduled
```

---

### Phase 8 — Orchestrator
**Prompt:** `"Build Phase 8: orchestrator"`

**Deliverables:** `orchestrator.py`

**Validation:**
```bash
# Dry run — scripts + voice only
python orchestrator.py --dry-run --week 1

# Full run — all agents
python orchestrator.py --week 1

# Single episode test
python orchestrator.py --episode 1 --week 1

# Verify log
cat orchestrator.log | grep "EP0"
# Expect: 7 success lines
```

---

### Phase 9 — VPS Deployment
**Prompt:** `"Build Phase 9: VPS deploy"`

**Deliverables:**
- `deploy/aibytes.service` — systemd unit file
- `deploy/setup.sh` — VPS bootstrap script (Python, Node.js, FFmpeg, Whisper install)
- `deploy/deploy.sh` — rsync + restart script

**Validation:**
```bash
# On VPS
sudo systemctl status aibytes
# Verify cron fires Sunday 6:00 AM IST:
crontab -l | grep aibytes
```

---

## VALIDATION GATES

| Gate | Commands | Pass Condition |
|------|----------|---------------|
| **G1 — Scaffold** | `pip install -r requirements.txt && npm install` | No errors |
| **G2 — Script** | `python orchestrator.py --dry-run --episode 1` | `ep_01_script.json` valid JSON |
| **G3 — Voice** | `python orchestrator.py --dry-run --episode 1` | `ep_01_voice.mp3` 55–65s |
| **G4 — Remotion** | `npx remotion studio` | Preview renders dark theme |
| **G5 — Visual** | `python orchestrator.py --episode 1` | `ep_01_visuals.mp4` 1080×1920, 60s |
| **G6 — Assembly** | `python orchestrator.py --episode 1` | `ep_01_final.mp4` 1080×1920, 58–62s, audio |
| **G7 — Publisher** | `python orchestrator.py --episode 1` | YouTube video ID in `orchestrator.log` |
| **G8 — Full run** | `python orchestrator.py --dry-run` | 7/7 scripts + MP3s, no errors |
| **G9 — Full run** | `python orchestrator.py` | 7/7 final MP4s, 7 YouTube IDs in log |
| **Final** | Check `orchestrator.log` + YouTube Studio | All 7 scheduled at correct times |

---

## CONTENT STRATEGY

**Topic bank — first 3 weeks:**

| Week | Topics |
|------|--------|
| 1 | What is RAG?, Prompt Engineering, AI Agents, Vector Databases, Fine-tuning vs RAG, Chain of Thought, Second Brain |
| 2 | MCP Protocol, LangChain, Embeddings explained, Hallucination, Temperature parameter, Few-shot prompting, LLM evaluation |
| 3 | Claude vs GPT vs Gemini, Local LLMs with Ollama, AI for founders, Cursor AI, Vibe coding, AI observability, $0 AI stack |

**Hook formulas (rotate weekly):**
```
1. "Your [thing] is [surprising claim]. Here is why."
2. "This Is How You [desirable outcome]"
3. "[Number] seconds to understand [complex concept]"
4. "Stop [wrong thing]. Do this instead."
5. "What nobody tells you about [topic]"
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
OUTPUT_BASE_PATH=./output
PUBLISH_TIME_UTC=02:30
START_PUBLISH_DATE=2026-05-12
```

---

## CODE STANDARDS (enforced across all agents)

| Rule | Requirement |
|------|------------|
| Types | Type hints on every function signature |
| Logging | `logging` module only — no `print()` |
| Secrets | All secrets from `.env` via `python-dotenv` |
| Retries | 3 retries + exponential backoff on every API call |
| Validation | Validate output before passing to next agent |
| Failure | Log error and raise — orchestrator handles skip/retry |
| TypeScript | No `any` type in Remotion components |

---

## ACCEPTANCE CRITERIA

- [ ] `python orchestrator.py --dry-run` generates 7 scripts + 7 MP3s without errors
- [ ] `python orchestrator.py` produces 7 final MP4s (1080×1920, ~60s each)
- [ ] All 7 reels uploaded to YouTube as private with correct scheduled times (8:00 AM IST, Mon–Sun)
- [ ] `orchestrator.log` shows success for all 7 episodes
- [ ] Full run completes in under 45 minutes on VPS
- [ ] `--dry-run` skips visual + assembly + publisher safely
- [ ] `--episode N` runs a single episode in isolation
- [ ] Failed episodes are retried and logged — pipeline does not crash

---

## WHAT THIS IS NOT

- Not a SaaS — no frontend, no auth, no payments, no user accounts
- Not real-time — batch job runs once per week (Sunday 6 AM IST)
- Not multi-user — personal pipeline for AI Bytes channel only

---

## NEXT STEP

Start building phase by phase:

```
"Build Phase 1: project scaffold"
"Build Phase 2: script agent"
"Build Phase 3: voice agent"
"Build Phase 4: Remotion visual component"
"Build Phase 5: visual agent"
"Build Phase 6: assembly agent"
"Build Phase 7: publisher agent"
"Build Phase 8: orchestrator"
"Build Phase 9: VPS deploy"
```

Or run a full dry-run after Phase 3:
```
/execute-prp PRPs/aibytes-pipeline-prp.md
```

---

*AI Bytes Pipeline — One topics.txt. Seven reels. Every Sunday.*
