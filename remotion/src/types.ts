export interface Slide {
  icon: string;
  heading: string;
  body: string;
}

export interface Theme {
  name: string;
  accent: string;
  accent2: string;
  overlay: string;
  pexels_mood: string;
}

export interface ClipsMap {
  hook?: string;
  concept?: string;
  slide_0?: string;
  slide_1?: string;
  slide_2?: string;
  slide_3?: string;
  cta?: string;
}

// ─── Diagram spec types ───────────────────────────────────────────────────────

export interface SplitPanel {
  label: string;
  points: string[];
}

export interface HubSpokeSpec {
  type: 'hub_spoke';
  hub: string;
  spokes: string[];
}

export interface ClusterGroup {
  label: string;
  items: string[];
}
export interface ClusterSpec {
  type: 'cluster';
  groups: ClusterGroup[];
}

export interface SplitCompareSpec {
  type: 'split_compare';
  left: SplitPanel;
  right: SplitPanel;
  verdict: string;
}

export interface SideBySideSpec {
  type: 'side_by_side';
  left: SplitPanel;
  right: SplitPanel;
}

export interface DialTick {
  value: number;
  description: string;
}
export interface DialSpec {
  type: 'dial';
  label: string;
  min_label: string;
  max_label: string;
  ticks: DialTick[];
}

export interface Bar {
  label: string;
  value: number;
}
export interface BarChartSpec {
  type: 'bar_chart';
  title: string;
  bars: Bar[];
}

export interface FlowStep {
  icon: string;
  label: string;
}
export interface FlowSpec {
  type: 'flow';
  steps: FlowStep[];
}

export interface SketchDiagramSpec {
  type: 'sketch';
}

export interface DataDiagramSpec {
  type: 'data';
}

export interface TokenDiagramSpec {
  type: 'token';
}

export type DiagramSpec =
  | HubSpokeSpec
  | ClusterSpec
  | SplitCompareSpec
  | SideBySideSpec
  | DialSpec
  | BarChartSpec
  | FlowSpec
  | SketchDiagramSpec
  | DataDiagramSpec
  | TokenDiagramSpec;

// ─── Sketch scene types (animated SVG diagram) ────────────────────────────────

export interface SketchNode {
  id: string;
  label: string;
  x: number;
  y: number;
  shape: 'rect' | 'circle' | 'diamond';
  width?: number;
  height?: number;
}

export interface SketchEdge {
  from: string;
  to: string;
  label?: string;
}

export interface SketchSpec {
  nodes: SketchNode[];
  edges: SketchEdge[];
  title?: string;
}

// ─── Data scene types (animated numbers and bar charts) ───────────────────────

export type DataSceneType = 'bars' | 'counter' | 'comparison';

export interface DataBar {
  label: string;
  value: number;
  maxValue: number;
  color?: string;
}

export interface DataSpec {
  type: DataSceneType;
  title: string;
  bars?: DataBar[];
  counterValue?: number;
  counterLabel?: string;
  counterSuffix?: string;
  unit?: string;
}

// ─── Token scene types (animated text tokenization) ────────────────────────────

export interface Token {
  text: string;
  color?: string;
  highlight?: boolean;
}

export interface TokenSpec {
  sentence: string;
  tokens: Token[];
  title?: string;
  showIds?: boolean;
  showWeights?: boolean;
  weights?: number[];
}

// ─── Beat types (Visual Director v3) ─────────────────────────────────────────

/** A single timed visual event within a scene */
export interface SceneBeat {
  /** Beat start time in seconds, relative to scene start */
  start: number;
  /** Beat end time in seconds, relative to scene start */
  end: number;
  /** What visually happens — object enters, transforms, moves, reveals, etc. */
  action: string;
  /** Optional: which element is in focus during this beat */
  focus?: string;
  /**
   * Optional: camera instruction for this beat.
   * One of: slow-push-in | zoom-in | zoom-out | pan-left | pan-right |
   *         pan-follow | reveal | static | focus-shift | track-object
   */
  camera?: string;
}

// ─── Storyboard types (Visual Director Agent output) ─────────────────────────

export type SceneType =
  | 'HOOK'
  | 'DEMONSTRATION'
  | 'TRANSFORMATION'
  | 'FLOW'
  | 'COMPARISON'
  | 'DIAGRAM'
  | 'DATA'
  | 'ZOOM'
  | 'SIMULATION'
  | 'METAPHOR'
  | 'TAKEAWAY'
  | 'CTA';

