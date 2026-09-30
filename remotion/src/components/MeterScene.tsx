/**
 * MeterScene — Visual Director v3
 *
 * Animated gauge/meter comparing two approaches:
 * Vanilla LLM vs RAG — scores fill in on separate gauge tracks.
 *
 * B0: "Vanilla LLM" gauge needle swings left (low score) — danger zone
 * B1: "With RAG" gauge needle swings right (high score) — success zone
 * B2: delta label appears + arrow highlights the gap
 *
 * No carry-in / no carry-out — standalone comparison scene.
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface MeterSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
}

export const MeterScene: React.FC<MeterSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 1.5};
  const b1 = beats[1] ?? {start: 1.5, end: 3.0};
  const b2 = beats[2] ?? {start: 3.0, end: 4.5};

  const vanillaP = easeOut(frame, fps, b0.start, b0.end);
  const ragP     = easeOut(frame, fps, b1.start, b1.end);
  const deltaP   = easeOut(frame, fps, b2.start, b2.end);

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  // Gauge arc params
  const CX = 540;
  const CY_VANILLA = 620;
  const CY_RAG     = 1200;
  const R = 220;
  const START_ANGLE = -210; // degrees (left of bottom)
  const END_ANGLE   =  30;  // degrees (right of bottom)
  const RANGE = END_ANGLE - START_ANGLE;

  // Scores
  const VANILLA_SCORE = 0.28;
  const RAG_SCORE     = 0.91;

  function arcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number): string {
    const s = (startDeg * Math.PI) / 180;
    const e = (endDeg   * Math.PI) / 180;
    const x1 = cx + r * Math.cos(s);
    const y1 = cy + r * Math.sin(s);
    const x2 = cx + r * Math.cos(e);
    const y2 = cy + r * Math.sin(e);
    const large = endDeg - startDeg > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
  }

  function needleAngle(score: number): number {
    return START_ANGLE + score * RANGE;
  }

  function needleEnd(cx: number, cy: number, r: number, angle: number) {
    const rad = (angle * Math.PI) / 180;
    return {x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad)};
  }

  const vanillaAngle = START_ANGLE + vanillaP * VANILLA_SCORE * RANGE;
  const ragAngle     = START_ANGLE + ragP     * RAG_SCORE     * RANGE;

  const vanillaNeedle = needleEnd(CX, CY_VANILLA, R - 30, vanillaAngle);
  const ragNeedle     = needleEnd(CX, CY_RAG,     R - 30, ragAngle);

  // Color zones on the track
  function zoneColor(score: number): string {
    if (score < 0.35) return '#ef4444';
    if (score < 0.65) return '#f59e0b';
    return accent2;
  }

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
          background: `radial-gradient(ellipse 900px 1200px at 50% 50%, ${accentColor}08 0%, transparent 70%)`,
        }}
      />

      <svg viewBox="0 0 1080 1920" width={1080} height={1920}
        style={{position: 'absolute', inset: 0}}>

        {/* ════════ VANILLA LLM GAUGE ═══════════════════════════════════ */}
        <g opacity={interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'})}>
          {/* track bg */}
          <path d={arcPath(CX, CY_VANILLA, R, START_ANGLE, END_ANGLE)}
            fill="none" stroke="#ffffff14" strokeWidth={28} strokeLinecap="round"/>

          {/* fill arc — animates from start to vanilla score */}
          <path d={arcPath(CX, CY_VANILLA, R, START_ANGLE,
            START_ANGLE + vanillaP * VANILLA_SCORE * RANGE)}
            fill="none" stroke="#ef4444" strokeWidth={28} strokeLinecap="round"
            opacity={0.9}/>

          {/* zone markers */}
          {[0, 0.35, 0.65, 1].map((t) => {
            const ang = START_ANGLE + t * RANGE;
            const p1 = needleEnd(CX, CY_VANILLA, R - 45, ang);
            const p2 = needleEnd(CX, CY_VANILLA, R + 5, ang);
            return (
              <line key={t} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                stroke="#ffffff44" strokeWidth={2}/>
            );
          })}

          {/* Needle */}
          <line x1={CX} y1={CY_VANILLA}
            x2={vanillaNeedle.x} y2={vanillaNeedle.y}
            stroke="#ef4444" strokeWidth={6} strokeLinecap="round"/>
          <circle cx={CX} cy={CY_VANILLA} r={14}
            fill="#ef4444" stroke="#050510" strokeWidth={3}/>

          {/* Score percentage */}
          <text x={CX} y={CY_VANILLA - 20} textAnchor="middle"
            fill="#ef4444" fontFamily={FONT} fontSize={48} fontWeight="900">
            {Math.round(vanillaP * VANILLA_SCORE * 100)}%
          </text>

          {/* Label */}
          <text x={CX} y={CY_VANILLA + R - 20} textAnchor="middle"
            fill="#ffffff88" fontFamily={FONT} fontSize={26} fontWeight="700">
            {onScreenText[0] ?? 'Vanilla LLM'}
          </text>
          <text x={CX} y={CY_VANILLA + R + 20} textAnchor="middle"
            fill="#ef4444" fontFamily={FONT} fontSize={20} fontWeight="700">
            Hallucination risk
          </text>
        </g>

        {/* ════════ RAG GAUGE ═══════════════════════════════════════════ */}
        <g opacity={ragP > 0.01 ? 1 : 0}>
          {/* track bg */}
          <path d={arcPath(CX, CY_RAG, R, START_ANGLE, END_ANGLE)}
            fill="none" stroke="#ffffff14" strokeWidth={28} strokeLinecap="round"/>

          {/* fill arc animates from start to RAG score */}
          <path d={arcPath(CX, CY_RAG, R, START_ANGLE,
            START_ANGLE + ragP * RAG_SCORE * RANGE)}
            fill="none" stroke={accent2} strokeWidth={28} strokeLinecap="round"
            opacity={0.9}/>

          {/* zone markers */}
          {[0, 0.35, 0.65, 1].map((t) => {
            const ang = START_ANGLE + t * RANGE;
            const p1 = needleEnd(CX, CY_RAG, R - 45, ang);
            const p2 = needleEnd(CX, CY_RAG, R + 5, ang);
            return (
              <line key={t} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                stroke="#ffffff44" strokeWidth={2}/>
            );
          })}

          {/* Needle */}
          <line x1={CX} y1={CY_RAG}
            x2={ragNeedle.x} y2={ragNeedle.y}
            stroke={accent2} strokeWidth={6} strokeLinecap="round"/>
          <circle cx={CX} cy={CY_RAG} r={14}
            fill={accent2} stroke="#050510" strokeWidth={3}/>

          {/* Score percentage */}
          <text x={CX} y={CY_RAG - 20} textAnchor="middle"
            fill={accent2} fontFamily={FONT} fontSize={48} fontWeight="900">
            {Math.round(ragP * RAG_SCORE * 100)}%
          </text>

          {/* Label */}
          <text x={CX} y={CY_RAG + R - 20} textAnchor="middle"
            fill="#ffffff88" fontFamily={FONT} fontSize={26} fontWeight="700">
            {onScreenText[1] ?? 'With RAG'}
          </text>
          <text x={CX} y={CY_RAG + R + 20} textAnchor="middle"
            fill={accent2} fontFamily={FONT} fontSize={20} fontWeight="700">
            Grounded answers
          </text>
        </g>

        {/* ── Delta arrow and label (beat 2) ─────────────────────────── */}
        {deltaP > 0.01 && (
          <g opacity={smoothstep(deltaP)}>
            {/* vertical arrow between gauges */}
            <line x1={920} y1={CY_VANILLA + 60} x2={920} y2={CY_RAG - 60}
              stroke={accentColor} strokeWidth={3} strokeDasharray="6 4"
              markerEnd="url(#arrowhead)"/>
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7"
                refX="10" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill={accentColor}/>
              </marker>
            </defs>
            {/* Delta label */}
            <rect x={860} y={CY_VANILLA + (CY_RAG - CY_VANILLA) / 2 - 35} width={160} height={70}
              rx={14} fill={`${accentColor}18`} stroke={`${accentColor}55`} strokeWidth={2}/>
            <text x={940} y={CY_VANILLA + (CY_RAG - CY_VANILLA) / 2 - 5} textAnchor="middle"
              fill={accentColor} fontFamily={FONT} fontSize={20} fontWeight="900">
              +{Math.round((RAG_SCORE - VANILLA_SCORE) * 100)}pts
            </text>
            <text x={940} y={CY_VANILLA + (CY_RAG - CY_VANILLA) / 2 + 22} textAnchor="middle"
              fill={accentColor} fontFamily={FONT} fontSize={16} fontWeight="700">
              {onScreenText[2] ?? 'accuracy lift'}
            </text>
          </g>
        )}
      </svg>
    </AbsoluteFill>
  );
};
