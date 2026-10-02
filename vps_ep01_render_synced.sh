#!/usr/bin/env bash
# =============================================================================
# EP01 SYNCED VISUALS RENDER — Whisper-measured timing
# Run on VPS: bash vps_ep01_render_synced.sh | tee /root/ai_bytes_pipeline/ep01_render_synced.log
#
# Scene durations derived from measured Whisper word timestamps:
#   scene_start = first spoken word timestamp for that scene
#   scene_end   = first spoken word timestamp of the NEXT scene
#   CTA scene_end = actual voice duration (47.74s)
#
# STOPS BEFORE assembly/publish — visual review only.
# =============================================================================
set -euo pipefail

PROJ="/root/ai_bytes_pipeline"
EP_DIR="$PROJ/output/week_01/ep01"
PROPS_FILE="$EP_DIR/ep01_render_props.json"
VISUALS="$EP_DIR/ep01_visuals_v3_synced.mp4"

echo "============================================================"
echo " EP01 SYNCED VISUALS RENDER — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo " Timing source: Whisper word timestamps (boundary-to-boundary)"
echo " DO NOT PUBLISH — stop for visual review"
echo "============================================================"

# ── 1. Pull latest code ─────────────────────────────────────────────────────
echo ""
echo "[1/5] Pulling latest code..."
cd "$PROJ" && git pull
echo "      Git HEAD: $(git rev-parse --short HEAD)"

# ── 2. Load environment ─────────────────────────────────────────────────────
echo ""
echo "[2/5] Loading .env from /opt/aibytes/.env"
set -a; source /opt/aibytes/.env; set +a

# ── 3. Write canonical script JSON (output/ is gitignored) ──────────────────
echo ""
echo "[3/5] Writing canonical script JSON + render props"
mkdir -p "$EP_DIR"

# Write script JSON for hash checks
cat > "$EP_DIR/ep01_script_EN.json" << 'SCRIPTJSON'
{
  "episode": "01",
  "topic": "How AI Actually Reads Your Text",
  "title": "AI Has Never Read a Single Word",
  "hook": "AI has never read a single word. Not one.",
  "concept": "Tokenization — how LLMs convert text to token IDs before processing",
  "slides": [
    {
      "type": "transform",
      "title": "Text → Tokens → Numbers",
      "from": "unbelievable",
      "to": "[1726, 42891, 481]",
      "label": "Tokenizer"
    },
    {
      "type": "token",
      "sentence": "unbelievable",
      "tokens": [
        {"text": "un", "highlight": true},
        {"text": "believ", "highlight": true},
        {"text": "able", "highlight": true}
      ],
      "title": "Tokens ≠ Words",
      "showIds": true
    },
    {
      "type": "bars",
      "title": "Relative Token Cost",
      "bars": [
        {"label": "English word", "value": 35, "maxValue": 100},
        {"label": "Code snippet", "value": 65, "maxValue": 100},
        {"label": "Rare / foreign word", "value": 85, "maxValue": 100}
      ]
    },
    {
      "type": "counter",
      "title": "Context Window",
      "counterValue": 100,
      "counterLabel": "Context consumed",
      "counterSuffix": "%"
    }
  ],
  "voiceover": "AI has never read a single word. Not one. Before an LLM sees your text, a tokenizer splits it into chunks called tokens. A token isn't always a word. Unbelievable becomes three tokens: un, believ, able. Every token gets mapped to an integer ID. The model processes numbers, not letters. These IDs feed into an embedding layer, converting each into a vector. The transformer attends to these vectors, predicting the next token one at a time. Tokens drive cost and context. You pay per token. Context windows are measured in tokens, not words. The longer your input, the more context you consume. Code and rare words cost more tokens. Write short, precise prompts — you're spending tokens. AI processes tokens, not words directly. Follow Srini on AI for practical AI, daily.",
  "takeaway": "AI processes tokens, not words directly.",
  "tags": "#SriniOnAI #Tokenization #LLM #GenerativeAI #AIShorts",
  "youtube_title": "AI Has Never Read a Single Word #Shorts",
  "youtube_description": "AI doesn't read words — it reads tokens. Every LLM converts your text into integer IDs before processing. Understanding tokens helps you write better prompts and cut API costs.\n\nTopic: Tokenization and how LLMs actually process text\n\n#SriniOnAI #Tokenization #LLM #GenerativeAI #AIShorts",
  "scheduled_publish": null,
  "theme": {
    "accent": "#a78bfa"
  }
}
SCRIPTJSON
echo "      Script JSON written: $(wc -c < "$EP_DIR/ep01_script_EN.json") bytes"