export type SceneComponent =
  // ── Original components ──────────────────────────────────────────────────
  | 'KineticTypoScene'
  | 'TokenScene'
  | 'SketchScene'
  | 'DataScene'
  | 'SplitCompareScene'
  | 'FlowScene'
  | 'HubSpokeScene'
  | 'ClusterScene'
  | 'DialScene'
  | 'BarChartScene'
  | 'NumberCounterScene'
  | 'TakeawayScene'
  | 'CTAScene'
  // ── Legacy fallback components (do not use in storyboard mode) ───────────
  | 'HookScene'
  | 'ConceptScene'
  | 'SlideScene'
  // ── Motion-first primitives (Visual Director v3) ─────────────────────────
  | 'TransformScene'       // A → B transformation with morphing objects
  | 'PipelineScene'        // Horizontal multi-stage pipeline animation
  | 'ContextWindowScene'   // Filling context window with tokens/chunks
  | 'TokenStreamScene'     // Streaming token-by-token generation
  | 'DocumentRetrievalScene' // Document cards fan out, chunks illuminate
  | 'NetworkBuildScene'    // Neural network or graph building node by node
  | 'LayerRevealScene'     // Stacked layers peel away one at a time
  | 'TimelineScene'        // Horizontal timeline with event markers
  | 'BeforeAfterScene'     // Animated wipe or split comparing two states
  | 'MeterScene'           // Filling gauge/meter bar (accuracy, speed, etc.)
  | 'GraphGrowthScene'     // Line or bar graph growing over time
  | 'CodeExecutionScene'   // Code executes line by line with output
  | 'CardStackScene'       // Stack of cards splaying out or sorting
  | 'DataFlowScene'        // Data packets moving through a system diagram
  // ── Visual Director v4 — creative visual reasoning ──────────────────────
  | 'AgentTraversalScene'  // Agent character traverses labeled zones with tools
  | 'CircularFlowScene';   // Four-quadrant spinning wheel (cyclical process)

/** Data payload for NumberCounterScene */
export interface NumberCounterData {
  type: 'counter';
  value: number;
  label: string;
  suffix?: string;
  start?: number;
}

/** Visual complexity score attached to each storyboard */
export interface VisualComplexityScore {
  visual_beats: number;
  demonstrations: number;
  transformations: number;
  diagrams_flows: number;
  data_visuals: number;
  typography_only_scenes: number;
  repeated_layouts: number;
  /** 0–100; storyboard fails if < 80 */
  visual_first_score: number;
}

/** Per-scene storyboard entry produced by visual_director_agent */
export interface StoryboardScene {
  scene_id: number;
  duration_seconds: number;
  narration: string;
  scene_type: SceneType;
  visual_goal: string;
  component: SceneComponent;
  objects: string[];
  animation: string;
  on_screen_text: string[];
  /** Free-form data payload passed directly to component */
  data?: NumberCounterData | DataSpec | TokenSpec | SketchSpec | Record<string, unknown>;
  transition: string;
  /**
   * Timed visual beats within this scene (Visual Director v3).
   * Required for scenes > 4 seconds; each beat = one meaningful visual event.
   */
  beats?: SceneBeat[];
  /**
   * Optional continuity: name of a visual object from the PREVIOUS scene
   * that carries into this scene to create a flowing narrative.
   */
  carry_object_from?: string;
  /**
   * Asset Planner decision (Phase 3B).
   * 'GENERATIVE_VIDEO' → this scene has a Higgsfield-generated background clip.
   * 'REMOTION_ONLY'    → fully deterministic Remotion rendering (default).
   * 'AI_IMAGE'         → AI still image background (future).
   */
  asset_source?: 'REMOTION_ONLY' | 'AI_IMAGE' | 'GENERATIVE_VIDEO';
  /**
   * Visual intent for Higgsfield generation (Phase 3B).
   * Written in English, language-neutral, no embedded text.
   */
  prompt_intent?: string;
  /**
   * Data provenance tag (Visual Director v3.1).
   * 'illustrative' → suppress precise numeric values, show relative bars/gauges only.
   */
  source_type?: string;
}

/** Full storyboard output from visual_director_agent */
export interface Storyboard {
  storyboard: StoryboardScene[];
  total_duration_seconds: number;
  visual_summary: string;
  visual_complexity: VisualComplexityScore;
  violations: string[];
}

// ─── Generated video clips map (Phase 3B) ────────────────────────────────────

/**
 * Map from scene_id (as string) to public-relative MP4 path.
 * e.g. { "s01": "clips/gen_video_s01.mp4" }
 * Populated by visual_agent after Higgsfield generation.
 */
export interface GeneratedVideoClipsMap {
  [sceneId: string]: string;
}

// ─── Main composition props ───────────────────────────────────────────────────

export interface AIBytesReelProps {
  episode: string;
  topic: string;
  title: string;
  hook: string;
  concept: string;
  slides: Slide[];
  voiceover: string;
  takeaway: string;
  tags: string;
  theme?: Theme;
  clips?: ClipsMap;
  diagram_spec?: DiagramSpec;
  sketch_spec?: SketchSpec;
  data_spec?: DataSpec;
  token_spec?: TokenSpec;
  /** Storyboard from visual_director_agent — when present, renders instead of legacy slides */
  storyboard?: StoryboardScene[];
  /**
   * Phase 3B: Higgsfield-generated video clips keyed by scene_id.
   * When present for a GENERATIVE_VIDEO scene, GeneratedVideoBackground
   * uses the clip as the background layer; Remotion overlays branding/text on top.
   */
  generatedVideoClips?: GeneratedVideoClipsMap;
}
