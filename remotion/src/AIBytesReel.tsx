import React from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {HookScene} from './components/HookScene';
import {ConceptScene} from './components/ConceptScene';
import {SlideScene} from './components/SlideScene';
import {CTAScene} from './components/CTAScene';
import type {AIBytesReelProps, ClipsMap, Theme} from './types';

const FPS = 30;
const CROSSFADE = 9; // 0.3s at 30fps

// Scene timing (seconds → frames)
const HOOK_START    = 0;
const HOOK_DURATION = 7 * FPS;        // 0–7s

const CONCEPT_START    = 7 * FPS;
const CONCEPT_DURATION = 8 * FPS;     // 7–15s

const SLIDES_START    = 15 * FPS;
const SLIDES_TOTAL    = 35 * FPS;     // 15–50s  (35s ÷ 4 slides = ~8.75s each)

const CTA_START    = 50 * FPS;
const CTA_DURATION = 10 * FPS;        // 50–60s

const slideKey = (i: number): keyof ClipsMap =>
  `slide_${i}` as keyof ClipsMap;

// Wraps a scene with fade-in and fade-out crossfade
const Fade: React.FC<{duration: number; children: React.ReactNode}> = ({duration, children}) => {
  const frame = useCurrentFrame();
  const opacity = Math.min(
    interpolate(frame, [0, CROSSFADE], [0, 1], {extrapolateRight: 'clamp'}),
    interpolate(frame, [duration - CROSSFADE, duration], [1, 0], {extrapolateRight: 'clamp'}),
  );
  return <AbsoluteFill style={{opacity}}>{children}</AbsoluteFill>;
};

const DEFAULT_THEME: Theme = {
  name: 'energy',
  accent: '#a78bfa',
  accent2: '#34d399',
  overlay: 'rgba(5,5,16,0.35)',
  pexels_mood: 'purple neon dark',
};

export const AIBytesReel: React.FC<AIBytesReelProps> = (props) => {
  const {hook, concept, slides, takeaway, clips, theme} = props;
  const t = theme ?? DEFAULT_THEME;
  const slideCount = slides.length;
  const slideDuration = Math.floor(SLIDES_TOTAL / slideCount);

  return (
    <AbsoluteFill style={{backgroundColor: '#050510'}}>
      {/* Hook: 0–7s */}
      <Sequence from={HOOK_START} durationInFrames={HOOK_DURATION}>
        <Fade duration={HOOK_DURATION}>
          <HookScene hook={hook} videoSrc={clips?.hook} theme={t} />
        </Fade>
      </Sequence>

      {/* Concept: 7–15s */}
      <Sequence from={CONCEPT_START} durationInFrames={CONCEPT_DURATION}>
        <Fade duration={CONCEPT_DURATION}>
          <ConceptScene concept={concept} videoSrc={clips?.concept} theme={t} />
        </Fade>
      </Sequence>

      {/* Slides: 15–50s */}
      {slides.map((slide, i) => (
        <Sequence
          key={i}
          from={SLIDES_START + i * slideDuration}
          durationInFrames={slideDuration}
        >
          <Fade duration={slideDuration}>
            <SlideScene
              icon={slide.icon}
              heading={slide.heading}
              body={slide.body}
              slideIndex={i}
              totalSlides={slideCount}
              videoSrc={clips?.[slideKey(i)]}
              theme={t}
            />
          </Fade>
        </Sequence>
      ))}

      {/* CTA: 50–60s */}
      <Sequence from={CTA_START} durationInFrames={CTA_DURATION}>
        <Fade duration={CTA_DURATION}>
          <CTAScene takeaway={takeaway} videoSrc={clips?.cta} theme={t} />
        </Fade>
      </Sequence>
    </AbsoluteFill>
  );
};
