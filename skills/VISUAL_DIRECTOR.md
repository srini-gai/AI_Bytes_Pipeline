# Visual Director — Global Rules
# Srini on AI — YouTube Shorts

> Version: v3.2 — Known-Good Baseline  
> Promoted from: RAG reference episode (rag_v32_recovery_draft.mp4, commit 45d1e20)  
> Tag: `v3.2-known-good`

These rules apply to **every future Short** produced by the Visual Director.
They are principles, not RAG-specific implementations.
The Visual Director must dynamically choose scenes appropriate to the concept.

---

## Baseline protection

Before modifying shared rendering infrastructure:

1. Retain the `v3.2-known-good` git tag as rollback point
2. Make the change
3. Render a regression sample
4. Run `python regression_guard.py` — all scenes must PASS
5. Only then promote the change

The following are **frozen** and must not be modified as part of any visual
Director update:

- `agents/voice_agent.py`
- `agents/assembly_agent.py`
- `agents/publisher_agent.py`
- Pipeline scheduling / orchestrator phases

The RAG reference episode renderer and storyboard are frozen at commit `45d1e20`.
Do **not** alter `remotion/src/rag_v3_storyboard.json` or any component
behaviour for the purpose of fixing another episode.

---

## Duration and pacing

| Param | Value |
|---|---|
| Target duration | 45–60 seconds |
| CTA | ≤ 3 seconds, always last |
| Hook | ≤ 4 seconds |
| Visual change cadence | One meaningful visual event every 2–4 seconds |
| Minimum visual beats per Short | ≥ 10 |
| Typography-only runtime cap | ≤ 25 % of total |

---

## Composition defaults

- **Format**: mobile-first 9:16, 1080 × 1920, 30 fps
- **Frame 1**: meaningful visual content from frame 1 — no empty openers
- **Objects**: one large dominant focal object per scene; full-canvas compositions
- **Narration vs visuals**: complement, never duplicate — visuals demonstrate, voice explains
- **Explanation cards**: forbidden — no paragraph-style static text cards
- **Camera**: camera-led focus where it clarifies; information physically moves / transforms
- **Continuity**: carry objects between scenes where the concept flows naturally
- **Labels**: readable on a 6-inch phone at arm's length; ≤ 6 words per on-screen label
- **Empty transitions**: minimise unintended background-only frames; CROSSFADE = 9 (0.3 s at 30 fps)
- **Creator/profile photo**: disabled until further notice

---

## Visual variety — scene selection

The Visual Director must choose the scene type that best fits the **concept being explained**.
It must **not** default to the same scene ordering or component mix as the RAG reference.

Available scene types (choose dynamically):

| Category | Scene types |
|---|---|
| Structural | `HOOK`, `TAKEAWAY`, `CTA` |
| Demonstration | `DEMONSTRATION`, `TRANSFORMATION`, `FLOW`, `COMPARISON` |
| Data | `DATA`, `DIAGRAM`, `ZOOM` |
| Concept | `SIMULATION`, `METAPHOR` |

Available components — choose by what the scene **does**, not by what worked in RAG:

| Component | Use when |
|---|---|
| `KineticTypoScene` | HOOK only; punchy one-line statement |
| `TransformScene` | A morphs into B visually |
| `BeforeAfterScene` | Animated wipe contrasting two states |
| `SplitCompareScene` | Side-by-side static comparison |
| `FlowScene` | Linear pipeline with icons |
| `PipelineScene` | Multi-stage data flow with moving packet |
| `DataFlowScene` | Labelled packets through a system diagram |
| `NetworkBuildScene` | Graph/neural net builds node-by-node |
| `GraphGrowthScene` | Line or bar chart grows in real time |
| `BarChartScene` | Simple bar gauge (0–100) |
| `DataScene` | Comparison bars |
| `MeterScene` | Filling gauge — qualitative or sourced-numeric |
| `LayerRevealScene` | Stacked layers peel/reveal |
| `TimelineScene` | Horizontal event timeline |
| `DocumentRetrievalScene` | Card fan → relevant items travel |
| `ContextWindowScene` | Rectangle fills with chunks/tokens |
| `TokenStreamScene` | Tokens generate left-to-right |
| `TokenScene` | Text → token boxes → IDs |
| `CodeExecutionScene` | Code runs line-by-line with output |
| `CardStackScene` | Deck fans/sorts/filters |
| `HubSpokeScene` | Radial hub + spokes |
| `ClusterScene` | Semantic cluster groupings |
| `NumberCounterScene` | Large number counting up |
| `DialScene` | Dial/knob for scalar value |
| `SketchScene` | Node-edge architecture diagram |
| `TakeawayScene` | Single bold takeaway (TAKEAWAY zone only) |
| `CTAScene` | Follow CTA (CTA zone only, ≤ 3 s) |

