import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

interface ConnectArrowProps {
  activeBeat: SceneBeat;
  from: {x: number; y: number};
  to: {x: number; y: number};
  color?: string;
  strokeWidth?: number;
  arrowHead?: boolean;
  style?: 'solid' | 'dashed' | 'animated';
  label?: string;
  artDirection?: ArtDirection;
  fps: number;
}

export const ConnectArrow: React.FC<ConnectArrowProps> = ({
  activeBeat,
  from,
  to,
  color,
  strokeWidth = 3,
  arrowHead = true,
  style = 'animated',
  label,
  artDirection: ad,
  fps,
}) => {
  const frame = useCurrentFrame();
  const lineColor = color ?? ad?.palette.primary ?? '#a78bfa';
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.font ?? '-apple-system, sans-serif';

  const startF = Math.round(activeBeat.start * fps);
  const endF = Math.round(activeBeat.end * fps);
  const p = interpolate(frame, [startF, endF], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const ep = 1 - Math.pow(1 - p, 3);

  if (frame < startF) return null;

  const cx = from.x + (to.x - from.x) * ep;
  const cy = from.y + (to.y - from.y) * ep;

  const midX = (from.x + to.x) / 2;
  const midY = (from.y + to.y) / 2;

  const angle = Math.atan2(to.y - from.y, to.x - from.x);
  const headLen = 16;

  return (
    <svg viewBox="0 0 1080 1920" width={1080} height={1920}
      style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
      <line
        x1={from.x} y1={from.y} x2={cx} y2={cy}
        stroke={lineColor} strokeWidth={strokeWidth}
        strokeDasharray={style === 'dashed' ? '8 6' : style === 'animated' ? '12 4' : 'none'}
        opacity={0.9}
      />
      {arrowHead && ep > 0.3 && (
        <polygon
          points={`${cx},${cy} ${cx - headLen * Math.cos(angle - 0.4)},${cy - headLen * Math.sin(angle - 0.4)} ${cx - headLen * Math.cos(angle + 0.4)},${cy - headLen * Math.sin(angle + 0.4)}`}
          fill={lineColor}
          opacity={Math.min(1, (ep - 0.3) * 3)}
        />
      )}
      {label && ep > 0.4 && (
        <text
          x={midX} y={midY - 14}
          textAnchor="middle"
          fill={textColor}
          fontFamily={fontFamily}
          fontSize={20}
          fontWeight={700}
          opacity={Math.min(1, (ep - 0.4) * 3)}
        >
          {label}
        </text>
      )}
    </svg>
  );
};