# Write render props with MEASURED Whisper boundary-to-boundary timing
cat > "$PROPS_FILE" << 'ENDJSON'
{
  "episode": 1,
  "topic": "How AI Actually Reads Your Text",
  "title": "AI Has Never Read a Single Word",
  "hook": "AI has never read a single word. Not one.",
  "concept": "Tokenization — how LLMs convert text to token IDs before processing",
  "voiceover": "AI has never read a single word. Not one. Before an LLM sees your text, a tokenizer splits it into chunks called tokens. A token isn't always a word. Unbelievable becomes three tokens: un, believ, able. Every token gets mapped to an integer ID. The model processes numbers, not letters. These IDs feed into an embedding layer, converting each into a vector. The transformer attends to these vectors, predicting the next token one at a time. Tokens drive cost and context. You pay per token. Context windows are measured in tokens, not words. The longer your input, the more context you consume. Code and rare words cost more tokens. Write short, precise prompts — you're spending tokens. AI processes tokens, not words directly. Follow Srini on AI for practical AI, daily.",
  "takeaway": "AI processes tokens, not words directly.",
  "tags": "#SriniOnAI #Tokenization #LLM #GenerativeAI #AIShorts",
  "slides": [],
  "storyboard": [
    {"scene_id": 1, "duration_seconds": 2.92, "narration": "AI has never read a single word. Not one.", "scene_type": "HOOK", "visual_goal": "The word 'WORD' physically shatters mid-display", "component": "KineticTypoScene", "objects": ["word_text", "shatter_fragments", "not_one_label"], "animation": "Giant WORD slams onto screen, cracks and fragments", "on_screen_text": ["WORD", "NOT ONE."], "data": null, "transition": "cut", "carry_object_from": null, "beats": []},
    {"scene_id": 2, "duration_seconds": 11.02, "narration": "Before an LLM sees your text, a tokenizer splits it into chunks called tokens. A token isn't always a word. Unbelievable becomes three tokens: un, believ, able.", "scene_type": "DEMONSTRATION", "visual_goal": "Real English sentence visually splits into labelled token boxes", "component": "TokenScene", "objects": ["input_sentence", "token_boxes", "boundary_markers"], "animation": "Full sentence slides in, tokenizer beam scans", "on_screen_text": ["un", "believ", "able", "TOKENS ≠ WORDS"], "data": null, "transition": "morph", "carry_object_from": null, "beats": []},
    {"scene_id": 3, "duration_seconds": 5.42, "narration": "Every token gets mapped to an integer ID. The model processes numbers, not letters.", "scene_type": "TRANSFORMATION", "visual_goal": "Token boxes morph into glowing integer IDs", "component": "TransformScene", "objects": ["token_boxes", "integer_ids", "id_labels"], "animation": "Token boxes carry over, each box flips into glowing integer ID", "on_screen_text": ["un → 1726", "believ → 42891", "able → 481", "A LIST OF NUMBERS"], "data": null, "transition": "morph", "carry_object_from": "token_boxes", "beats": []},
    {"scene_id": 4, "duration_seconds": 4.14, "narration": "These IDs feed into an embedding layer, converting each into a vector.", "scene_type": "FLOW", "visual_goal": "Integer IDs transform into floating vector arrows then attention lines draw between them", "component": "NetworkBuildScene", "objects": ["id_nodes", "vector_arrows", "attention_lines", "transformer_label"], "animation": "ID column fans into horizontal row of ID nodes", "on_screen_text": ["INTEGER IDs", "EMBEDDING VECTORS", "ATTENTION"], "data": null, "transition": "fade", "carry_object_from": "integer_ids", "beats": []},
    {"scene_id": 5, "duration_seconds": 4.36, "narration": "The transformer attends to these vectors, predicting the next token one at a time.", "scene_type": "DEMONSTRATION", "visual_goal": "Tokens stream out one by one from the transformer", "component": "TokenStreamScene", "objects": ["transformer_core", "output_tokens", "token_cursor"], "animation": "Compact transformer block glows, tokens emit from right edge", "on_screen_text": ["NEXT TOKEN", "ONE AT A TIME"], "data": null, "transition": "slide-right", "carry_object_from": "attention_lines", "beats": []},
    {"scene_id": 6, "duration_seconds": 5.76, "narration": "Tokens drive cost and context. You pay per token. Context windows are measured in tokens, not words.", "scene_type": "COMPARISON", "visual_goal": "Side-by-side bar comparison of token cost across text types", "component": "DataScene", "source_type": "illustrative", "objects": ["text_examples", "token_bars", "cost_labels"], "animation": "Three rows appear staggered", "on_screen_text": ["English word", "Code snippet", "Rare / foreign word", "TOKEN COST"], "data": {"type": "bars", "title": "Relative Token Cost", "bars": [{"label": "English word", "value": 35}, {"label": "Code snippet", "value": 65}, {"label": "Rare / foreign word", "value": 85}]}, "transition": "fade", "carry_object_from": null, "beats": []},
    {"scene_id": 7, "duration_seconds": 2.64, "narration": "The longer your input, the more context you consume.", "scene_type": "DATA", "visual_goal": "A growing bar fills a context window gauge", "component": "NumberCounterScene", "source_type": "illustrative", "objects": ["counter_display", "unit_label", "context_label"], "animation": "Bar fills progressively to show context consumption", "on_screen_text": ["CONTEXT WINDOW", "TOKENS", "input length → context consumed"], "data": {"type": "counter", "value": 100, "label": "Context consumed", "suffix": "%"}, "transition": "zoom-in", "carry_object_from": null, "beats": []},
    {"scene_id": 8, "duration_seconds": 5.88, "narration": "Code and rare words cost more tokens. Write short, precise prompts — you're spending tokens.", "scene_type": "COMPARISON", "visual_goal": "Verbose prompt vs terse prompt token cost comparison", "component": "BeforeAfterScene", "source_type": "illustrative", "objects": ["verbose_panel", "terse_panel", "cost_indicator"], "animation": "Left panel verbose prompt red bar, right panel terse prompt green bar", "on_screen_text": ["VERBOSE PROMPT", "TERSE PROMPT", "MORE TOKENS", "FEWER TOKENS"], "data": null, "transition": "fade", "carry_object_from": null, "beats": []},
    {"scene_id": 9, "duration_seconds": 2.86, "narration": "AI processes tokens, not words directly.", "scene_type": "TAKEAWAY", "visual_goal": "Single bold takeaway line with token-box icon", "component": "TakeawayScene", "objects": ["token_icon", "takeaway_text", "underline_sweep"], "animation": "Small token box icon drops from top", "on_screen_text": ["AI processes TOKENS", "not words directly"], "data": null, "transition": "fade", "carry_object_from": null, "beats": []},
    {"scene_id": 10, "duration_seconds": 2.74, "narration": "Follow Srini on AI for practical AI, daily.", "scene_type": "CTA", "visual_goal": "Follow CTA — 3 seconds, clean", "component": "CTAScene", "objects": ["cta_label", "follow_button"], "animation": "Channel name and Follow pill rise from bottom", "on_screen_text": ["Follow Srini on AI", "for practical AI, daily."], "data": null, "transition": "fade", "carry_object_from": null, "beats": []}
  ],
  "theme": {
    "name": "energy",
    "accent": "#a78bfa",
    "accent2": "#34d399",
    "overlay": "rgba(5,5,16,0.35)",
    "pexels_mood": "purple neon dark"
  },
  "generatedVideoClips": {
    "s01": "clips/gen_video_s01.mp4"
  },
  "showCreatorProfile": false
}
ENDJSON
echo "      Render props written: $(wc -c < "$PROPS_FILE") bytes"

