# CLAUDE.md — AI Bytes Pipeline

> Rules Claude follows in every conversation for this project.

---

## What This Project Is

A Python CLI pipeline that reads `topics.txt` and produces 7 YouTube Shorts automatically.
NO frontend. NO database. NO auth. NO payments.
Pure Python agents + external APIs + FFmpeg + Remotion.

---

## Tech Stack

- **Language:** Python 3.11
- **Script generation:** Anthropic Claude API (`claude-sonnet-4-20250514`)
- **Voice:** ElevenLabs TTS API (`eleven_multilingual_v2`)
- **Video rendering:** Remotion (Node.js, headless `npx remotion render`)
- **Assembly:** FFmpeg + MoviePy + OpenAI Whisper (local, `base` model)
- **Publishing:** YouTube Data API v3 (OAuth2 refresh token)
- **Deployment:** Hostinger VPS — 187.127.151.27 (Ubuntu 22.04)

---

## Project Structure

```
aibytes-pipeline/
├── orchestrator.py        # Master runner — loops topics, calls all agents
├── topics.txt             # 7 topics, one per line — human edits weekly
├── .env                   # All API keys (never commit)
├── requirements.txt
├── package.json           # Root Node.js (scripts only)
├── agents/
│   ├── __init__.py
│   ├── script_agent.py
│   ├── voice_agent.py
│   ├── visual_agent.py
│   ├── assembly_agent.py
│   └── publisher_agent.py
├── remotion/
│   ├── package.json
│   └── src/
│       ├── Root.tsx
│       ├── AIBytesReel.tsx
│       └── components/
├── output/week_NN/ep_NN/  # Generated files
├── skills/                # Skill reference files
└── PRPs/                  # Product requirements prompts
```

---

## Code Standards

### Python
- Type hints on every function signature
- `logging` module only — never `print()`
- Retry logic on every API call (3 retries, exponential backoff)
- Validate output before passing to next agent
- Load all secrets from `.env` via `python-dotenv`
- `Path` from `pathlib` for all file operations

### Standard agent signature
```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def run(episode: int, week: int, input_data: dict) -> dict:
    """Standard agent signature — all agents follow this."""
    try:
        # do work
        logger.info(f"EP{episode:02d} — agent completed")
        return {"success": True, "output_path": str(path)}
    except Exception as e:
        logger.error(f"EP{episode:02d} — agent failed: {e}")
        raise
```

### TypeScript (Remotion components)
- No `any` type — ever
- Props typed from script JSON schema
- Dark theme tokens: `bg=#050510`, `accent=#a78bfa`, `secondary=#34d399`

---

## Forbidden

- `print()` → use `logging`
- Hardcoded API keys → use `.env`
- Stop pipeline on single episode failure → log error, continue to next
- `any` type in TypeScript Remotion components

---

## Output Validation Rules

| Agent | Validates |
|-------|-----------|
| script_agent | JSON parses cleanly, has all required fields |
| voice_agent | MP3 duration 55–65 seconds |
| visual_agent | MP4 is 1080×1920, exactly 60 seconds |
| assembly_agent | MP4 is 1080×1920, 58–62 seconds, has audio track |
| publisher_agent | YouTube video ID returned and logged |

---

## Skills

| Task | Skill file |
|------|-----------|
| Content + hook writing | `skills/content-creator` |
| Architecture decisions | `skills/senior-architect` |
| Python agent patterns | `skills/senior-backend` |
| Video content strategy | `skills/video-content-strategist` |
| Pipeline orchestration | `skills/PIPELINE.md` |
| VPS deployment | `skills/DEPLOYMENT.md` |
| Agent testing | `skills/TESTING.md` |
| YouTube API patterns | `skills/YOUTUBE.md` |

---

## Workflow

```
1. Edit topics.txt (7 lines, one topic per line)
2. python orchestrator.py --dry-run   # test script + voice only
3. python orchestrator.py             # full run — all 5 agents
4. cat orchestrator.log               # verify all 7 uploaded
```

---

## CLI Flags

| Flag | Effect |
|------|--------|
| `--dry-run` | script + voice agents only, skip visual/assembly/publisher |
| `--week N` | override week number (default: auto from date) |
| `--episode N` | run only episode N |

---

## Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REFRESH_TOKEN=...
YOUTUBE_CHANNEL_ID=...
OUTPUT_BASE_PATH=./output
PUBLISH_TIME_UTC=02:30
START_PUBLISH_DATE=2026-05-12
```
