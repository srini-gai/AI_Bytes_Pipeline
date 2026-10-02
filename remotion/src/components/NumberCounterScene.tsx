/**
 * NumberCounterScene — context container fill (v41 token-native).
 *
 * s07: 2.64s ≈ 79 frames at 30fps.
 *   Beat A (0–26f):  Container frame appears, first token blocks fill from bottom
 *   Beat B (26–53f): Tokens fill rapidly, container saturating
 *   Beat C (53–79f): Nearly full, label pulses
 *
 * qualitative=true → context container fill with token blocks (no precise number).
 * qualitative=false → original numeric counter (unchanged).
 *
 * Data: {type: "counter", value: 100, label: "Context consumed", suffix: "%"}
 */
import React from 'react';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const MONO = '"JetBrains Mono", "Fira Code", "SF Mono", monospace';
const BG = '#050510';

interface NumberCounterData {
  type: 'counter';
  value: number;
  label: string;
  suffix?: string;
  start?: number;
}

interface NumberCounterSceneProps {
  data: NumberCounterData;
  accentColor: string;
  durationInFrames: number;
  qualitative?: boolean;
}

// Token block grid for context container
const GRID_COLS = 8;
const GRID_ROWS = 12;
const BLOCK_SIZE = 56;
const BLOCK_GAP = 6;
const TOTAL_BLOCKS = GRID_COLS * GRID_ROWS;

// Deterministic mini-labels for token blocks
function blockLabel(idx: number): string {
  const labels = ['tok', 'id', 'vec', 'emb', 'att', 'pos', 'enc', 'dec', 'pad', 'cls', 'sep', 'eos'];
  return labels[idx % labels.length];
}

function formatNumber(n: number, target: number): string {
  if (target >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + 'B';
  if (target >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (target >= 100_000) return Math.round(n / 1_000).toLocaleString() + 'K';
  if (target >= 10_000) return Math.round(n).toLocaleString();
  return Math.round(n).toString();
}

export const NumberCounterScene: React.FC<NumberCounterSceneProps> = ({
  data,
  accentColor,
  durationInFrames,
  qualitative = false,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const accent2 = '#34d399';

  const sceneOpacity = interpolate(
    frame,
    [0, 6, durationInFrames - 6, durationInFrames],
    [0, 1, 1, 0.3],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  if (qualitative) {
    return (
      <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity}}>
        <ContextContainerFill
          data={data}
          accentColor={accentColor}
          accent2={accent2}
          frame={frame}
          fps={fps}
          durationInFrames={durationInFrames}
        />
      </AbsoluteFill>
    );
  }

  // ── Non-qualitative: original numeric counter ─────────────────────────────
  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity}}>
      <NumericCounter data={data} accentColor={accentColor} frame={frame} fps={fps} durationInFrames={durationInFrames} />
    </AbsoluteFill>
  );
};

// ── Context Container Fill (v41 qualitative mode) ───────────────────────────

interface ContainerFillProps {
  data: NumberCounterData;
  accentColor: string;
  accent2: string;
  frame: number;
  fps: number;
  durationInFrames: number;
}