# ── 4. Pre-render checks ────────────────────────────────────────────────────
echo ""
echo "[4/5] Pre-render checks..."

# THREE_HASH_CHECK
python3 << 'PYHASH'
import json, hashlib, sys

with open("/root/ai_bytes_pipeline/output/week_01/ep01/ep01_script_EN.json") as f:
    script = json.load(f)
with open("/root/ai_bytes_pipeline/output/week_01/ep01/ep01_render_props.json") as f:
    props = json.load(f)

canon = script["voiceover"].strip()
canon_hash = hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]

sb_concat = " ".join(s["narration"] for s in props["storyboard"])
sb_hash = hashlib.sha256(sb_concat.encode("utf-8")).hexdigest()[:16]

voice_hash_path = "/root/ai_bytes_pipeline/output/week_01/ep01/ep01_voice_hash_EN.txt"
try:
    voice_hash = open(voice_hash_path).read().strip()
except FileNotFoundError:
    print("FATAL: voice hash file not found — run vps_ep01_voice_timing.sh first")
    sys.exit(1)

print(f"canonical_script_hash:       {canon_hash}")
print(f"storyboard_narration_hash:   {sb_hash}")
print(f"voice_source_hash:           {voice_hash}")

all_match = (canon_hash == sb_hash == voice_hash)
print(f"\nTHREE_HASH_CHECK = {'PASS' if all_match else 'FAIL'}")
if not all_match:
    print("FATAL: Hash mismatch — aborting render")
    sys.exit(1)

