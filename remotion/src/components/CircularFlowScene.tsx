/**
 * CircularFlowScene — Visual Director v4
 *
 * A four-quadrant spinning wheel showing a cyclical process:
 * PLAN → ACT → OBSERVE → ADJUST (or any four-step loop).
 *
 * Beat structure:
 *   B0: Wheel fades in, all four quadrants visible but dim
 *   B1: Wheel begins rotating, first quadrant highlights with detail icon
 *   B2: Second quadrant highlights — zoom-into-detail available
 *   B3: Third quadrant highlights
 *   B4: Fourth quadrant highlights, full cycle glow, continuous rotation
 *
 * Props:
 *   - beats: timed visual events
 *   - onScreenText: quadrant labels [q1, q2, q3, q4] (e.g. PLAN, ACT, OBSERVE, ADJUST)
 *   - objects: detail icons per quadrant [icon1, icon2, icon3, icon4]
 *   - data.center_label?: string — text in the center hub
 *   - data.detail_labels?: string[] — sub-labels shown when quadrant is active
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, easeOut, linearProgress} from './beatUtils';
import type {SceneBeat} from '../types';

interface CircularFlowSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  data?: {
    center_label?: string;
    detail_labels?: string[];
  };
}

// ─── Layout constants ────────────────────────────────────────────────────────

const CANVAS_W = 1080;
const CANVAS_H = 1920;
const CENTER_X = CANVAS_W / 2;
const CENTER_Y = CANVAS_H / 2 - 40; // slightly above center for mobile
const WHEEL_R = 300;
const HUB_R = 70;
const QUADRANT_ICON_R = 180; // radius for icon placement
const LABEL_R = 250; // radius for label placement

// Quadrant angles (starting from top, clockwise)
const QUADRANT_ANGLES = [
  -Math.PI / 2,          // top (PLAN)
  0,                     // right (ACT)
  Math.PI / 2,           // bottom (OBSERVE)
  Math.PI,               // left (ADJUST)
];

// Quadrant colors
const Q_COLORS = ['#a78bfa', '#818cf8', '#34d399', '#fbbf24'];

// ─── Component ───────────────────────────────────────────────────────────────

export const CircularFlowScene: React.FC<CircularFlowSceneProps> = ({
  beats,
  onScreenText,
  objects,
  accentColor = ACCENT,
  accent2 = ACCENT2,
  data,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Labels
  const labels = [
    onScreenText[0] ?? 'PLAN',
    onScreenText[1] ?? 'ACT',
    onScreenText[2] ?? 'OBSERVE',
    onScreenText[3] ?? 'ADJUST',
  ];

  // Icons
  const icons = [
    objects[0] ?? '💭',
    objects[1] ?? '🔧',
    objects[2] ?? '🔍',
    objects[3] ?? '🔄',
  ];

  const centerLabel = data?.center_label ?? 'LOOP';
  const detailLabels = data?.detail_labels ?? [];

  // Beat progress
  const b = beats.map((beat) => ({
    progress: easeOut(frame, fps, beat.start, beat.end),
    linear: linearProgress(frame, fps, beat.start, beat.end),
    started: frame >= Math.round(beat.start * fps),
    ended: frame >= Math.round(beat.end * fps),
  }));

  while (b.length < 5) {
    b.push({progress: 0, linear: 0, started: false, ended: false});
  }

  // Active quadrant index (-1 = none)
  const activeQuadrant = b[4].started ? 3
    : b[3].started ? 2
    : b[2].started ? 1
    : b[1].started ? 0 : -1;

  // Rotation: starts at B1, continuous
  const rotationStartBeat = beats[1] ?? {start: 1, end: 2};
  const rotationProgress = linearProgress(
    frame, fps, rotationStartBeat.start,
    (beats[beats.length - 1]?.end ?? 6)
  );
  const rotation = rotationProgress * 360 * 0.4; // ~0.4 full rotations over scene duration

  // Scene entrance
  const sceneOpacity = interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'});

  // Full cycle glow (beat 4)
  const cycleGlow = b[4].progress;

  return (
    <AbsoluteFill style={{backgroundColor: BG, fontFamily: FONT}}>
      <svg
        viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
        style={{width: '100%', height: '100%', opacity: sceneOpacity}}
      >
        {/* ── Title text ── */}
        <text
          x={CENTER_X}
          y={CENTER_Y - WHEEL_R - 80}
          textAnchor="middle"
          fontSize={26}
          fontWeight={700}
          fill="rgba(255,255,255,0.8)"
          opacity={b[0].progress}
        >
          {onScreenText[4] ?? ''}
        </text>

        {/* ── Rotating group ── */}
        <g transform={`translate(${CENTER_X}, ${CENTER_Y}) rotate(${rotation})`}>

          {/* Outer ring */}
          <circle
            cx={0} cy={0} r={WHEEL_R}
            fill="none"
            stroke={cycleGlow > 0 ? accent2 : 'rgba(255,255,255,0.08)'}
            strokeWidth={cycleGlow > 0 ? 3 : 2}
            opacity={b[0].progress * (cycleGlow > 0 ? 0.6 + 0.4 * cycleGlow : 0.5)}
          />

          {/* Inner ring */}
          <circle
            cx={0} cy={0} r={WHEEL_R * 0.6}
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth={1}
            opacity={b[0].progress}
          />

          {/* ── Quadrant sectors ── */}
          {[0, 1, 2, 3].map((i) => {
            const startAngle = QUADRANT_ANGLES[i] - Math.PI / 4;
            const endAngle = QUADRANT_ANGLES[i] + Math.PI / 4;
            const isActive = i === activeQuadrant;
            const isComplete = i < activeQuadrant || (b[4].ended);
            const qColor = Q_COLORS[i];

            // Sector path (arc segment)
            const innerR = HUB_R + 10;
            const outerR = WHEEL_R - 10;
            const x1o = outerR * Math.cos(startAngle);
            const y1o = outerR * Math.sin(startAngle);
            const x2o = outerR * Math.cos(endAngle);
            const y2o = outerR * Math.sin(endAngle);
            const x1i = innerR * Math.cos(endAngle);
            const y1i = innerR * Math.sin(endAngle);
            const x2i = innerR * Math.cos(startAngle);
            const y2i = innerR * Math.sin(startAngle);

            const sectorPath = [
              `M ${x1o} ${y1o}`,
              `A ${outerR} ${outerR} 0 0 1 ${x2o} ${y2o}`,
              `L ${x1i} ${y1i}`,
              `A ${innerR} ${innerR} 0 0 0 ${x2i} ${y2i}`,
              'Z',
            ].join(' ');

            const fillOpacity = isActive ? 0.25 : isComplete ? 0.15 : 0.05;

            // Icon position
            const iconAngle = QUADRANT_ANGLES[i];
            const iconX = QUADRANT_ICON_R * Math.cos(iconAngle);
            const iconY = QUADRANT_ICON_R * Math.sin(iconAngle);

            // Label position (further out)
            const labelX = LABEL_R * Math.cos(iconAngle);
            const labelY = LABEL_R * Math.sin(iconAngle);

            // Counter-rotate text so it stays upright
            const counterRotation = -rotation;

            return (
              <g key={`q-${i}`} opacity={b[0].progress}>
                {/* Sector fill */}
                <path
                  d={sectorPath}
                  fill={qColor}
                  opacity={fillOpacity}
                  stroke={isActive ? qColor : 'rgba(255,255,255,0.06)'}
                  strokeWidth={isActive ? 2 : 0.5}
                />

                {/* Active pulse ring */}
                {isActive && (
                  <circle
                    cx={iconX}
                    cy={iconY}
                    r={35 + 5 * Math.sin(b[activeQuadrant + 1]?.linear * Math.PI * 4)}
                    fill="none"
                    stroke={qColor}
                    strokeWidth={2}
                    opacity={0.4}
                  />
                )}

                {/* Icon */}
                <g transform={`translate(${iconX}, ${iconY}) rotate(${counterRotation})`}>
                  <text
                    x={0} y={0}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={isActive ? 36 : 28}
                    opacity={isActive || isComplete ? 1 : 0.4}
                  >
                    {icons[i]}
                  </text>
                </g>

                {/* Label */}
                <g transform={`translate(${labelX}, ${labelY}) rotate(${counterRotation})`}>
                  <text
                    x={0} y={-18}
                    textAnchor="middle"
                    fontSize={isActive ? 17 : 14}
                    fontWeight={700}
                    letterSpacing={1.5}
                    fill={isActive ? '#fff' : 'rgba(255,255,255,0.5)'}
                  >
                    {labels[i]}
                  </text>

                  {/* Detail label when active */}
                  {isActive && detailLabels[i] && (
                    <text
                      x={0} y={4}
                      textAnchor="middle"
                      fontSize={12}
                      fill="rgba(255,255,255,0.6)"
                      opacity={b[activeQuadrant + 1]?.progress ?? 0}
                    >
                      {detailLabels[i]}
                    </text>
                  )}
                </g>

                {/* Flow arrow between quadrants */}
                {(() => {
                  const nextAngle = QUADRANT_ANGLES[(i + 1) % 4];
                  const midAngle = (iconAngle + nextAngle) / 2
                    + (i === 3 ? Math.PI : 0); // wrap for last→first
                  const arrowR = QUADRANT_ICON_R;
                  const ax = arrowR * Math.cos(midAngle);
                  const ay = arrowR * Math.sin(midAngle);
                  return (
                    <g
                      transform={`translate(${ax}, ${ay}) rotate(${counterRotation})`}
                      opacity={isComplete || isActive ? 0.8 : 0.2}
                    >
                      <text
                        textAnchor="middle"
                        dominantBaseline="central"
                        fontSize={18}
                        fill={isActive ? qColor : 'rgba(255,255,255,0.3)'}
                      >
                        →
                      </text>
                    </g>
                  );
                })()}
              </g>
            );
          })}

          {/* ── Center hub ── */}
          <circle
            cx={0} cy={0} r={HUB_R}
            fill="rgba(255,255,255,0.06)"
            stroke={cycleGlow > 0 ? accent2 : 'rgba(255,255,255,0.12)'}
            strokeWidth={cycleGlow > 0 ? 2 : 1}
          />
          <g transform={`rotate(${-rotation})`}>
            <text
              x={0} y={0}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={16}
              fontWeight={700}
              letterSpacing={2}
              fill={cycleGlow > 0 ? accent2 : 'rgba(255,255,255,0.6)'}
            >
              {centerLabel}
            </text>
          </g>
        </g>

        {/* ── Cycle count indicator (below wheel) ── */}
        {b[4].started && (
          <g opacity={b[4].progress}>
            <text
              x={CENTER_X}
              y={CENTER_Y + WHEEL_R + 60}
              textAnchor="middle"
              fontSize={18}
              fill={accent2}
              fontWeight={600}
            >
              {onScreenText[5] ?? 'Continuous improvement loop'}
            </text>
          </g>
        )}
      </svg>
    </AbsoluteFill>
  );
};
