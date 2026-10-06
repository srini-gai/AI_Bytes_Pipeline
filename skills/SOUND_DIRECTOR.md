# Sound Director — Global Rules
# Srini on AI — YouTube Shorts

> Version: v1.0 — planning layer only (no generation, no mixing)

Sound is added only where it **materially improves comprehension or attention**.
It is never added automatically to every animation, text entrance or transition.

---

## Inputs are locked

The Sound Director plans against an approved, frozen episode:

- canonical narration hash (= storyboard = voice-source hash)
- locked voice file + measured duration and Whisper word timings
- synchronized visual render identity (`ep{NN}_visuals.meta.json`) and scene boundaries
- Art Director world (`art_direction`)

It must not change narration, voice, scene timing, visuals, captions, Art Director or
Visual Director output. A plan records these identities; if any changes, the plan is stale.

---

## Classification (every candidate event)

| Class | Use |
|---|---|
| `SEMANTIC_SFX` | The sound carries meaning the viewer should notice (a rejection, a hand-off, a completion). |
| `AMBIENT` | Continuous low-level texture that sets the world (rarely needed). |
| `TRANSITION` | Marks a structural change between scenes — only when the cut itself needs help. |
| `NONE` | No sound. **The default.** Most visual events stay silent. |

Target **5–8 meaningful SFX events** per ~45–60 s Short. Repeating one confirmation
(e.g. a checklist tick) counts as one event.

## Placement rules

- Sync to the **visual** state change, not to a word.
- Prefer natural speech gaps (from Whisper word timings) for anything louder than a tick.
- Never stack two cues within ~0.4 s unless they are one designed gesture.
- Deliberate silence is a tool: a "waiting" chatbot moment should stay silent.
- No whoosh on transitions, no click per text appearance, no sound per beat.

## Sound identity follows the Art Director world

| World | Prefer | Avoid |
|---|---|---|
| `bright-workspace` | clean, modern, tactile, light UI / productivity sounds, subtle digital texture, restrained confirmations | trailer booms, sci-fi lasers, gaming sounds, aggressive cyber FX, whooshes |
| `cinematic-dark` | (to be defined when a dark episode is sound-designed) | |

## Mix rules (for the future mixing stage)

- Voice is the reference and is **never ducked**.
- SFX sit below voice: ticks/blips about −18 to −22 dB relative to voice; emphasis
  cues (stamp, completion) about −10 to −14 dB; cues inside speech gaps may sit higher.
- Any music bed is side-chain ducked under voice and may rise in the CTA hold.
- Final master target: YouTube ≈ −14 LUFS integrated, true peak ≤ −1 dBTP.

## Generation (later stage)

- ElevenLabs Sound Effects, fixed duration per asset (cheaper and predictable than auto).
- One asset per distinct sound; reuse an asset for repeated cues.
- Cache generated assets by prompt+duration hash; never regenerate an approved asset.
