/**
 * NumberCounterScene — animated hero-number counter.
 *
 * Animates a large number counting up from 0 (or from a smaller start value)
 * to a final target value. Designed for "128K tokens", "1 trillion params", etc.
 *
 * Props (via data field from storyboard):
 *   value   — target number to count to
 *   label   — what it means (e.g. "token context window")
 *   suffix  — optional unit appended after number (e.g. "K", "B", "tokens/s")
 *   start   — optional starting value (default 0)
 *
 * Layout:
 *   - Number grows from small to large (spring animation)
 *   - Label fades in below
 *   - Pulsing glow ring behind the number at peak
 */
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const BG = '#050510';

const COUNT_START_FRAME = 12;  // frames before counter begins
const COUNT_END_FRAME = 75;    // frames at which counter reaches target

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
}

function formatNumber(n: number, target: number): string {
  // Format the number with commas, matching the magnitude of the target
  if (target >= 1_000_000_000) {
    return (n / 1_000_000_000).toFixed(1) + 'B';
  }
  if (target >= 1_000_000) {
    return (n / 1_000_000).toFixed(1) + 'M';
  }
  if (target >= 100_000) {
    return Math.round(n / 1_000).toLocaleString() + 'K';
  }
  if (target >= 10_000) {
    return Math.round(n).toLocaleString();
  }
  return Math.round(n).toString();
}

export const NumberCounterScene: React.FC<NumberCounterSceneProps> = ({
  data,
  accentColor,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const {value: targetValue, label, suffix = '', start: startValue = 0} = data;

  // Eased count progress (accelerates then decelerates)
  const rawProgress = interpolate(
    frame,
    [COUNT_START_FRAME, COUNT_END_FRAME],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: (t: number) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
    },
  );

  const currentValue = startValue + (targetValue - startValue) * rawProgress;

  // Scale spring — number "pops in" from small to large
  const scaleSpring = spring({
    fps,
    frame: Math.max(0, frame - 6),
    config: {damping: 12, stiffness: 80, mass: 0.5},
    durationInFrames: 25,
  });
  const numberScale = interpolate(scaleSpring, [0, 1], [0.4, 1]);

  // Overall scene fade
  const sceneOpacity = interpolate(
    frame,
    [0, 10, durationInFrames - 10, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Label fade-in after counter starts
  const labelOpacity = interpolate(
    frame,
    [COUNT_START_FRAME + 15, COUNT_START_FRAME + 35],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Pulsing glow at peak
  const peakReached = frame >= COUNT_END_FRAME;
  const pulsePhase = (frame - COUNT_END_FRAME) / 40;
  const glowSize = peakReached
    ? 350 + 60 * Math.sin(pulsePhase * 2 * Math.PI)
    : 250 * rawProgress;

  // Suffix/unit appears as number completes
  const suffixOpacity = interpolate(
    frame,
    [COUNT_END_FRAME - 5, COUNT_END_FRAME + 10],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const displayNumber = formatNumber(currentValue, targetValue);

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity}}>
      {/* Background radial glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse ${glowSize}px ${glowSize * 0.7}px at 50% 48%, ${accentColor}1a 0%, transparent 70%)`,
        }}
      />

      {/* Ring around number at peak */}
      {peakReached && (
        <AbsoluteFill
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              width: 360 + 40 * Math.sin(pulsePhase * 2 * Math.PI),
              height: 360 + 40 * Math.sin(pulsePhase * 2 * Math.PI),
              borderRadius: '50%',
              border: `3px solid ${accentColor}44`,
              boxShadow: `0 0 60px ${accentColor}33`,
              opacity: interpolate(
                frame,
                [COUNT_END_FRAME, COUNT_END_FRAME + 20],
                [0, 0.8],
                {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
              ),
            }}
          />
        </AbsoluteFill>
      )}

      {/* Main number */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 0,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: 8,
            transform: `scale(${numberScale})`,
          }}
        >
          <span
            style={{
              fontFamily: FONT,
              fontSize: 120,
              fontWeight: 900,
              color: '#ffffff',
              letterSpacing: -4,
              lineHeight: 1,
              fontVariantNumeric: 'tabular-nums',
              textShadow: `0 0 40px ${accentColor}66, 0 0 80px ${accentColor}33`,
            }}
          >
            {displayNumber}
          </span>

          {suffix && (
            <span
              style={{
                fontFamily: FONT,
                fontSize: 48,
                fontWeight: 700,
                color: accentColor,
                opacity: suffixOpacity,
                letterSpacing: 1,
              }}
            >
              {suffix}
            </span>
          )}
        </div>

        {/* Label below the number */}
        <div
          style={{
            marginTop: 24,
            fontFamily: FONT,
            fontSize: 26,
            fontWeight: 400,
            color: 'rgba(255,255,255,0.65)',
            letterSpacing: 2,
            textTransform: 'uppercase',
            textAlign: 'center',
            padding: '0 80px',
            opacity: labelOpacity,
          }}
        >
          {label}
        </div>
      </AbsoluteFill>

      {/* Ticker-tape dots racing up */}
      <AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden'}}>
        {[...Array(6)].map((_, i) => {
          const dotPhase = (frame / 90 + i / 6) % 1;
          const y = 1920 - dotPhase * 2200;
          const x = 80 + (i / 5) * 920;
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: x,
                top: y,
                width: 4,
                height: 4,
                borderRadius: '50%',
                background: accentColor,
                opacity: 0.3 * (1 - dotPhase),
              }}
            />
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
