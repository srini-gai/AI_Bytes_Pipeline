# Visual Director — Global Rules
# Srini on AI — YouTube Shorts

> Version: v4.0 — Creative Visual Reasoning  
> Evolved from: v3.2 Known-Good Baseline  
> Reference episodes: RAG (ep00), Tokens (ep01)

These rules apply to **every future Short** produced by the Visual Director.
They are principles, not episode-specific implementations.

---

## v4 Core Principle — Creative Visual Reasoning

The Visual Director must NOT start by selecting Remotion components.

Before choosing any implementation primitive, the system must answer:

**"What visual story would make this concept understandable even with the audio muted?"**

Voice EXPLAINS. Visuals DEMONSTRATE.

---

## v4 Planning Pipeline (mandatory order)

Every episode follows this 11-stage sequence:

```
 1. Canonical Narration        — input from script_agent (unchanged)
 2. Claim Classification       — FACTUAL_EXACT / ILLUSTRATIVE / VISUAL_METAPHOR per claim
 3. Visual Thesis              — core concept, metaphor, continuity, transformation, grammar
 4. Conceptual Beat Decomposition — intellectual beats, NOT narration sentences
 5. Physical Visual Actions    — map to visual action primitives
 6. Continuity Object          — carry one object through scenes as chapters
 7. Visual Grammar             — what to use AND what to deliberately avoid
 8. Novelty Comparison         — compare against visual_fingerprints.json
 9. Scene Plan                 — duration, pacing, structure
10. Primitive / Component Mapping — ONLY NOW choose implementation components
11. Renderability Validation   — can current components render each beat?
```

The system prompt in `visual_director_agent.py` enforces this order.

---

## Claim Classification (v4 — required per beat)

Every visual concept or claim must be classified:

### FACTUAL_EXACT

A factual value or mechanism that must be represented accurately.

- Examples: sourced model limits, documented API behaviour, exact technical sequences
- Requires `source_reference` when externally factual

### ILLUSTRATIVE

A simplified representation used to communicate relative behaviour.

- Examples: score badges, relative token lengths, fictional task progress, qualitative scales
- Must NOT look like measured research data

### VISUAL_METAPHOR

A deliberately non-literal visual explanation.

- Examples: judge paddle for preference, compass for model objective, travelling objects for information flow
- Must NOT imply the metaphor is the literal implementation

Add `claim_type` to each beat in the storyboard JSON.

---

## Visual Action Primitives (v4 — action vocabulary)

Describe what happens visually using these action verbs:

```
split | merge | transform | flip | travel | track | rank | sort |
connect | fill | drain | collapse | expand | loop | traverse |
compare | reveal | zoom | check-off | accelerate | explode | reorganize
```

A fade, pulse, glow, or text entrance ALONE does not qualify as a meaningful visual beat.

Scenes should be **compositions** of these primitives.
Existing named components remain implementation tools, not creative templates.

---

## Novelty Memory (v4 — anti-template guard)

### Fingerprint storage

After every approved episode, persist a fingerprint to `output/visual_fingerprints.json`.

Fingerprint fields:

- `visual_thesis` — one-line thesis
- `continuity_object_type` — what it is and how it transforms
- `dominant_motion_grammar` — primary motion pattern
- `scene_layout_sequence` — layout per scene
- `camera_choreography` — camera per scene
- `comparison_structure` — how comparisons are structured
- `dominant_primitives` — primary visual action verbs used
- `visual_world` — overall visual environment/style

### Novelty guard

Before approving a new plan, compare it against recent approved episode fingerprints.

If similarity to any recent episode is HIGH:
- The planner must explain similarities
- The planner must intentionally alter the plan

Do NOT require arbitrary novelty when reuse is logically appropriate.
Do NOT penalise legitimate reuse of generic primitives.
The objective is to avoid repeated visual grammar, not prohibit reuse of good components.

---

## Renderability Validation (v4 — required before implementation)

Before implementing any episode, check each planned beat:

1. Can current components/primitives render this?
2. Can an existing component be parameterised safely?
3. Does it genuinely require a new reusable component?
4. Is the requested animation too complex/brittle for Remotion?
5. Will the focal object remain readable on a phone?
6. Is there meaningful state change within ≤ 3 seconds?

**Do NOT quietly simplify a creative plan into a static diagram.**
Explicitly report implementation gaps.

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
| Minimum visual beats per Short | ≥ 8 |
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
It must **not** default to the same scene ordering or component mix as any reference episode.

Available scene types (choose dynamically):

| Category | Scene types |
|---|---|
| Structural | `HOOK`, `TAKEAWAY`, `CTA` |
| Demonstration | `DEMONSTRATION`, `TRANSFORMATION`, `FLOW`, `COMPARISON` |
| Data | `DATA`, `DIAGRAM`, `ZOOM` |
| Concept | `SIMULATION`, `METAPHOR` |

Available components — choose by what the scene **does**, AFTER creative planning:

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

- Visual thesis and claim classifications (v4)
- Visual fingerprint and novelty assessment (v4)
- Scene count and scene ordering
- Component selection (chosen for the concept, not copied from any reference)
- Object names and carry-over selections
- On-screen labels and narration alignment
- Camera moves per beat
- Pexels search queries (via `visual_agent.py`)
- Whether `sourced_numeric` or `illustrative` applies (determined per data claim)
- Specific numeric values and their source references (when `sourced_numeric`)
- Storyboard `data` payloads

---

## Do not apply episode-specific defaults globally

Implementation details from any reference episode must NOT become global defaults.
This includes scene counts, specific durations, specific component orderings,
or domain-specific scene sequences from RAG, Tokens, or any other episode.

Each new episode must be planned through the v4 Creative Visual Reasoning pipeline,
starting from the concept, not from a template.
