/**
 * GraphGrowthScene — Visual Director v3
 *
 * A bar/line chart where bars grow from the x-axis — informational change.
 * B0: axes draw
 * B1: bars grow from baseline (staggered left to right)
 * B2: trend line overlays — peak bar highlights with callout
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface GraphGrowthSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
}

const BAR_VALUES = [0.25, 0.38, 0.52, 0.44, 0.67, 0.79, 0.91];
const BAR_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'];

export const GraphGrowthScene: React.FC<GraphGrowthSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 1.0};
  const b1 = beats[1] ?? {start: 1.0, end: 3.0};
  const b2 = beats[2] ?? {start: 3.0, end: 5.0};

  const axisP  = easeOut(frame, fps, b0.start, b0.end);
  const barP   = linearProgress(frame, fps, b1.start, b1.end);
  const trendP = easeOut(frame, fps, b2.start, b2.end);

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  const CHART_X = 100;
  const CHART_Y = 700;
  const CHART_W = 880;
  const CHART_H = 600;
  const BAR_W   = CHART_W / BAR_VALUES.length * 0.65;
  const BAR_GAP = CHART_W / BAR_VALUES.length;
  const MAX_IDX = BAR_VALUES.indexOf(Math.max(...BAR_VALUES));

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity, overflow: 'hidden'}}>
      <svg viewBox="0 0 1080 1920" width={1080} height={1920} style={{position:'absolute',inset:0}}>

        {/* Axes */}
        <line x1={CHART_X} y1={CHART_Y} x2={CHART_X} y2={CHART_Y + CHART_H * axisP}
          stroke={`${accentColor}88`} strokeWidth={3} strokeLinecap="round"/>
        <line x1={CHART_X} y1={CHART_Y + CHART_H}
              x2={CHART_X + CHART_W * axisP} y2={CHART_Y + CHART_H}
          stroke={`${accentColor}88`} strokeWidth={3} strokeLinecap="round"/>

        {/* Bars */}
        {BAR_VALUES.map((v, i) => {
          const delay = i / BAR_VALUES.length * 0.6;
          const bp = smoothstep(interpolate(barP, [delay, delay + 0.4], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          }));
          const bx   = CHART_X + i * BAR_GAP + (BAR_GAP - BAR_W) / 2;
          const bh   = CHART_H * v * bp;
          const by   = CHART_Y + CHART_H - bh;
          const isMax = i === MAX_IDX;
          const col  = isMax && trendP > 0.3 ? accent2 : accentColor;

          return (
            <g key={i}>
              <rect x={bx} y={by} width={BAR_W} height={bh}
                rx={6} fill={`${col}33`} stroke={col} strokeWidth={1.5}/>
              <text x={bx + BAR_W / 2} y={CHART_Y + CHART_H + 30} textAnchor="middle"
                fill="#ffffff66" fontFamily={FONT} fontSize={18}>
                {BAR_LABELS[i]}
              </text>
              {/* Callout on peak bar */}
              {isMax && trendP > 0.3 && (
                <>
                  <line x1={bx + BAR_W / 2} y1={by - 10} x2={bx + BAR_W / 2} y2={by - 50}
                    stroke={accent2} strokeWidth={2} opacity={smoothstep(trendP)}/>
                  <rect x={bx + BAR_W / 2 - 70} y={by - 95} width={140} height={40}
                    rx={10} fill={`${accent2}22`} stroke={`${accent2}88`} strokeWidth={1.5}
                    opacity={smoothstep(trendP)}/>
                  <text x={bx + BAR_W / 2} y={by - 68} textAnchor="middle"
                    fill={accent2} fontFamily={FONT} fontSize={18} fontWeight="700"
                    opacity={smoothstep(trendP)}>
                    {onScreenText[0] ?? 'Peak'}
                  </text>
                </>
              )}
            </g>
          );
        })}

        {/* Trend line */}
        {trendP > 0.01 && (
          <polyline
            points={BAR_VALUES.map((v, i) => {
              const bx = CHART_X + i * BAR_GAP + BAR_GAP / 2;
              const by = CHART_Y + CHART_H - CHART_H * v;
              return `${bx},${by}`;
            }).slice(0, Math.ceil(trendP * BAR_VALUES.length)).join(' ')}
            fill="none" stroke={accent2} strokeWidth={3} strokeLinecap="round"
            opacity={0.8}
          />
        )}
      </svg>
    </AbsoluteFill>
  );
};
