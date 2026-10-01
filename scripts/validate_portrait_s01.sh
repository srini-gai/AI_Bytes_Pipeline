#!/usr/bin/env bash
# validate_portrait_s01.sh
# Phase 3B: portrait orientation validation for s01 Higgsfield asset.
# Run on VPS as root from /root/ai_bytes_pipeline after `git pull`.
#
# Steps:
#   1. Schema probe — confirms aspect_ratio field is accepted (no generation cost)
#   2. Cost/budget check
#   3. ONE generation with aspect_ratio="9:16"
#   4. Portrait validation (height > width required)
#   5. Stage clip for Remotion
#   6. Render 5-second Remotion preview
#
# CONSTRAINTS:
#   - No aesthetic retries
#   - No crop workaround
#   - No full episode render
#   - No publish
set -euo pipefail

PROJECT=/root/ai_bytes_pipeline
ENV_FILE=/opt/aibytes/.env
CACHE_DIR="$PROJECT/output/generative_video_cache"
PREVIEW_OUT="$PROJECT/output/week_01/ep01/ep01_s01_preview.mp4"
REMOTION_CLIP="$PROJECT/remotion/public/clips/gen_video_s01.mp4"

cd "$PROJECT"
source "$ENV_FILE" 2>/dev/null || true

echo "=== Phase 3B: Portrait S01 Validation ==="
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# ── Step 1: Schema probe ───────────────────────────────────────────────────────
echo "--- Step 1: Schema probe (no generation cost) ---"
python3 - <<'PROBE_EOF'
import json, os, sys, urllib.request, urllib.error
from dotenv import load_dotenv
load_dotenv('/opt/aibytes/.env', override=True)

KEY_ID = os.getenv('HIGGSFIELD_API_KEY_ID', '')
KEY_SECRET = os.getenv('HIGGSFIELD_API_KEY_SECRET', '')
if not KEY_ID or not KEY_SECRET:
    print("ERROR: credentials not loaded — check /opt/aibytes/.env")
    sys.exit(1)

