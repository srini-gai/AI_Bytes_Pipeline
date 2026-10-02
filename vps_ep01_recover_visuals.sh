#!/usr/bin/env bash
# =============================================================================
# EP01 RECOVERY RENDER — Visuals only, stop before assembly/publish
# Fixes: legacy-mode 60s ep01_final_EN.mp4 was stale; visuals must be re-rendered
# with storyboard v3.2 (10 scenes) and the cached Higgsfield s01 clip.
#
# Run on VPS: bash vps_ep01_recover_visuals.sh | tee /root/ai_bytes_pipeline/ep01_recover.log
#
# STOPS BEFORE: voice synthesis, assembly, publishing.
# ACTION REQUIRED: scp the resulting ep01_visuals.mp4 to your local machine for review.
# =============================================================================
set -euo pipefail

PROJ="/root/ai_bytes_pipeline"
EP_DIR="$PROJ/output/week_01/ep01"
PROPS_FILE="$EP_DIR/ep01_render_props.json"
VISUALS="$EP_DIR/ep01_visuals.mp4"
FINAL="$EP_DIR/ep01_final_EN.mp4"

echo "============================================================"
echo " EP01 RECOVERY RENDER — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo " Goal: correct 45s storyboard-v3 visuals"
echo " DO NOT PUBLISH — stop for visual review"
echo "============================================================"

# ── 1. Pull latest code (render-mode guard + stale-final fix) ─────────────────
echo ""
echo "[1/4] Pulling latest code..."
cd "$PROJ" && git pull
echo "      Git HEAD: $(git rev-parse --short HEAD)"

# ── 2. Load environment ───────────────────────────────────────────────────────
echo ""
echo "[2/4] Loading .env from /opt/aibytes/.env"
set -a; source /opt/aibytes/.env; set +a

