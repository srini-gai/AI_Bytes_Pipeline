/**
 * NetworkBuildScene — Embedding vector space (v41 token-native).
 *
 * 4.14s ≈ 124 frames at 30fps. 3 beats:
 *   Beat A (0–40f):   Three integer IDs fall into deep space from above
 *   Beat B (40–80f):  IDs expand/transform into vector arrows
 *   Beat C (80–124f): Attention lines emerge between vectors
 *
 * on_screen_text: ["INTEGER IDs", "EMBEDDING VECTORS", "ATTENTION"]
 * NO small circles, NO centered node graph, NO edges between dots.
 * Full-canvas deep-space feel with large dominant objects.
 */
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, MONO} from './beatUtils';
import type {SceneBeat} from '../types';

interface NetworkBuildSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
}

// The three token IDs carried from s03
const TOKEN_IDS = [1726, 42891, 481];
const TOKEN_LABELS = ['un', 'believ', 'able'];

// Positions for the three ID/vector objects (spread across 1080x1920 canvas)
const POSITIONS = [
  {x: 270, y: 500},
  {x: 540, y: 960},
  {x: 810, y: 1420},
];

// Vector arrow directions (radiate from each position)
const VECTOR_DIRS = [
  [{dx: -120, dy: -80}, {dx: 80, dy: -100}, {dx: -60, dy: 90}],
  [{dx: 130, dy: -60}, {dx: -90, dy: -110}, {dx: 110, dy: 70}],
  [{dx: -100, dy: -90}, {dx: 70, dy: -70}, {dx: 100, dy: 80}],
];