# Send minimal payload to trigger 422 validation error (reveals accepted fields)
payload = json.dumps({"aspect_ratio": "9:16"}).encode()
req = urllib.request.Request(
    "https://api.higgsfield.ai/kling-video/v3.0/std/text-to-video",
    data=payload,
    headers={
        "Authorization": f"Key {KEY_ID}:{KEY_SECRET}",
        "Content-Type": "application/json",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        body = r.read().decode()[:800]
        print(f"Schema probe: HTTP {r.status} — {body}")
        # 200 means a request was QUEUED — extract request_id for cancellation
        try:
            data = json.loads(body)
            rid = data.get("request_id") or data.get("id")
            if rid:
                print(f"WARNING: probe queued a request: {rid}")
                print("Attempting cancellation...")
                cancel_payload = json.dumps({}).encode()
                cancel_req = urllib.request.Request(
                    f"https://platform.higgsfield.ai/requests/{rid}/cancel",
                    data=cancel_payload,
                    headers={"Authorization": f"Key {KEY_ID}:{KEY_SECRET}"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(cancel_req, timeout=10) as cr:
                        print(f"Cancel response: HTTP {cr.status} {cr.read().decode()[:200]}")
                except urllib.error.HTTPError as ce:
                    print(f"Cancel: HTTP {ce.code} {ce.read().decode()[:200]}")
        except Exception:
            pass
except urllib.error.HTTPError as e:
    body = e.read().decode()[:800]
    print(f"Schema probe: HTTP {e.code}")
    print(f"Response: {body}")
    if e.code == 422:
        print("→ 422 = validation error reveals accepted fields (expected)")
    elif e.code == 400:
        print("→ 400 = bad request — inspect above for accepted/rejected fields")
    elif e.code == 404:
        print("→ 404 = endpoint not found — endpoint path may have changed")
    elif e.code == 401:
        print("→ 401 = credentials rejected")
PROBE_EOF

echo ""

# ── Step 2: Budget check + generation ─────────────────────────────────────────
echo "--- Step 2-4: Generation + portrait validation ---"
python3 - <<'GEN_EOF'
import hashlib, json, logging, os, sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)

sys.path.insert(0, '/root/ai_bytes_pipeline')
from dotenv import load_dotenv
load_dotenv('/opt/aibytes/.env', override=True)

from agents.providers.adapters.higgsfield import HiggsfieldAdapter
from agents.providers.base import GenerationRequest, GenerationType

adapter = HiggsfieldAdapter()
if not adapter.is_available():
    print("ERROR: HiggsfieldAdapter.is_available() returned False — credentials missing")
    sys.exit(1)

PROMPT = (
    "Abstract digital data stream, glowing blue and violet light particles "
    "flowing through dark space, representing neural network token processing, "
    "cinematic depth of field, smooth motion"
)

req = GenerationRequest(
    episode=1,
    scene_id="s01",
    generation_type=GenerationType.VIDEO,
    prompt_intent=PROMPT,
    duration_seconds=5.0,
    aspect_ratio="9:16",
    model="kling-v3.0-std",
)

ph = hashlib.sha256(PROMPT.strip().lower().encode()).hexdigest()

print("=== Generation metadata ===")
print(f"Provider:               Higgsfield")
print(f"Model:                  Kling 3.0 Standard")
print(f"Duration:               {req.duration_seconds}s")
print(f"Requested aspect ratio: {req.aspect_ratio}")
print(f"Sound:                  off (no audio in payload)")
print(f"multi_shots:            false")
print(f"Prompt hash:            {ph[:16]}...")
estimated = adapter.estimate_cost(req)
print(f"Estimated cost:         ${estimated:.4f}")
print()

result = adapter.generate(req)

print()
print("=== Result ===")
print(f"Asset path:   {result.asset_path}")
print(f"Resolution:   {result.width}x{result.height}")
print(f"Duration:     {result.duration_seconds}s")
print(f"Provider:     {result.provider}")
print(f"Model:        {result.model}")

portrait = (
    result.height is not None
    and result.width is not None
    and result.height > result.width
)
if portrait:
    print(f"Portrait:     YES ✓ ({result.height} > {result.width})")
else:
    print(f"Portrait:     NO — LANDSCAPE ({result.width}x{result.height})")
    print("STOP: asset is not portrait. No retry. Report returned resolution.")
    sys.exit(2)

if adapter.last_manifest_entry:
    e = adapter.last_manifest_entry
    print(f"Task ID:      {e.task_id}")
    print(f"Cache key:    {e.asset_id[:16]}...")
    print(f"Cache status: {e.cache_status}")
    print(f"Latency:      {e.generation_latency_seconds}s")
    print(f"Fallback:     {e.fallback_status}")

# Write cache key to temp file for the shell script to pick up
Path('/tmp/new_cache_key.txt').write_text(e.asset_id)
GEN_EOF

GEN_STATUS=$?
if [ $GEN_STATUS -eq 2 ]; then
    echo ""
    echo "STOP: Higgsfield returned landscape asset. No crop attempted. Stopping."
    exit 2
fi

# ── Step 5: Stage clip for Remotion ───────────────────────────────────────────
echo ""
echo "--- Step 5: Stage portrait clip for Remotion ---"
CACHE_KEY=$(cat /tmp/new_cache_key.txt 2>/dev/null || echo "")
if [ -z "$CACHE_KEY" ]; then
    echo "ERROR: could not read cache key"
    exit 1
fi
SRC="$CACHE_DIR/${CACHE_KEY}.mp4"
if [ ! -f "$SRC" ]; then
    echo "ERROR: cached clip not found at $SRC"
    exit 1
fi
cp "$SRC" "$REMOTION_CLIP"
echo "Staged: $(ls -lh "$REMOTION_CLIP")"

# ── Step 6: Render Remotion preview ───────────────────────────────────────────
echo ""
echo "--- Step 6: Render 5-second Remotion preview ---"

cat > /tmp/s01_preview_props.json << 'PROPS_EOF'
{
  "storyboard": {
    "episode": 1,
    "week": 1,
    "topic": "AI Doesn't Read Words — It Reads Tokens",
    "language": "en",
    "scenes": [
      {
        "id": "s01",
        "type": "hook",
        "durationSeconds": 5,
        "text": "AI doesn't read words.\nIt reads tokens.",
        "subtext": "",
        "highlightWord": ""
      }
    ]
  },
  "generatedVideoClips": {
    "s01": "clips/gen_video_s01.mp4"
  },
  "theme": {
    "bg": "#050510",
    "accent": "#a78bfa",
    "secondary": "#34d399"
  }
}
PROPS_EOF

mkdir -p "$PROJECT/output/week_01/ep01"

cd "$PROJECT/remotion"
npx remotion render src/index.ts AIBytesReel "$PREVIEW_OUT" \
    --props /tmp/s01_preview_props.json \
    --frames 0-149 \
    --log verbose \
    2>&1 | tail -40

echo ""
echo "--- Preview verification ---"
ffprobe -v quiet -print_format json -show_streams "$PREVIEW_OUT" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
vs = next((s for s in d['streams'] if s['codec_type']=='video'), {})
print('Preview resolution:', vs.get('width'), 'x', vs.get('height'))
print('Preview duration:  ', vs.get('duration'), 's')
print('Codec:             ', vs.get('codec_name'))
"
ls -lh "$PREVIEW_OUT"

echo ""
echo "=== Phase 3B portrait validation complete ==="
