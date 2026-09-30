/**
 * DataFlowScene — Visual Director v3
 *
 * Data packets moving through a system diagram.
 * Beat-driven: query bubble emits → travels → enters node → node searches → beams radiate.
 *
 * Scene continuity: carries a "query bubble" object across to the next scene.
 * The bubble stays visible at the right edge of the canvas on beat 3 end.
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, MONO, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface DataFlowSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  carryFrom?: string;
}

export const DataFlowScene: React.FC<DataFlowSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Canvas layout (1080 wide × 1920 tall — we work in a 1080×600 zone centred at 40%)
  const CY = 760; // centre Y of action area

  // User icon — left side
  const USER_X = 120;

  // Retrieval node — centre
  const NODE_X = 540;
  const NODE_R = 90;

  // Knowledge base cylinder — right
  const KB_X = 900;

  // ── Beat 0: query bubble emits from user, floats right (0–1.5s) ──────────
  const b0 = beats[0] ?? {start: 0, end: 1.5};
  const bubbleP   = easeOut(frame, fps, b0.start, b0.end);
  // Bubble travels user → retrieval node entrance
  const bubbleX   = interpolate(bubbleP, [0, 1], [USER_X + 70, NODE_X - NODE_R - 10]);
  const bubbleY   = interpolate(bubbleP, [0, 0.5, 1], [CY - 20, CY - 60, CY - 20]); // arc
  const bubbleAlpha = interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'});

  // ── Beat 1: bubble enters node, node glows (1.5–3.0s) ───────────────────
  const b1 = beats[1] ?? {start: 1.5, end: 3.0};
  const nodeEnterP = easeOut(frame, fps, b1.start, b1.end);
  const nodePulse  = linearProgress(frame, fps, b1.start, b1.end);
  // Bubble moves from edge of node into its centre and fades into it
  const bubbleInNodeX = interpolate(nodeEnterP, [0, 1], [NODE_X - NODE_R - 10, NODE_X]);
  const bubbleInNodeAlpha = interpolate(nodeEnterP, [0.5, 1], [1, 0]);
  // Node glow intensity
  const nodeGlow = smoothstep(nodePulse) * 0.9 + 0.1;
  // Node ring pulse
  const nodeRingScale = 1 + smoothstep(nodePulse) * 0.3;
  const nodeRingAlpha = interpolate(nodePulse, [0, 0.3, 1], [0, 0.6, 0]);

  // ── Beat 2: search beams radiate toward KB, cylinder fills (3.0–5.0s) ───
  const b2 = beats[2] ?? {start: 3.0, end: 5.0};
  const beamP     = linearProgress(frame, fps, b2.start, b2.end);
  const beamSmooth = smoothstep(beamP);
  // KB fill segments (3 rows)
  const kbSegCount = 3;

  // pan/camera: on beat 2 the "camera" zooms out — we scale down slightly to reveal system
  const camScale = interpolate(
    linearProgress(frame, fps, b2.start, b2.end),
    [0, 1],
    [1, 0.92],
  );

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  // Determine which beat we're on for bubble position
  const afterBeat1 = frame >= Math.round(b1.start * fps);
  const bX = afterBeat1 ? bubbleInNodeX : bubbleX;
  const bY = afterBeat1 ? CY : bubbleY;
  const bAlpha = afterBeat1 ? bubbleInNodeAlpha : bubbleAlpha;
  const bVisible = bAlpha > 0.05 && !(nodeEnterP > 0.99);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        opacity: sceneOpacity,
        overflow: 'hidden',
      }}
    >
      {/* Background */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 1000px 600px at 50% 42%, ${accentColor}0c 0%, transparent 65%)`,
        }}
      />

      {/* ── Scene SVG canvas ────────────────────────────────────────────── */}
      <svg
        viewBox={`0 0 1080 1920`}
        width={1080}
        height={1920}
        style={{
          position: 'absolute',
          inset: 0,
          transform: `scale(${camScale})`,
          transformOrigin: '50% 40%',
        }}
      >
        {/* ── User icon ─────────────────────────────────────────────────── */}
        <g opacity={interpolate(frame, [0, 10], [0, 1], {extrapolateRight: 'clamp'})}>
          <circle cx={USER_X} cy={CY - 10} r={48} fill={`${accentColor}18`} stroke={accentColor} strokeWidth={2}/>
          {/* person silhouette */}
          <circle cx={USER_X} cy={CY - 22} r={16} fill={accentColor} opacity={0.9}/>
          <path d={`M${USER_X - 28} ${CY + 20} Q${USER_X} ${CY - 8} ${USER_X + 28} ${CY + 20}`}
            fill="none" stroke={accentColor} strokeWidth={3} strokeLinecap="round"/>
          {/* "Your question" label */}
          <text x={USER_X} y={CY + 80} textAnchor="middle" fill={accentColor}
            fontFamily={FONT} fontSize={22} fontWeight="700">
            {onScreenText[0] ?? 'Your question'}
          </text>
        </g>

        {/* ── Query bubble ─────────────────────────────────────────────── */}
        {bVisible && (
          <g opacity={bAlpha}>
            <ellipse cx={bX} cy={bY} rx={54} ry={36}
              fill={`${accentColor}22`} stroke={accentColor} strokeWidth={2}/>
            <text x={bX} y={bY + 8} textAnchor="middle"
              fill="#fff" fontFamily={MONO} fontSize={18} fontWeight="700">
              query
            </text>
          </g>
        )}

        {/* ── Retrieval node ────────────────────────────────────────────── */}
        {/* Pulse ring */}
        <circle
          cx={NODE_X} cy={CY} r={NODE_R * nodeRingScale}
          fill="none" stroke={accentColor}
          strokeWidth={3} opacity={nodeRingAlpha}
        />
        {/* Node body */}
        <circle
          cx={NODE_X} cy={CY} r={NODE_R}
          fill={`${accentColor}${Math.round(nodeGlow * 28).toString(16).padStart(2, '0')}`}
          stroke={accentColor}
          strokeWidth={afterBeat1 ? 3 : 1.5}
        />
        {/* Magnifying glass inside node */}
        <g transform={`translate(${NODE_X - 22}, ${CY - 22})`} opacity={0.9}>
          <circle cx={18} cy={18} r={14} fill="none" stroke="#fff" strokeWidth={3}/>
          <line x1={28} y1={28} x2={38} y2={38} stroke="#fff" strokeWidth={3} strokeLinecap="round"/>
        </g>
        <text x={NODE_X} y={CY + 130} textAnchor="middle"
          fill={accentColor} fontFamily={FONT} fontSize={22} fontWeight="700">
          {onScreenText[1] ?? 'Retrieval engine'}
        </text>

        {/* ── Search beams (beat 2) ─────────────────────────────────────── */}
        {[0, 1, 2].map((i) => {
          const beamDelay = i * 0.15;
          const segP = smoothstep(interpolate(beamP, [beamDelay, 0.6 + beamDelay], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          }));
          const bEndX = NODE_X + NODE_R + (KB_X - 180 - NODE_X - NODE_R) * segP;
          const yOff = (i - 1) * 40;
          return (
            <line
              key={i}
              x1={NODE_X + NODE_R} y1={CY + yOff}
              x2={bEndX} y2={CY + yOff}
              stroke={accentColor}
              strokeWidth={2.5}
              strokeDasharray="8 6"
              opacity={beamP > 0.05 ? 0.75 : 0}
            />
          );
        })}

        {/* ── Knowledge base cylinder ─────────────────────────────────── */}
        <g opacity={interpolate(frame, [0, 12], [0, 1], {extrapolateRight: 'clamp'})}>
          {/* Cylinder body (simplified as rect + ellipses) */}
          <rect x={KB_X - 70} y={CY - 100} width={140} height={200}
            rx={8} fill={`${accent2}12`} stroke={`${accent2}44`} strokeWidth={1.5}/>
          <ellipse cx={KB_X} cy={CY - 100} rx={70} ry={22}
            fill={`${accent2}22`} stroke={`${accent2}88`} strokeWidth={2}/>
          <ellipse cx={KB_X} cy={CY + 100} rx={70} ry={22}
            fill={`${accent2}18`} stroke={`${accent2}66`} strokeWidth={2}/>

          {/* Fill segments that light up as beams arrive */}
          {Array.from({length: kbSegCount}).map((_, i) => {
            const segFill = smoothstep(interpolate(beamSmooth, [i / kbSegCount, (i + 1) / kbSegCount], [0, 1], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
            }));
            const sy = CY - 90 + i * 66;
            return (
              <rect
                key={i}
                x={KB_X - 60} y={sy} width={120} height={60}
                rx={4}
                fill={accent2}
                opacity={0.08 + segFill * 0.35}
              />
            );
          })}

          <text x={KB_X} y={CY + 150} textAnchor="middle"
            fill={accent2} fontFamily={FONT} fontSize={22} fontWeight="700">
            Knowledge base
          </text>
        </g>
      </svg>
    </AbsoluteFill>
  );
};
