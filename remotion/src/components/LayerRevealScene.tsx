/**
 * LayerRevealScene — Visual Director v3
 *
 * Stacked layers peel back one by one to reveal structure beneath.
 * B0: top layer slides off to the right
 * B1: second layer peels away
 * B2: core layer revealed — label expands
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface LayerRevealSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
}

export const LayerRevealScene: React.FC<LayerRevealSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 1.5};
  const b1 = beats[1] ?? {start: 1.5, end: 3.0};
  const b2 = beats[2] ?? {start: 3.0, end: 5.0};

  const peel0 = easeOut(frame, fps, b0.start, b0.end);
  const peel1 = easeOut(frame, fps, b1.start, b1.end);
  const revealP = easeOut(frame, fps, b2.start, b2.end);

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  const LAYERS = [
    {label: onScreenText[0] ?? 'Interface',  color: accentColor,  y: 500,  w: 820, h: 180},
    {label: onScreenText[1] ?? 'Logic',      color: '#6366f1',    y: 750,  w: 820, h: 180},
    {label: onScreenText[2] ?? 'Data',       color: accent2,      y: 1000, w: 820, h: 180},
  ];

  const peels = [peel0, peel1, 0];

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity, overflow: 'hidden'}}>
      <AbsoluteFill style={{background: `radial-gradient(ellipse 800px 900px at 50% 50%, ${accentColor}0c 0%, transparent 65%)`}}/>

      <svg viewBox="0 0 1080 1920" width={1080} height={1920} style={{position:'absolute',inset:0}}>
        {LAYERS.map((layer, i) => {
          const px = peels[i] * 1200;
          const baseX = (1080 - layer.w) / 2;
          return (
            <g key={i} transform={`translate(${px}, 0)`}>
              <rect x={baseX} y={layer.y} width={layer.w} height={layer.h}
                rx={18} fill={`${layer.color}18`} stroke={`${layer.color}88`} strokeWidth={2.5}/>
              <text x={1080 / 2} y={layer.y + layer.h / 2 + 10} textAnchor="middle"
                fill={layer.color} fontFamily={FONT} fontSize={32} fontWeight="700">
                {layer.label}
              </text>
            </g>
          );
        })}

        {/* Reveal label */}
        {revealP > 0.2 && (
          <text x={540} y={1300} textAnchor="middle"
            fill={accent2} fontFamily={FONT} fontSize={26} fontWeight="700"
            opacity={smoothstep(revealP)}>
            Foundation exposed
          </text>
        )}
      </svg>
    </AbsoluteFill>
  );
};
