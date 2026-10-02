#!/usr/bin/env bash
# =============================================================================
# EP01 Voice B Generation + Whisper Timing Report
# Run on VPS: bash vps_ep01_voice_timing.sh | tee /root/ai_bytes_pipeline/ep01_voice_timing.log
#
# This script:
#   1. Generates Voice B audio via ElevenLabs (canonical 131-word script)
#   2. Runs Whisper for word-level timestamps
#   3. Maps words to canonical scene narrations
#   4. Reports measured timing per scene
#   5. Shows three-hash consistency check
#   6. Shows projected VOICE_VISUAL_SYNC result
#
# STOPS BEFORE RENDER — review measured timing before proceeding.
# =============================================================================
set -euo pipefail

PROJ="/root/ai_bytes_pipeline"
EP_DIR="$PROJ/output/week_01/ep01"

echo "============================================================"
echo " EP01 Voice B + Whisper Timing — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo " STOP BEFORE RENDER — timing review only"
echo "============================================================"

# ── 1. Pull latest code ─────────────────────────────────────────────────────
echo ""
echo "[1/3] Pulling latest code..."
cd "$PROJ" && git pull
echo "      Git HEAD: $(git rev-parse --short HEAD)"

# ── 2. Load environment ─────────────────────────────────────────────────────
echo ""
echo "[2/3] Loading .env from /opt/aibytes/.env"
set -a; source /opt/aibytes/.env; set +a

# ── 3. Generate voice + Whisper timing ───────────────────────────────────────
echo ""
echo "[3/3] Running voice generation + Whisper word timing..."
cd "$PROJ"
python3 << 'PYEOF'
import sys
import json
import hashlib
import logging
from pathlib import Path

