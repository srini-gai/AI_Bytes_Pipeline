#!/usr/bin/env bash
# =============================================================================
# EP01 Full Episode Production Script — "AI Doesn't Read Words — It Reads Tokens"
# Run on VPS: bash vps_ep01_produce.sh  |  tee /root/ai_bytes_pipeline/ep01_produce.log
# =============================================================================
set -euo pipefail

PROJ="/root/ai_bytes_pipeline"
EP_DIR="$PROJ/output/week_01/ep01"
PROPS_FILE="$EP_DIR/ep01_render_props.json"
VISUALS="$EP_DIR/ep01_visuals.mp4"
FINAL="$EP_DIR/ep01_final_EN.mp4"

echo "============================================================"
echo " EP01 Full Episode Production — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "============================================================"

# ── 1. Pull latest code (includes KineticTypoScene + assembly fixes) ──────────
echo ""
echo "[1/5] Pulling latest code..."
cd "$PROJ" && git pull
echo "      Git HEAD: $(git rev-parse --short HEAD)"

# ── 2. Load environment ───────────────────────────────────────────────────────
echo ""
echo "[2/5] Loading .env from /opt/aibytes/.env"
set -a; source /opt/aibytes/.env; set +a

# ── 3. Write render props JSON ────────────────────────────────────────────────
echo ""
echo "[3/5] Writing Remotion render props to $PROPS_FILE"
mkdir -p "$EP_DIR"
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
    {"scene_id": 1, "duration_seconds": 3.0, "narration": "AI has never read a single word. Not one.", "scene_type": "HOOK", "visual_goal": "The word 'WORD' physically shatters mid-display", "component": "KineticTypoScene", "objects": ["word_text", "shatter_fragments", "not_one_label"], "animation": "Giant WORD slams onto screen, cracks and fragments", "on_screen_text": ["WORD", "NOT ONE."], "data": null, "transition": "cut", "carry_object_from": null, "beats": []},
    {"scene_id": 2, "duration_seconds": 7.0, "narration": "Before an LLM sees your text, a tokenizer splits it into chunks called tokens. A token isn't always a word. Unbelievable becomes three tokens: un, believ, able.", "scene_type": "DEMONSTRATION", "visual_goal": "Real English sentence visually splits into labelled token boxes", "component": "TokenScene", "objects": ["input_sentence", "token_boxes", "boundary_markers"], "animation": "Full sentence slides in, tokenizer beam scans", "on_screen_text": ["un", "believ", "able", "TOKENS ≠ WORDS"], "data": null, "transition": "morph", "carry_object_from": null, "beats": []},
    {"scene_id": 3, "duration_seconds": 5.0, "narration": "Every token gets mapped to an integer ID. The model processes numbers, not letters.", "scene_type": "TRANSFORMATION", "visual_goal": "Token boxes morph into glowing integer IDs", "component": "TransformScene", "objects": ["token_boxes", "integer_ids", "id_labels"], "animation": "Token boxes carry over, each box flips into glowing integer ID", "on_screen_text": ["un → 1726", "believ → 42891", "able → 481", "A LIST OF NUMBERS"], "data": null, "transition": "morph", "carry_object_from": "token_boxes", "beats": []},
    {"scene_id": 4, "duration_seconds": 5.0, "narration": "These IDs feed into an embedding layer, converting each into a vector.", "scene_type": "FLOW", "visual_goal": "Integer IDs transform into floating vector arrows then attention lines draw between them", "component": "NetworkBuildScene", "objects": ["id_nodes", "vector_arrows", "attention_lines", "transformer_label"], "animation": "ID column fans into horizontal row of ID nodes", "on_screen_text": ["INTEGER IDs", "EMBEDDING VECTORS", "ATTENTION"], "data": null, "transition": "fade", "carry_object_from": "integer_ids", "beats": []},
    {"scene_id": 5, "duration_seconds": 5.0, "narration": "The transformer attends to these vectors, predicting the next token one at a time.", "scene_type": "DEMONSTRATION", "visual_goal": "Tokens stream out one by one from the transformer", "component": "TokenStreamScene", "objects": ["transformer_core", "output_tokens", "token_cursor"], "animation": "Compact transformer block glows, tokens emit from right edge", "on_screen_text": ["NEXT TOKEN", "ONE AT A TIME"], "data": null, "transition": "slide-right", "carry_object_from": "attention_lines", "beats": []},
    {"scene_id": 6, "duration_seconds": 6.0, "narration": "Tokens drive cost and context. You pay per token. Context windows are measured in tokens, not words.", "scene_type": "COMPARISON", "visual_goal": "Side-by-side bar comparison of token cost across text types", "component": "DataScene", "source_type": "illustrative", "objects": ["text_examples", "token_bars", "cost_labels"], "animation": "Three rows appear staggered", "on_screen_text": ["English word", "Code snippet", "Rare / foreign word", "TOKEN COST"], "data": {"type": "bars", "title": "Relative Token Cost", "bars": [{"label": "English word", "value": 35}, {"label": "Code snippet", "value": 65}, {"label": "Rare / foreign word", "value": 85}]}, "transition": "fade", "carry_object_from": null, "beats": []},
    {"scene_id": 7, "duration_seconds": 4.0, "narration": "The longer your input, the more context you consume.", "scene_type": "DATA", "visual_goal": "A growing bar fills a context window gauge", "component": "NumberCounterScene", "source_type": "illustrative", "objects": ["counter_display", "unit_label", "context_label"], "animation": "Bar fills progressively to show context consumption", "on_screen_text": ["CONTEXT WINDOW", "TOKENS", "input length → context consumed"], "data": {"type": "counter", "value": 100, "label": "Context consumed", "suffix": "%"}, "transition": "zoom-in", "carry_object_from": null, "beats": []},
    {"scene_id": 8, "duration_seconds": 5.0, "narration": "Code and rare words cost more tokens. Write short, precise prompts — you're spending tokens.", "scene_type": "COMPARISON", "visual_goal": "Verbose prompt vs terse prompt token cost comparison", "component": "BeforeAfterScene", "source_type": "illustrative", "objects": ["verbose_panel", "terse_panel", "cost_indicator"], "animation": "Left panel verbose prompt red bar, right panel terse prompt green bar", "on_screen_text": ["VERBOSE PROMPT", "TERSE PROMPT", "MORE TOKENS", "FEWER TOKENS"], "data": null, "transition": "fade", "carry_object_from": null, "beats": []},
    {"scene_id": 9, "duration_seconds": 3.0, "narration": "AI processes tokens, not words directly.", "scene_type": "TAKEAWAY", "visual_goal": "Single bold takeaway line with token-box icon", "component": "TakeawayScene", "objects": ["token_icon", "takeaway_text", "underline_sweep"], "animation": "Small token box icon drops from top", "on_screen_text": ["AI processes TOKENS", "not words directly"], "data": null, "transition": "fade", "carry_object_from": null, "beats": []},
    {"scene_id": 10, "duration_seconds": 3.0, "narration": "Follow Srini on AI for practical AI, daily.", "scene_type": "CTA", "visual_goal": "Follow CTA — 3 seconds, clean", "component": "CTAScene", "objects": ["cta_label", "follow_button"], "animation": "Channel name and Follow pill rise from bottom", "on_screen_text": ["Follow Srini on AI", "for practical AI, daily."], "data": null, "transition": "fade", "carry_object_from": null, "beats": []}
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
echo "      Props written: $(wc -c < "$PROPS_FILE") bytes"