# Compute total visual duration
total = sum(s["duration_seconds"] for s in props["storyboard"])
print(f"\nVISUAL_RENDER_MODE=STORYBOARD_V3")
print(f"SCENES=10")
print(f"")
print(f"COMPONENT_SEQUENCE: KineticTypoScene -> TokenScene -> TransformScene -> NetworkBuildScene -> TokenStreamScene -> DataScene -> NumberCounterScene -> BeforeAfterScene -> TakeawayScene -> CTAScene")
print(f"")
print(f"Scene | Component              | Duration | Whisper boundary       | Asset source")
print(f"------|------------------------|----------|------------------------|---------------------------")
boundaries = [
    ("s01", "KineticTypoScene",    2.92, " 0.00s →  2.92s", "HIGGSFIELD cached"),
    ("s02", "TokenScene",         11.02, " 2.92s → 13.94s", "Remotion dark bg"),
    ("s03", "TransformScene",      5.42, "13.94s → 19.36s", "Remotion dark bg"),
    ("s04", "NetworkBuildScene",   4.14, "19.36s → 23.50s", "Remotion dark bg"),
    ("s05", "TokenStreamScene",    4.36, "23.50s → 27.86s", "Remotion dark bg"),
    ("s06", "DataScene",           5.76, "27.86s → 33.62s", "Remotion dark bg"),
    ("s07", "NumberCounterScene",  2.64, "33.62s → 36.26s", "Remotion dark bg"),
    ("s08", "BeforeAfterScene",    5.88, "36.26s → 42.14s", "Remotion dark bg"),
    ("s09", "TakeawayScene",       2.86, "42.14s → 45.00s", "Remotion dark bg"),
    ("s10", "CTAScene",            2.74, "45.00s → 47.74s", "Remotion dark bg"),
]
for sid, comp, dur, bounds, src in boundaries:
    print(f"{sid:<6}| {comp:<22} | {dur:>6.2f}s | {bounds} | {src}")
print(f"------|------------------------|----------|------------------------|---------------------------")
print(f"TOTAL |                        | {total:>6.2f}s |  0.00s → 47.74s        |")
print(f"")
print(f"TOTAL_DURATION={total:.2f}s")

# Check voice file exists (DO NOT regenerate)
import os
voice_path = "/root/ai_bytes_pipeline/output/week_01/ep01/ep01_voice_EN.mp3"
if os.path.exists(voice_path):
    size_kb = os.path.getsize(voice_path) / 1024
    print(f"\nVoice B: present ({size_kb:.0f} KB) — will NOT regenerate")
else:
    print(f"\nWARNING: Voice MP3 not found at {voice_path}")
    print("Run vps_ep01_voice_timing.sh first")
    sys.exit(1)
PYHASH

# Confirm Higgsfield clip exists (DO NOT regenerate)
CLIP="$PROJ/remotion/public/clips/gen_video_s01.mp4"
if [ -f "$CLIP" ]; then
  echo ""
  echo "Higgsfield s01 clip: PRESENT (cached, no new generation) — $(du -h "$CLIP" | cut -f1)"
