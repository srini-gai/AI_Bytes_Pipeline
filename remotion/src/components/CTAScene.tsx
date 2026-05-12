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

interface CTASceneProps {
  takeaway: string;
  videoSrc?: string;
  theme?: SceneTheme;
}

export const CTAScene: React.FC<CTASceneProps> = ({takeaway, videoSrc, theme}) => {
  const frame = useCurrentFrame();
  const t = theme ?? DEFAULT_THEME;

  const labelOpacity = interpolate(frame, [5, 20], [0, 1], {extrapolateRight: 'clamp'});
  const labelY = interpolate(frame, [5, 20], [14, 0], {extrapolateRight: 'clamp'});

  const textOpacity = interpolate(frame, [18, 40], [0, 1], {extrapolateRight: 'clamp'});
  const textY = interpolate(frame, [18, 40], [28, 0], {extrapolateRight: 'clamp'});

  const btnOpacity = interpolate(frame, [35, 55], [0, 1], {extrapolateRight: 'clamp'});
  const btnY = interpolate(frame, [35, 55], [24, 0], {extrapolateRight: 'clamp'});

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
          background: 'linear-gradient(to bottom, transparent 50%, rgba(0,0,0,0.85) 100%)',
        }}
      />

      {/* Floating text — no card, no box */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '0 88px',
          zIndex: 2,
        }}
      >
        {/* KEY TAKEAWAY label */}
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
          Key Takeaway
        </div>

        {/* Takeaway text */}
        <div
          style={{
            opacity: textOpacity,
            transform: `translateY(${textY}px)`,
            fontSize: 64,
            fontWeight: 800,
            color: '#ffffff',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            letterSpacing: -0.5,
            lineHeight: 1.25,
            textAlign: 'center',
            textShadow: '0 4px 28px rgba(0,0,0,0.95)',
            marginBottom: 60,
          }}
        >
          {takeaway}
        </div>

        {/* Follow AI Bytes — theme gradient pill button */}
        <div
          style={{
            opacity: btnOpacity,
            transform: `translateY(${btnY}px)`,
            background: `linear-gradient(135deg, ${t.accent} 0%, ${t.accent2} 100%)`,
            borderRadius: 60,
            padding: '28px 80px',
            fontSize: 38,
            fontWeight: 800,
            color: '#ffffff',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            letterSpacing: 0.5,
            boxShadow: `0 8px 40px ${t.accent}55`,
            textAlign: 'center' as const,
          }}
        >
          Follow AI Bytes
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
