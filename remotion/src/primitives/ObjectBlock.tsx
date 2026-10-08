import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

interface ObjectBlockProps {
  activeBeat: SceneBeat;
  label: string;
  position: {x: number; y: number};
  width?: number;
  height?: number;
  color?: string;
  blockStyle?: 'solid' | 'outlined' | 'ghosted' | 'crossed-out';
  icon?: string;
  sublabel?: string;
  artDirection?: ArtDirection;
  fps: number;
}

export const ObjectBlock: React.FC<ObjectBlockProps> = ({
  activeBeat,
  label,
  position,
  width = 200,
  height = 120,
  color,
  blockStyle = 'outlined',
  icon,
  sublabel,
  artDirection: ad,
  fps,
}) => {
  const frame = useCurrentFrame();
  const blockColor = color ?? ad?.palette.primary ?? '#a78bfa';
  const textColor = ad?.palette.text ?? '#ffffff';
  const bgColor = ad?.palette.bg ?? '#050510';
  const fontFamily = ad?.typography.font ?? '-apple-system, sans-serif';

  const startF = Math.round(activeBeat.start * fps);
  const p = interpolate(frame, [startF, startF + 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  if (frame < startF) return null;

  const cx = position.x;
  const cy = position.y;

  let fill: string;
  let stroke: string;
  let strokeW: number;
  let textOp = 0.9;

  switch (blockStyle) {
    case 'solid':
      fill = `${blockColor}35`;
      stroke = blockColor;
      strokeW = 3;
      break;
    case 'outlined':
      fill = `${blockColor}18`;
      stroke = `${blockColor}aa`;
      strokeW = 2.5;
      break;
    case 'ghosted':
      fill = `${blockColor}0a`;
      stroke = `${blockColor}55`;
      strokeW = 2;
      textOp = 0.6;
      break;
    case 'crossed-out':
      fill = `${blockColor}12`;
      stroke = `${blockColor}66`;
      strokeW = 2;
      textOp = 0.5;
      break;
  }

  return (
    <svg viewBox="0 0 1080 1920" width={1080} height={1920}
      style={{position: 'absolute', inset: 0, pointerEvents: 'none', opacity: p}}>
      <rect
        x={cx - width / 2} y={cy - height / 2}
        width={width} height={height}
        fill={fill} stroke={stroke} strokeWidth={strokeW}
        rx={12}
      />

      {blockStyle === 'crossed-out' && (
        <>
          <line
            x1={cx - width / 2 + 10} y1={cy - height / 2 + 10}
            x2={cx + width / 2 - 10} y2={cy + height / 2 - 10}
            stroke={ad?.palette.danger ?? '#ff3333'} strokeWidth={3} opacity={0.7}
          />
          <line
            x1={cx + width / 2 - 10} y1={cy - height / 2 + 10}
            x2={cx - width / 2 + 10} y2={cy + height / 2 - 10}
            stroke={ad?.palette.danger ?? '#ff3333'} strokeWidth={3} opacity={0.7}
          />
        </>
      )}

      {icon && (
        <text x={cx} y={cy - 8} textAnchor="middle"
          fill={textColor} fontSize={32} opacity={textOp}>
          {icon}
        </text>
      )}

      <text x={cx} y={cy + (icon ? 24 : 8)} textAnchor="middle"
        fill={blockColor} fontFamily={fontFamily} fontSize={22} fontWeight={700}
        opacity={textOp}>
        {label}
      </text>

      {sublabel && (
        <text x={cx} y={cy + height / 2 + 24} textAnchor="middle"
          fill={`${textColor}66`} fontFamily={fontFamily} fontSize={16} fontWeight={600}>
          {sublabel}
        </text>
      )}
    </svg>
  );
};
