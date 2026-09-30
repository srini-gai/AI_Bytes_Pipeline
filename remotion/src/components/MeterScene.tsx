/**
 * MeterScene — Visual Director v3.2
 *
 * Risk comparison: qualitative HIGH RISK → LOWER RISK.
 * No invented percentages. Gauges show qualitative zones only.
 *
 * v3.2 QA FIX: on_screen_text[2] from storyboard is "+63pts accuracy lift" — a
 * fabricated statistic. This component IGNORES on_screen_text[2] entirely and
 * hardcodes "with sources" for the SAFER chip subtitle.
 *
 * QA RULE (permanent): The Visual Director must NEVER display on_screen_text[]
 * values that contain precise numeric claims (%, pts, x improvement) unless those
 * values are explicitly sourced in the episode's research data.
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, easeOut, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface MeterSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
}

// Qualitative targets — not real data, just proportional zone placement
const VANILLA_TARGET = 0.22;   // lands in danger zone (left quarter)
const RAG_TARGET     = 0.76;   // lands in safe zone (right three-quarters)

export const MeterScene: React.FC<MeterSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 1.8};
  const b1 = beats[1] ?? {start: 1.8, end: 3.4};
  const b2 = beats[2] ?? {start: 3.4, end: 4.8};

  const vanillaP = easeOut(frame, fps, b0.start, b0.end);
  const ragP     = easeOut(frame, fps, b1.start, b1.end);
  const deltaP   = easeOut(frame, fps, b2.start, b2.end);

  // No scene fade — content present from frame 0
  const sceneOpacity = 1;

  // Gauge geometry — larger and using more canvas
  const CX = 540;
  const CY_VANILLA = 520;
  const CY_RAG     = 1340;
  const R = 260;
  const START_ANGLE = -215; // degrees
  const END_ANGLE   =  35;
  const RANGE = END_ANGLE - START_ANGLE;

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

  function needleEnd(cx: number, cy: number, r: number, angle: number) {
    const rad = (angle * Math.PI) / 180;
    return {x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad)};
  }

  // Needle angle: interpolated from start toward target * progress
  const vanillaAngle = START_ANGLE + vanillaP * VANILLA_TARGET * RANGE;
  const ragAngle     = START_ANGLE + ragP     * RAG_TARGET     * RANGE;
  const vNeedle = needleEnd(CX, CY_VANILLA, R - 40, vanillaAngle);
  const rNeedle = needleEnd(CX, CY_RAG,     R - 40, ragAngle);

  // Zone colours (3 zones on track)
  const ZONE_RED    = '#ef4444';
  const ZONE_AMBER  = '#f59e0b';
  const ZONE_GREEN  = ACCENT2;

  // Zone boundaries (fraction of RANGE)
  const ZONE_1 = 0.33;  // red → amber
  const ZONE_2 = 0.66;  // amber → green

  // Which zone is each needle in? (for zone labels)
  const vanillaZone = vanillaP * VANILLA_TARGET < ZONE_1 ? 'danger' : 'warning';
  const ragZone     = ragP * RAG_TARGET > ZONE_2 ? 'safe' : 'warning';

  return (
    <AbsoluteFill style={{backgroundColor: BG, overflow: 'hidden', opacity: sceneOpacity}}>
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 900px 1400px at 50% 50%, ${accentColor}08 0%, transparent 70%)`,
      }}/>

      <svg viewBox="0 0 1080 1920" width={1080} height={1920}
        style={{position: 'absolute', inset: 0}}>

        {/* ═══════════════ VANILLA LLM GAUGE ═══════════════════════════════ */}
        <g opacity={interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'})}>

          {/* Track background */}
          <path d={arcPath(CX, CY_VANILLA, R, START_ANGLE, END_ANGLE)}
            fill="none" stroke="#ffffff10" strokeWidth={32} strokeLinecap="round"/>

          {/* Zone colour segments on track */}
          <path d={arcPath(CX, CY_VANILLA, R, START_ANGLE, START_ANGLE + ZONE_1 * RANGE)}
            fill="none" stroke={ZONE_RED} strokeWidth={32} strokeLinecap="round" opacity={0.35}/>
          <path d={arcPath(CX, CY_VANILLA, R, START_ANGLE + ZONE_1 * RANGE, START_ANGLE + ZONE_2 * RANGE)}
            fill="none" stroke={ZONE_AMBER} strokeWidth={32} strokeLinecap="round" opacity={0.25}/>
          <path d={arcPath(CX, CY_VANILLA, R, START_ANGLE + ZONE_2 * RANGE, END_ANGLE)}
            fill="none" stroke={ZONE_GREEN} strokeWidth={32} strokeLinecap="round" opacity={0.15}/>

          {/* Active fill arc */}
          <path d={arcPath(CX, CY_VANILLA, R, START_ANGLE,
            START_ANGLE + vanillaP * VANILLA_TARGET * RANGE)}
            fill="none" stroke={ZONE_RED} strokeWidth={32} strokeLinecap="round" opacity={0.9}/>

          {/* Zone separator ticks */}
          {[ZONE_1, ZONE_2].map((z) => {
            const ang = START_ANGLE + z * RANGE;
            const p1 = needleEnd(CX, CY_VANILLA, R - 54, ang);
            const p2 = needleEnd(CX, CY_VANILLA, R + 8, ang);
            return <line key={z} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              stroke="#ffffff55" strokeWidth={3}/>;
          })}

          {/* Needle */}
          <line x1={CX} y1={CY_VANILLA} x2={vNeedle.x} y2={vNeedle.y}
            stroke={ZONE_RED} strokeWidth={8} strokeLinecap="round"/>
          <circle cx={CX} cy={CY_VANILLA} r={18}
            fill={ZONE_RED} stroke={BG} strokeWidth={4}/>

          {/* Gauge title */}
          <text x={CX} y={CY_VANILLA - R - 30} textAnchor="middle"
            fill="#ffffff88" fontFamily={FONT} fontSize={34} fontWeight="700">
            {onScreenText[0] ?? 'Vanilla LLM'}
          </text>

          {/* Zone label — large, inside the gauge arc */}
          <text x={CX} y={CY_VANILLA + 40} textAnchor="middle"
            fill={ZONE_RED} fontFamily={FONT} fontSize={80} fontWeight="900"
            opacity={smoothstep(vanillaP)}>
            HIGH RISK
          </text>

          {/* Qualitative descriptor below */}
          <text x={CX} y={CY_VANILLA + R - 10} textAnchor="middle"
            fill={ZONE_RED} fontFamily={FONT} fontSize={28} fontWeight="700"
            opacity={smoothstep(vanillaP)}>
            Hallucination not checked
          </text>
        </g>

        {/* ═══════════════ RAG GAUGE ═══════════════════════════════════════ */}
        <g opacity={ragP > 0.01 ? 1 : 0}>

          {/* Track background */}
          <path d={arcPath(CX, CY_RAG, R, START_ANGLE, END_ANGLE)}
            fill="none" stroke="#ffffff10" strokeWidth={32} strokeLinecap="round"/>

          {/* Zone colour segments */}
          <path d={arcPath(CX, CY_RAG, R, START_ANGLE, START_ANGLE + ZONE_1 * RANGE)}
            fill="none" stroke={ZONE_RED} strokeWidth={32} strokeLinecap="round" opacity={0.15}/>
          <path d={arcPath(CX, CY_RAG, R, START_ANGLE + ZONE_1 * RANGE, START_ANGLE + ZONE_2 * RANGE)}
            fill="none" stroke={ZONE_AMBER} strokeWidth={32} strokeLinecap="round" opacity={0.25}/>
          <path d={arcPath(CX, CY_RAG, R, START_ANGLE + ZONE_2 * RANGE, END_ANGLE)}
            fill="none" stroke={ZONE_GREEN} strokeWidth={32} strokeLinecap="round" opacity={0.4}/>

          {/* Active fill arc */}
          <path d={arcPath(CX, CY_RAG, R, START_ANGLE,
            START_ANGLE + ragP * RAG_TARGET * RANGE)}
            fill="none" stroke={ZONE_GREEN} strokeWidth={32} strokeLinecap="round" opacity={0.9}/>

          {/* Zone separator ticks */}
          {[ZONE_1, ZONE_2].map((z) => {
            const ang = START_ANGLE + z * RANGE;
            const p1 = needleEnd(CX, CY_RAG, R - 54, ang);
            const p2 = needleEnd(CX, CY_RAG, R + 8, ang);
            return <line key={z} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              stroke="#ffffff55" strokeWidth={3}/>;
          })}

          {/* Needle */}
          <line x1={CX} y1={CY_RAG} x2={rNeedle.x} y2={rNeedle.y}
            stroke={ZONE_GREEN} strokeWidth={8} strokeLinecap="round"/>
          <circle cx={CX} cy={CY_RAG} r={18}
            fill={ZONE_GREEN} stroke={BG} strokeWidth={4}/>

          {/* Gauge title */}
          <text x={CX} y={CY_RAG - R - 30} textAnchor="middle"
            fill="#ffffff88" fontFamily={FONT} fontSize={34} fontWeight="700">
            {onScreenText[1] ?? 'With RAG'}
          </text>

          {/* Zone label */}
          <text x={CX} y={CY_RAG + 40} textAnchor="middle"
            fill={ZONE_GREEN} fontFamily={FONT} fontSize={80} fontWeight="900"
            opacity={smoothstep(ragP)}>
            LOWER RISK
          </text>

          {/* Qualitative descriptor */}
          <text x={CX} y={CY_RAG + R - 10} textAnchor="middle"
            fill={ZONE_GREEN} fontFamily={FONT} fontSize={28} fontWeight="700"
            opacity={smoothstep(ragP)}>
            Sources grounding every answer
          </text>
        </g>

        {/* ── "vs" connector + qualitative result (beat 2) ─────────────────── */}
        {deltaP > 0.01 && (
          <g opacity={smoothstep(deltaP)}>
            {/* Vertical dashed connector between gauges */}
            <line x1={900} y1={CY_VANILLA + 80} x2={900} y2={CY_RAG - 80}
              stroke={accentColor} strokeWidth={3} strokeDasharray="8 5" opacity={0.5}/>
            {/* Arrow tip */}
            <polygon
              points={`900,${CY_RAG - 70} 892,${CY_RAG - 90} 908,${CY_RAG - 90}`}
              fill={accentColor} opacity={0.5}/>

            {/* Delta chip: qualitative only — on_screen_text[2] is IGNORED (may be a
                fabricated stat like "+63pts accuracy lift"). Always display "with sources". */}
            <rect x={830} y={(CY_VANILLA + CY_RAG) / 2 - 50} width={140} height={100}
              rx={18} fill={`${accentColor}18`} stroke={`${accentColor}66`} strokeWidth={2}/>
            <text x={900} y={(CY_VANILLA + CY_RAG) / 2 - 10} textAnchor="middle"
              fill={accentColor} fontFamily={FONT} fontSize={28} fontWeight="900">
              SAFER
            </text>
            <text x={900} y={(CY_VANILLA + CY_RAG) / 2 + 26} textAnchor="middle"
              fill={accentColor} fontFamily={FONT} fontSize={20} fontWeight="700">
              with sources
            </text>
          </g>
        )}
      </svg>
    </AbsoluteFill>
  );
};