sys.path.insert(0, '/root/ai_bytes_pipeline')
from dotenv import load_dotenv
load_dotenv('/opt/aibytes/.env', override=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

EP_DIR = Path("/root/ai_bytes_pipeline/output/week_01/ep01")

# ── Load canonical script ────────────────────────────────────────────────────
script_path = EP_DIR / "ep01_script_EN.json"
with open(script_path) as f:
    script = json.load(f)

canonical_voiceover = script["voiceover"].strip()
canon_hash = hashlib.sha256(canonical_voiceover.encode("utf-8")).hexdigest()[:16]
word_count = len(canonical_voiceover.split())

print(f"\n{'='*60}")
print(f"CANONICAL SCRIPT")
print(f"{'='*60}")
print(f"Hash:       {canon_hash}")
print(f"Words:      {word_count}")
print(f"Text:       {canonical_voiceover[:80]}...")

# ── Delete cached voice to force regeneration ────────────────────────────────
voice_path = EP_DIR / "ep01_voice_EN.mp3"
if voice_path.exists():
    log.info("Removing cached voice MP3 to force regeneration with new canonical text")
    voice_path.unlink()

# ── Generate Voice B ─────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"VOICE B GENERATION")
print(f"{'='*60}")

from agents import voice_agent
voice_result = voice_agent.run(script=script, episode=1, week=1, lang='en')

voice_duration = voice_result["duration"]
voice_hash = voice_result["voice_source_hash"]

print(f"Voice path:     {voice_result['output_path']}")
print(f"Voice duration: {voice_duration:.2f}s")
print(f"Voice hash:     {voice_hash}")
print(f"Hash match:     {'PASS' if voice_hash == canon_hash else 'FAIL'}")

# ── Run Whisper for word-level timestamps ────────────────────────────────────
print(f"\n{'='*60}")
print(f"WHISPER WORD TIMESTAMPS")
print(f"{'='*60}")

import whisper

log.info("Loading Whisper base model...")
model = whisper.load_model("base")

log.info("Transcribing with word_timestamps=True...")
result = model.transcribe(
    str(voice_path),
    word_timestamps=True,
    language="en",
)

# Extract all word-level timestamps
words_with_times = []
for segment in result["segments"]:
    for word_info in segment.get("words", []):
        words_with_times.append({
            "word": word_info["word"].strip(),
            "start": word_info["start"],
            "end": word_info["end"],
        })

print(f"Total words detected: {len(words_with_times)}")
print(f"First word: '{words_with_times[0]['word']}' at {words_with_times[0]['start']:.2f}s")
print(f"Last word:  '{words_with_times[-1]['word']}' ends at {words_with_times[-1]['end']:.2f}s")

# Save Whisper word timestamps for reference
whisper_path = EP_DIR / "ep01_whisper_words.json"
with open(whisper_path, "w") as f:
    json.dump(words_with_times, f, indent=2)
print(f"Saved: {whisper_path}")

# ── Map words to canonical scene narrations ──────────────────────────────────
print(f"\n{'='*60}")
print(f"SCENE-BY-SCENE MEASURED TIMING")
print(f"{'='*60}")

# Canonical scene narrations (approved mapping)
scene_narrations = [
    {"scene": "s01", "component": "KineticTypoScene",  "narration": "AI has never read a single word. Not one."},
    {"scene": "s02", "component": "TokenScene",         "narration": "Before an LLM sees your text, a tokenizer splits it into chunks called tokens. A token isn't always a word. Unbelievable becomes three tokens: un, believ, able."},
    {"scene": "s03", "component": "TransformScene",     "narration": "Every token gets mapped to an integer ID. The model processes numbers, not letters."},
    {"scene": "s04", "component": "NetworkBuildScene",   "narration": "These IDs feed into an embedding layer, converting each into a vector."},
    {"scene": "s05", "component": "TokenStreamScene",    "narration": "The transformer attends to these vectors, predicting the next token one at a time."},
    {"scene": "s06", "component": "DataScene",           "narration": "Tokens drive cost and context. You pay per token. Context windows are measured in tokens, not words."},
    {"scene": "s07", "component": "NumberCounterScene",  "narration": "The longer your input, the more context you consume."},
    {"scene": "s08", "component": "BeforeAfterScene",    "narration": "Code and rare words cost more tokens. Write short, precise prompts — you're spending tokens."},
    {"scene": "s09", "component": "TakeawayScene",       "narration": "AI processes tokens, not words directly."},
    {"scene": "s10", "component": "CTAScene",            "narration": "Follow Srini on AI for practical AI, daily."},
]

# Build a flat list of canonical words in order
canonical_words = canonical_voiceover.split()

# Map each Whisper word to its index in the canonical word list
# Use a greedy forward-match: walk through canonical words and Whisper words together
def normalize(w):
    """Normalize word for matching — lowercase, strip punctuation."""
    import re
    return re.sub(r'[^a-z0-9]', '', w.lower())

# Build scene word boundaries from canonical text
scene_word_ranges = []
word_idx = 0
for sn in scene_narrations:
    scene_words = sn["narration"].split()
    start_idx = word_idx
    end_idx = word_idx + len(scene_words) - 1
    scene_word_ranges.append({
        "scene": sn["scene"],
        "component": sn["component"],
        "narration": sn["narration"],
        "word_count": len(scene_words),
        "canonical_start_idx": start_idx,
        "canonical_end_idx": end_idx,
    })
    word_idx += len(scene_words)

print(f"Total canonical words: {word_idx}")
print(f"Total Whisper words:   {len(words_with_times)}")

# Map Whisper words to canonical words using greedy alignment
# Whisper may merge/split words differently, so we do fuzzy matching
whisper_idx = 0
scene_timings = []

for sr in scene_word_ranges:
    scene_start_time = None
    scene_end_time = None

    # Count how many canonical words this scene has
    n_words = sr["word_count"]

    # Find the Whisper words that correspond to this scene's canonical words
    # We consume Whisper words greedily, matching against canonical words
    canonical_scene_words = sr["narration"].split()
    matched_whisper_words = []

    canon_ptr = 0  # pointer into canonical_scene_words
    whisper_consumed = 0

    while canon_ptr < len(canonical_scene_words) and whisper_idx < len(words_with_times):
        w = words_with_times[whisper_idx]
        norm_whisper = normalize(w["word"])
        norm_canon = normalize(canonical_scene_words[canon_ptr])

        if scene_start_time is None:
            scene_start_time = w["start"]

        scene_end_time = w["end"]
        matched_whisper_words.append(w)
        whisper_idx += 1
        whisper_consumed += 1

        # Check if this Whisper word matches the canonical word
        if norm_whisper == norm_canon:
            canon_ptr += 1
        elif norm_canon.startswith(norm_whisper):
            # Whisper split a word — keep consuming until we match
            accumulated = norm_whisper
            while accumulated != norm_canon and whisper_idx < len(words_with_times):
                w2 = words_with_times[whisper_idx]
                accumulated += normalize(w2["word"])
                scene_end_time = w2["end"]
                matched_whisper_words.append(w2)
                whisper_idx += 1
                whisper_consumed += 1
                if norm_canon in accumulated:
                    break
            canon_ptr += 1
        else:
            # Best effort — advance canonical pointer
            canon_ptr += 1

    duration = (scene_end_time - scene_start_time) if scene_start_time is not None and scene_end_time is not None else 0.0

    scene_timings.append({
        "scene": sr["scene"],
        "component": sr["component"],
        "word_count": sr["word_count"],
        "start": scene_start_time or 0.0,
        "end": scene_end_time or 0.0,
        "measured_duration": duration,
        "whisper_words_consumed": whisper_consumed,
    })

# Print measured timing table
print(f"\n{'Scene':<6} {'Component':<22} {'Words':>5} {'Start':>7} {'End':>7} {'Duration':>8}")
print(f"{'-'*6} {'-'*22} {'-'*5} {'-'*7} {'-'*7} {'-'*8}")
total_measured = 0.0
for st in scene_timings:
    print(f"{st['scene']:<6} {st['component']:<22} {st['word_count']:>5} {st['start']:>7.2f} {st['end']:>7.2f} {st['measured_duration']:>7.2f}s")
    total_measured += st['measured_duration']
print(f"{'-'*6} {'-'*22} {'-'*5} {'-'*7} {'-'*7} {'-'*8}")
print(f"{'TOTAL':<6} {'':22} {word_idx:>5} {'0.00':>7} {scene_timings[-1]['end']:>7.2f} {total_measured:>7.2f}s")

# Save timing report
timing_path = EP_DIR / "ep01_scene_timing.json"
with open(timing_path, "w") as f:
    json.dump(scene_timings, f, indent=2)
print(f"\nSaved: {timing_path}")

# ── Three-hash consistency check ─────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"THREE-HASH CONSISTENCY CHECK")
print(f"{'='*60}")

# 1. Canonical script hash
print(f"canonical_script_hash:       {canon_hash}")

# 2. Storyboard narration hash (from concatenated scene narrations)
storyboard_concat = " ".join(sn["narration"] for sn in scene_narrations)
sb_hash = hashlib.sha256(storyboard_concat.encode("utf-8")).hexdigest()[:16]
print(f"storyboard_narration_hash:   {sb_hash}")

# 3. Voice source hash (saved by voice_agent)
print(f"voice_source_hash:           {voice_hash}")

all_match = (canon_hash == sb_hash == voice_hash)
print(f"\nTHREE_HASH_CHECK = {'PASS ✓' if all_match else 'FAIL ✗'}")
if not all_match:
    if canon_hash != sb_hash:
        print(f"  MISMATCH: canonical != storyboard")
    if canon_hash != voice_hash:
        print(f"  MISMATCH: canonical != voice")
    if sb_hash != voice_hash:
        print(f"  MISMATCH: storyboard != voice")

# ── Projected VOICE_VISUAL_SYNC ──────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"VOICE_VISUAL_SYNC PROJECTION")
print(f"{'='*60}")

# Estimated visual duration from storyboard durations
estimated_visual_durations = [3.0, 7.0, 5.0, 5.0, 5.0, 6.0, 4.0, 5.0, 3.0, 3.0]
estimated_visual_total = sum(estimated_visual_durations)

print(f"Voice duration:              {voice_duration:.2f}s")
print(f"Estimated visual duration:   {estimated_visual_total:.1f}s (storyboard sum)")
print(f"Difference:                  {abs(voice_duration - estimated_visual_total):.2f}s")
print(f"Tolerance:                   2.0s")

sync_pass = abs(voice_duration - estimated_visual_total) <= 2.0
print(f"\nVOICE_VISUAL_SYNC (projected) = {'PASS ✓' if sync_pass else 'FAIL ✗'}")

if not sync_pass:
    print(f"\n  ⚠ Scene durations will need adjustment based on measured timing.")
    print(f"  The measured word timestamps above show actual narration timing per scene.")
    print(f"  Update storyboard scene durations to match measured narration + breathing room.")

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"SUMMARY — STOP FOR REVIEW")
print(f"{'='*60}")
print(f"Canonical script:    131 words, hash {canon_hash}")
print(f"Voice B duration:    {voice_duration:.2f}s")
print(f"Three-hash check:    {'PASS' if all_match else 'FAIL'}")
print(f"Sync projection:     {'PASS' if sync_pass else 'FAIL — adjust scene durations'}")
print(f"")
print(f"Files generated:")
print(f"  Voice:   {voice_result['output_path']}")
print(f"  Hash:    {EP_DIR}/ep01_voice_hash_EN.txt")
print(f"  Whisper: {whisper_path}")
print(f"  Timing:  {timing_path}")
print(f"")
print(f"DO NOT RENDER YET — review measured voice-to-scene timeline first.")
PYEOF

echo ""
echo "============================================================"
echo " EP01 Voice Timing Report Complete — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo " Review the measured timing above before proceeding to render."
echo " DO NOT RENDER — stop for review"
echo "============================================================"
