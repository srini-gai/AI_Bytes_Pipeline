import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

export type VisualAction =
  | 'enter' | 'exit' | 'travel' | 'track' | 'zoom'
  | 'split' | 'merge' | 'transform' | 'reveal' | 'hide'
  | 'connect' | 'fill' | 'drain' | 'generate' | 'collapse'
  | 'explode' | 'compare' | 'stamp' | 'hold';

export type ObjectType =
  | 'text' | 'token' | 'ribbon' | 'block' | 'card'
  | 'gauge' | 'arrow' | 'zone' | 'label' | 'stamp'
  | 'icon' | 'document' | 'lane';

export type LayoutType =
  | 'full-canvas' | 'centered' | 'horizontal-pipeline'
  | 'vertical-stack' | 'dual-lane' | 'radial'
  | 'scatter' | 'fan' | 'grid';

export interface PrimitiveBase {
  activeBeat: SceneBeat;
  artDirection?: ArtDirection;
  durationInFrames: number;
  fps: number;
}

export interface Point {
  x: number;
  y: number;
}

export interface Bounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ComponentCapability {
  id: string;
  type: 'scene' | 'primitive';
  supportedActions: VisualAction[];
  supportedObjectTypes: ObjectType[];
  supportedLayouts: LayoutType[];
  durationRange: {min: number; max: number};
  artDirectionFamilies: 'all' | string[];
  multiBeat: boolean;
  maxBeats?: number;
  configurableProperties: string[];
}
