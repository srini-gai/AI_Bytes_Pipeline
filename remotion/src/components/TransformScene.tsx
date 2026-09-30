/**
 * TransformScene — Visual Director v3
 *
 * Shows an A→B transformation: objects appear, change, combine or rearrange.
 * Used here for the RAG acronym assembly: letters stamp in one by one
 * with icons snapping below, then connector lines draw between stages.
 *
 * Beat-driven: each letter/item stamps in on its own beat; final beat
 * reveals the full assembled object.
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface TransformItem {
  letter: string;
  label: string;
  icon: string;
  color: string;
}

interface TransformSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];   // ["Retrieval","Augmented","Generation"] or similar
  objects: string[];
  accentColor?: string;
  accent2?: string;
}

const DEFAULT_ITEMS: TransformItem[] = [
  {letter: 'R', label: 'Retrieval',   icon: '🔍', color: '#6366f1'},
  {letter: 'A', label: 'Augmented',   icon: '🧩', color: '#a78bfa'},
  {letter: 'G', label: 'Generation',  icon: '✨', color: '#34d399'},
];

export const TransformScene: React.FC<TransformSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Build items from onScreenText or use defaults
  const items: TransformItem[] = onScreenText.length >= 3
    ? [
        {letter: 'R', label: onScreenText[0] ?? 'Retrieval',  icon: '🔍', color: '#6366f1'},
        {letter: 'A', label: onScreenText[1] ?? 'Augmented',  icon: '🧩', color: accentColor},
        {letter: 'G', label: onScreenText[2] ?? 'Generation', icon: '✨', color: accent2},
      ]
    : DEFAULT_ITEMS;

  // Each of the first 3 beats: one letter stamps in
  const letterProgress = items.map((_, i) => {
    const beat = beats[i] ?? {start: i * 1.0, end: i * 1.0 + 1.0};
    return easeOut(frame, fps, beat.start, beat.end);
  });

  // Final beat: connector lines draw
  const b3 = beats[3] ?? {start: 3.0, end: 5.0};
  const lineProgress = linearProgress(frame, fps, b3.start, b3.start + (b3.end - b3.start) * 0.6);
  const lineSmooth   = smoothstep(lineProgress);

  // Camera push-in on final beat: scale up slightly
  const camScale = interpolate(
    linearProgress(frame, fps, b3.start, b3.end),
    [0, 1],
    [1, 1.06],
  );

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  const CARD_W = 240;
  const CARD_GAP = 48;
  const TOTAL_W  = items.length * CARD_W + (items.length - 1) * CARD_GAP;
  const START_X  = (1080 - TOTAL_W) / 2;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        opacity: sceneOpacity,
        overflow: 'hidden',
      }}
    >
      {/* Background glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 800px 500px at 50% 48%, ${accentColor}10 0%, transparent 70%)`,
        }}
      />

      {/* Main canvas — centred vertically at 46% */}
      <AbsoluteFill
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transform: `scale(${camScale})`,
          transformOrigin: '50% 46%',
        }}
      >
        <div style={{position: 'relative', width: TOTAL_W, paddingTop: 100}}>
          {/* Letter cards */}
          {items.map((item, i) => {
            const p = letterProgress[i];
            const x = i * (CARD_W + CARD_GAP);
            const y = interpolate(p, [0, 1], [-120, 0]);
            const scale = interpolate(p, [0, 0.7, 1], [0.3, 1.12, 1]);
            const alpha = interpolate(p, [0, 0.3], [0, 1], {extrapolateRight: 'clamp'});

            return (
              <div
                key={item.letter}
                style={{
                  position: 'absolute',
                  left: x,
                  width: CARD_W,
                  opacity: alpha,
                  transform: `translateY(${y}px) scale(${scale})`,
                  transformOrigin: '50% 100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 16,
                }}
              >
                {/* Big letter */}
                <div
                  style={{
                    fontFamily: FONT,
                    fontSize: 160,
                    fontWeight: 900,
                    color: item.color,
                    lineHeight: 1,
                    textShadow: `0 0 80px ${item.color}66`,
                    letterSpacing: -4,
                  }}
                >
                  {item.letter}
                </div>

                {/* Icon below letter */}
                <div
                  style={{
                    fontSize: 52,
                    transform: `scale(${interpolate(p, [0.5, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})})`,
                    filter: `drop-shadow(0 0 16px ${item.color}88)`,
                  }}
                >
                  {item.icon}
                </div>

                {/* Label */}
                <div
                  style={{
                    fontFamily: FONT,
                    fontSize: 26,
                    fontWeight: 700,
                    color: item.color,
                    letterSpacing: 2,
                    textTransform: 'uppercase',
                    opacity: interpolate(p, [0.6, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
                  }}
                >
                  {item.label}
                </div>
              </div>
            );
          })}

          {/* Connector lines (draw on beat 3) */}
          {items.slice(0, -1).map((_, i) => {
            const lineStart = i / (items.length - 1);
            const lineEnd   = (i + 1) / (items.length - 1);
            // Each line draws in sequence: stagger within the overall lineSmooth
            const segP = smoothstep(
              interpolate(lineSmooth, [lineStart * 0.8, lineEnd * 0.8], [0, 1], {
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              }),
            );
            const x1 = i * (CARD_W + CARD_GAP) + CARD_W;
            const x2 = x1 + CARD_GAP;

            return (
              <div
                key={`line-${i}`}
                style={{
                  position: 'absolute',
                  left: x1,
                  top: 72, // aligns with letter midpoint
                  width: segP * CARD_GAP,
                  height: 3,
                  background: `linear-gradient(90deg, ${items[i].color}, ${items[i + 1].color})`,
                  borderRadius: 2,
                  boxShadow: `0 0 10px ${accentColor}66`,
                  opacity: lineSmooth > 0.05 ? 1 : 0,
                }}
              />
            );
          })}
        </div>
      </AbsoluteFill>

      {/* "RAG" label that appears on final beat */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'flex-end',
          paddingBottom: 200,
          opacity: interpolate(linearProgress(frame, fps, b3.start, b3.end), [0.3, 1], [0, 1]),
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: 8,
            textTransform: 'uppercase',
            color: accentColor,
          }}
        >
          Retrieval-Augmented Generation
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
