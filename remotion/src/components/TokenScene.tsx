import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {TokenSpec} from '../types';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const BG = '#050510';

const TITLE_FADE_START = 5;
const TITLE_FADE_END = 15;

// ── stage 1 — full sentence ─────────────────────────────────────────────────
const SENTENCE_FADE_IN_END = 20;
const SENTENCE_FADE_OUT_START = 26;
const SENTENCE_FADE_OUT_END = 34;

// ── stage 2 — token boxes spread apart ──────────────────────────────────────
const STAGE2_START = 31;
const STAGE2_END = 90;
const TOKEN_STAGGER = 4;      // frames between each token's fade-in start
const TOKEN_FADE_FRAMES = 14;
const BASE_GAP = 10;
const MAX_GAP = 20;

// ── stage 3 — ids / weights / pulse ─────────────────────────────────────────
const STAGE3_START = 91;
const STAGE3_FADE_FRAMES = 20;
const PULSE_PERIOD = 50;

const ROW_TOP = 860;
const WEIGHT_MAX_H = 80;

interface TokenSceneProps {
  tokenSpec: TokenSpec;
  accentColor: string;
  durationInFrames: number;
}

function pseudoTokenId(text: string): number {
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
  }
  return 100 + (hash % 9900);
}

export const TokenScene: React.FC<TokenSceneProps> = ({tokenSpec, accentColor}) => {
  const frame = useCurrentFrame();
  const {sentence, tokens, title, showIds, showWeights, weights} = tokenSpec;
  const n = tokens.length;
  const centerIndex = (n - 1) / 2;

  const titleOpacity = interpolate(
    frame,
    [TITLE_FADE_START, TITLE_FADE_END],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const sentenceOpacity = interpolate(
    frame,
    [0, SENTENCE_FADE_IN_END, SENTENCE_FADE_OUT_START, SENTENCE_FADE_OUT_END],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const gap = interpolate(
    frame,
    [STAGE2_START, STAGE2_END],
    [BASE_GAP, MAX_GAP],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const spreadFactor = gap - BASE_GAP;

  const stage3Progress = interpolate(
    frame,
    [STAGE3_START, STAGE3_START + STAGE3_FADE_FRAMES],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const showPulse = !showIds && !showWeights;
  const pulseOpacity = 0.85 + 0.15 * Math.sin(((frame - STAGE3_START) / PULSE_PERIOD) * 2 * Math.PI);

  return (
    <AbsoluteFill style={{backgroundColor: BG}}>
      <AbsoluteFill
        style={{background: `radial-gradient(ellipse 800px 500px at 50% 55%, ${accentColor}14 0%, transparent 70%)`}}
      />

      {title && (
        <div
          style={{
            position: 'absolute', top: 140, left: 0, right: 0,
            textAlign: 'center', opacity: titleOpacity, zIndex: 2,
            fontSize: 20, fontWeight: 700, color: '#ffffff',
            fontFamily: FONT, letterSpacing: 0.5, padding: '0 60px',
          }}
        >
          {title}
        </div>
      )}

      {sentenceOpacity > 0 && (
        <div
          style={{
            position: 'absolute', top: 0, bottom: 0, left: 0, right: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            opacity: sentenceOpacity, zIndex: 2,
            fontSize: 32, fontWeight: 600, color: '#ffffff',
            fontFamily: FONT, textAlign: 'center', padding: '0 100px',
          }}
        >
          {sentence}
        </div>
      )}

      {frame >= STAGE2_START && (
        <div
          style={{
            position: 'absolute', left: 0, right: 0, top: ROW_TOP,
            display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignItems: 'flex-start',
            gap: `28px ${BASE_GAP}px`,
            padding: '0 60px', zIndex: 2,
          }}
        >
          {tokens.map((token, i) => {
            const start = STAGE2_START + i * TOKEN_STAGGER;
            const fadeInOpacity = interpolate(
              frame,
              [start, start + TOKEN_FADE_FRAMES],
              [0, 1],
              {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
            );
            const boxOpacity = frame >= STAGE3_START && showPulse
              ? fadeInOpacity * pulseOpacity
              : fadeInOpacity;

            const delta = i - centerIndex;
            const translateX = delta * spreadFactor;
            const color = token.color ?? accentColor;

            const idOpacity = showIds ? stage3Progress : 0;
            const weightValue = showWeights ? Math.max(0, Math.min(1, weights?.[i] ?? 0)) : 0;
            const weightH = Math.round(WEIGHT_MAX_H * weightValue * stage3Progress);

            return (
              <div
                key={i}
                style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center',
                  transform: `translateX(${translateX}px)`,
                }}
              >
                <div
                  style={{
                    padding: 8, borderRadius: 10,
                    background: color, opacity: boxOpacity,
                    boxShadow: token.highlight ? `0 0 24px ${color}aa` : `0 0 12px ${color}55`,
                    border: token.highlight ? '2px solid #ffffff' : '2px solid transparent',
                  }}
                >
                  <span
                    style={{
                      fontSize: 26, fontWeight: 700, color: '#ffffff',
                      fontFamily: FONT, whiteSpace: 'nowrap',
                    }}
                  >
                    {token.text}
                  </span>
                </div>

                {showIds && (
                  <div
                    style={{
                      marginTop: 10, opacity: idOpacity,
                      fontSize: 16, color: 'rgba(255,255,255,0.5)', fontFamily: FONT,
                    }}
                  >
                    [{pseudoTokenId(token.text)}]
                  </div>
                )}

                {showWeights && (
                  <div style={{marginTop: 10, width: 4, height: WEIGHT_MAX_H, display: 'flex', alignItems: 'flex-end'}}>
                    <div
                      style={{
                        width: 4, height: weightH, borderRadius: 2,
                        background: accentColor, boxShadow: `0 0 10px ${accentColor}88`,
                      }}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </AbsoluteFill>
  );
};
