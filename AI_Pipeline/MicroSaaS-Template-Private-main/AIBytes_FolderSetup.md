# AI Bytes Pipeline — Folder Setup Guide
## Exactly what to keep, replace, and add from claude-skills

---

## STEP 1 — Create the project folder

```bash
# On your Windows machine
mkdir "C:\Additional case AI\AIBytes-Pipeline"
```

---

## STEP 2 — Copy MicroSaaS template into it

Copy everything from your MicroSaaS-Template-Private-main folder into AIBytes-Pipeline.

After copy, your folder looks like this:

```
AIBytes-Pipeline/
├── .claude/
│   └── commands/
│       ├── execute-prp.md       ✅ KEEP as-is
│       ├── generate-prp.md      ✅ KEEP as-is
│       └── setup-project.md     ✅ KEEP as-is
├── agents/
│   ├── ORCHESTRATOR.md          ✅ KEEP as-is
│   ├── backend-agent.md         ✅ KEEP as-is
│   ├── database-agent.md        ✅ KEEP as-is
│   └── frontend-agent.md        ✅ KEEP as-is
├── skills/
│   ├── BACKEND.md               ✅ KEEP as-is
│   ├── DATABASE.md              ❌ NOT NEEDED (no DB in AI Bytes) — delete or ignore
│   ├── DEPLOYMENT.md            ⚠️  KEEP but Claude Code will override with VPS rules
│   ├── FRONTEND.md              ❌ NOT NEEDED (no frontend) — delete or ignore
│   └── TESTING.md               ✅ KEEP as-is
├── CLAUDE.md                    ✏️  REPLACE — see Step 4 below
├── INITIAL.md                   ✏️  REPLACE — with the AIBytes_INITIAL.md I gave you
└── README.md                    ✏️  UPDATE — rename to AI Bytes Pipeline
```

---

## STEP 3 — Sparse clone ONLY what you need from your claude-skills repo

You don't need all 235 skills. Use sparse checkout to pull only 3 folders.

```bash
# Open terminal inside AIBytes-Pipeline folder
cd "C:\Additional case AI\AIBytes-Pipeline"

# Create a temp folder for sparse clone
mkdir claude-skills-temp
cd claude-skills-temp

# Init sparse clone from YOUR private repo
git clone --filter=blob:none --sparse https://github.com/srini-gai/claude-skills.git .

# Pull ONLY these 3 folders
git sparse-checkout set marketing-skill/content-creator engineering-team/senior-architect engineering-team/python-expert
```

This downloads ~3MB instead of the full 9.38MB.

---

## STEP 4 — Copy the 3 skill folders into skills/

```bash
# Still in claude-skills-temp, copy into your project's skills folder
xcopy "marketing-skill\content-creator" "..\skills\content-creator\" /E /I
xcopy "engineering-team\senior-architect" "..\skills\senior-architect\" /E /I
xcopy "engineering-team\python-expert" "..\skills\python-expert\" /E /I

# Go back to project root and delete temp folder
cd ..
rmdir /S /Q claude-skills-temp
```

---

## STEP 5 — Replace CLAUDE.md

Delete the existing CLAUDE.md and create a new one with this content:

```markdown
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

```
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
```

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

```
1. Edit topics.txt (7 lines)
2. python orchestrator.py --dry-run   (test script + voice only)
3. python orchestrator.py             (full run)
4. Check orchestrator.log             (verify all 7 uploaded)
```

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
```

---

## STEP 6 — Replace INITIAL.md

Delete the existing INITIAL.md and drop in the AIBytes_INITIAL.md file I gave you.
Rename it to INITIAL.md.

---

## FINAL folder structure after all steps

```
AIBytes-Pipeline/
├── .claude/
│   └── commands/
│       ├── execute-prp.md          ✅ original — kept
│       ├── generate-prp.md         ✅ original — kept
│       └── setup-project.md        ✅ original — kept
│
├── agents/
│   ├── ORCHESTRATOR.md             ✅ original — kept
│   ├── backend-agent.md            ✅ original — kept
│   ├── database-agent.md           ✅ original — kept
│   └── frontend-agent.md           ✅ original — kept
│
├── skills/
│   ├── BACKEND.md                  ✅ original — kept (Python patterns)
│   ├── DEPLOYMENT.md               ✅ original — kept (VPS deploy)
│   ├── TESTING.md                  ✅ original — kept
│   ├── content-creator/            ✅ NEW — from claude-skills
│   │   └── SKILL.md
│   ├── senior-architect/           ✅ NEW — from claude-skills
│   │   └── SKILL.md
│   └── python-expert/              ✅ NEW — from claude-skills
│       └── SKILL.md
│
├── CLAUDE.md                       ✏️  REPLACED — AI Bytes specific
├── INITIAL.md                      ✏️  REPLACED — AI Bytes product definition
└── README.md                       (update later)
```

---

## STEP 7 — Open in Cursor and run

```bash
# Open Cursor → File → Open Folder → AIBytes-Pipeline

# In Claude Code terminal:
/generate-prp INITIAL.md

# After PRP is generated:
/execute-prp PRPs/aibytes-pipeline-prp.md
```

---

## Summary — What changed vs original template

| File | Action | Reason |
|------|--------|--------|
| CLAUDE.md | Replaced | No DB, no frontend, Python CLI rules |
| INITIAL.md | Replaced | AI Bytes pipeline product definition |
| skills/DATABASE.md | Ignored | No database in this project |
| skills/FRONTEND.md | Ignored | No frontend in this project |
| skills/content-creator/ | Added | Hook writing, script frameworks |
| skills/senior-architect/ | Added | Pipeline architecture guidance |
| skills/python-expert/ | Added | Python agent best practices |
| All .claude/commands/ | Kept | Same generate-prp / execute-prp flow |
| All agents/ | Kept | Orchestrator pattern still applies |

*Total setup time: ~15 minutes*