export const NetworkBuildScene: React.FC<NetworkBuildSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Use beats if provided, else proportional defaults
  const totalFrames = fps * 4.14;
  const b0End = beats[0]?.end ? beats[0].end * fps : Math.round(totalFrames * 0.32);
  const b1Start = beats[1]?.start ? beats[1].start * fps : Math.round(totalFrames * 0.28);
  const b1End = beats[1]?.end ? beats[1].end * fps : Math.round(totalFrames * 0.65);
  const b2Start = beats[2]?.start ? beats[2].start * fps : Math.round(totalFrames * 0.60);

  // ── Beat A: IDs fall from above ───────────────────────────────────────────
  const idFalls = TOKEN_IDS.map((_, i) => {
    const stagger = i * 6;
    return spring({
      fps,
      frame: Math.max(0, frame - stagger),
      config: {damping: 12, stiffness: 120, mass: 0.6},
      durationInFrames: Math.round(b0End),
    });
  });

  // ── Beat B: IDs transform into vectors ────────────────────────────────────
  const vectorProgress = interpolate(
    frame,
    [b1Start, b1End],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // ID opacity fades as vectors appear
  const idTextOpacity = interpolate(
    vectorProgress,
    [0, 0.4, 0.7],
    [1, 0.8, 0.3],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // ── Beat C: Attention lines ───────────────────────────────────────────────
  const attentionProgress = interpolate(
    frame,
    [b2Start, b2Start + 30],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Pulse glow on attention
  const attentionGlow = attentionProgress > 0
    ? 0.5 + 0.5 * Math.sin((frame - b2Start) * 0.15)
    : 0;

  // Scene envelope
  const sceneOpacity = interpolate(
    frame,
    [0, 6, totalFrames - 6, totalFrames],
    [0, 1, 1, 0.4],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Label transitions
  const label0Opacity = interpolate(frame, [4, 12, b1Start, b1Start + 8], [0, 0.7, 0.7, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const label1Opacity = interpolate(frame, [b1Start + 4, b1Start + 14, b2Start, b2Start + 8], [0, 0.7, 0.7, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const label2Opacity = interpolate(frame, [b2Start + 4, b2Start + 14], [0, 0.7], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity, overflow: 'hidden'}}>
      {/* Deep space background gradient */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 1200px 900px at 50% 50%, ${accentColor}08 0%, transparent 70%)`,
      }} />

      {/* Grid lines for depth feel */}
      <svg viewBox="0 0 1080 1920" width={1080} height={1920} style={{position: 'absolute', inset: 0, opacity: 0.04}}>
        {Array.from({length: 12}, (_, i) => (
          <line key={`h${i}`} x1={0} y1={i * 160} x2={1080} y2={i * 160} stroke="#ffffff" strokeWidth={1} />
        ))}
        {Array.from({length: 7}, (_, i) => (
          <line key={`v${i}`} x1={i * 180} y1={0} x2={i * 180} y2={1920} stroke="#ffffff" strokeWidth={1} />
        ))}
      </svg>

      <svg viewBox="0 0 1080 1920" width={1080} height={1920} style={{position: 'absolute', inset: 0}}>
        {/* Attention lines between positions (Beat C) */}
        {attentionProgress > 0.01 && POSITIONS.map((posA, i) =>
          POSITIONS.filter((_, j) => j > i).map((posB, j) => {
            const lineP = Math.min(1, attentionProgress * 1.5 - j * 0.2);
            if (lineP <= 0) return null;
            const midX = (posA.x + posB.x) / 2;
            const midY = (posA.y + posB.y) / 2;
            return (
              <g key={`att-${i}-${j}`}>
                <line
                  x1={posA.x} y1={posA.y}
                  x2={posA.x + (posB.x - posA.x) * lineP}
                  y2={posA.y + (posB.y - posA.y) * lineP}
                  stroke={accent2}
                  strokeWidth={2.5}
                  opacity={0.4 + attentionGlow * 0.3}
                  strokeDasharray="8 6"
                />
                {lineP > 0.8 && (
                  <circle
                    cx={midX} cy={midY} r={6}
                    fill={accent2}
                    opacity={0.6 + attentionGlow * 0.3}
                  />
                )}
              </g>
            );
          })
        )}

        {/* Token ID objects */}
        {TOKEN_IDS.map((id, i) => {
          const pos = POSITIONS[i];
          const fall = idFalls[i];
          const startY = -200;
          const y = interpolate(fall, [0, 1], [startY, pos.y]);
          const scale = interpolate(fall, [0, 1], [0.5, 1]);

          // Vector arrows emanating from the ID position
          const arrows = VECTOR_DIRS[i];

          return (
            <g key={i} transform={`translate(${pos.x}, ${y}) scale(${scale})`}>
              {/* Glow behind */}
              <circle cx={0} cy={0}
                r={60 + vectorProgress * 30}
                fill="none"
                stroke={accentColor}
                strokeWidth={1}
                opacity={0.15 + vectorProgress * 0.1}
              />

              {/* Vector arrows (Beat B) */}
              {vectorProgress > 0.01 && arrows.map((dir, ai) => {
                const arrowP = Math.min(1, vectorProgress * 1.5 - ai * 0.15);
                if (arrowP <= 0) return null;
                const ex = dir.dx * arrowP;
                const ey = dir.dy * arrowP;
                return (
                  <g key={ai}>
                    <line
                      x1={0} y1={0} x2={ex} y2={ey}
                      stroke={accentColor}
                      strokeWidth={3}
                      opacity={arrowP * 0.7}
                    />
                    {/* Arrowhead */}
                    {arrowP > 0.5 && (
                      <circle
                        cx={ex} cy={ey} r={4}
                        fill={accentColor}
                        opacity={arrowP * 0.8}
                      />
                    )}
                  </g>
                );
              })}

              {/* ID number — large, dominant */}
              <text
                x={0} y={8}
                textAnchor="middle"
                fontFamily="'JetBrains Mono', 'Fira Code', monospace"
                fontSize={48}
                fontWeight={700}
                fill="#ffffff"
                opacity={idTextOpacity}
              >
                {id}
              </text>

              {/* Small label below */}
              <text
                x={0} y={40}
                textAnchor="middle"
                fontFamily={FONT}
                fontSize={18}
                fontWeight={500}
                fill={accentColor}
                opacity={0.5 * idTextOpacity}
              >
                {TOKEN_LABELS[i]}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Phase labels */}
      {label0Opacity > 0.01 && (
        <div style={{
          position: 'absolute', top: 160, left: 0, right: 0,
          textAlign: 'center', opacity: label0Opacity, zIndex: 5,
        }}>
          <span style={{
            fontFamily: FONT, fontSize: 26, fontWeight: 800,
            color: 'rgba(255,255,255,0.7)', letterSpacing: 4,
          }}>
            {onScreenText[0] ?? 'INTEGER IDs'}
          </span>
        </div>
      )}
      {label1Opacity > 0.01 && (
        <div style={{
          position: 'absolute', top: 160, left: 0, right: 0,
          textAlign: 'center', opacity: label1Opacity, zIndex: 5,
        }}>
          <span style={{
            fontFamily: FONT, fontSize: 26, fontWeight: 800,
            color: accentColor, letterSpacing: 4,
          }}>
            {onScreenText[1] ?? 'EMBEDDING VECTORS'}
          </span>
        </div>
      )}
      {label2Opacity > 0.01 && (
        <div style={{
          position: 'absolute', top: 160, left: 0, right: 0,
          textAlign: 'center', opacity: label2Opacity, zIndex: 5,
        }}>
          <span style={{
            fontFamily: FONT, fontSize: 26, fontWeight: 800,
            color: accent2, letterSpacing: 4,
          }}>
            {onScreenText[2] ?? 'ATTENTION'}
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};
