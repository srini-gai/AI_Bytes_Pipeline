import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

REQUIRED_FIELDS = [
    "episode", "topic", "title", "hook", "concept",
    "slides", "voiceover", "takeaway", "tags",
    "youtube_title", "youtube_description", "scheduled_publish",
    "theme", "diagram_spec",
]

_VALID_DIAGRAM_TYPES = {
    "hub_spoke", "cluster", "split_compare",
    "dial", "bar_chart", "side_by_side", "flow",
}

# Rotate through 5 hook formulas by episode number
HOOK_FORMULAS = [
    "Your [thing] is [surprising claim]. Here is why.",
    "This Is How You [desirable outcome]",
    "[Number] seconds to understand [complex concept]",
    "Stop [wrong thing]. Do this instead.",
    "What nobody tells you about [topic]",
]

_SYSTEM_PROMPT_BASE = """\
You are a YouTube Shorts scriptwriter for the AI Bytes channel.
AI Bytes produces 60-second educational shorts explaining AI concepts to developers and founders.

Your task: write a complete, structured script for the given topic as a single raw JSON object.
Output ONLY the JSON — no markdown, no code fences, no explanation before or after.

Required JSON schema:
{
  "episode": "<zero-padded number, e.g. 01>",
  "topic": "<topic string>",
  "title": "<YouTube-friendly title, max 70 chars>",
  "hook": "<10 WORDS OR FEWER — bold claim, curiosity, or shock — no question marks>",
  "concept": "<formal AI concept name>",
  "slides": [
    {"icon": "<single emoji>", "heading": "<3-5 word heading>", "body": "<2-3 sentence explanation>"},
    {"icon": "<single emoji>", "heading": "<3-5 word heading>", "body": "<2-3 sentence explanation>"},
    {"icon": "<single emoji>", "heading": "<3-5 word heading>", "body": "<2-3 sentence explanation>"},
    {"icon": "<single emoji>", "heading": "<3-5 word heading>", "body": "<2-3 sentence explanation>"}
  ],
  "voiceover": "<EXACTLY 150–175 WORDS — full narration. Opens with the hook. Explains concept simply. Ends with CTA to follow AI Bytes every day.>",
  "takeaway": "<one-line key lesson, max 10 words>",
  "tags": "<space-separated hashtags, always include #AIBytes>",
  "youtube_title": "<title MUST end with exactly ' #Shorts'>",
  "youtube_description": "<3-5 lines with value prop + hashtag block>",
  "scheduled_publish": "<ISO 8601 UTC, will be filled by pipeline>",
  "theme": {
    "name": "<one of: danger|calm|creative|future|technical|energy>",
    "accent": "<primary hex color from theme guide>",
    "accent2": "<secondary hex color from theme guide>",
    "overlay": "<rgba CSS string, e.g. rgba(20,0,0,0.45)>",
    "pexels_mood": "<2-4 word mood for Pexels video searches>"
  },
  "diagram_spec": "<object — see DIAGRAM GUIDE below for exact schema per type>"
}

RULES (violation = invalid output):
- hook: MUST be 10 words or fewer. Statement, not question. Creates urgency.
- voiceover: The voiceover field MUST be 150-175 words. AIM FOR 155 WORDS — stay close to 155, never exceed 175. Count carefully before responding. This ensures the ElevenLabs audio output is 58-65 seconds long. Do not go below 150 words under any circumstances.
- slides: EXACTLY 4 items. Each covers a different angle.
- youtube_title: MUST end with ' #Shorts' (space then #Shorts).
- theme.name: MUST be exactly one of the 6 values listed. Use the exact colors from the THEME GUIDE.
- diagram_spec.type: MUST be exactly one of the 7 values in the DIAGRAM GUIDE. Populate only the fields for that type.
- Output raw JSON only — no ```json fences, no preamble.

THEME GUIDE — pick based on the topic's emotional feel:
- danger   : problems, errors, hallucinations, risks        → accent=#ff3333, accent2=#ff6600, overlay=rgba(20,0,0,0.45),    pexels_mood="dark dramatic red"
- calm     : organisation, productivity, clarity, memory    → accent=#60a5fa, accent2=#e2e8f0, overlay=rgba(0,10,30,0.40),   pexels_mood="soft blue minimal calm"
- creative : prompting, ideas, writing, generation          → accent=#f59e0b, accent2=#fb923c, overlay=rgba(20,10,0,0.40),   pexels_mood="warm golden creative"
- future   : agents, automation, next-gen AI, robotics      → accent=#22d3ee, accent2=#818cf8, overlay=rgba(0,10,20,0.45),   pexels_mood="cyan space futuristic"
- technical: databases, architecture, code, vectors, search → accent=#22c55e, accent2=#4ade80, overlay=rgba(0,15,5,0.45),    pexels_mood="green tech dark"
- energy   : general AI concepts, exciting breakthroughs    → accent=#a78bfa, accent2=#34d399, overlay=rgba(5,5,16,0.35),    pexels_mood="purple neon dark"

DIAGRAM GUIDE — pick type by topic, then output ONLY the fields shown for that type:

hub_spoke   → MCP Protocol, AI Agents
  {"type":"hub_spoke","hub":"<center node label>","spokes":["<node>","<node>","<node>","<node>"]}
  (4-6 spokes; each is a short label for a connected capability or client)

cluster     → Embeddings
  {"type":"cluster","groups":[{"label":"<group name>","items":["<item>","<item>","<item>"]},{"label":"<group name>","items":["<item>","<item>","<item>"]}]}
  (2-3 groups of semantically similar words/concepts)

split_compare → Hallucination
  {"type":"split_compare","left":{"label":"<what AI says>","points":["<point>","<point>"]},"right":{"label":"<reality>","points":["<point>","<point>"]},"verdict":"<one-line conclusion about the gap>"}

dial        → Temperature parameter
  {"type":"dial","label":"<parameter name>","min_label":"<low end description>","max_label":"<high end description>","ticks":[{"value":0.0,"description":"<what this setting does>"},{"value":0.7,"description":"<what this setting does>"},{"value":1.0,"description":"<what this setting does>"}]}

bar_chart   → Few-shot prompting, LLM evaluation
  {"type":"bar_chart","title":"<chart title>","bars":[{"label":"<category>","value":<0-100>},{"label":"<category>","value":<0-100>},...]}
  (3-5 bars; values are relative 0-100 scores/percentages)

side_by_side → Local LLMs, Fine-tuning vs RAG
  {"type":"side_by_side","left":{"label":"<option A>","points":["<point>","<point>","<point>"]},"right":{"label":"<option B>","points":["<point>","<point>","<point>"]}}
  (neutral comparison — no verdict)

flow        → RAG, Chain of Thought, Second Brain
  {"type":"flow","steps":[{"icon":"<emoji>","label":"<step name>"},{"icon":"<emoji>","label":"<step name>"},{"icon":"<emoji>","label":"<step name>"},{"icon":"<emoji>","label":"<step name>"}]}
  (3-5 steps in execution order)\
"""

