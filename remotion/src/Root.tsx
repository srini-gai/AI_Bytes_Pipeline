import React from 'react';
import {Composition} from 'remotion';
import {AIBytesReel} from './AIBytesReel';
import type {AIBytesReelProps} from './types';
import ragV3Storyboard from './rag_v3_storyboard.json';

// ── Safe development-time default (Remotion Studio / missing props) ────────────
// Derived from the RAG v3 reference storyboard so Studio still launches correctly.
// This value is NEVER used when a storyboard is supplied via --props at render time:
// calculateMetadata (below) dynamically overrides durationInFrames from the actual
// storyboard before the first frame is rendered.
const RAG_V3_TOTAL_SECONDS = ragV3Storyboard.storyboard.reduce(
  (acc: number, s: {duration_seconds: number}) => acc + s.duration_seconds,
  0,
);
const RAG_V3_FRAMES = Math.round(RAG_V3_TOTAL_SECONDS * 30);

const defaultProps: AIBytesReelProps = {
  episode: ragV3Storyboard.episode,
  topic: ragV3Storyboard.topic,
  title: ragV3Storyboard.title,
  hook: ragV3Storyboard.hook,
  concept: ragV3Storyboard.concept,
  voiceover: ragV3Storyboard.voiceover,
  takeaway: ragV3Storyboard.takeaway,
  tags: ragV3Storyboard.tags,
  slides: [],
  // Storyboard mode — overrides all legacy fields
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  storyboard: ragV3Storyboard.storyboard as unknown as AIBytesReelProps['storyboard'],
  // Dark purple/teal brand theme
  theme: {
    name: 'energy',
    accent: '#a78bfa',
    accent2: '#34d399',
    overlay: 'rgba(5,5,16,0.35)',
    pexels_mood: 'purple neon dark',
  },
};

// ── Dynamic composition duration ──────────────────────────────────────────────
// Called by Remotion before the first frame is rendered, with the resolved props
// (defaultProps merged with --props overrides).  When a storyboard is present,
// durationInFrames is derived from its scenes so the composition always matches
// the planned duration exactly — no frame is truncated or held beyond the CTA.
// Without a storyboard (legacy mode), falls back to RAG_V3_FRAMES.
const calculateMetadata = ({
  props,
}: {
  defaultProps: Record<string, unknown>;
  props: Record<string, unknown>;
  abortSignal: AbortSignal;
  compositionId: string;
}): {durationInFrames: number} => {
  const FPS = 30;
  const storyboard = props.storyboard as Array<{duration_seconds: number}> | undefined;

  if (Array.isArray(storyboard) && storyboard.length > 0) {
    const totalSeconds = storyboard.reduce(
      (acc, scene) => acc + (scene.duration_seconds ?? 0),
      0,
    );
    const frames = Math.round(totalSeconds * FPS);
    return {durationInFrames: frames};
  }

  // Legacy / no-storyboard: keep the RAG v3 baseline
  return {durationInFrames: RAG_V3_FRAMES};
};

// ── Legacy fallback defaultProps (no storyboard) ─────────────────────────────
// Uncomment this block and swap into <Composition defaultProps=...> to switch back
// const legacyDefaultProps: AIBytesReelProps = { ... };

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="AIBytesReel"
      // Cast required: Remotion's LooseComponentType expects Record<string,unknown>
      component={AIBytesReel as unknown as React.ComponentType<Record<string, unknown>>}
      // Safe Studio / CI fallback — overridden at render time by calculateMetadata
      durationInFrames={RAG_V3_FRAMES}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultProps as unknown as Record<string, unknown>}
      calculateMetadata={calculateMetadata as unknown as Parameters<typeof Composition>[0]['calculateMetadata']}
    />
  );
};
