/**
 * TakeawayScene — Token convergence takeaway (v41 token-native).
 *
 * s09: 2.86s ≈ 86 frames at 30fps.
 *   Beat A (0–28f):   Scattered token blocks visible across canvas
 *   Beat B (28–55f):  Tokens converge inward to center point
 *   Beat C (55–86f):  Collapsed tokens form glow, takeaway text emerges
 *
 * on_screen_text: ["AI processes TOKENS", "not words directly"]
 * NO RAG icons, NO pipeline diagrams. Pure token convergence.
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const MONO = '"JetBrains Mono", "Fira Code", "SF Mono", monospace';
const BG = '#050510';

interface TakeawaySceneProps {
  text: string;
  accentColor: string;
  accent2?: string;
  durationInFrames: number;
  beats?: SceneBeat[];
  onScreenText?: string[];
  artDirection?: ArtDirection;
}

// Scattered token positions (deterministic, spread across 1080×1920)
function seededRand(seed: number): number {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

const TOKEN_COUNT = 12;
// Default scatter fragments — only used when no episode content is available
const DEFAULT_TOKEN_TEXTS = ['un', '1726', 'believ', '42891', 'able', '481', 'tok', 'vec', 'emb', 'att', 'The', 'cat'];

/**
 * Derive scatter words from the episode's actual content (text + onScreenText).
 * Avoids showing Tokens-episode fragments in non-Tokens episodes.
 */
function deriveScatterWords(text: string, onScreenText?: string[]): string[] {
  const source = [text, ...(onScreenText ?? [])].join(' ');
  const words = source
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length >= 2 && w.length <= 10);
  if (words.length === 0) return DEFAULT_TOKEN_TEXTS;
  const result: string[] = [];
  for (let i = 0; i < TOKEN_COUNT; i++) {
    result.push(words[i % words.length]);
  }
  return result;
}

// Generate scattered positions
const SCATTER_POSITIONS = Array.from({length: TOKEN_COUNT}, (_, i) => ({
  x: 80 + seededRand(i * 7 + 1) * 920,
  y: 200 + seededRand(i * 13 + 3) * 1400,
  rot: (seededRand(i * 19 + 5) - 0.5) * 40,
  scale: 0.6 + seededRand(i * 23 + 7) * 0.6,
}));

// Center convergence point
const CENTER_X = 540;
const CENTER_Y = 860;

