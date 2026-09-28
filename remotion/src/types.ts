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
  | 'HookScene'
  | 'ConceptScene'
  | 'SlideScene';

/** Data payload for NumberCounterScene */
export interface NumberCounterData {
  type: 'counter';
  value: number;
  label: string;
  suffix?: string;
  start?: number;
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
  /** Free-form data payload passed directly to component (e.g. NumberCounterData, TokenSpec, DataSpec) */
  data?: NumberCounterData | DataSpec | TokenSpec | SketchSpec | Record<string, unknown>;
  transition: string;
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
}
