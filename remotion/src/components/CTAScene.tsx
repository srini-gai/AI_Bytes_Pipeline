import React from 'react';
import {AbsoluteFill, interpolate, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import type {ArtDirection} from '../themes';

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
  artDirection?: ArtDirection;
}

export const CTAScene: React.FC<CTASceneProps> = ({takeaway, videoSrc, theme, artDirection: ad}) => {
  const frame = useCurrentFrame();
  const t = theme ?? DEFAULT_THEME;

  // Art-direction derived values with backward-compatible fallbacks
  const bgColor = ad?.palette.bg ?? '#050510';
  const textColor = ad?.palette.text ?? '#ffffff';
  const overlayColor = ad?.overlay ?? t.overlay;
  const useGlow = ad?.depth.use_glow ?? true;

  // Compressed to fit ≤3s (≤90 frames): label→f20, text→f40, button→f70
  const labelOpacity = interpolate(frame, [0, 12], [0, 1], {extrapolateRight: 'clamp'});
  const labelY = interpolate(frame, [0, 12], [14, 0], {extrapolateRight: 'clamp'});

  const textOpacity = interpolate(frame, [18, 40], [0, 1], {extrapolateRight: 'clamp'});
  const textY = interpolate(frame, [18, 40], [28, 0], {extrapolateRight: 'clamp'});

  const btnOpacity = interpolate(frame, [48, 70], [0, 1], {extrapolateRight: 'clamp'});
  const btnY = interpolate(frame, [48, 70], [24, 0], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: bgColor}}>
      {/* Accent gradient fallback — visible even without a video; ensures
          luminance stays above QA threshold during Fade crossfade */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 900px 1200px at 50% 55%, ${t.accent}44 0%, ${t.accent2}18 60%, transparent 100%)`,
      }}/>

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
      <AbsoluteFill style={{backgroundColor: overlayColor}} />

      {/* Bottom gradient — caption zone */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(to bottom, transparent 50%, ${ad?.light_or_dark === 'light' ? 'rgba(0,0,0,0.15)' : 'rgba(0,0,0,0.85)'} 100%)`,
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
            textShadow: useGlow ? `0 2px 12px rgba(0,0,0,0.9), 0 0 24px ${t.accent}66` : 'none',
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
            color: textColor,
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            letterSpacing: -0.5,
            lineHeight: 1.25,
            textAlign: 'center',
            textShadow: useGlow ? '0 4px 28px rgba(0,0,0,0.95)' : 'none',
            marginBottom: 60,
          }}
        >
          {takeaway}
        </div>

        {/* Follow Srini on AI — theme gradient pill button */}
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
          Follow for practical AI, daily
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
