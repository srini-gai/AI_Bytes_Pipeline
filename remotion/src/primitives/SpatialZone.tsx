import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';
import type {Bounds} from './types';

interface SpatialZoneProps {
  activeBeat: SceneBeat;
  label?: string;
  bounds: Bounds;
  borderColor?: string;
  fillColor?: string;
  borderStyle?: 'solid' | 'dashed' | 'glow';
  labelPosition?: 'top' | 'inside' | 'bottom';
  artDirection?: ArtDirection;
  fps: number;
}

export const SpatialZone: React.FC<SpatialZoneProps> = ({
  activeBeat,
  label,
  bounds,
  borderColor,
  fillColor,
  borderStyle = 'glow',
  labelPosition = 'top',
  artDirection: ad,
  fps,
}) => {
  const frame = useCurrentFrame();
  const zoneColor = borderColor ?? ad?.palette.danger ?? '#ff3333';
  const bgColor = ad?.palette.bg ?? '#050510';
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.font ?? '-apple-system, sans-serif';

  const startF = Math.round(activeBeat.start * fps);
  const endF = Math.round(activeBeat.end * fps);
  const p = interpolate(frame, [startF, startF + 15], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  if (frame < startF) return null;

  const pulse = 0.5 + 0.5 * Math.sin(frame * 0.12);
  const fill = fillColor ?? `${bgColor}dd`;

  let labelY: number;
  switch (labelPosition) {
    case 'top': labelY = bounds.y - 16; break;
    case 'inside': labelY = bounds.y + 40; break;
    case 'bottom': labelY = bounds.y + bounds.height + 30; break;
  }

  return (
    <svg viewBox="0 0 1080 1920" width={1080} height={1920}
      style={{position: 'absolute', inset: 0, pointerEvents: 'none', opacity: p}}>
      <defs>
        <filter id="zoneGlow">
          <feGaussianBlur stdDeviation="8" result="blur"/>
          <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      <rect
        x={bounds.x} y={bounds.y}
        width={bounds.width} height={bounds.height}
        fill={fill}
        stroke={zoneColor}
        strokeWidth={borderStyle === 'glow' ? 2.5 : 2}
        strokeDasharray={borderStyle === 'dashed' ? '12 8' : 'none'}
        rx={12}
        filter={borderStyle === 'glow' ? 'url(#zoneGlow)' : undefined}
        opacity={0.85 + pulse * 0.15}
      />

      <rect
        x={bounds.x} y={bounds.y}
        width={bounds.width} height={bounds.height}
        fill="none"
        rx={12}
        stroke={`${zoneColor}30`}
        strokeWidth={20}
        opacity={pulse * 0.4}
      />

      {label && (
        <text
          x={bounds.x + bounds.width / 2}
          y={labelY}
          textAnchor="middle"
          fill={zoneColor}
          fontFamily={fontFamily}
          fontSize={28}
          fontWeight={800}
          letterSpacing={4}
          opacity={0.9}
        >
          {label}
        </text>
      )}
    </svg>
  );
};