const ContextContainerFill: React.FC<ContainerFillProps> = ({
  data, accentColor, accent2, frame, fps, durationInFrames,
}) => {
  const gridW = GRID_COLS * (BLOCK_SIZE + BLOCK_GAP) - BLOCK_GAP;
  const gridH = GRID_ROWS * (BLOCK_SIZE + BLOCK_GAP) - BLOCK_GAP;
  const containerPad = 20;
  const containerW = gridW + containerPad * 2;
  const containerH = gridH + containerPad * 2;
  const containerX = (1080 - containerW) / 2;
  const containerY = 340;

  // Container frame appears
  const frameOpacity = interpolate(
    frame, [4, 14], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Fill progress — blocks fill bottom-to-top, left-to-right
  const fillProgress = interpolate(
    frame, [8, durationInFrames - 12], [0, 0.92],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
     easing: (t: number) => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2},
  );
  const filledBlocks = Math.floor(fillProgress * TOTAL_BLOCKS);

  // Label
  const labelOpacity = interpolate(
    frame, [12, 24], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Warning pulse when nearly full
  const nearFull = fillProgress > 0.7;
  const warnPulse = nearFull ? 0.5 + 0.5 * Math.sin(frame * 0.25) : 0;

  return (
    <>
      {/* Background glow */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 700px 500px at 50% 55%, ${accentColor}10 0%, transparent 70%)`,
      }} />

      {/* Title */}
      <div style={{
        position: 'absolute', top: 180, left: 0, right: 0,
        textAlign: 'center', opacity: labelOpacity, zIndex: 3,
        fontSize: 32, fontWeight: 800, color: 'rgba(255,255,255,0.8)',
        fontFamily: FONT, letterSpacing: 2,
      }}>
        {data.label.toUpperCase()}
      </div>

      {/* Container frame */}
      <div style={{
        position: 'absolute',
        left: containerX,
        top: containerY,
        width: containerW,
        height: containerH,
        border: `3px solid ${nearFull ? `rgba(239,68,68,${0.4 + warnPulse * 0.4})` : `${accentColor}55`}`,
        borderRadius: 18,
        opacity: frameOpacity,
        boxShadow: nearFull
          ? `0 0 ${30 + warnPulse * 30}px rgba(239,68,68,0.2), inset 0 0 20px rgba(239,68,68,0.05)`
          : `0 0 30px ${accentColor}15`,
        zIndex: 2,
        overflow: 'hidden',
      }}>
        {/* Grid of token blocks — fills bottom-to-top */}
        <div style={{
          position: 'absolute',
          left: containerPad,
          top: containerPad,
          display: 'flex',
          flexWrap: 'wrap',
          gap: BLOCK_GAP,
          width: gridW,
        }}>
          {Array.from({length: TOTAL_BLOCKS}, (_, idx) => {
            // Fill bottom-to-top: reverse row order
            const col = idx % GRID_COLS;
            const row = Math.floor(idx / GRID_COLS);
            const bottomUpIdx = (GRID_ROWS - 1 - row) * GRID_COLS + col;
            const isFilled = bottomUpIdx < filledBlocks;

            // Stagger appearance
            const blockDelay = bottomUpIdx * 0.6;
            const blockOpacity = isFilled
              ? interpolate(
                  frame,
                  [8 + blockDelay, 8 + blockDelay + 4],
                  [0, 1],
                  {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
                )
              : 0.06;

            const fillColor = nearFull && isFilled
              ? interpolate(warnPulse, [0, 1], [0, 0.15])
              : 0;

            return (
              <div key={idx} style={{
                width: BLOCK_SIZE,
                height: BLOCK_SIZE,
                borderRadius: 8,
                background: isFilled
                  ? `${accentColor}${Math.round((0.2 + fillColor) * 255).toString(16).padStart(2, '0')}`
                  : `rgba(255,255,255,0.03)`,
                border: isFilled ? `1.5px solid ${accentColor}55` : '1.5px solid rgba(255,255,255,0.06)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                opacity: blockOpacity,
              }}>
                {isFilled && blockOpacity > 0.5 && (
                  <span style={{
                    fontFamily: MONO,
                    fontSize: 10,
                    fontWeight: 600,
                    color: `${accentColor}88`,
                    letterSpacing: 0.5,
                  }}>
                    {blockLabel(bottomUpIdx)}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Fill meter label at bottom */}
      <div style={{
        position: 'absolute',
        top: containerY + containerH + 30,
        left: 0, right: 0,
        textAlign: 'center',
        opacity: labelOpacity,
        zIndex: 3,
      }}>
        <span style={{
          fontFamily: FONT,
          fontSize: 22,
          fontWeight: 700,
          color: nearFull ? `rgba(239,68,68,${0.6 + warnPulse * 0.3})` : `${accentColor}aa`,
          letterSpacing: 3,
        }}>
          {nearFull ? 'FILLING UP' : 'CONTEXT WINDOW'}
        </span>
      </div>
    </>
  );
};

// ── Original Numeric Counter (non-qualitative) ─────────────────────────────

interface NumericCounterProps {
  data: NumberCounterData;
  accentColor: string;
  frame: number;
  fps: number;
  durationInFrames: number;
}

const NumericCounter: React.FC<NumericCounterProps> = ({
  data, accentColor, frame, fps, durationInFrames,
}) => {
  const {value: targetValue, label, suffix = '', start: startValue = 0} = data;

  const rawProgress = interpolate(
    frame, [12, 75], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
     easing: (t: number) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2},
  );
  const currentValue = startValue + (targetValue - startValue) * rawProgress;

  const scaleSpring = spring({
    fps, frame: Math.max(0, frame - 6),
    config: {damping: 12, stiffness: 80, mass: 0.5},
    durationInFrames: 25,
  });
  const numberScale = interpolate(scaleSpring, [0, 1], [0.4, 1]);

  const labelOpacity = interpolate(
    frame, [27, 47], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const peakReached = frame >= 75;
  const pulsePhase = (frame - 75) / 40;
  const glowSize = peakReached ? 350 + 60 * Math.sin(pulsePhase * 2 * Math.PI) : 250 * rawProgress;

  const suffixOpacity = interpolate(
    frame, [70, 85], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <>
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse ${glowSize}px ${glowSize * 0.7}px at 50% 48%, ${accentColor}1a 0%, transparent 70%)`,
      }} />

      {peakReached && (
        <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <div style={{
            width: 360 + 40 * Math.sin(pulsePhase * 2 * Math.PI),
            height: 360 + 40 * Math.sin(pulsePhase * 2 * Math.PI),
            borderRadius: '50%',
            border: `3px solid ${accentColor}44`,
            boxShadow: `0 0 60px ${accentColor}33`,
            opacity: interpolate(frame, [75, 95], [0, 0.8], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          }} />
        </AbsoluteFill>
      )}

      <AbsoluteFill style={{
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{display: 'flex', alignItems: 'baseline', gap: 8, transform: `scale(${numberScale})`}}>
          <span style={{
            fontFamily: FONT, fontSize: 120, fontWeight: 900,
            color: '#ffffff', letterSpacing: -4, lineHeight: 1,
            fontVariantNumeric: 'tabular-nums',
            textShadow: `0 0 40px ${accentColor}66, 0 0 80px ${accentColor}33`,
          }}>
            {formatNumber(currentValue, targetValue)}
          </span>
          {suffix && (
            <span style={{
              fontFamily: FONT, fontSize: 48, fontWeight: 700,
              color: accentColor, opacity: suffixOpacity, letterSpacing: 1,
            }}>
              {suffix}
            </span>
          )}
        </div>
        <div style={{
          marginTop: 24, fontFamily: FONT, fontSize: 26,
          fontWeight: 400, color: 'rgba(255,255,255,0.65)',
          letterSpacing: 2, textTransform: 'uppercase',
          textAlign: 'center', padding: '0 80px', opacity: labelOpacity,
        }}>
          {label}
        </div>
      </AbsoluteFill>
    </>
  );
};
