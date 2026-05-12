# CLAUDE.md — AI Bytes Pipeline

> Rules Claude follows in every conversation for this project.

---

## What This Project Is

A Python CLI pipeline that reads topics.txt and produces 7 YouTube Shorts automatically.
NO frontend. NO database. NO auth. NO payments.
Pure Python agents + external APIs + FFmpeg + Remotion.

---

## Tech Stack

- **Language:** Python 3.11
- **Script generation:** Anthropic Claude API
- **Voice:** ElevenLabs TTS API
- **Video rendering:** Remotion (Node.js, headless)
- **Assembly:** FFmpeg + MoviePy + OpenAI Whisper
- **Publishing:** YouTube Data API v3
- **Deployment:** Hostinger VPS — 187.127.151.27

---

## Project Structure

AIBytes-Pipeline/
├── orchestrator.py        # Master runner
├── topics.txt             # 7 topics, one per line
├── .env                   # All API keys
├── requirements.txt
├── agents/
│   ├── script_agent.py
│   ├── voice_agent.py
│   ├── visual_agent.py
│   ├── assembly_agent.py
│   └── publisher_agent.py
├── remotion/src/          # Remotion React components
├── output/week_NN/        # Generated files
└── skills/                # Skill reference files

---

## Code Standards

### Python
- Type hints on every function
- Use logging not print()
- Retry logic on every API call (3 retries, exponential backoff)
- Validate outputs before passing to next agent
- Load all secrets from .env via python-dotenv

### Agent pattern
```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def run(episode: int, week: int, input_data: dict) -> dict:
    """Every agent follows this signature."""
    try:
        # do work
        logger.info(f"EP{episode:02d} — agent completed")
        return {"success": True, "output_path": str(path)}
    except Exception as e:
        logger.error(f"EP{episode:02d} — agent failed: {e}")
        raise
```

---

## Forbidden

- `print()` → use `logging`
- Hardcoded API keys → use `.env`
- Stop full pipeline on single episode failure → log and continue
- `any` type in TypeScript (Remotion components)

---

## Skills

| Task | Skill file |
|------|-----------|
| Python agent patterns | `skills/BACKEND.md` |
| Content + hook writing | `skills/content-creator/SKILL.md` |
| Architecture decisions | `skills/senior-architect/SKILL.md` |
| Python best practices | `skills/python-expert/SKILL.md` |
| VPS deployment | `skills/DEPLOYMENT.md` |
| Testing agents | `skills/TESTING.md` |

---

## Workflow
Edit topics.txt (7 lines)
python orchestrator.py --dry-run   (test script + voice only)
python orchestrator.py             (full run)
Check orchestrator.log             (verify all 7 uploaded)

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
```