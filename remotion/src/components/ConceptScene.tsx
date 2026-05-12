import React from 'react';
import {AbsoluteFill, interpolate, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';

interface SceneTheme {
  accent: string;
  accent2: string;
  overlay: string;
}

const DEFAULT_THEME: SceneTheme = {
  accent: '#a78bfa',
  accent2: '#34d399',
  overlay: 'rgba(5,5,16,0.35)',
};

interface ConceptSceneProps {
  concept: string;
  videoSrc?: string;
  theme?: SceneTheme;
}

export const ConceptScene: React.FC<ConceptSceneProps> = ({concept, videoSrc, theme}) => {
  const frame = useCurrentFrame();
  const t = theme ?? DEFAULT_THEME;

  const labelOpacity = interpolate(frame, [8, 24], [0, 1], {extrapolateRight: 'clamp'});
  const labelY = interpolate(frame, [8, 24], [14, 0], {extrapolateRight: 'clamp'});

  const titleOpacity = interpolate(frame, [22, 45], [0, 1], {extrapolateRight: 'clamp'});
  const titleY = interpolate(frame, [22, 45], [24, 0], {extrapolateRight: 'clamp'});

  const underlineWidth = interpolate(frame, [42, 68], [0, 240], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: '#050510'}}>
      {/* Full screen Pexels background video */}
      {videoSrc && (
        <AbsoluteFill>
          <OffthreadVideo
            src={staticFile(videoSrc)}
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
            muted
          />
        </AbsoluteFill>
      )}

      {/* Theme tinted overlay */}
      <AbsoluteFill style={{backgroundColor: t.overlay}} />

      {/* Bottom gradient — caption zone */}
      <AbsoluteFill
        style={{
          background: 'linear-gradient(to bottom, transparent 55%, rgba(0,0,0,0.80) 100%)',
        }}
      />

      {/* Text content — centered, no card */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '0 80px',
          zIndex: 2,
        }}
      >
        {/* TODAY'S CONCEPT label */}
        <div
          style={{
            opacity: labelOpacity,
            transform: `translateY(${labelY}px)`,
            fontSize: 22,
            letterSpacing: 6,
            textTransform: 'uppercase' as const,
            color: t.accent,
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            fontWeight: 700,
            marginBottom: 28,
            textShadow: `0 2px 12px rgba(0,0,0,0.9), 0 0 24px ${t.accent}66`,
          }}
        >
          Today's Concept
        </div>

        {/* Concept title */}
        <div
          style={{
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
            fontSize: 80,
            fontWeight: 900,
            color: '#ffffff',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            letterSpacing: -1,
            lineHeight: 1.15,
            textAlign: 'center',
            textShadow: '0 4px 28px rgba(0,0,0,0.95)',
            marginBottom: 36,
          }}
        >
          {concept}
        </div>

        {/* Glowing theme-coloured underline */}
        <div
          style={{
            width: underlineWidth,
            height: 4,
            background: `linear-gradient(90deg, ${t.accent}, ${t.accent2})`,
            borderRadius: 2,
            boxShadow: `0 0 24px ${t.accent}CC`,
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
