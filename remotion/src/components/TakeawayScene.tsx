/**
 * TakeawayScene — the "Key Takeaway" summary scene.
 *
 * Shows a single bold statement with animated visual summary.
 * Sits just before the CTA scene at the end of every episode.
 *
 * Props:
 *   text          — the takeaway statement (≤ 10 words)
 *   accentColor   — theme accent hex
 *   durationInFrames
 */
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const BG = '#050510';

interface TakeawaySceneProps {
  text: string;
  accentColor: string;
  accent2?: string;
  durationInFrames: number;
}

export const TakeawayScene: React.FC<TakeawaySceneProps> = ({
  text,
  accentColor,
  accent2 = '#34d399',
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Scene fade
  const sceneOpacity = interpolate(
    frame,
    [0, 8, durationInFrames - 10, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Horizontal rule width sweeps from 0 → full width
  const ruleSpring = spring({
    fps,
    frame: Math.max(0, frame - 8),
    config: {damping: 16, stiffness: 70, mass: 0.5},
    durationInFrames: 25,
  });
  const ruleWidth = interpolate(ruleSpring, [0, 1], [0, 80]);

  // Label appears first
  const labelOpacity = interpolate(frame, [10, 25], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const labelY = interpolate(frame, [10, 25], [12, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // Main text rises up with spring
  const textSpring = spring({
    fps,
    frame: Math.max(0, frame - 22),
    config: {damping: 14, stiffness: 90, mass: 0.6},
    durationInFrames: 30,
  });
  const textY = interpolate(textSpring, [0, 1], [50, 0]);
  const textOpacity = interpolate(frame, [22, 40], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // Glow pulsing at steady state
  const pulsePhase = frame / 50;
  const glowSize = 600 + 80 * Math.sin(pulsePhase * 2 * Math.PI);

  // Checkmark icon draws in
  const checkOpacity = interpolate(frame, [38, 55], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const checkScale = interpolate(frame, [38, 55], [0.3, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity}}>
      {/* Radial glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse ${glowSize}px ${glowSize * 0.6}px at 50% 50%, ${accentColor}0f 0%, transparent 70%)`,
        }}
      />

      {/* Subtle grid lines */}
      <AbsoluteFill
        style={{
          backgroundImage: `
            linear-gradient(${accentColor}08 1px, transparent 1px),
            linear-gradient(90deg, ${accentColor}08 1px, transparent 1px)
          `,
          backgroundSize: '80px 80px',
        }}
      />

      {/* Content */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 80px',
          gap: 0,
        }}
      >
        {/* ✓ icon */}
        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: '50%',
            background: `linear-gradient(135deg, ${accentColor} 0%, ${accent2} 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 36,
            opacity: checkOpacity,
            transform: `scale(${checkScale})`,
            boxShadow: `0 0 40px ${accentColor}55`,
          }}
        >
          <svg
            width="36"
            height="36"
            viewBox="0 0 36 36"
            fill="none"
          >
            <path
              d="M7 18L15 26L29 10"
              stroke="#ffffff"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        {/* TAKEAWAY label */}
        <div
          style={{
            opacity: labelOpacity,
            transform: `translateY(${labelY}px)`,
            fontFamily: FONT,
            fontSize: 18,
            fontWeight: 700,
            color: accentColor,
            letterSpacing: 6,
            textTransform: 'uppercase',
            marginBottom: 20,
          }}
        >
          Key Takeaway
        </div>

        {/* Gradient rule */}
        <div
          style={{
            width: `${ruleWidth}%`,
            height: 2,
            background: `linear-gradient(90deg, transparent, ${accentColor}, ${accent2}, transparent)`,
            marginBottom: 32,
            opacity: 0.8,
          }}
        />

        {/* Main takeaway text */}
        <div
          style={{
            opacity: textOpacity,
            transform: `translateY(${textY}px)`,
            fontFamily: FONT,
            fontSize: 56,
            fontWeight: 800,
            color: '#ffffff',
            lineHeight: 1.3,
            textAlign: 'center',
            letterSpacing: -0.5,
            textShadow: `0 0 60px ${accentColor}44`,
          }}
        >
          {text}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