export const TakeawayScene: React.FC<TakeawaySceneProps> = ({
  text,
  accentColor,
  accent2 = '#34d399',
  durationInFrames,
  beats,
  onScreenText,
  artDirection: ad,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Art direction derivations (fall back to legacy dark-tech look)
  const bgColor = ad?.palette.bg ?? BG;
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.font ?? FONT;
  const monoFamily = ad?.typography.mono ?? MONO;
  const useGlow = ad?.depth.use_glow ?? true;
  const isLight = ad?.light_or_dark === 'light';
  const itemColors = ad?.item_colors;

  // Derive scatter words from episode content (memoized per render)
  const scatterWords = React.useMemo(
    () => deriveScatterWords(text, onScreenText),
    [text, onScreenText],
  );

  const totalFrames = durationInFrames;

  // Beat boundaries. Light worlds have no glow to carry the converge phase, so
  // the words converge earlier and the takeaway arrives sooner (holds longer).
  const convergeStart = Math.round(totalFrames * (isLight ? 0.22 : 0.33));
  const convergeEnd = Math.round(totalFrames * (isLight ? 0.50 : 0.64));
  const textStart = Math.round(totalFrames * (isLight ? 0.42 : 0.60));

  // Scene opacity
  const sceneOpacity = interpolate(
    frame, [0, 6, totalFrames - 4, totalFrames], [0, 1, 1, 0.4],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Convergence progress: 0 = scattered, 1 = converged to center
  const convergeP = interpolate(
    frame, [convergeStart, convergeEnd], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  // Ease-in-out
  const easedConverge = convergeP < 0.5
    ? 2 * convergeP * convergeP
    : 1 - Math.pow(-2 * convergeP + 2, 2) / 2;

  // Token opacity: visible scattered, then shrink at center
  const tokenPeak = isLight ? 1 : 0.8;
  const tokenOpacity = interpolate(
    frame, [4, 14, convergeEnd - 4, convergeEnd + 8], [0, tokenPeak, tokenPeak, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Center glow grows as tokens converge
  const glowIntensity = interpolate(
    easedConverge, [0, 0.5, 1], [0, 0.2, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Text emergence
  const textOpacity = interpolate(
    frame, [textStart, textStart + 14], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const textScale = interpolate(
    frame, [textStart, textStart + 14], [0.7, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // On-screen text lines
  const line1 = onScreenText?.[0] ?? 'AI processes TOKENS';
  const line2 = onScreenText?.[1] ?? 'not words directly';

  return (
    <AbsoluteFill style={{backgroundColor: bgColor, opacity: sceneOpacity, overflow: 'hidden'}}>
      {/* Center convergence glow */}
      {useGlow && (
        <AbsoluteFill style={{
          background: `radial-gradient(circle ${200 + glowIntensity * 300}px at ${CENTER_X}px ${CENTER_Y}px,
            ${accentColor}${Math.round(glowIntensity * 0.25 * 255).toString(16).padStart(2, '0')} 0%,
            transparent 70%)`,
        }} />
      )}

      {/* Flash at convergence peak */}
      {useGlow && glowIntensity > 0.9 && (
        <AbsoluteFill style={{
          background: `radial-gradient(circle 120px at ${CENTER_X}px ${CENTER_Y}px,
            ${isLight
              ? `rgba(0,0,0,${(glowIntensity - 0.9) * 3})`
              : `rgba(255,255,255,${(glowIntensity - 0.9) * 3})`} 0%, transparent 80%)`,
        }} />
      )}

      {/* Scattered / converging token blocks */}
      {tokenOpacity > 0.01 && SCATTER_POSITIONS.map((pos, i) => {
        const currentX = pos.x + (CENTER_X - pos.x) * easedConverge;
        const currentY = pos.y + (CENTER_Y - pos.y) * easedConverge;
        const currentRot = pos.rot * (1 - easedConverge);
        const currentScale = pos.scale * (1 - easedConverge * 0.6);

        const color = itemColors && itemColors.length > 0
          ? itemColors[i % itemColors.length]
          : (i % 2 === 0 ? accentColor : accent2);

        return (
          <div key={i} style={{
            position: 'absolute',
            left: currentX,
            top: currentY,
            transform: `translate(-50%, -50%) rotate(${currentRot}deg) scale(${currentScale})`,
            opacity: tokenOpacity,
            zIndex: 2,
          }}>
            {/* Light worlds: solid, readable word tags on surface cards (no glow to
                carry faint tokens). Dark worlds keep the original glow-era tokens. */}
            <div style={isLight ? {
              padding: '10px 20px',
              borderRadius: 12,
              background: `linear-gradient(${color}22, ${color}22), ${ad?.palette.surface ?? '#ffffff'}`,
              border: `2px solid ${color}`,
              boxShadow: ad?.depth.shadow_md,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              whiteSpace: 'nowrap',
            } : {
              width: 110,
              height: 80,
              borderRadius: 14,
              background: `${color}35`,
              border: `2.5px solid ${color}88`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 0 18px ${color}22`,
            }}>
              <span style={isLight ? {
                fontFamily: fontFamily,
                fontSize: 28,
                fontWeight: 800,
                color,
              } : {
                fontFamily: monoFamily,
                fontSize: 22,
                fontWeight: 700,
                color,
              }}>
                {scatterWords[i]}
              </span>
            </div>
          </div>
        );
      })}

      {/* Takeaway text emerges from convergence point */}
      {textOpacity > 0.01 && (
        <AbsoluteFill style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: textOpacity,
          transform: `scale(${textScale})`,
          zIndex: 5,
          padding: '0 60px',
        }}>
          {/* Key takeaway label */}
          <div style={{
            fontFamily: fontFamily,
            fontSize: 18,
            fontWeight: 700,
            color: accentColor,
            letterSpacing: 6,
            textTransform: 'uppercase',
            marginBottom: 24,
          }}>
            Key Takeaway
          </div>

          {/* Main text */}
          <div style={{
            fontFamily: fontFamily,
            fontSize: 52,
            fontWeight: 900,
            color: textColor,
            lineHeight: 1.3,
            textAlign: 'center',
            letterSpacing: -0.5,
            textShadow: useGlow ? `0 0 60px ${accentColor}55` : 'none',
            marginBottom: 12,
          }}>
            {line1}
          </div>
          <div style={{
            fontFamily: fontFamily,
            fontSize: 36,
            fontWeight: 700,
            color: `${accent2}cc`,
            textAlign: 'center',
            letterSpacing: 1,
          }}>
            {line2}
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
