/**
 * DocumentRetrievalScene — Visual Director v3.1
 *
 * Camera-led storytelling: viewer travels through the retrieval system.
 * Sequence: query text large → query travels toward KB → KB cylinder expands
 * to dominate screen → documents fan OUT across the full canvas → 3 selected
 * chunks enlarge and leave frame-right (carry-over to ContextWindowScene).
 *
 * v3.1 changes:
 * - Cards 240×300px (up from 76×104) — readable on phone
 * - Fan radius 520px — fills full canvas width
 * - Camera tracks: zooms in on KB as it expands, then pulls back to show fan
 * - Selected chunks are 340×420px (giant), leaving frame-right
 * - All action uses the full 1080×1920 canvas, not a central strip
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, MONO, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface DocumentRetrievalSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  carryFrom?: string;
}

const TOTAL_DOCS = 12;

// Colors for matched vs unmatched docs
const MATCH_COL = '#34d399';
const DULL_COL  = 'rgba(255,255,255,0.18)';

// Which doc indices are the "selected" ones
const SELECTED = new Set([2, 5, 8]);

export const DocumentRetrievalScene: React.FC<DocumentRetrievalSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 1.2}; // query enters, KB appears
  const b1 = beats[1] ?? {start: 1.2, end: 2.8}; // documents fan across canvas
  const b2 = beats[2] ?? {start: 2.8, end: 4.5}; // selected chunks enlarge + leave frame

  // ── Timing ───────────────────────────────────────────────────────────────
  const queryP   = easeOut(frame, fps, b0.start, b0.start + 0.5);
  const kbP      = easeOut(frame, fps, b0.start + 0.4, b0.end);
  const fanP     = linearProgress(frame, fps, b1.start, b1.end);
  const selectP  = easeOut(frame, fps, b2.start, b2.start + 0.8);
  const exitP    = easeOut(frame, fps, b2.start + 0.5, b2.end);

  // ── Camera zoom: push into KB centre during b0, hold, then pull out for fan ──
  const camZoomIn  = easeOut(frame, fps, b0.start, b0.end);
  const camZoomOut = easeOut(frame, fps, b1.start, b1.start + 0.8);
  const camScale   = interpolate(camZoomIn, [0, 1], [0.85, 1.22])
                   * interpolate(camZoomOut, [0, 1], [1, 0.78]);
  const camY       = interpolate(camZoomIn, [0, 1], [60, -80])
                   + interpolate(camZoomOut, [0, 1], [0, 80]);

  // ── Layout ────────────────────────────────────────────────────────────────
  const KB_X = 540;
  const KB_Y = 880;
  const KB_BASE_R = 90;
  const KB_R = KB_BASE_R + smoothstep(kbP) * 60; // expands from 90→150

  // Fan: docs arc from top-left to bottom-right around the KB
  const FAN_RADIUS = 520;

  // Query text position — large, top-left, moves toward KB
  const queryX = interpolate(queryP, [0, 1], [100, KB_X - 80]);
  const queryY = interpolate(queryP, [0, 1], [300, KB_Y - 180]);
  const queryScale = interpolate(queryP, [0, 1], [1.0, 0.6]);

  return (
    <AbsoluteFill style={{backgroundColor: BG, overflow: 'hidden'}}>
      {/* Background radial glow shifts from accent (retrieval) → accent2 (match) */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 900px 1100px at ${KB_X}px ${KB_Y}px,
          ${fanP > 0.3 ? `${accent2}18` : `${accentColor}14`} 0%,
          transparent 65%)`,
      }}/>

      <svg
        viewBox="0 0 1080 1920"
        width={1080}
        height={1920}
        style={{
          position: 'absolute', inset: 0,
          transform: `scale(${camScale}) translateY(${camY}px)`,
          transformOrigin: `${KB_X}px ${KB_Y}px`,
        }}
      >
        {/* ── Query text — large and dominating ─────────────────────────── */}
        {queryP > 0 && (
          <g transform={`translate(${queryX}, ${queryY}) scale(${queryScale})`}
            opacity={interpolate(fanP, [0.4, 0.8], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}>
            <rect x={-20} y={-60} width={520} height={90}
              rx={14} fill={`${accentColor}15`} stroke={`${accentColor}55`} strokeWidth={2}/>
            <text x={10} y={0} fill={accentColor} fontFamily={MONO}
              fontSize={52} fontWeight="800">
              {onScreenText[0] ?? 'What is RAG?'}
            </text>
          </g>
        )}

        {/* ── Query → KB connection line ─────────────────────────────────── */}
        {queryP > 0.5 && kbP > 0 && (
          <line
            x1={queryX + 200} y1={queryY + 10}
            x2={KB_X} y2={KB_Y - KB_R}
            stroke={`${accentColor}44`} strokeWidth={2} strokeDasharray="10 6"
            opacity={smoothstep(kbP)}/>
        )}

        {/* ── Knowledge Base cylinder ─────────────────────────────────────── */}
        <g opacity={smoothstep(kbP)}>
          {/* Glow ring */}
          <circle cx={KB_X} cy={KB_Y} r={KB_R + 30}
            fill="none" stroke={accentColor} strokeWidth={1}
            opacity={0.2 + smoothstep(kbP) * 0.3} strokeDasharray="20 10"/>
          {/* Body */}
          <ellipse cx={KB_X} cy={KB_Y + 20} rx={KB_R} ry={20}
            fill={`${accentColor}22`} stroke={accentColor} strokeWidth={2.5}/>
          <rect x={KB_X - KB_R} y={KB_Y - 60} width={KB_R * 2} height={80}
            fill={`${accentColor}14`} stroke={accentColor} strokeWidth={2.5}/>
          <ellipse cx={KB_X} cy={KB_Y - 60} rx={KB_R} ry={20}
            fill={`${accentColor}30`} stroke={accentColor} strokeWidth={2.5}/>
          {/* KB label */}
          <text x={KB_X} y={KB_Y - 60} textAnchor="middle" dominantBaseline="middle"
            fill="#fff" fontFamily={FONT} fontSize={26} fontWeight="700">
            Knowledge Base
          </text>
          {/* Doc count badge */}
          <text x={KB_X} y={KB_Y + 40} textAnchor="middle"
            fill={accentColor} fontFamily={MONO} fontSize={22} fontWeight="700">
            {Math.round(smoothstep(kbP) * TOTAL_DOCS)} docs indexed
          </text>
        </g>

        {/* ── Document fan — large cards arc across canvas ───────────────── */}
        {Array.from({length: TOTAL_DOCS}, (_, i) => {
          const docProgress = linearProgress(frame, fps,
            b1.start + i * (b1.end - b1.start) / TOTAL_DOCS,
            b1.start + (i + 1) * (b1.end - b1.start) / TOTAL_DOCS + 0.3
          );
          if (docProgress <= 0) return null;

          // Arc from 200° to -20° (top-left to bottom-right, passing top)
          const angle = (200 - (i / (TOTAL_DOCS - 1)) * 220) * (Math.PI / 180);
          const targetX = KB_X + Math.cos(angle) * FAN_RADIUS;
          const targetY = KB_Y + Math.sin(angle) * FAN_RADIUS;
          // Card starts at KB_X/KB_Y and spreads out
          const cx = interpolate(docProgress, [0, 1], [KB_X, targetX]);
          const cy = interpolate(docProgress, [0, 1], [KB_Y, targetY]);
          const cardScale = interpolate(docProgress, [0, 0.6], [0.2, 1]);

          const isSelected = SELECTED.has(i);
          const cardCol = isSelected ? MATCH_COL : DULL_COL;
          const borderOpacity = isSelected ? 0.9 : 0.25;

          // In beat 2: non-selected fade out, selected enlarge and exit right
          const beat2SelectP = isSelected ? selectP : 0;
          const beat2FadeOut = isSelected ? 1 : (1 - smoothstep(selectP));

          // Selected cards grow in b2
          const selScale = 1 + smoothstep(beat2SelectP) * 1.5;
          // Exit: selected cards translate off-screen right
          const exitX = smoothstep(exitP) * 700;

          const CARD_W = 160;
          const CARD_H = 210;

          return (
            <g key={i}
              transform={`translate(${cx + (isSelected ? exitX : 0)}, ${cy})`}
              opacity={smoothstep(docProgress) * beat2FadeOut}>
              <g transform={`scale(${cardScale * selScale})`}>
                {/* Card body */}
                <rect x={-CARD_W / 2} y={-CARD_H / 2}
                  width={CARD_W} height={CARD_H}
                  rx={12}
                  fill={isSelected ? `${MATCH_COL}15` : '#ffffff08'}
                  stroke={cardCol}
                  strokeWidth={isSelected ? 3 : 1.5}
                  opacity={borderOpacity}
                />
                {/* Lines representing text */}
                {[0, 1, 2, 3].map(l => (
                  <rect key={l}
                    x={-CARD_W / 2 + 14} y={-CARD_H / 2 + 30 + l * 30}
                    width={isSelected ? CARD_W - 28 : CARD_W * (0.5 + Math.random() * 0.4) - 14}
                    height={8} rx={4}
                    fill={isSelected ? MATCH_COL : 'rgba(255,255,255,0.2)'}
                    opacity={isSelected ? 0.7 : 0.4}
                  />
                ))}
                {/* Match indicator for selected */}
                {isSelected && (
                  <text x={0} y={CARD_H / 2 - 24} textAnchor="middle"
                    fill={MATCH_COL} fontFamily={FONT} fontSize={22} fontWeight="900">
                    ✓ MATCH
                  </text>
                )}
              </g>
            </g>
          );
        })}

        {/* ── "Retrieving…" label centred below KB during b1 ─────────────── */}
        {fanP > 0.1 && exitP < 0.3 && (
          <text x={KB_X} y={KB_Y + 200} textAnchor="middle"
            fill={accentColor} fontFamily={FONT} fontSize={30} fontWeight="700"
            opacity={smoothstep(fanP) * (1 - smoothstep(selectP))}>
            {onScreenText[1] ?? 'Searching knowledge base…'}
          </text>
        )}

        {/* ── "3 relevant chunks" label (b2) ─────────────────────────────── */}
        {selectP > 0.3 && (
          <text x={KB_X} y={KB_Y + 240} textAnchor="middle"
            fill={accent2} fontFamily={FONT} fontSize={34} fontWeight="800"
            opacity={smoothstep(selectP)}>
            {onScreenText[2] ?? '3 relevant chunks found'}
          </text>
        )}
      </svg>
    </AbsoluteFill>
  );
};