# ── 3. Write render props JSON (10-scene Tokens v3.2 storyboard) ─────────────
echo ""
echo "[3/4] Writing Remotion render props to $PROPS_FILE"
mkdir -p "$EP_DIR"
cat > "$PROPS_FILE" << 'ENDJSON'
{
  "episode": 1,
  "topic": "How AI Actually Reads Your Text",
  "title": "AI Has Never Read a Single Word",
  "hook": "AI has never read a single word. Not one.",
  "concept": "Tokenization — how LLMs convert text to token IDs before processing",
  "voiceover": "AI has never read a single word. Not one. Before an LLM sees your text, it runs a tokenizer. The tokenizer splits your sentence into chunks — tokens. A token is not a word. It could be half a word, punctuation, or a space. Unbelievable becomes three tokens: un, believ, able. ChatGPT is two tokens. An emoji is one. Every token gets mapped to an integer ID. That's what the model processes — numbers, not letters. These numbers feed an embedding layer, converting each ID into a high-dimensional vector. The transformer works on these vectors, attending to each other, predicting the next token one at a time. Token count matters for cost and context. You pay per token. Context windows are measured in tokens — not words. GPT-4 Turbo has 128,000 tokens of context. Code and rare words cost more. So write short, precise prompts — you're spending tokens. The model reads integers, not language. Follow Srini on AI for practical AI, daily.",
  "takeaway": "AI reads tokens, not words. Tokens = the true unit of LLM thinking.",
  "tags": "#SriniOnAI #Tokenization #LLM #GenerativeAI #AIShorts",
  "slides": [],
  "storyboard": [
    {"scene_id": 1, "duration_seconds": 3.0, "narration": "AI has never read a single word. Not one.", "scene_type": "HOOK", "visual_goal": "The word 'WORD' physically shatters mid-display", "component": "KineticTypoScene", "objects": ["word_text", "shatter_fragments", "not_one_label"], "animation": "Giant WORD slams onto screen, cracks and fragments", "on_screen_text": ["WORD", "NOT ONE."], "data": null, "transition": "cut", "carry_object_from": null, "beats": []},
    {"scene_id": 2, "duration_seconds": 5.0, "narration": "Before an LLM sees your text, it runs it through a tokenizer.", "scene_type": "DEMONSTRATION", "visual_goal": "Real English sentence visually splits into labelled token boxes", "component": "TokenScene", "objects": ["input_sentence", "token_boxes", "boundary_markers"], "animation": "Full sentence slides in, tokenizer beam scans", "on_screen_text": ["un", "believ", "able", "TOKENS ≠ WORDS"], "data": null, "transition": "morph", "carry_object_from": null, "beats": []},
    {"scene_id": 3, "duration_seconds": 5.0, "narration": "Every token gets mapped to an integer ID.", "scene_type": "TRANSFORMATION", "visual_goal": "Token boxes morph into glowing integer IDs", "component": "TransformScene", "objects": ["token_boxes", "integer_ids", "id_labels"], "animation": "Token boxes carry over, each box flips into glowing integer ID", "on_screen_text": ["un → 1726", "believ → 42891", "able → 481", "A LIST OF NUMBERS"], "data": null, "transition": "morph", "carry_object_from": "token_boxes", "beats": []},
    {"scene_id": 4, "duration_seconds": 5.5, "narration": "These numbers feed into an embedding layer.", "scene_type": "FLOW", "visual_goal": "Integer IDs transform into floating vector arrows then attention lines draw between them", "component": "NetworkBuildScene", "objects": ["id_nodes", "vector_arrows", "attention_lines", "transformer_label"], "animation": "ID column fans into horizontal row of ID nodes", "on_screen_text": ["INTEGER IDs", "EMBEDDING VECTORS", "ATTENTION"], "data": null, "transition": "fade", "carry_object_from": "integer_ids", "beats": []},
    {"scene_id": 5, "duration_seconds": 4.5, "narration": "To predict the next token, one at a time.", "scene_type": "DEMONSTRATION", "visual_goal": "Tokens stream out one by one from the transformer", "component": "TokenStreamScene", "objects": ["transformer_core", "output_tokens", "token_cursor"], "animation": "Compact transformer block glows, tokens emit from right edge", "on_screen_text": ["NEXT TOKEN", "ONE AT A TIME"], "data": null, "transition": "slide-right", "carry_object_from": "attention_lines", "beats": []},
    {"scene_id": 6, "duration_seconds": 5.5, "narration": "A token is not always a word. Code and rare words cost more.", "scene_type": "COMPARISON", "visual_goal": "Side-by-side bar comparison of token cost across text types", "component": "DataScene", "source_type": "illustrative", "objects": ["text_examples", "token_bars", "cost_labels"], "animation": "Three rows appear staggered", "on_screen_text": ["English word", "Code snippet", "Rare / foreign word", "TOKEN COST"], "data": {"type": "bars", "title": "Relative Token Cost", "bars": [{"label": "English word", "value": 35}, {"label": "Code snippet", "value": 65}, {"label": "Rare / foreign word", "value": 85}]}, "transition": "fade", "carry_object_from": null, "beats": []},
    {"scene_id": 7, "duration_seconds": 4.5, "narration": "GPT-4 Turbo has a 128,000 token context window.", "scene_type": "DATA", "visual_goal": "A large number counts up to 128,000", "component": "NumberCounterScene", "source_type": "sourced_numeric", "source_reference": "OpenAI GPT-4 Turbo model card", "objects": ["counter_display", "unit_label", "context_label"], "animation": "Counter starts at 0, rapidly counts up to 128,000", "on_screen_text": ["128,000", "TOKENS", "context window"], "data": {"type": "counter", "value": 128000, "label": "GPT-4 Turbo context window", "suffix": " tokens"}, "transition": "zoom-in", "carry_object_from": null, "beats": []},
    {"scene_id": 8, "duration_seconds": 5.0, "narration": "You pay per token. Short, precise prompts save money.", "scene_type": "COMPARISON", "visual_goal": "Verbose prompt vs terse prompt token cost comparison", "component": "BeforeAfterScene", "source_type": "illustrative", "objects": ["verbose_panel", "terse_panel", "cost_indicator"], "animation": "Left panel verbose prompt red bar, right panel terse prompt green bar", "on_screen_text": ["VERBOSE PROMPT", "TERSE PROMPT", "MORE TOKENS", "FEWER TOKENS"], "data": null, "transition": "fade", "carry_object_from": null, "beats": []},
    {"scene_id": 9, "duration_seconds": 4.0, "narration": "AI reads tokens, not words. Tokens are the true unit of LLM thinking.", "scene_type": "TAKEAWAY", "visual_goal": "Single bold takeaway line with token-box icon", "component": "TakeawayScene", "objects": ["token_icon", "takeaway_text", "underline_sweep"], "animation": "Small token box icon drops from top", "on_screen_text": ["AI reads TOKENS", "not words"], "data": null, "transition": "fade", "carry_object_from": null, "beats": []},
    {"scene_id": 10, "duration_seconds": 3.0, "narration": "Follow for practical AI, daily.", "scene_type": "CTA", "visual_goal": "Follow CTA — 3 seconds, clean", "component": "CTAScene", "objects": ["cta_label", "follow_button"], "animation": "Channel name and Follow pill rise from bottom", "on_screen_text": ["Follow for practical AI, daily."], "data": null, "transition": "fade", "carry_object_from": null, "beats": []}
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

# Confirm Higgsfield clip exists (DO NOT regenerate)
CLIP="$PROJ/remotion/public/clips/gen_video_s01.mp4"
if [ -f "$CLIP" ]; then
  echo "      ✓ Higgsfield s01 clip present (cached, no new generation): $(du -h "$CLIP" | cut -f1)"
else
  echo "      ✗ ERROR: Higgsfield clip NOT found at $CLIP"
  echo "        Cache key: 4856fe4c7d9a5f7dc3ae7301852f4a27b3e42a1b5b20dedea4a867479e29d22e"
  echo "        Restore from: ls $PROJ/remotion/public/clips/"
  exit 1
fi

# Print pre-render mode declaration
echo ""
echo "VISUAL_RENDER_MODE=STORYBOARD_V3"
echo "SCENES=10"
echo "COMPONENT_SEQUENCE: KineticTypoScene -> TokenScene -> TransformScene -> NetworkBuildScene -> TokenStreamScene -> DataScene -> NumberCounterScene -> BeforeAfterScene -> TakeawayScene -> CTAScene"
echo ""
echo "Scene | Component              | Duration | Asset source"
echo "------|------------------------|----------|---------------------------"
echo "s01   | KineticTypoScene       |     3.0s | HIGGSFIELD cached → clips/gen_video_s01.mp4"
echo "s02   | TokenScene             |     5.0s | Remotion dark bg"
echo "s03   | TransformScene         |     5.0s | Remotion dark bg"
echo "s04   | NetworkBuildScene      |     5.5s | Remotion dark bg"
echo "s05   | TokenStreamScene       |     4.5s | Remotion dark bg"
echo "s06   | DataScene              |     5.5s | Remotion dark bg"
echo "s07   | NumberCounterScene     |     4.5s | Remotion dark bg"
echo "s08   | BeforeAfterScene       |     5.0s | Remotion dark bg"
echo "s09   | TakeawayScene          |     4.0s | Remotion dark bg"
echo "s10   | CTAScene               |     3.0s | Remotion dark bg"
echo "------|------------------------|----------|---------------------------"
echo "TOTAL |                        |    45.0s |"
echo ""

# ── 4. Delete stale visuals to force re-render ────────────────────────────────
echo "[4/4] Rendering visuals via Remotion (storyboard_v3)..."
if [ -f "$VISUALS" ]; then
  echo "      Removing stale ep01_visuals.mp4 to force fresh render..."
  rm -f "$VISUALS"
fi
# Also remove stale final so assembly_agent won't skip it on next run
if [ -f "$FINAL" ]; then
  echo "      Removing stale ep01_final_EN.mp4 (legacy 60s) — will be re-assembled on next pass"
  rm -f "$FINAL"
fi

cd "$PROJ/remotion"
npm install --silent 2>&1 | tail -3
echo "      Starting npx remotion render with --props storyboard..."
npx remotion render AIBytesReel "$VISUALS" \
  --props="$PROPS_FILE" \
  --concurrency=2 \
  2>&1
echo "      Render complete."

# Validate visuals
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
if not (40 <= dur <= 55):
    print(f"      FAIL: duration {dur:.2f}s outside 40-55s (expected ~45s for storyboard)")
    sys.exit(1)
print(f"      ✓ Visuals PASS — {dur:.2f}s (storyboard_v3 render confirmed)")
PYEOF

echo ""
echo "============================================================"
echo " EP01 RECOVERY RENDER COMPLETE — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo " Visuals: $VISUALS"
echo ""
echo " NEXT: scp the file to your local machine for visual review:"
echo "   scp root@187.127.151.27:$VISUALS ~/Desktop/ep01_visuals_v3.mp4"
echo ""
echo " If visuals pass review, run assembly only:"
echo "   cd $PROJ && python3 -c \""
echo "   import sys, json, logging"
echo "   sys.path.insert(0, '$PROJ')"
echo "   from dotenv import load_dotenv; load_dotenv('/opt/aibytes/.env', override=True)"
echo "   logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')"
echo "   from agents import assembly_agent"
echo "   r = assembly_agent.run(episode=1, week=1, lang='en')"
echo "   print(r)"
echo "   \""
echo ""
echo " DO NOT PUBLISH — stop for visual review"
echo "============================================================"
