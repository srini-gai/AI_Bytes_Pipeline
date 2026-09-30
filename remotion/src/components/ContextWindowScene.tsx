/**
 * ContextWindowScene — Visual Director v3
 *
 * Documents slide into a context window rectangle, which then
 * compresses and attaches to an LLM node.
 *
 * B0: context window rectangle appears; document cards slide in from left
 * B1: rectangle rim illuminates as docs slot in — "context" label pops
 * B2: window compresses vertically (tokens packing down)
 * B3: compressed window flies right and docks to LLM circle
 *
 * Carry-in: document cards (from DocumentRetrievalScene staging area)
 * Carry-out: context window rectangle (for TokenStreamScene)
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
  carryFrom?: string; // 'document cards'
}

const DOC_COUNT = 3;

export const ContextWindowScene: React.FC<ContextWindowSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 1.5};
  const b1 = beats[1] ?? {start: 1.5, end: 2.8};
  const b2 = beats[2] ?? {start: 2.8, end: 4.0};
  const b3 = beats[3] ?? {start: 4.0, end: 5.0};

  // ── Beat 0: window rect + docs slide in ─────────────────────────────────
  const windowP = easeOut(frame, fps, b0.start, b0.end);
  const docSlideP = easeOut(frame, fps, b0.start + 0.2, b0.end);

  // ── Beat 1: rim glow, label pop ─────────────────────────────────────────
  const rimP  = linearProgress(frame, fps, b1.start, b1.end);
  const labelP = easeOut(frame, fps, b1.start + 0.2, b1.end);

  // ── Beat 2: window compresses ────────────────────────────────────────────
  const compressP = easeOut(frame, fps, b2.start, b2.end);

  // ── Beat 3: compressed window flies to LLM ───────────────────────────────
  const flyP = easeOut(frame, fps, b3.start, b3.end);

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  // Window geometry
  const WIN_X    = 540;  // centre x
  const WIN_Y    = 820;  // centre y
  const WIN_W    = 460;
  const WIN_H_FULL    = 480;
  const WIN_H_COMPACT = 180; // compressed height
  const LLM_X   = 940;  // LLM circle x (right side)
  const LLM_Y   = WIN_Y;

  const winH = interpolate(compressP, [0, 1], [WIN_H_FULL, WIN_H_COMPACT]);
  const winX = interpolate(flyP,      [0, 1], [WIN_X, LLM_X]);
  const winOpacity = interpolate(flyP, [0.85, 1], [1, 0]);

  // rim glow color intensity
  const rimAlpha = Math.round(smoothstep(rimP) * 0xcc).toString(16).padStart(2, '0');

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        opacity: sceneOpacity,
        overflow: 'hidden',
      }}
    >
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 800px 600px at 50% 43%, ${accentColor}0d 0%, transparent 65%)`,
        }}
      />

      <svg viewBox="0 0 1080 1920" width={1080} height={1920}
        style={{position: 'absolute', inset: 0}}>

        {/* ── Carry-in doc cards from left (beat 0) ─────────────────────── */}
        {Array.from({length: DOC_COUNT}, (_, i) => {
          const stagger = i * 0.15;
          const p = smoothstep(interpolate(docSlideP, [stagger, stagger + 0.6], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          }));
          const srcX  = WIN_X - WIN_W / 2 - 280 + i * 10;
          const dstX  = WIN_X - WIN_W / 2 + 30 + i * 12;
          const cardY = WIN_Y - 120 + i * 100;
          const cx = interpolate(p, [0, 1], [srcX, dstX]);

          return (
            <g key={i} opacity={interpolate(compressP, [0.4, 0.9], [1, 0.2], {extrapolateRight: 'clamp'})}>
              <rect x={cx - 55} y={cardY - 48} width={110} height={96}
                rx={8}
                fill={`${accent2}15`} stroke={`${accent2}77`} strokeWidth={1.5}/>
              {[0, 1, 2].map((l) => (
                <rect key={l} x={cx - 38} y={cardY - 28 + l * 26} width={76} height={8}
                  rx={4} fill={accent2} opacity={0.35 + smoothstep(rimP) * 0.25}/>
              ))}
              {/* rank badge */}
              <circle cx={cx + 44} cy={cardY - 38} r={14}
                fill={accent2} opacity={p}/>
              <text x={cx + 44} y={cardY - 33} textAnchor="middle"
                fill="#050510" fontFamily={FONT} fontSize={13} fontWeight="900">
                {i + 1}
              </text>
            </g>
          );
        })}

        {/* ── Context window rectangle ─────────────────────────────────── */}
        <g transform={`translate(${winX}, ${WIN_Y})`} opacity={winOpacity}>
          {/* main rect */}
          <rect
            x={-WIN_W / 2} y={-winH / 2} width={WIN_W} height={winH}
            rx={16}
            fill={`${accentColor}08`}
            stroke={`${accentColor}${rimAlpha}`}
            strokeWidth={3}
            opacity={windowP}
          />

          {/* Token rows inside window (visible after beat 0) */}
          {windowP > 0.5 && Array.from({length: 6}, (_, r) => {
            const rowY = -winH / 2 + 28 + r * (winH / 7);
            const rowOpacity = smoothstep(interpolate(rimP, [r * 0.12, r * 0.12 + 0.35], [0, 1], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
            }));
            return (
              <g key={r} opacity={rowOpacity * windowP}>
                <rect x={-WIN_W / 2 + 20} y={rowY} width={(WIN_W - 40) * (0.5 + (r % 3) * 0.18)} height={10}
                  rx={5} fill={accentColor} opacity={0.22}/>
              </g>
            );
          })}

          {/* "Context window" label (beat 1) */}
          <text x={0} y={-winH / 2 - 20}
            textAnchor="middle"
            fill={accentColor} fontFamily={FONT} fontSize={22} fontWeight="700"
            opacity={smoothstep(labelP)}>
            {onScreenText[0] ?? 'Context window'}
          </text>

          {/* Token count badge (beat 2) */}
          {compressP > 0.1 && (
            <g opacity={smoothstep(compressP)}>
              <rect x={-60} y={winH / 2 - 40} width={120} height={36}
                rx={18} fill={`${accentColor}22`} stroke={`${accentColor}88`} strokeWidth={1.5}/>
              <text x={0} y={winH / 2 - 18} textAnchor="middle"
                fill={accentColor} fontFamily={MONO} fontSize={17} fontWeight="700">
                {onScreenText[1] ?? '~1500 tokens'}
              </text>
            </g>
          )}
        </g>

        {/* ── LLM circle (target, appears on beat 3) ────────────────────── */}
        {frame >= Math.round(b3.start * fps) && (
          <g>
            <circle cx={LLM_X} cy={LLM_Y} r={90}
              fill={`${accentColor}12`} stroke={accentColor} strokeWidth={2.5}
              opacity={interpolate(flyP, [0, 0.3], [0, 1])}/>
            <text x={LLM_X} y={LLM_Y + 8} textAnchor="middle"
              fill="#fff" fontFamily={FONT} fontSize={22} fontWeight="700"
              opacity={interpolate(flyP, [0, 0.3], [0, 1])}>
              LLM
            </text>
            {/* Connection glow on arrival */}
            <circle cx={LLM_X} cy={LLM_Y} r={100}
              fill="none" stroke={accentColor} strokeWidth={4}
              opacity={interpolate(flyP, [0.7, 1], [0, 0.5])}/>
          </g>
        )}
      </svg>
    </AbsoluteFill>
  );
};
