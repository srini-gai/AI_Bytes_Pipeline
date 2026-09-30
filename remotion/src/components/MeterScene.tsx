/**
 * MeterScene — Visual Director v3.1 (illustrative mode)
 *
 * Risk comparison: qualitative HIGHER RISK → MORE GROUNDED.
 * No invented percentages. Gauges show qualitative zones only.
 *
 * ILLUSTRATIVE MODE (sourced_numeric rule):
 * - This storyboard scene has no sourced_numeric metadata.
 * - Needle positions are locked to zone CENTERS — not arbitrary fractions
 *   that would visually imply a specific measurement.
 * - VANILLA_ZONE_CENTER = midpoint of red zone (fraction 0..0.33) = 0.165
 * - RAG_ZONE_CENTER     = midpoint of green zone (fraction 0.66..1.0) = 0.83
 * - These communicate "clearly in danger zone" / "clearly in safe zone"
 *   without implying any specific percentage value.
 * - Gauge titles are hardcoded: "WITHOUT RAG" / "WITH RAG" (not from
 *   onScreenText, which may carry storyboard-fabricated labels).
 * - Zone labels: "HIGHER RISK" / "MORE GROUNDED"
 *
 * Layout: two large gauges stacked vertically, each R=260, using full canvas.
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

// ILLUSTRATIVE MODE — zone-center positions, not arbitrary fractions.
// Zone boundaries: red 0..0.33, amber 0.33..0.66, green 0.66..1.0
// Centers: red midpoint = 0.165, green midpoint = 0.83
// Using zone centers (not intermediate values) makes clear these are
// qualitative "clearly in zone" indicators, not precision measurements.
const VANILLA_ZONE_CENTER = 0.165;  // solidly in red/danger zone
const RAG_ZONE_CENTER     = 0.83;   // solidly in green/safe zone

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

  // Needle angle: sweep from arc start to zone-center position
  const vanillaAngle = START_ANGLE + vanillaP * VANILLA_ZONE_CENTER * RANGE;
  const ragAngle     = START_ANGLE + ragP     * RAG_ZONE_CENTER     * RANGE;
  const vNeedle = needleEnd(CX, CY_VANILLA, R - 40, vanillaAngle);
  const rNeedle = needleEnd(CX, CY_RAG,     R - 40, ragAngle);

  // Zone colours (3 zones on track)
  const ZONE_RED    = '#ef4444';
  const ZONE_AMBER  = '#f59e0b';
  const ZONE_GREEN  = ACCENT2;

  // Zone boundaries (fraction of RANGE)
  const ZONE_1 = 0.33;  // red → amber
  const ZONE_2 = 0.66;  // amber → green

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
            START_ANGLE + vanillaP * VANILLA_ZONE_CENTER * RANGE)}
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

          {/* Gauge title — hardcoded qualitative label (illustrative mode:
              storyboard onScreenText may carry fabricated values, ignored here) */}
          <text x={CX} y={CY_VANILLA - R - 30} textAnchor="middle"
            fill="#ffffff88" fontFamily={FONT} fontSize={34} fontWeight="700">
            WITHOUT RAG
          </text>

          {/* Zone label — large, inside the gauge arc */}
          <text x={CX} y={CY_VANILLA + 40} textAnchor="middle"
            fill={ZONE_RED} fontFamily={FONT} fontSize={80} fontWeight="900"
            opacity={smoothstep(vanillaP)}>
            HIGHER RISK
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
            START_ANGLE + ragP * RAG_ZONE_CENTER * RANGE)}
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

          {/* Gauge title — hardcoded qualitative label (illustrative mode) */}
          <text x={CX} y={CY_RAG - R - 30} textAnchor="middle"
            fill="#ffffff88" fontFamily={FONT} fontSize={34} fontWeight="700">
            WITH RAG
          </text>

          {/* Zone label */}
          <text x={CX} y={CY_RAG + 40} textAnchor="middle"
            fill={ZONE_GREEN} fontFamily={FONT} fontSize={80} fontWeight="900"
            opacity={smoothstep(ragP)}>
            MORE GROUNDED
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

            {/* Delta chip: qualitative, never a made-up number */}
            <rect x={830} y={(CY_VANILLA + CY_RAG) / 2 - 50} width={140} height={100}
              rx={18} fill={`${accentColor}18`} stroke={`${accentColor}66`} strokeWidth={2}/>
            <text x={900} y={(CY_VANILLA + CY_RAG) / 2 - 10} textAnchor="middle"
              fill={accentColor} fontFamily={FONT} fontSize={28} fontWeight="900">
              SAFER
            </text>
            <text x={900} y={(CY_VANILLA + CY_RAG) / 2 + 26} textAnchor="middle"
              fill={accentColor} fontFamily={FONT} fontSize={20} fontWeight="700">
              {'with sources'}
            </text>
          </g>
        )}
      </svg>
    </AbsoluteFill>
  );
};
