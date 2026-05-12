import React from 'react';
import {AbsoluteFill, interpolate, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

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

interface HookSceneProps {
  hook: string;
  videoSrc?: string;
  theme?: SceneTheme;
}

export const HookScene: React.FC<HookSceneProps> = ({hook, videoSrc, theme}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = theme ?? DEFAULT_THEME;

  const words = hook.split(' ');
  const framesPerWord = Math.round(fps * 0.15);

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

      {/* Bottom gradient — caption readability only */}
      <AbsoluteFill
        style={{
          background: 'linear-gradient(to bottom, transparent 55%, rgba(0,0,0,0.80) 100%)',
        }}
      />

      {/* AI BYTES watermark top-left */}
      <div
        style={{
          position: 'absolute',
          top: 72,
          left: 72,
          fontSize: 22,
          letterSpacing: 5,
          color: 'rgba(255,255,255,0.45)',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
          fontWeight: 700,
          textTransform: 'uppercase' as const,
          zIndex: 2,
          textShadow: '0 2px 8px rgba(0,0,0,0.6)',
        }}
      >
        AI BYTES
      </div>

      {/* Hook text — word-by-word reveal */}
      <AbsoluteFill
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '0 80px',
          zIndex: 2,
        }}
      >
        <div style={{textAlign: 'center', lineHeight: 1.25}}>
          {words.map((word, i) => {
            const startFrame = i * framesPerWord;
            const opacity = interpolate(
              frame,
              [startFrame, startFrame + framesPerWord],
              [0, 1],
              {extrapolateRight: 'clamp'}
            );
            const translateY = interpolate(
              frame,
              [startFrame, startFrame + framesPerWord],
              [20, 0],
              {extrapolateRight: 'clamp'}
            );
            return (
              <span
                key={i}
                style={{
                  display: 'inline-block',
                  opacity,
                  transform: `translateY(${translateY}px)`,
                  fontSize: 72,
                  fontWeight: 900,
                  color: '#ffffff',
                  margin: '0 8px 10px',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                  textShadow: `0 4px 20px rgba(0,0,0,0.9), 0 0 40px ${t.accent}33`,
                  letterSpacing: -0.5,
                }}
              >
                {word}
              </span>
            );
          })}
          {/* Accent line under hook */}
          <div
            style={{
              height: 3,
              width: interpolate(frame, [words.length * framesPerWord, words.length * framesPerWord + 15], [0, 160], {extrapolateRight: 'clamp'}),
              background: `linear-gradient(90deg, ${t.accent}, ${t.accent2})`,
              margin: '16px auto 0',
              borderRadius: 2,
              boxShadow: `0 0 16px ${t.accent}88`,
            }}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
