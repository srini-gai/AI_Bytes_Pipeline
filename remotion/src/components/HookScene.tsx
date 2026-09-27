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
  /** Topic name — used to derive the category tag in the top bar */
  topic?: string;
  /** Category override — if provided, shown instead of auto-derived tag */
  category?: string;
}

// Frames 0–4: static thumbnail frame (full hook visible, no animation)
// Frame 5+:   word-by-word animation as normal
const ANIM_START = 5;

/**
 * Derive a short category tag from the topic string.
 * Keeps it to max 2 words / ~14 chars to fit the pill.
 */
function deriveCategory(topic: string | undefined): string {
  if (!topic) return 'AI Concept';
  const t = topic.trim();
  // If it's short enough already, use it directly
  if (t.length <= 16) return t;
  // Otherwise take the first 2 meaningful words
  const words = t.split(/\s+/).slice(0, 2);
  return words.join(' ');
}

export const HookScene: React.FC<HookSceneProps> = ({hook, videoSrc, theme, emoji = '🧠', episode, topic, category}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = theme ?? DEFAULT_THEME;

  const words = hook.split(' ');
  const framesPerWord = Math.round(fps * 0.15);

  // Static layer: fully visible frames 0–4, instantly hidden from frame 5
  const staticVisible = frame < ANIM_START;

  // Top bar slide-down animation: starts fully visible at frame 0 (thumbnail)
  // and stays visible. Very subtle slide-in effect from frame 1.
  const barTranslateY = interpolate(frame, [0, 10], [-8, 0], {extrapolateRight: 'clamp'});
  const barOpacity = interpolate(frame, [0, 8], [1, 1], {extrapolateRight: 'clamp'});

  const categoryLabel = category ?? deriveCategory(topic);

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

      {/* ───────────────────────────────────────────────────────────────────────
          OPTION B TOP BAR — Srini on AI branding
          Contains: avatar circle · channel name · episode category tag
          ─────────────────────────────────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 10,
          opacity: barOpacity,
          transform: `translateY(${barTranslateY}px)`,
        }}
      >
        {/* Subtle top-bar backdrop with gradient fade */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: 160,
            background: 'linear-gradient(to bottom, rgba(5,5,16,0.90) 60%, transparent 100%)',
          }}
        />

        {/* Bar content row */}
        <div
          style={{
            position: 'relative',
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            gap: 20,
            padding: '52px 52px 0 52px',
          }}
        >
          {/* ── Avatar: circular Srini logo with cyan/purple gradient ring ── */}
          <div
            style={{
              width: 88,
              height: 88,
              borderRadius: '50%',
              flexShrink: 0,
              /* Gradient ring: use a slightly larger wrapper with the gradient background,
                 then the inner circle clips to a white 3px border effect */
              background: 'linear-gradient(135deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%)',
              padding: 3,
              boxSizing: 'border-box',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(129,140,248,0.5), 0 0 40px rgba(34,211,238,0.25)',
            }}
          >
            <div
              style={{
                width: '100%',
                height: '100%',
                borderRadius: '50%',
                overflow: 'hidden',
                backgroundColor: '#050510',
              }}
            >
              <img
                src={staticFile('srini-logo.png')}
                alt="Srini on AI"
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  display: 'block',
                }}
              />
            </div>
          </div>

          {/* ── Channel name + category tag column ── */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
            {/* Channel name */}
            <div
              style={{
                color: '#ffffff',
                fontSize: 36,
                fontWeight: 800,
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                letterSpacing: -0.5,
                lineHeight: 1,
                textShadow: '0 2px 12px rgba(0,0,0,0.8)',
              }}
            >
              Srini on AI
            </div>

            {/* Episode category tag pill */}
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                alignSelf: 'flex-start',
                background: `linear-gradient(90deg, ${t.accent}33, ${t.accent2}22)`,
                border: `1px solid ${t.accent}88`,
                borderRadius: 24,
                padding: '5px 16px',
              }}
            >
              <span
                style={{
                  color: t.accent,
                  fontSize: 20,
                  fontWeight: 700,
                  letterSpacing: 1.5,
                  textTransform: 'uppercase' as const,
                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                  textShadow: `0 0 12px ${t.accent}66`,
                }}
              >
                {categoryLabel}
              </span>
            </div>
          </div>
        </div>
      </div>
      {/* ─────────────────────────────────────────────────────────────────── */}

      {/* Large topic emoji — centered, pushed down to clear the top bar */}
      <div
        style={{
          position: 'absolute',
          top: 280,
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
            padding: '160px 80px 0',
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
            padding: '160px 80px 0',
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
