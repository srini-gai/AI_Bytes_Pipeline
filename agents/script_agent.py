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
    "dial", "bar_chart", "side_by_side", "flow", "sketch", "data", "token",
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
  "diagram_spec": "<object — see DIAGRAM GUIDE below for exact schema per type>",
  "sketch_spec": "<object — REQUIRED only when diagram_spec.type is 'sketch'. See DIAGRAM GUIDE.>",
  "data_spec": "<object — REQUIRED only when diagram_spec.type is 'data'. See DIAGRAM GUIDE.>",
  "token_spec": "<object — REQUIRED only when diagram_spec.type is 'token'. See DIAGRAM GUIDE.>"
}

RULES (violation = invalid output):
- hook: MUST be 10 words or fewer. Statement, not question. Creates urgency.
- voiceover: The voiceover field MUST be 150-175 words. AIM FOR 155 WORDS — stay close to 155, never exceed 175. Count carefully before responding. This ensures the ElevenLabs audio output is 58-65 seconds long. Do not go below 150 words under any circumstances.
- slides: EXACTLY 4 items. Each covers a different angle.
- youtube_title: MUST end with ' #Shorts' (space then #Shorts).
- theme.name: MUST be exactly one of the 6 values listed. Use the exact colors from the THEME GUIDE.
- diagram_spec.type: MUST be exactly one of the 10 values in the DIAGRAM GUIDE. Populate only the fields for that type.
- When diagram_type is sketch, generate a sketch_spec with 3-6 nodes and edges that visually explain the concept as a flow diagram. Keep node labels under 20 chars. Keep edge labels under 10 chars.
- When diagram_type is data, generate a data_spec (see DIAGRAM GUIDE) matching the chosen data sub-type ("bars", "counter", or "comparison").
- When diagram_type is token, generate a token_spec (see DIAGRAM GUIDE) with a sentence, 2-12 tokens, and (if provided) a weights array matching tokens length.
- Output raw JSON only — no ```json fences, no preamble.

Choose diagram_type="token" when the topic involves:
- Tokenization, tokens, context window, vocabulary, embeddings, text processing, or NLP — anything about how raw text gets split/counted/represented as discrete units.
This takes priority over "sketch" whenever the concept is best shown as one example sentence breaking apart into token boxes, rather than a multi-component pipeline diagram.

DIAGRAM TYPE ROUTING — choose diagram_type="sketch" when the topic involves:
- A process with 3-6 distinct steps that connect to each other (not just a linear list — steps that branch, merge, or feed into a shared destination).
- Any topic containing words: training, backpropagation, gradient, attention, transformer, neural network, RLHF.
- Whenever a flow diagram would benefit from showing data transformations between named components (e.g. text -> tokens -> embeddings -> model), prefer "sketch" over "flow" so the transformation between each node is visible.
Do not default to "flow", "hub_spoke", or the other types out of habit — check this routing list first. Only fall back to the other diagram types when none of the above conditions apply.

Choose diagram_type="data" when the topic involves:
- Statistics, benchmark numbers, or performance metrics (accuracy %, latency, cost, throughput, token counts).
- A before/after or old-way/new-way comparison where the story is "X was slow, Y is fast" or "X used to cost N, now it costs M".
- A single striking number worth building the whole scene around (e.g. "trained on 45 terabytes of text", "processes 100,000 tokens per second").
Pick the data_spec sub-type to match:
- "bars" — 2-5 labeled quantities being ranked or compared against each other (e.g. accuracy across model sizes, cost per provider).
- "counter" — one hero number the whole scene builds up to (e.g. parameter count, dataset size, speed multiplier).
- "comparison" — exactly two quantities in an old-vs-new / before-vs-after frame (bars[0] = old/slow, bars[1] = new/fast).

When diagram_type='data', you MUST also populate a top-level data_spec with:
- type: one of "bars" | "counter" | "comparison".
- title: short scene title (max 30 chars).
- For "bars": a "bars" array of 2-5 {label, value, maxValue, color?} objects.
- For "comparison": a "bars" array of exactly 2 {label, value, maxValue, color?} objects — index 0 is old/slow, index 1 is new/fast.
- For "counter": counterValue (the target number), counterLabel (what it means), and optionally counterSuffix (e.g. "x faster").
- Optionally set "unit" (e.g. "%", "ms", "x") appended after numbers in bars/comparison.

Example for topic "How Much Faster Is Local Inference?":
data_spec = {
  "type": "comparison",
  "title": "Cloud vs Local",
  "unit": "ms",
  "bars": [
    {"label": "Cloud API", "value": 850, "maxValue": 850},
    {"label": "Local GPU", "value": 120, "maxValue": 850}
  ]
}

When diagram_type='token', you MUST also populate a top-level token_spec with:
- sentence: the example sentence being tokenized (plain text).
- tokens: 2-12 {text, color?, highlight?} objects — text is the token substring; set highlight:true on at most one or two tokens worth calling out.
- title: optional short scene title (max 30 chars).
- showIds: optional bool — show a fake-but-plausible token ID under each box.
- showWeights: optional bool — show a small attention/importance bar under each box.
- weights: REQUIRED if showWeights is true — array of numbers (0-1), same length as tokens, one per token.

Example for topic "How AI Actually Reads Your Text":
token_spec = {
  "title": "Text -> Tokens -> Numbers",
  "sentence": "Hello world how are you",
  "tokens": [
    {"text": "Hello", "highlight": true},
    {"text": "world"},
    {"text": "how"},
    {"text": "are"},
    {"text": "you"}
  ],
  "showIds": true,
  "weights": [0.8, 0.6, 0.4, 0.5, 0.3]
}

When diagram_type='sketch', you MUST also populate a top-level sketch_spec with:
- 3 to 6 nodes: each has id, label (max 18 chars), x, y, shape.
- At least 2 edges connecting the nodes.
- A short title (max 30 chars).
- Node spacing: x values between 80-580, y values between 150-500.
- Shapes: "rect" for processes/data, "circle" for models/engines, "diamond" for decision points.

Example for topic "How AI Actually Reads Your Text":
sketch_spec = {
  "title": "From Text to Tokens",
  "nodes": [
    {"id":"t","label":"Your Text","x":80,"y":280,"shape":"rect","width":140,"height":50},
    {"id":"tk","label":"Tokenizer","x":280,"y":280,"shape":"diamond","width":130,"height":60},
    {"id":"id","label":"Token IDs","x":480,"y":180,"shape":"rect","width":130,"height":50},
    {"id":"em","label":"Embeddings","x":480,"y":380,"shape":"rect","width":130,"height":50},
    {"id":"llm","label":"LLM","x":620,"y":280,"shape":"circle","width":80,"height":80}
  ],
  "edges": [
    {"from":"t","to":"tk","label":"splits"},
    {"from":"tk","to":"id","label":"maps"},
    {"from":"tk","to":"em","label":"encodes"},
    {"from":"id","to":"llm"},
    {"from":"em","to":"llm","label":"feeds"}
  ]
}

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
  (3-5 steps in execution order)

sketch      → Training, Backpropagation, Attention, Transformers, Neural networks, RLHF,
              and any multi-step process (3-6 steps) whose components transform data as it
              passes between them. See DIAGRAM TYPE ROUTING above. (For tokenization/text-
              splitting specifically, use "token" instead — see below.)
  diagram_spec: {"type":"sketch"}
  ALSO output a top-level "sketch_spec" object:
  {"nodes":[{"id":"<short id>","label":"<node label, under 20 chars>","x":<number>,"y":<number>,"shape":"rect|circle|diamond","width":<number>,"height":<number>},...],"edges":[{"from":"<id>","to":"<id>","label":"<optional, under 10 chars>"},...],"title":"<optional diagram title>"}
  (3-6 nodes placed on a canvas roughly 720 wide x 500 tall; edges reference node ids and show the flow between them)

data        → Stats, benchmark numbers, performance metrics, before/after or old-way/new-way
              comparisons, or a single hero number worth building a scene around.
              See DIAGRAM TYPE ROUTING above for sub-type selection.
  diagram_spec: {"type":"data"}
  ALSO output a top-level "data_spec" object, matching the chosen sub-type:
  bars       → {"type":"bars","title":"<chart title>","unit":"<optional, e.g. %>","bars":[{"label":"<category>","value":<number>,"maxValue":<number>,"color":"<optional hex>"},...]}  (2-5 bars)
  counter    → {"type":"counter","title":"<scene title>","counterValue":<number>,"counterLabel":"<what it means>","counterSuffix":"<optional, e.g. x faster>","unit":"<optional>"}
  comparison → {"type":"comparison","title":"<scene title>","unit":"<optional>","bars":[{"label":"<old/slow>","value":<number>,"maxValue":<number>},{"label":"<new/fast>","value":<number>,"maxValue":<number>}]}  (exactly 2 — index 0 is old/slow, index 1 is new/fast)

token       → Tokenization, tokens, context window, vocabulary, embeddings, text processing, NLP —
              any topic best shown as one example sentence breaking apart into token boxes.
              See "Choose diagram_type='token'" above.
  diagram_spec: {"type":"token"}
  ALSO output a top-level "token_spec" object:
  {"sentence":"<example sentence>","tokens":[{"text":"<substring>","color":"<optional hex>","highlight":<optional bool>},...],"title":"<optional>","showIds":<optional bool>,"showWeights":<optional bool>,"weights":"<optional number[] — REQUIRED, same length as tokens, if showWeights is true>"}
  (2-12 tokens; weights values are 0-1)\
"""

_TAMIL_SYSTEM_SUFFIX = (
    "\n\nLANGUAGE INSTRUCTION: Generate the voiceover field in Tamil (தமிழ்). "
    "Keep all technical terms in English exactly as-is: RAG, LLM, API, GPT, AI, "
    "tokens, embeddings, vector database, fine-tuning, etc. "
    "Use natural conversational Tamil, not formal or stiff. "
    "All other fields (title, hook, slides, takeaway, youtube_title, youtube_description) "
    "remain in English.\n\n"
    "TAMIL WORD COUNT: The voiceover MUST be 100-130 words in Tamil. "
    "This is equivalent to 150-165 English words in spoken duration. "
    "AIM FOR 110 WORDS. Tamil uses longer words so fewer are needed for the same audio duration. "
    "Count carefully before responding. Do not exceed 130 Tamil words.\n\n"
    "TAMIL HOOK: The hook field remains in English but may be up to 15 words."
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
    # dtype == "sketch"/"data"/"token": diagram_spec itself carries no extra fields —
    # the actual diagram content lives in the top-level 'sketch_spec'/'data_spec'/
    # 'token_spec' field, validated separately by _validate_sketch_spec()/
    # _validate_data_spec()/_validate_token_spec().


_VALID_SKETCH_SHAPES = {"rect", "circle", "diamond"}


def _validate_sketch_spec(spec: object) -> None:
    if not isinstance(spec, dict):
        raise ValueError("'sketch_spec' must be a JSON object when diagram_spec.type is 'sketch'")

    nodes = spec.get("nodes", [])
    if not isinstance(nodes, list) or not (3 <= len(nodes) <= 6):
        raise ValueError("sketch_spec requires 3-6 nodes")

    node_ids = set()
    for node in nodes:
        for key in ("id", "label", "x", "y", "shape"):
            if key not in node:
                raise ValueError(f"sketch_spec node missing '{key}'")
        if node["shape"] not in _VALID_SKETCH_SHAPES:
            raise ValueError(f"sketch_spec node shape '{node['shape']}' must be one of {sorted(_VALID_SKETCH_SHAPES)}")
        if len(node["label"]) > 20:
            raise ValueError(f"sketch_spec node label exceeds 20 chars: '{node['label']}'")
        node_ids.add(node["id"])

    edges = spec.get("edges", [])
    if not isinstance(edges, list) or not edges:
        raise ValueError("sketch_spec requires at least 1 edge")
    for edge in edges:
        if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
            raise ValueError("sketch_spec edge 'from'/'to' must reference valid node ids")
        label = edge.get("label")
        if label and len(label) > 10:
            raise ValueError(f"sketch_spec edge label exceeds 10 chars: '{label}'")


_VALID_DATA_TYPES = {"bars", "counter", "comparison"}


def _validate_data_bar(bar: object, index: int) -> None:
    if not isinstance(bar, dict):
        raise ValueError(f"data_spec bars[{index}] must be a JSON object")
    if not bar.get("label"):
        raise ValueError(f"data_spec bars[{index}] missing 'label'")
    if not isinstance(bar.get("value"), (int, float)):
        raise ValueError(f"data_spec bars[{index}] needs numeric 'value'")
    if not isinstance(bar.get("maxValue"), (int, float)):
        raise ValueError(f"data_spec bars[{index}] needs numeric 'maxValue'")


def _validate_data_spec(spec: object) -> None:
    if not isinstance(spec, dict):
        raise ValueError("'data_spec' must be a JSON object when diagram_spec.type is 'data'")

    dstype = spec.get("type")
    if dstype not in _VALID_DATA_TYPES:
        raise ValueError(f"data_spec.type '{dstype}' must be one of {sorted(_VALID_DATA_TYPES)}")
    if not spec.get("title"):
        raise ValueError("data_spec requires 'title'")

    if dstype == "bars":
        bars = spec.get("bars", [])
        if not isinstance(bars, list) or not (2 <= len(bars) <= 5):
            raise ValueError("data_spec bars requires 2-5 bars")
        for i, bar in enumerate(bars):
            _validate_data_bar(bar, i)
    elif dstype == "comparison":
        bars = spec.get("bars", [])
        if not isinstance(bars, list) or len(bars) != 2:
            raise ValueError("data_spec comparison requires exactly 2 bars (old/slow, new/fast)")
        for i, bar in enumerate(bars):
            _validate_data_bar(bar, i)
    elif dstype == "counter":
        if not isinstance(spec.get("counterValue"), (int, float)):
            raise ValueError("data_spec counter requires numeric 'counterValue'")
        if not spec.get("counterLabel"):
            raise ValueError("data_spec counter requires 'counterLabel'")


def _validate_token_spec(spec: object) -> None:
    if not isinstance(spec, dict):
        raise ValueError("'token_spec' must be a JSON object when diagram_spec.type is 'token'")

    if not spec.get("sentence"):
        raise ValueError("token_spec requires 'sentence'")

    tokens = spec.get("tokens", [])
    if not isinstance(tokens, list) or not (2 <= len(tokens) <= 12):
        raise ValueError("token_spec requires 2-12 tokens")
    for i, token in enumerate(tokens):
        if not isinstance(token, dict) or not token.get("text"):
            raise ValueError(f"token_spec tokens[{i}] missing 'text'")

    if spec.get("showWeights"):
        weights = spec.get("weights")
        if not isinstance(weights, list) or len(weights) != len(tokens):
            raise ValueError(
                f"token_spec weights must be an array matching tokens length ({len(tokens)}) when showWeights is true"
            )
    elif spec.get("weights") is not None:
        weights = spec["weights"]
        if not isinstance(weights, list) or len(weights) != len(tokens):
            raise ValueError(
                f"token_spec weights must be an array matching tokens length ({len(tokens)})"
            )


def _validate(data: dict, episode: int, lang: str = "en") -> None:
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

    hook_limit = 15 if lang == "ta" else 10
    hook_words = len(data["hook"].split())
    if hook_words > hook_limit:
        raise ValueError(f"Hook is {hook_words} words — must be ≤{hook_limit}: '{data['hook']}'")

    vo_words = len(data["voiceover"].split())
    if lang == "ta":
        if not (95 <= vo_words <= 135):
            raise ValueError(f"Voiceover is {vo_words} words — must be 95–135 (Tamil)")
    else:
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
    if data["diagram_spec"].get("type") == "sketch":
        _validate_sketch_spec(data.get("sketch_spec"))
    if data["diagram_spec"].get("type") == "data":
        _validate_data_spec(data.get("data_spec"))
    if data["diagram_spec"].get("type") == "token":
        _validate_token_spec(data.get("token_spec"))


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

            _validate(data, episode, lang)

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
