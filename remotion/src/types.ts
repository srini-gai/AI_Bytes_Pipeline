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

export type DiagramSpec =
  | HubSpokeSpec
  | ClusterSpec
  | SplitCompareSpec
  | SideBySideSpec
  | DialSpec
  | BarChartSpec
  | FlowSpec
  | SketchDiagramSpec
  | DataDiagramSpec;

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
}