# Confirm Higgsfield clip exists
CLIP="$PROJ/remotion/public/clips/gen_video_s01.mp4"
if [ -f "$CLIP" ]; then
  echo "      ✓ Higgsfield s01 clip present: $(du -h "$CLIP" | cut -f1)"
else
  echo "      ✗ ERROR: Higgsfield clip NOT found at $CLIP"
  echo "      Run: ls $PROJ/remotion/public/clips/ to diagnose"
  exit 1
fi

# ── 4. Render visuals via Remotion ────────────────────────────────────────────
echo ""
echo "[4/5] Rendering visuals (Remotion)..."
cd "$PROJ/remotion"
npm install --silent 2>&1 | tail -3
echo "      Starting npx remotion render..."
npx remotion render AIBytesReel "$VISUALS" \
  --props="$PROPS_FILE" \
  --concurrency=2 \
  2>&1
echo "      Render complete."

# Validate visuals dimensions + duration
python3 - <<PYEOF
import subprocess, json, sys
r = subprocess.run(
    ['ffprobe','-v','quiet','-show_streams','-print_format','json', '$VISUALS'],
    capture_output=True, text=True
)
info = json.loads(r.stdout)
vs = next(s for s in info['streams'] if s['codec_type']=='video')
w, h = int(vs['width']), int(vs['height'])
dur = float(vs.get('duration', 0))
print(f"      Visuals probe: {w}x{h}, {dur:.2f}s")
if w != 1080 or h != 1920:
    print(f"      FAIL: expected 1080x1920, got {w}x{h}")
    sys.exit(1)
if not (40 <= dur <= 65):
    print(f"      FAIL: duration {dur:.2f}s outside 40-65s")
    sys.exit(1)
print("      ✓ Visuals PASS")
PYEOF

# ── 5. Voice + Assembly via Python agents ─────────────────────────────────────
echo ""
echo "[5/5] Running voice_agent + assembly_agent..."
cd "$PROJ"
python3 - <<'PYEOF'
import sys, json, logging
sys.path.insert(0, '/root/ai_bytes_pipeline')
from dotenv import load_dotenv
load_dotenv('/opt/aibytes/.env', override=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# Load script
with open('/root/ai_bytes_pipeline/output/week_01/ep01/ep01_script_EN.json') as f:
    script = json.load(f)

# Voice agent
log.info("--- voice_agent start ---")
from agents import voice_agent
voice_result = voice_agent.run(script=script, episode=1, week=1, lang='en')
log.info(f"Voice: {voice_result['output_path']}  duration={voice_result['duration']:.1f}s")
print(f"VOICE_PATH={voice_result['output_path']}")
print(f"VOICE_DURATION={voice_result['duration']:.2f}")

# Assembly agent
log.info("--- assembly_agent start ---")
from agents import assembly_agent
asm_result = assembly_agent.run(episode=1, week=1, lang='en')
log.info(f"Assembly: {asm_result.get('output_path')}  duration={asm_result.get('duration','?')}s  size={asm_result.get('size_mb','?')}MB")
print(f"FINAL_PATH={asm_result.get('output_path')}")
print(f"FINAL_DURATION={asm_result.get('duration','?')}")
print(f"FINAL_SIZE_MB={asm_result.get('size_mb','?')}")
print("ASSEMBLY_SUCCESS=true")
PYEOF

echo ""
echo "============================================================"
echo " EP01 PRODUCTION COMPLETE — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo " Visuals:  $VISUALS"
echo " Final:    $FINAL"
echo " DO NOT PUBLISH — stop for visual review"
echo "============================================================"
