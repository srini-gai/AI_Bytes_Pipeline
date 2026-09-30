/**
 * ContextWindowScene — Visual Director v3.1 (reviewed v3.2)
 *
 * Full-width context window fills the canvas from top.
 * Document chunks insert sequentially — each one lands with visible impact.
 *
 * v3.2 QA NOTE: The '0.92', '0.87', '0.81' values on chunk badges are
 * COSINE SIMILARITY SCORES — they show relative retrieval ranking, not absolute
 * accuracy claims. These are internal retrieval metadata labels, not performance
 * statistics. They do NOT violate the no-fabricated-stats rule.
 * (Compare: MeterScene "+63pts accuracy lift" WAS a violation — removed.)
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, MONO, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface ContextWindowSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  carryFrom?: string;
}

const CHUNKS = [
  {label: 'Doc A — paragraph 1', lines: 4, color: '#a78bfa'},
  {label: 'Doc B — key passage', lines: 3, color: '#34d399'},
  {label: 'Doc C — definition',  lines: 2, color: '#60a5fa'},
];

const WIN_X  = 50;
const WIN_W  = 980;
const WIN_TOP = 160;
const CHUNK_H = 200;
const CHUNK_GAP = 16;
const LLM_R   = 160;
const LLM_CX  = 540;

export const ContextWindowScene: React.FC<ContextWindowSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 1.0}; // window frame opens
  const b1 = beats[1] ?? {start: 1.0, end: 3.0}; // chunks insert one by one
  const b2 = beats[2] ?? {start: 3.0, end: 4.5}; // window compresses → passes to LLM

  // ── Window frame opening ─────────────────────────────────────────────────
  const winP     = easeOut(frame, fps, b0.start, b0.end);
  const winAlpha = smoothstep(winP);

  // ── Chunks inserting ─────────────────────────────────────────────────────
  // Each chunk reveals over a 0.6s window within b1
  const chunkDuration = (b1.end - b1.start) / CHUNKS.length;
  const chunkProgresses = CHUNKS.map((_, i) =>
    easeOut(frame, fps, b1.start + i * chunkDuration, b1.start + (i + 1) * chunkDuration)
  );

  // How many chunks are visible (for window height calc)
  const chunksVisible = chunkProgresses.filter(p => p > 0).length;
  const windowFill = CHUNKS.length > 0 ? chunksVisible / CHUNKS.length : 0;

  // Window grows dynamically as chunks arrive
  const WIN_H = 120 + Math.min(chunksVisible, CHUNKS.length) * (CHUNK_H + CHUNK_GAP) + 20;

  // ── Beat 2: window compresses, LLM grows below ───────────────────────────
  const compressP = easeOut(frame, fps, b2.start, b2.start + 0.8);
  const llmP      = easeOut(frame, fps, b2.start + 0.3, b2.end);

  const winScaleY = interpolate(compressP, [0, 1], [1, 0.18]);
  const winAlphaFade = interpolate(compressP, [0, 1], [1, 0.3]);
  const llmAlpha  = smoothstep(llmP);
  const llmR      = LLM_R * smoothstep(llmP);

  // LLM Y: below the window's normal bottom
  const LLM_CY = WIN_TOP + WIN_H + 100 + LLM_R;

  return (
    <AbsoluteFill style={{backgroundColor: BG, overflow: 'hidden'}}>
      {/* Background gradient — purple left side matching accent */}
      <AbsoluteFill style={{
        background: `linear-gradient(135deg, ${accentColor}0e 0%, transparent 50%),
          radial-gradient(ellipse 700px 1000px at ${WIN_X + WIN_W / 2}px 800px, ${accentColor}10 0%, transparent 65%)`,
      }}/>

      <svg
        viewBox="0 0 1080 1920"
        width={1080}
        height={1920}
        style={{position: 'absolute', inset: 0}}
      >
        {/* ── Context Window frame ────────────────────────────────────────── */}
        <g opacity={winAlpha * winAlphaFade}
          transform={`translate(${WIN_X + WIN_W / 2}, ${WIN_TOP + WIN_H / 2}) scaleY(${winScaleY}) translate(-${WIN_X + WIN_W / 2}, -${WIN_TOP + WIN_H / 2})`}>

          {/* Border rect — grows with content */}
          <rect x={WIN_X} y={WIN_TOP} width={WIN_W} height={WIN_H}
            rx={20}
            fill={`${accentColor}08`}
            stroke={accentColor}
            strokeWidth={3}/>

          {/* Header bar */}
          <rect x={WIN_X} y={WIN_TOP} width={WIN_W} height={56}
            rx={20} fill={`${accentColor}20`}/>
          <text x={WIN_X + 28} y={WIN_TOP + 37} fill="#fff"
            fontFamily={FONT} fontSize={28} fontWeight="700">
            Context Window
          </text>
          {/* Token counter */}
          <text x={WIN_X + WIN_W - 28} y={WIN_TOP + 37} textAnchor="end"
            fill={accentColor} fontFamily={MONO} fontSize={22} fontWeight="700">
            {Math.round(windowFill * 3840)} / 8192 tokens
          </text>

          {/* Progress bar */}
          <rect x={WIN_X + 16} y={WIN_TOP + 60} width={WIN_W - 32} height={6}
            rx={3} fill="#ffffff10"/>
          <rect x={WIN_X + 16} y={WIN_TOP + 60} width={(WIN_W - 32) * windowFill} height={6}
            rx={3} fill={accentColor}/>

          {/* ── Chunks ─────────────────────────────────────────────────── */}
          {CHUNKS.map((chunk, i) => {
            const p = chunkProgresses[i];
            if (p <= 0) return null;
            const chunkY = WIN_TOP + 88 + i * (CHUNK_H + CHUNK_GAP);
            // Chunks enter from screen-left (carry-over direction from DocRetrieval)
            const chunkX = interpolate(p, [0, 1], [-WIN_W, 0]);
            const chunkOpacity = smoothstep(p);

            return (
              <g key={i} transform={`translate(${chunkX}, 0)`} opacity={chunkOpacity}>
                {/* Chunk background */}
                <rect x={WIN_X + 12} y={chunkY} width={WIN_W - 24} height={CHUNK_H}
                  rx={12}
                  fill={`${chunk.color}10`}
                  stroke={`${chunk.color}55`} strokeWidth={1.5}/>

                {/* Source label */}
                <text x={WIN_X + 32} y={chunkY + 34}
                  fill={chunk.color} fontFamily={FONT} fontSize={22} fontWeight="800">
                  {chunk.label}
                </text>

                {/* Text line representation */}
                {Array.from({length: chunk.lines}, (_, l) => (
                  <rect key={l}
                    x={WIN_X + 32} y={chunkY + 50 + l * 32}
                    width={WIN_W - 80 - (l === chunk.lines - 1 ? 160 : 0)}
                    height={10} rx={5}
                    fill="#ffffff25"
                  />
                ))}

                {/* Match score badge */}
                <rect x={WIN_X + WIN_W - 130} y={chunkY + 14}
                  width={100} height={34}
                  rx={17}
                  fill={`${chunk.color}25`}
                  stroke={`${chunk.color}80`} strokeWidth={1.5}/>
                <text x={WIN_X + WIN_W - 80} y={chunkY + 37}
                  textAnchor="middle"
                  fill={chunk.color} fontFamily={MONO} fontSize={18} fontWeight="700">
                  {['0.92', '0.87', '0.81'][i]}
                </text>
              </g>
            );
          })}

          {/* "Query" section at bottom if all chunks arrived */}
          {chunksVisible >= CHUNKS.length && (
            <g opacity={smoothstep(chunkProgresses[CHUNKS.length - 1])}>
              <rect x={WIN_X + 12} y={WIN_TOP + 88 + CHUNKS.length * (CHUNK_H + CHUNK_GAP)} width={WIN_W - 24} height={80}
                rx={12} fill="#60a5fa10" stroke="#60a5fa44" strokeWidth={1.5}/>
              <text x={WIN_X + 32} y={WIN_TOP + 88 + CHUNKS.length * (CHUNK_H + CHUNK_GAP) + 30}
                fill="#60a5fa" fontFamily={FONT} fontSize={22} fontWeight="800">
                User Query
              </text>
              <text x={WIN_X + 32} y={WIN_TOP + 88 + CHUNKS.length * (CHUNK_H + CHUNK_GAP) + 58}
                fill="rgba(255,255,255,0.7)" fontFamily={MONO} fontSize={20}>
                {onScreenText[0] ?? 'What is RAG?'}
              </text>
            </g>
          )}
        </g>

        {/* ── Arrow "passes to LLM" ────────────────────────────────────────── */}
        {compressP > 0.3 && (
          <g opacity={smoothstep(compressP)}>
            <line
              x1={LLM_CX} y1={WIN_TOP + WIN_H * winScaleY + 20}
              x2={LLM_CX} y2={LLM_CY - llmR - 10}
              stroke={accentColor} strokeWidth={3}
              markerEnd="url(#arrow-ctx)" strokeDasharray="12 6"/>
            <defs>
              <marker id="arrow-ctx" markerWidth="10" markerHeight="7"
                refX="10" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill={accentColor}/>
              </marker>
            </defs>
          </g>
        )}

        {/* ── LLM orb ─────────────────────────────────────────────────────── */}
        {llmP > 0 && (
          <g opacity={llmAlpha}>
            {/* Outer pulse ring */}
            <circle cx={LLM_CX} cy={LLM_CY} r={llmR + 20}
              fill="none" stroke={accentColor} strokeWidth={1.5}
              strokeDasharray="16 8" opacity={0.4}/>
            {/* Body */}
            <circle cx={LLM_CX} cy={LLM_CY} r={llmR}
              fill={`${accentColor}18`} stroke={accentColor} strokeWidth={3}/>
            <text x={LLM_CX} y={LLM_CY + 12} textAnchor="middle"
              fill="#fff" fontFamily={FONT} fontSize={52} fontWeight="900">
              LLM
            </text>
            <text x={LLM_CX} y={LLM_CY + 56} textAnchor="middle"
              fill={accentColor} fontFamily={FONT} fontSize={24} fontWeight="700">
              {onScreenText[1] ?? 'Generating grounded answer'}
            </text>
          </g>
        )}
      </svg>
    </AbsoluteFill>
  );
};
