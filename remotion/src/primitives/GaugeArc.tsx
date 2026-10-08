import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

interface GaugeZone {
  start: number;
  end: number;
  color: string;
  label?: string;
}

interface GaugeArcProps {
  activeBeat: SceneBeat;
  center: {x: number; y: number};
  radius?: number;
  targetValue: number;
  fillColor?: string;
  zones?: GaugeZone[];
  title?: string;
  valueLabel?: string;
  pulse?: boolean;
  artDirection?: ArtDirection;
  fps: number;
}

function arcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number): string {
  const s = (startDeg * Math.PI) / 180;
  const e = (endDeg * Math.PI) / 180;
  const x1 = cx + r * Math.cos(s);
  const y1 = cy + r * Math.sin(s);
  const x2 = cx + r * Math.cos(e);
  const y2 = cy + r * Math.sin(e);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

export const GaugeArc: React.FC<GaugeArcProps> = ({
  activeBeat,
  center,
  radius = 260,
  targetValue,
  fillColor,
  zones = [],
  title,
  valueLabel,
  pulse = false,
  artDirection: ad,
  fps,
}) => {
  const frame = useCurrentFrame();
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.font ?? '-apple-system, sans-serif';
  const gaugeColor = fillColor ?? ad?.palette.danger ?? '#ff3333';

  const startF = Math.round(activeBeat.start * fps);
  const endF = Math.round(activeBeat.end * fps);

  const fillP = interpolate(frame, [startF, endF], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const easedP = 1 - Math.pow(1 - fillP, 3);
  const currentVal = easedP * targetValue;

  const START_ANGLE = -215;
  const END_ANGLE = 35;
  const RANGE = END_ANGLE - START_ANGLE;

  const cx = center.x;
  const cy = center.y;

  const needleAngle = START_ANGLE + currentVal * RANGE;
  const needleRad = (needleAngle * Math.PI) / 180;
  const nLen = radius - 40;
  const nx = cx + nLen * Math.cos(needleRad);
  const ny = cy + nLen * Math.sin(needleRad);

  const pulseOp = pulse && fillP >= 1 ? (0.7 + 0.3 * Math.sin(frame * 0.15)) : 1;

  return (
    <svg viewBox="0 0 1080 1920" width={1080} height={1920}
      style={{position: 'absolute', inset: 0}}>

      <path d={arcPath(cx, cy, radius, START_ANGLE, END_ANGLE)}
        fill="none" stroke="#ffffff10" strokeWidth={32} strokeLinecap="round"/>

      {zones.map((z, i) => (
        <path key={i}
          d={arcPath(cx, cy, radius, START_ANGLE + z.start * RANGE, START_ANGLE + z.end * RANGE)}
          fill="none" stroke={z.color} strokeWidth={32} strokeLinecap="round"
          opacity={0.3}
        />
      ))}

      <path
        d={arcPath(cx, cy, radius, START_ANGLE, START_ANGLE + currentVal * RANGE)}
        fill="none" stroke={gaugeColor} strokeWidth={32} strokeLinecap="round"
        opacity={0.9}
      />

      <line x1={cx} y1={cy} x2={nx} y2={ny}
        stroke={gaugeColor} strokeWidth={8} strokeLinecap="round" opacity={pulseOp}/>
      <circle cx={cx} cy={cy} r={18}
        fill={gaugeColor} stroke="#050510" strokeWidth={4}/>

      {title && (
        <text x={cx} y={cy - radius - 30} textAnchor="middle"
          fill={`${textColor}88`} fontFamily={fontFamily} fontSize={34} fontWeight={700}>
          {title}
        </text>
      )}

      {valueLabel && fillP > 0.5 && (
        <text x={cx} y={cy + 40} textAnchor="middle"
          fill={gaugeColor} fontFamily={fontFamily} fontSize={72} fontWeight={900}
          opacity={Math.min(1, (fillP - 0.5) * 4)}>
          {valueLabel}
        </text>
      )}

      {zones.map((z, i) => z.label && (
        <text key={`lbl-${i}`}
          x={cx} y={cy + radius - 10} textAnchor="middle"
          fill={z.color} fontFamily={fontFamily} fontSize={24} fontWeight={700}
          opacity={currentVal >= z.start ? Math.min(1, (currentVal - z.start) * 4) : 0}>
          {z.label}
        </text>
      ))}
    </svg>
  );
};