**No more than 2 scenes in a row may share the same component.**
**Do not re-use the RAG scene sequence or component selection as a default template.**

---

## Numeric integrity rule (permanent — applies to all numeric scene components)

Every numeric visualisation component (`MeterScene`, `BarChartScene`, `DataScene`,
`GraphGrowthScene`, `NumberCounterScene`, `DialScene`, and any future numeric component)
must declare one of two source types:

### `source_type: sourced_numeric`

A real, verifiable number is available. Provide source metadata.

```json
{
  "source_type": "sourced_numeric",
  "source_reference": "Paper / benchmark / official doc — exact citation"
}
```

Precise percentages, dollar savings, accuracy scores, performance gains, and
measurements are **allowed only** with `sourced_numeric` + a non-empty `source_reference`.

### `source_type: illustrative`

No verified external source exists for the number. Communicate the relationship qualitatively.

```json
{
  "source_type": "illustrative"
}
```

- Needle / bar / counter **must** represent a qualitative zone or relative position —
  not an arbitrary intermediate value that implies a specific measurement.
- Use zone-centre positions: midpoint of the intended zone (e.g. red zone centre = 0.165
  of arc, green zone centre = 0.83 of arc) rather than any made-up fraction.
- Labels must be qualitative: HIGHER RISK / MORE GROUNDED / FASTER / SLOWER,
  never `27%` or `+63 pts`.

**Forbidden under `illustrative`:**
percentages • accuracy scores • dollar amounts • performance multipliers •
benchmark comparisons • made-up measurements of any kind.

This rule is enforced by `qa_validator.py` check 6 (sourced_numeric rule).
A QA HARD_FAIL on this check blocks the episode from publishing.

---

## Storyboard structure (canonical Short template)

```
0–3 s     HOOK         — Visually surprise; one punchy phenomenon
3–8 s     DEMONSTRATION — Show the phenomenon BEFORE explaining
8–40 s    EXPLANATION  — Multiple beats; diagrams, transforms, comparisons, simulations
40–50 s   WHY IT MATTERS — Concrete real-world usage beats
50–55 s   TAKEAWAY     — Compress the whole lesson into one visual moment
55–58 s   CTA          — Always ≤ 3 seconds; always last
```

Scene durations: 2.0–8.0 s; prefer 2.5–5.0 s.
Any scene > 4 s MUST have ≥ 2 beats. Any scene > 6 s MUST have ≥ 3 beats.

---

## Regression guard — checks every Short must pass

Run `python regression_guard.py` before treating any render as a candidate for publishing.

Every Short must pass:

| Check | Threshold |
|---|---|
| Scene count | All storyboard scenes present in render |
| Scene midpoint visibility | Luminance ≥ 5.0 at scene midframe |
| First meaningful frame | Non-background content by frame 0 |
| Longest empty interval | ≤ 1 s of consecutive background-only frames |
| Internal/debug labels | None visible |
| Mobile readability | Labels readable at 1080 × 1920 |
| Unsupported numeric claims | 0 QA HARD_FAIL violations |
| Consecutive background-only scenes | None |

---

## QA is observational only

`qa_validator.py` detects and reports. It must **never**:

- Hide scenes
- Filter scenes
- Modify storyboard content
- Suppress component rendering
- Alter renderer visibility flags

Rendering and QA are fully separate concerns.
QA reports; the human (or a future automated gate) decides whether to proceed.

---

## What remains topic-specific (not in global defaults)

The following are per-episode concerns chosen by the Visual Director at generation time:

- Scene count and scene ordering
- Component selection (chosen for the concept, not copied from RAG)
- Object names and carry-over selections
- On-screen labels and narration alignment
- Camera moves per beat
- Pexels search queries (via `visual_agent.py`)
- Whether `sourced_numeric` or `illustrative` applies (determined per data claim)
- Specific numeric values and their source references (when `sourced_numeric`)
- Storyboard `data` payloads

---

## Do not apply RAG-specific defaults globally

The following are RAG implementation details. They must NOT become global defaults:

- Two-gauge MeterScene layout (WITHOUT RAG / WITH RAG)
- Red/green zone positioning (VANILLA_ZONE_CENTER / RAG_ZONE_CENTER)
- 11-scene count or 51.5 s duration
- Document retrieval + context window scene ordering
- RAG acronym decomposition scene
- Any scene component unique to document-retrieval workflows
