/**
 * TokenStreamScene — Sequential token emission (v41 token-native).
 *
 * 4.36s ≈ 131 frames at 30fps. 3 beats:
 *   Beat A (0–44f):   Transformer block glows, first token emits
 *   Beat B (44–87f):  Second token emits, camera follows growing stream
 *   Beat C (87–131f): Third token emits, stream accelerates
 *
 * on_screen_text: ["NEXT TOKEN", "ONE AT A TIME"]
 * NO context blocks, NO answer panels, NO citations — pure emission.
 * Camera follows the token stream across the canvas.
 */
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, MONO, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface TokenStreamSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  carryFrom?: string;
}

// Emitted tokens — generic prediction sequence
const EMITTED_TOKENS = ['The', 'cat', 'sat', 'on', 'the'];

export const TokenStreamScene: React.FC<TokenStreamSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const totalFrames = Math.round(fps * 4.36);
  const beatLen = Math.round(totalFrames / 3);

  // Beat boundaries
  const b0End = beats[0]?.end ? Math.round(beats[0].end * fps) : beatLen;
  const b1Start = beats[1]?.start ? Math.round(beats[1].start * fps) : Math.round(beatLen * 0.9);
  const b1End = beats[1]?.end ? Math.round(beats[1].end * fps) : beatLen * 2;
  const b2Start = beats[2]?.start ? Math.round(beats[2].start * fps) : Math.round(beatLen * 1.85);

  // Transformer block position (left side)
  const TX_CX = 200;
  const TX_CY = 960;
  const TX_W = 240;
  const TX_H = 320;

  // Token emission positions (stream right across canvas)
  const tokenStartX = TX_CX + TX_W / 2 + 60;
  const tokenSpacing = 220;

  // Scene opacity envelope
  const sceneOpacity = interpolate(
    frame,
    [0, 6, totalFrames - 6, totalFrames],
    [0, 1, 1, 0.4],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Processing pulse on transformer
  const processPulse = 0.5 + 0.5 * Math.sin(frame * 0.2);

  // Each token has its own emission timing
  const tokenEmissions = EMITTED_TOKENS.map((_, i) => {
    const emitFrame = Math.round(i * (totalFrames * 0.22));
    const emitProgress = spring({
      fps,
      frame: Math.max(0, frame - emitFrame),
      config: {damping: 14, stiffness: 100, mass: 0.5},
      durationInFrames: 25,
    });
    const isEmitted = frame >= emitFrame;
    return {emitProgress, isEmitted, emitFrame};
  });

  // Camera pans right as tokens stream out
  const emittedCount = tokenEmissions.filter(t => t.isEmitted).length;
  const camPanX = interpolate(
    emittedCount,
    [0, 1, 2, 3, 4, 5],
    [0, 0, -80, -180, -280, -350],
  );

  // Labels
  const label0Opacity = interpolate(
    frame,
    [8, 18, b1End, b1End + 10],
    [0, 0.8, 0.8, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const label1Opacity = interpolate(
    frame,
    [b2Start, b2Start + 12],
    [0, 0.8],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity, overflow: 'hidden'}}>
      {/* Background glow follows transformer */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 600px 600px at ${TX_CX + camPanX}px ${TX_CY}px, ${accentColor}12 0%, transparent 60%)`,
      }} />

      <div style={{
        position: 'absolute',
        inset: 0,
        transform: `translateX(${camPanX}px)`,
        transition: 'transform 0.3s ease-out',
      }}>
        <svg viewBox="0 0 1080 1920" width={1080} height={1920}
          style={{position: 'absolute', inset: 0}}>

          {/* ── Transformer block ─────────────────────────────────────── */}
          {/* Outer glow */}
          <rect
            x={TX_CX - TX_W / 2 - 8} y={TX_CY - TX_H / 2 - 8}
            width={TX_W + 16} height={TX_H + 16}
            rx={24}
            fill="none"
            stroke={accentColor}
            strokeWidth={2}
            opacity={0.15 + processPulse * 0.15}
          />

          {/* Body */}
          <rect
            x={TX_CX - TX_W / 2} y={TX_CY - TX_H / 2}
            width={TX_W} height={TX_H}
            rx={18}
            fill={`${accentColor}15`}
            stroke={accentColor}
            strokeWidth={3}
          />

          {/* Internal processing lines */}
          {Array.from({length: 5}, (_, i) => {
            const ly = TX_CY - TX_H / 2 + 50 + i * 50;
            const phase = (frame * 0.08 + i * 0.7) % 1;
            return (
              <rect key={i}
                x={TX_CX - TX_W / 2 + 24}
                y={ly}
                width={(TX_W - 48) * (0.3 + phase * 0.7)}
                height={6}
                rx={3}
                fill={accentColor}
                opacity={0.15 + phase * 0.25}
              />
            );
          })}

          {/* Label */}
          <text x={TX_CX} y={TX_CY + TX_H / 2 + 45}
            textAnchor="middle"
            fontFamily={FONT} fontSize={24} fontWeight={700}
            fill={accentColor} opacity={0.6}>
            TRANSFORMER
          </text>

          {/* ── Emission arrow ─────────────────────────────────────────── */}
          <line
            x1={TX_CX + TX_W / 2 + 4} y1={TX_CY}
            x2={tokenStartX - 10} y2={TX_CY}
            stroke={accent2}
            strokeWidth={3}
            opacity={0.4}
            strokeDasharray="6 4"
          />
          <polygon
            points={`${tokenStartX - 10},${TX_CY - 8} ${tokenStartX},${TX_CY} ${tokenStartX - 10},${TX_CY + 8}`}
            fill={accent2}
            opacity={0.5}
          />

          {/* ── Emitted token blocks ──────────────────────────────────── */}
          {EMITTED_TOKENS.map((tok, i) => {
            const {emitProgress, isEmitted} = tokenEmissions[i];
            if (!isEmitted) return null;

            const x = tokenStartX + i * tokenSpacing;
            const y = TX_CY;
            const scale = emitProgress;
            const opacity = emitProgress;

            // Latest token gets highlight
            const isLatest = i === emittedCount - 1;

            return (
              <g key={i}
                transform={`translate(${x}, ${y}) scale(${scale})`}
                opacity={opacity}>
                {/* Token box */}
                <rect
                  x={-70} y={-50}
                  width={140} height={100}
                  rx={14}
                  fill={isLatest ? `${accent2}25` : `${accent2}12`}
                  stroke={isLatest ? accent2 : `${accent2}66`}
                  strokeWidth={isLatest ? 3 : 2}
                />
                {/* Glow on latest */}
                {isLatest && (
                  <rect
                    x={-74} y={-54}
                    width={148} height={108}
                    rx={18}
                    fill="none"
                    stroke={accent2}
                    strokeWidth={2}
                    opacity={0.3 + processPulse * 0.2}
                  />
                )}
                {/* Token text */}
                <text x={0} y={12}
                  textAnchor="middle"
                  fontFamily={MONO}
                  fontSize={42}
                  fontWeight={800}
                  fill="#ffffff">
                  {tok}
                </text>
                {/* Sequence number */}
                <text x={0} y={-58}
                  textAnchor="middle"
                  fontFamily={MONO}
                  fontSize={16}
                  fontWeight={600}
                  fill={accent2}
                  opacity={0.5}>
                  t{i + 1}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Phase labels — fixed position (don't pan with camera) */}
      {label0Opacity > 0.01 && (
        <div style={{
          position: 'absolute', top: 300, left: 0, right: 0,
          textAlign: 'center', opacity: label0Opacity, zIndex: 5,
        }}>
          <span style={{
            fontFamily: FONT, fontSize: 36, fontWeight: 900,
            color: accent2, letterSpacing: 4,
          }}>
            {onScreenText[0] ?? 'NEXT TOKEN'}
          </span>
        </div>
      )}
      {label1Opacity > 0.01 && (
        <div style={{
          position: 'absolute', top: 300, left: 0, right: 0,
          textAlign: 'center', opacity: label1Opacity, zIndex: 5,
        }}>
          <span style={{
            fontFamily: FONT, fontSize: 36, fontWeight: 900,
            color: '#ffffff', letterSpacing: 4,
          }}>
            {onScreenText[1] ?? 'ONE AT A TIME'}
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};
