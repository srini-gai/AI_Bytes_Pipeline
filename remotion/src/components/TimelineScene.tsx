/**
 * TimelineScene — Visual Director v3
 *
 * Horizontal timeline where events appear and scroll into view.
 * B0: spine draws left-to-right
 * B1: event nodes pop onto timeline (staggered)
 * B2: current-moment indicator highlights — future fades
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface TimelineSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
}

export const TimelineScene: React.FC<TimelineSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 1.5};
  const b1 = beats[1] ?? {start: 1.5, end: 3.5};
  const b2 = beats[2] ?? {start: 3.5, end: 5.5};

  const spineP  = easeOut(frame, fps, b0.start, b0.end);
  const eventP  = linearProgress(frame, fps, b1.start, b1.end);
  const momentP = easeOut(frame, fps, b2.start, b2.end);

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  // Events from onScreenText or defaults
  const eventLabels = onScreenText.length >= 4 ? onScreenText : [
    '2020', '2021', '2022', 'Now', '2024',
  ];

  const NOW_IDX  = 3;
  const EVENTS_X = [120, 300, 490, 680, 870];
  const SPINE_Y  = 960;

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity, overflow: 'hidden'}}>
      <svg viewBox="0 0 1080 1920" width={1080} height={1920} style={{position:'absolute',inset:0}}>

        {/* Spine */}
        <line x1={80} y1={SPINE_Y} x2={80 + spineP * 920} y2={SPINE_Y}
          stroke={`${accentColor}66`} strokeWidth={3}/>

        {/* Events */}
        {EVENTS_X.map((ex, i) => {
          const np = smoothstep(interpolate(eventP, [i / EVENTS_X.length * 0.6, i / EVENTS_X.length * 0.6 + 0.4], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          }));
          if (np < 0.01) return null;
          const isNow   = i === NOW_IDX;
          const isFuture = i > NOW_IDX;
          const col = isNow ? accent2 : isFuture ? `${accentColor}44` : accentColor;
          const futureAlpha = isFuture ? (1 - smoothstep(momentP)) * 0.6 + 0.15 : 1;

          return (
            <g key={i} opacity={np * futureAlpha}>
              {/* Dot */}
              <circle cx={ex} cy={SPINE_Y} r={isNow ? 20 * (1 + momentP * 0.3) : 14}
                fill={isNow ? accent2 : `${col}22`} stroke={col} strokeWidth={2.5}/>
              {/* Label */}
              <text x={ex} y={SPINE_Y - 40} textAnchor="middle"
                fill={col} fontFamily={FONT} fontSize={isNow ? 22 : 18} fontWeight={isNow ? 900 : 700}>
                {eventLabels[i] ?? `E${i}`}
              </text>
              {/* Tick below */}
              <line x1={ex} y1={SPINE_Y + 14} x2={ex} y2={SPINE_Y + 50}
                stroke={col} strokeWidth={2} opacity={0.5}/>
            </g>
          );
        })}

        {/* "Now" glow pulse */}
        {momentP > 0.01 && (
          <circle cx={EVENTS_X[NOW_IDX]} cy={SPINE_Y} r={30 + momentP * 30}
            fill="none" stroke={accent2} strokeWidth={2}
            opacity={(1 - momentP) * 0.5}/>
        )}
      </svg>
    </AbsoluteFill>
  );
};
