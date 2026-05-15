import React from 'react';
import {AbsoluteFill, interpolate, OffthreadVideo, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

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

interface SlideSceneProps {
  icon: string;
  heading: string;
  body: string;
  slideIndex: number;
  totalSlides: number;
  videoSrc?: string;
  theme?: SceneTheme;
}

export const SlideScene: React.FC<SlideSceneProps> = ({
  icon,
  heading,
  body,
  slideIndex,
  totalSlides,
  videoSrc,
  theme,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = theme ?? DEFAULT_THEME;

  // Slide-up transition — 0.4s ease-out
  const slideUp = interpolate(frame, [0, Math.round(fps * 0.4)], [80, 0], {
    extrapolateRight: 'clamp',
  });
  const contentOpacity = interpolate(frame, [0, Math.round(fps * 0.4)], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // Icon bounce
  const iconSpring = spring({
    frame: Math.max(0, frame - 4),
    fps,
    config: {damping: 12, mass: 0.7, stiffness: 200},
    durationInFrames: 18,
  });

  const bodyOpacity = interpolate(frame, [12, 26], [0, 1], {
    extrapolateRight: 'clamp',
  });

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

      {/* Bottom gradient — bottom 40% for caption zone */}
      <AbsoluteFill
        style={{
          background: 'linear-gradient(to bottom, transparent 40%, rgba(0,0,0,0.75) 100%)',
        }}
      />

      {/* Main content — positioned at top 28%, slides up on enter */}
      <div
        style={{
          position: 'absolute',
          top: '28%',
          left: 0,
          right: 0,
          padding: '0 88px',
          opacity: contentOpacity,
          transform: `translateY(${slideUp}px)`,
          zIndex: 2,
        }}
      >
        {/* Icon — bounce in */}
        <div
          style={{
            fontSize: 96,
            marginBottom: 24,
            transform: `scale(${iconSpring})`,
            display: 'block',
            lineHeight: 1,
            filter: `drop-shadow(0 0 16px ${t.accent}66)`,
          }}
        >
          {icon}
        </div>

        {/* Heading */}
        <div
          style={{
            fontSize: 72,
            fontWeight: 800,
            color: '#ffffff',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            letterSpacing: -0.5,
            lineHeight: 1.2,
            marginBottom: 28,
            textShadow: '0 4px 20px rgba(0,0,0,0.95)',
          }}
        >
          {heading}
        </div>

        {/* Theme accent divider */}
        <div
          style={{
            width: 48,
            height: 3,
            background: `linear-gradient(90deg, ${t.accent}, ${t.accent2})`,
            borderRadius: 2,
            marginBottom: 28,
            boxShadow: `0 0 12px ${t.accent}88`,
          }}
        />

        {/* Body */}
        <div
          style={{
            opacity: bodyOpacity,
            fontSize: 40,
            color: 'rgba(255,255,255,0.88)',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            lineHeight: 1.6,
            maxWidth: '85%',
            textShadow: '0 2px 14px rgba(0,0,0,0.9)',
          }}
        >
          {body}
        </div>
      </div>
    </AbsoluteFill>
  );
};
