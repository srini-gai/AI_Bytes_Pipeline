/**
 * TokenScene — 6-beat tokenization journey (v41 token-native).
 *
 * 11.02s ≈ 331 frames at 30fps. Each beat ≈55 frames (~1.8s).
 *
 *   Beat A (0–55f):    Full sentence types across canvas at 120px
 *   Beat B (55–110f):  Camera rapidly zooms into the word, filling screen
 *   Beat C (110–170f): Word stretches and physically splits into un|believ|able
 *   Beat D (170–225f): Three token blocks separate, each fills canvas zone
 *   Beat E (225–280f): Each block flips/rotates to reveal its integer ID
 *   Beat F (280–331f): Token-ID blocks accelerate out of frame
 *
 * Props unchanged — same TokenSpec interface.
 */
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {TokenSpec} from '../types';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const MONO = '"JetBrains Mono", "Fira Code", "SF Mono", monospace';
const BG = '#050510';

function pseudoTokenId(text: string): number {
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
  }
  return 100 + (hash % 9900);
}

interface TokenSceneProps {
  tokenSpec: TokenSpec;
  accentColor: string;
  durationInFrames: number;
}

export const TokenScene: React.FC<TokenSceneProps> = ({
  tokenSpec,
  accentColor,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {sentence, tokens, title, showIds} = tokenSpec;
  const accent2 = '#34d399';

  // ── Beat boundaries (proportional to duration) ────────────────────────────
  const B = (frac: number) => Math.round(durationInFrames * frac);
  const BEAT_A_END   = B(0.166);   // ~55f
  const BEAT_B_START = B(0.15);
  const BEAT_B_END   = B(0.332);   // ~110f
  const BEAT_C_START = B(0.30);
  const BEAT_C_END   = B(0.514);   // ~170f
  const BEAT_D_START = B(0.48);
  const BEAT_D_END   = B(0.68);    // ~225f
  const BEAT_E_START = B(0.65);
  const BEAT_E_END   = B(0.846);   // ~280f
  const BEAT_F_START = B(0.82);

  // ── Fade envelope ─────────────────────────────────────────────────────────
  const sceneOpacity = interpolate(
    frame,
    [0, 6, durationInFrames - 6, durationInFrames],
    [0, 1, 1, 0.3],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // ══════════════════════════════════════════════════════════════════════════
  // Beat A — sentence types across canvas
  // ══════════════════════════════════════════════════════════════════════════
  const typewriterProgress = interpolate(
    frame,
    [4, BEAT_A_END - 8],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const sentenceCharsVisible = Math.floor(typewriterProgress * sentence.length);

  const sentenceOpacity = interpolate(
    frame,
    [BEAT_B_START, BEAT_B_END],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // ══════════════════════════════════════════════════════════════════════════
  // Beat B — camera zooms into word (scale up, sentence fades)
  // ══════════════════════════════════════════════════════════════════════════
  const zoomScale = interpolate(
    frame,
    [BEAT_B_START, BEAT_B_END],
    [1, 3.5],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // ══════════════════════════════════════════════════════════════════════════
  // Beat C — word stretches, splits into tokens
  // ══════════════════════════════════════════════════════════════════════════
  const splitProgress = interpolate(
    frame,
    [BEAT_C_START, BEAT_C_END],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Word visibility: appears as zoom finishes, stays through split
  const wordOpacity = interpolate(
    frame,
    [BEAT_B_START + 10, BEAT_B_END - 10, BEAT_D_END],
    [0, 1, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Crack lines between tokens
  const crackOpacity = interpolate(
    frame,
    [BEAT_C_START + 10, BEAT_C_START + 25],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // ══════════════════════════════════════════════════════════════════════════
  // Beat D — token blocks separate into full-canvas zones
  // ══════════════════════════════════════════════════════════════════════════
  const separateProgress = interpolate(
    frame,
    [BEAT_D_START, BEAT_D_END],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Token positions: stacked vertically, each taking a zone of the 1920h canvas
  const tokenPositions = tokens.map((_, i) => {
    const targetY = 320 + i * 480; // Spread across 320, 800, 1280
    const startY = 960; // Center
    return interpolate(separateProgress, [0, 1], [startY, targetY]);
  });

  // Scale tokens up as they separate
  const tokenScale = interpolate(
    separateProgress,
    [0, 0.5, 1],
    [1, 1.3, 1.15],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Box highlight glow
  const boxGlow = interpolate(
    separateProgress,
    [0.3, 0.8],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // ══════════════════════════════════════════════════════════════════════════
  // Beat E — flip to reveal IDs
  // ══════════════════════════════════════════════════════════════════════════
  const flipProgressArr = tokens.map((_, i) => {
    const stagger = i * 8;
    return interpolate(
      frame,
      [BEAT_E_START + stagger, BEAT_E_START + stagger + 20],
      [0, 1],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
    );
  });

  // ══════════════════════════════════════════════════════════════════════════
  // Beat F — accelerate out of frame
  // ══════════════════════════════════════════════════════════════════════════
  const exitProgress = interpolate(
    frame,
    [BEAT_F_START, durationInFrames - 2],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Title display
  const titleOpacity = interpolate(
    frame,
    [BEAT_C_END - 10, BEAT_C_END + 5, BEAT_F_START, BEAT_F_START + 10],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Phase detection for rendering
  const inBeatAB = frame < BEAT_C_START;
  const inSplitPhase = frame >= BEAT_C_START && frame < BEAT_D_START + 15;
  const inSeparated = frame >= BEAT_D_START;

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity}}>
      {/* Ambient glow */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 1000px 700px at 50% 50%, ${accentColor}10 0%, transparent 60%)`,
      }} />

      {/* ── Beat A: Typewriter sentence ─────────────────────────────── */}
      {sentenceOpacity > 0.01 && (
        <AbsoluteFill style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: sentenceOpacity,
          transform: frame >= BEAT_B_START
            ? `scale(${zoomScale}) translateY(${interpolate(zoomScale, [1, 3.5], [0, -30])}px)`
            : undefined,
          zIndex: 2,
        }}>
          <div style={{
            fontFamily: FONT,
            fontSize: 100,
            fontWeight: 900,
            color: '#ffffff',
            textAlign: 'center',
            padding: '0 60px',
            letterSpacing: 2,
            textShadow: `0 0 40px ${accentColor}44`,
          }}>
            {sentence.slice(0, sentenceCharsVisible)}
            {sentenceCharsVisible < sentence.length && (
              <span style={{
                opacity: Math.sin(frame * 0.4) > 0 ? 1 : 0,
                color: accentColor,
              }}>|</span>
            )}
          </div>
        </AbsoluteFill>
      )}

      {/* ── Beat C/D/E/F: Token blocks ─────────────────────────────── */}
      {frame >= BEAT_B_END - 20 && (
        <>
          {/* During split phase: word with crack lines */}
          {inSplitPhase && !inSeparated && (
            <AbsoluteFill style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 3,
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: `${splitProgress * 40}px`,
                opacity: wordOpacity,
              }}>
                {tokens.map((token, i) => (
                  <React.Fragment key={i}>
                    <span style={{
                      fontFamily: FONT,
                      fontSize: 120,
                      fontWeight: 900,
                      color: '#ffffff',
                      textShadow: `0 0 30px ${accentColor}66`,
                      display: 'inline-block',
                      padding: `${splitProgress * 16}px ${splitProgress * 24}px`,
                      borderRadius: splitProgress * 16,
                      background: splitProgress > 0.3
                        ? `${token.color ?? accentColor}${Math.round(splitProgress * 40).toString(16).padStart(2, '0')}`
                        : 'transparent',
                      transition: 'none',
                    }}>
                      {token.text}
                    </span>
                    {i < tokens.length - 1 && crackOpacity > 0 && (
                      <div style={{
                        width: 3,
                        height: `${crackOpacity * 120}px`,
                        background: `linear-gradient(to bottom, transparent, ${accent2}, transparent)`,
                        opacity: crackOpacity * (1 - splitProgress * 0.5),
                        flexShrink: 0,
                      }} />
                    )}
                  </React.Fragment>
                ))}
              </div>
            </AbsoluteFill>
          )}

          {/* Separated token blocks — full canvas zones */}
          {inSeparated && tokens.map((token, i) => {
            const y = tokenPositions[i];
            const flipP = flipProgressArr[i];
            const isFlipped = flipP > 0.5;
            const rotateY = flipP * 180;

            // Exit: each token flies in a different direction
            const exitDirs = [
              {x: -800, y: -400},
              {x: 0, y: -600},
              {x: 800, y: -400},
            ];
            const dir = exitDirs[i] ?? exitDirs[0];
            const eased = exitProgress * exitProgress;
            const exitX = dir.x * eased;
            const exitY = dir.y * eased;
            const exitRot = (i - 1) * 30 * eased;

            const color = token.color ?? accentColor;
            const id = pseudoTokenId(token.text);

            return (
              <div
                key={i}
                style={{
                  position: 'absolute',
                  left: '50%',
                  top: y,
                  transform: `translate(-50%, -50%) scale(${tokenScale})
                    rotateY(${rotateY}deg)
                    translate(${exitX}px, ${exitY}px) rotate(${exitRot}deg)`,
                  transformStyle: 'preserve-3d',
                  perspective: 1200,
                  opacity: 1 - exitProgress * 0.8,
                  zIndex: 4,
                }}
              >
                {/* Front face: token text */}
                <div style={{
                  backfaceVisibility: 'hidden',
                  padding: '24px 48px',
                  borderRadius: 20,
                  background: isFlipped ? 'transparent' : `${color}30`,
                  border: isFlipped ? 'none' : `3px solid ${color}88`,
                  boxShadow: boxGlow > 0 && !isFlipped
                    ? `0 0 ${40 + boxGlow * 40}px ${color}44, inset 0 0 20px ${color}11`
                    : 'none',
                  display: isFlipped ? 'none' : 'block',
                }}>
                  <span style={{
                    fontFamily: FONT,
                    fontSize: 72,
                    fontWeight: 900,
                    color: '#ffffff',
                    letterSpacing: 2,
                    textShadow: `0 0 20px ${color}66`,
                  }}>
                    {token.text}
                  </span>
                </div>

                {/* Back face: integer ID */}
                <div style={{
                  backfaceVisibility: 'hidden',
                  transform: 'rotateY(180deg)',
                  position: isFlipped ? 'relative' : 'absolute',
                  top: isFlipped ? undefined : 0,
                  left: isFlipped ? undefined : 0,
                  display: isFlipped ? 'flex' : 'none',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 8,
                  padding: '20px 40px',
                  borderRadius: 20,
                  background: `${accent2}20`,
                  border: `3px solid ${accent2}66`,
                  boxShadow: `0 0 50px ${accent2}33`,
                }}>
                  <span style={{
                    fontFamily: MONO,
                    fontSize: 64,
                    fontWeight: 700,
                    color: accent2,
                    letterSpacing: 3,
                    textShadow: `0 0 20px ${accent2}66`,
                  }}>
                    {id}
                  </span>
                  <span style={{
                    fontFamily: FONT,
                    fontSize: 22,
                    fontWeight: 500,
                    color: 'rgba(255,255,255,0.4)',
                    letterSpacing: 1,
                  }}>
                    {token.text}
                  </span>
                </div>
              </div>
            );
          })}
        </>
      )}

      {/* Title label */}
      {title && titleOpacity > 0.01 && (
        <div style={{
          position: 'absolute',
          top: 100,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: titleOpacity,
          zIndex: 5,
        }}>
          <span style={{
            fontFamily: FONT,
            fontSize: 28,
            fontWeight: 800,
            color: 'rgba(255,255,255,0.7)',
            letterSpacing: 4,
            textTransform: 'uppercase',
          }}>
            {title}
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};
