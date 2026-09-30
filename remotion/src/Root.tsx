import React from 'react';
import {Composition} from 'remotion';
import {AIBytesReel} from './AIBytesReel';
import type {AIBytesReelProps} from './types';
import ragV3Storyboard from './rag_v3_storyboard.json';

// ── v3 draft-render defaultProps ─────────────────────────────────────────────
// Total: 11 scenes × ~4.6s avg = 50.5s = 1515 frames at 30fps
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

// ── Legacy fallback defaultProps (no storyboard) ─────────────────────────────
// Uncomment this block and swap into <Composition defaultProps=...> to switch back
// const legacyDefaultProps: AIBytesReelProps = { ... };

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="AIBytesReel"
      // Cast required: Remotion's LooseComponentType expects Record<string,unknown>
      component={AIBytesReel as unknown as React.ComponentType<Record<string, unknown>>}
      durationInFrames={RAG_V3_FRAMES}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultProps as unknown as Record<string, unknown>}
    />
  );
};