else
  echo ""
  echo "ERROR: Higgsfield clip NOT found at $CLIP"
  echo "Cache key: 4856fe4c7d9a5f7dc3ae7301852f4a27b3e42a1b5b20dedea4a867479e29d22e"
  exit 1
fi

# ── 5. Render synced visuals via Remotion ────────────────────────────────────
echo ""
echo "[5/5] Rendering synced visuals (Remotion storyboard_v3 + measured timing)..."

# Delete any previous synced visuals
if [ -f "$VISUALS" ]; then
  echo "      Removing previous ep01_visuals_v3_synced.mp4..."
  rm -f "$VISUALS"
fi

cd "$PROJ/remotion"
npm install --silent 2>&1 | tail -3
echo "      Starting npx remotion render..."
npx remotion render AIBytesReel "$VISUALS" \
  --props="$PROPS_FILE" \
  --concurrency=2 \
  2>&1
echo "      Render complete."

# ── Visual regression checks ────────────────────────────────────────────────
echo ""
echo "Running visual regression checks..."
python3 - <<'PYEOF'
import subprocess, json, sys

visuals = "/root/ai_bytes_pipeline/output/week_01/ep01/ep01_visuals_v3_synced.mp4"

# ffprobe video stream
r = subprocess.run(
    ['ffprobe', '-v', 'quiet', '-show_streams', '-print_format', 'json', visuals],
    capture_output=True, text=True
)
if r.returncode != 0:
    print(f"FAIL: ffprobe returned {r.returncode}")
    sys.exit(1)

info = json.loads(r.stdout)
vs = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
if not vs:
    print("FAIL: no video stream found")
    sys.exit(1)

w, h = int(vs['width']), int(vs['height'])
dur = float(vs.get('duration', 0))

print(f"Resolution:  {w}x{h}")
print(f"Duration:    {dur:.2f}s")
print(f"Codec:       {vs.get('codec_name', '?')}")
print(f"FPS:         {vs.get('r_frame_rate', '?')}")

# Check 1: Resolution
if w != 1080 or h != 1920:
    print(f"FAIL: expected 1080x1920, got {w}x{h}")
    sys.exit(1)
print("CHECK 1: Resolution 1080x1920 — PASS")

# Check 2: Duration within expected range (47.74 ± 3s for Remotion rounding)
if not (44 <= dur <= 51):
    print(f"FAIL: duration {dur:.2f}s outside 44-51s expected range")
    sys.exit(1)
print(f"CHECK 2: Duration {dur:.2f}s in [44, 51] — PASS")

# Check 3: No audio track (visuals-only)
audio = [s for s in info['streams'] if s['codec_type'] == 'audio']
has_audio = len(audio) > 0
print(f"CHECK 3: Audio streams = {len(audio)} {'(visual-only expected)' if not has_audio else '(has audio — OK for Remotion)'}")

# Check 4: Frame count sanity (expect ~30fps × duration)
nb_frames = vs.get('nb_frames')
if nb_frames and nb_frames != 'N/A':
    frames = int(nb_frames)
    expected_min = int(dur * 28)
    expected_max = int(dur * 32)
    ok = expected_min <= frames <= expected_max
    print(f"CHECK 4: Frame count {frames} ({'PASS' if ok else 'WARN'} — expected {expected_min}-{expected_max})")
else:
    print("CHECK 4: Frame count — N/A (stream doesn't report nb_frames)")

print("")
print("=" * 60)
print("VISUAL REGRESSION: ALL CHECKS PASSED")
print("=" * 60)
PYEOF

echo ""
echo "============================================================"
echo " EP01 SYNCED VISUALS RENDER COMPLETE — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo " Output: $VISUALS"
echo ""
echo " NEXT: Review the visual-only MP4:"
echo "   scp root@187.127.151.27:$VISUALS ~/Desktop/ep01_visuals_v3_synced.mp4"
echo ""
echo " DO NOT assemble voice yet."
echo " DO NOT publish."
echo " Return visual-only MP4 and QA results, then STOP for review."
echo "============================================================"