_TAMIL_SYSTEM_SUFFIX = (
    "\n\nLANGUAGE INSTRUCTION: Generate the voiceover field in Tamil (தமிழ்). "
    "Keep all technical terms in English exactly as-is: RAG, LLM, API, GPT, AI, "
    "tokens, embeddings, vector database, fine-tuning, etc. "
    "Use natural conversational Tamil, not formal or stiff. "
    "All other fields (title, hook, slides, takeaway, youtube_title, youtube_description) "
    "remain in English."
)


def _build_system_prompt(lang: str) -> str:
    if lang == "ta":
        return _SYSTEM_PROMPT_BASE + _TAMIL_SYSTEM_SUFFIX
    return _SYSTEM_PROMPT_BASE


def _episode_dir(episode: int, week: int) -> Path:
    base = Path(os.getenv("OUTPUT_BASE_PATH", "./output"))
    path = base / f"week_{week:02d}" / f"ep{episode:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _scheduled_publish(episode: int) -> str:
    """Return ISO 8601 UTC publish time: START_PUBLISH_DATE + (episode-1) days at PUBLISH_TIME_UTC."""
    start = os.getenv("START_PUBLISH_DATE", "2026-05-12")
    hhmm = os.getenv("PUBLISH_TIME_UTC", "02:30")
    hour, minute = map(int, hhmm.split(":"))
    base = datetime.strptime(start, "%Y-%m-%d").replace(
        hour=hour, minute=minute, second=0, microsecond=0, tzinfo=timezone.utc
    )
    publish_dt = base + timedelta(days=episode - 1)
    return publish_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_json(raw: str) -> dict:
    """Strip accidental code fences then parse JSON."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop opening fence line; drop closing fence line if present
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    return json.loads(text)


def _validate_diagram_spec(spec: object, episode: int) -> None:
    if not isinstance(spec, dict):
        raise ValueError("'diagram_spec' must be a JSON object")
    dtype = spec.get("type")
    if dtype not in _VALID_DIAGRAM_TYPES:
        raise ValueError(
            f"diagram_spec.type '{dtype}' must be one of {sorted(_VALID_DIAGRAM_TYPES)}"
        )
    if dtype == "hub_spoke":
        if not spec.get("hub"):
            raise ValueError("diagram_spec hub_spoke requires 'hub'")
        spokes = spec.get("spokes", [])
        if not isinstance(spokes, list) or len(spokes) < 3:
            raise ValueError("diagram_spec hub_spoke requires at least 3 spokes")
    elif dtype == "cluster":
        groups = spec.get("groups", [])
        if not isinstance(groups, list) or len(groups) < 2:
            raise ValueError("diagram_spec cluster requires at least 2 groups")
        for g in groups:
            if not g.get("label") or not isinstance(g.get("items"), list) or len(g["items"]) < 2:
                raise ValueError("diagram_spec cluster each group needs 'label' and at least 2 items")
    elif dtype == "split_compare":
        for side in ("left", "right"):
            s = spec.get(side)
            if not isinstance(s, dict) or not s.get("label") or not isinstance(s.get("points"), list):
                raise ValueError(f"diagram_spec split_compare requires '{side}' with label and points[]")
        if not spec.get("verdict"):
            raise ValueError("diagram_spec split_compare requires 'verdict'")
    elif dtype == "dial":
        for key in ("label", "min_label", "max_label"):
            if not spec.get(key):
                raise ValueError(f"diagram_spec dial requires '{key}'")
        ticks = spec.get("ticks", [])
        if not isinstance(ticks, list) or len(ticks) < 2:
            raise ValueError("diagram_spec dial requires at least 2 ticks")
        for tick in ticks:
            if not isinstance(tick.get("value"), (int, float)) or not tick.get("description"):
                raise ValueError("diagram_spec dial each tick needs 'value' (number) and 'description'")
    elif dtype == "bar_chart":
        if not spec.get("title"):
            raise ValueError("diagram_spec bar_chart requires 'title'")
        bars = spec.get("bars", [])
        if not isinstance(bars, list) or len(bars) < 2:
            raise ValueError("diagram_spec bar_chart requires at least 2 bars")
        for bar in bars:
            if not bar.get("label") or not isinstance(bar.get("value"), (int, float)):
                raise ValueError("diagram_spec bar_chart each bar needs 'label' and numeric 'value'")
    elif dtype == "side_by_side":
        for side in ("left", "right"):
            s = spec.get(side)
            if not isinstance(s, dict) or not s.get("label") or not isinstance(s.get("points"), list):
                raise ValueError(f"diagram_spec side_by_side requires '{side}' with label and points[]")
    elif dtype == "flow":
        steps = spec.get("steps", [])
        if not isinstance(steps, list) or len(steps) < 2:
            raise ValueError("diagram_spec flow requires at least 2 steps")
        for step in steps:
            if not step.get("icon") or not step.get("label"):
                raise ValueError("diagram_spec flow each step needs 'icon' and 'label'")


def _validate(data: dict, episode: int) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"Missing fields: {missing}")

    slides = data.get("slides", [])
    if len(slides) != 4:
        raise ValueError(f"Expected 4 slides, got {len(slides)}")
    for i, slide in enumerate(slides):
        for key in ("icon", "heading", "body"):
            if not slide.get(key):
                raise ValueError(f"Slide {i+1} missing '{key}'")

    hook_words = len(data["hook"].split())
    if hook_words > 10:
        raise ValueError(f"Hook is {hook_words} words — must be ≤10: '{data['hook']}'")

    vo_words = len(data["voiceover"].split())
    if not (150 <= vo_words <= 175):
        raise ValueError(f"Voiceover is {vo_words} words — must be 150–175")

    if not data["youtube_title"].strip().endswith("#Shorts"):
        raise ValueError(f"youtube_title must end with '#Shorts': '{data['youtube_title']}'")

    theme = data.get("theme")
    if not isinstance(theme, dict):
        raise ValueError("'theme' must be a JSON object")
    _VALID_THEMES = {"danger", "calm", "creative", "future", "technical", "energy"}
    for key in ("name", "accent", "accent2", "overlay", "pexels_mood"):
        if not theme.get(key):
            raise ValueError(f"theme missing '{key}'")
    if theme["name"] not in _VALID_THEMES:
        raise ValueError(
            f"theme.name '{theme['name']}' must be one of {sorted(_VALID_THEMES)}"
        )

    _validate_diagram_spec(data.get("diagram_spec"), episode)


def run(topic: str, episode: int, week: int, lang: str = "en") -> dict:
    """Generate a structured script JSON for one episode.

    Args:
        topic:   AI concept topic string (e.g. "What is RAG?")
        episode: Episode number 1–7
        week:    Week number
        lang:    Language code — "en" (default) or "ta" (Tamil)

    Returns:
        {"success": True, "output_path": str, "script": dict, "lang": str}
    """
    lang = lang.lower()
    if lang not in ("en", "ta"):
        raise ValueError(f"Unsupported lang '{lang}' — use 'en' or 'ta'")
    if not topic:
        raise ValueError("script_agent.run() requires a non-empty topic")

    output_path = _episode_dir(episode, week) / f"ep{episode:02d}_script_{lang.upper()}.json"
    hook_hint = HOOK_FORMULAS[(episode - 1) % len(HOOK_FORMULAS)]

    user_msg = (
        f"Topic: {topic}\n"
        f"Episode: {episode:02d}\n"
        f"Week: {week}\n"
        f"Hook formula hint: {hook_hint}\n\n"
        "Write the complete script JSON now."
    )
    system_prompt = _build_system_prompt(lang)

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            logger.info(f"EP{episode:02d} — Claude API call (attempt {attempt}/3)")

            response = client.messages.create(
                model=MODEL,
                max_tokens=1500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )

            raw = response.content[0].text
            data = _parse_json(raw)

            # Overwrite fields the pipeline owns
            data["episode"] = f"{episode:02d}"
            data["scheduled_publish"] = _scheduled_publish(episode)

            _validate(data, episode)

            output_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info(f"EP{episode:02d} [{lang.upper()}] — script saved -> {output_path}")
            return {"success": True, "output_path": str(output_path), "script": data, "lang": lang}

        except (json.JSONDecodeError, ValueError) as e:
            # Malformed output from Claude — retry
            last_error = e
            logger.warning(f"EP{episode:02d} [{lang.upper()}] — attempt {attempt} bad output: {e}")
            if attempt < 3:
                time.sleep(2**attempt)

        except anthropic.AuthenticationError as e:
            raise RuntimeError(f"EP{episode:02d} Claude auth failed — check ANTHROPIC_API_KEY in .env") from e

        except anthropic.RateLimitError as e:
            last_error = e
            logger.warning(f"EP{episode:02d} [{lang.upper()}] — rate limited, waiting before retry")
            if attempt < 3:
                time.sleep(60)

        except Exception as e:
            last_error = e
            logger.error(f"EP{episode:02d} [{lang.upper()}] — attempt {attempt} unexpected error: {e}")
            if attempt < 3:
                time.sleep(2**attempt)

    raise RuntimeError(f"EP{episode:02d} [{lang.upper()}] script_agent failed after 3 attempts: {last_error}")
