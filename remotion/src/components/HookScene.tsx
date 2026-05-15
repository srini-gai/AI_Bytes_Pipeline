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
  emoji?: string;
  episode?: string;
}

// Frames 0–4: static thumbnail frame (full hook visible, no animation)
// Frame 5+:   word-by-word animation as normal
const ANIM_START = 5;

export const HookScene: React.FC<HookSceneProps> = ({hook, videoSrc, theme, emoji = '🧠', episode}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = theme ?? DEFAULT_THEME;

  const words = hook.split(' ');
  const framesPerWord = Math.round(fps * 0.15);

  // Static layer: fully visible frames 0–4, instantly hidden from frame 5
  const staticVisible = frame < ANIM_START;

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

      {/* Strong base overlay — ensures text contrast at frame 0 / thumbnail */}
      <AbsoluteFill style={{backgroundColor: 'rgba(5,5,16,0.7)'}} />

      {/* Theme tint on top */}
      <AbsoluteFill style={{backgroundColor: t.overlay}} />

      {/* Bottom gradient — caption readability */}
      <AbsoluteFill
        style={{
          background: 'linear-gradient(to bottom, transparent 55%, rgba(0,0,0,0.80) 100%)',
        }}
      />

      {/* Episode pill — top-left, fully visible frame 0 */}
      <div
        style={{
          position: 'absolute',
          top: 72,
          left: 72,
          fontSize: 18,
          letterSpacing: 3,
          color: t.accent,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
          fontWeight: 700,
          textTransform: 'uppercase' as const,
          zIndex: 3,
          textShadow: '0 2px 8px rgba(0,0,0,0.8)',
          background: 'rgba(0,0,0,0.4)',
          padding: '6px 14px',
          borderRadius: 20,
          border: `1px solid ${t.accent}55`,
        }}
      >
        AI BYTES · EP{episode ?? '01'}
      </div>

      {/* Large topic emoji — top-center, fully visible frame 0 */}
      <div
        style={{
          position: 'absolute',
          top: 200,
          left: 0,
          right: 0,
          textAlign: 'center',
          fontSize: 64,
          zIndex: 3,
          lineHeight: 1,
        }}
      >
        {emoji}
      </div>

      {/* STATIC hook text — frames 0–4: full hook at 36px, no animation */}
      {staticVisible && (
        <AbsoluteFill
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            padding: '0 80px',
            zIndex: 2,
          }}
        >
          <div
            style={{
              textAlign: 'center',
              maxWidth: '85%',
              fontSize: 36,
              fontWeight: 900,
              color: '#ffffff',
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
              textShadow: '0 4px 20px rgba(0,0,0,0.9)',
              lineHeight: 1.35,
            }}
          >
            {hook}
          </div>
        </AbsoluteFill>
      )}

      {/* ANIMATED hook text — word-by-word from frame 5 */}
      {!staticVisible && (
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
              const startFrame = ANIM_START + i * framesPerWord;
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
                width: interpolate(
                  frame,
                  [ANIM_START + words.length * framesPerWord, ANIM_START + words.length * framesPerWord + 15],
                  [0, 160],
                  {extrapolateRight: 'clamp'}
                ),
                background: `linear-gradient(90deg, ${t.accent}, ${t.accent2})`,
                margin: '16px auto 0',
                borderRadius: 2,
                boxShadow: `0 0 16px ${t.accent}88`,
              }}
            />
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
