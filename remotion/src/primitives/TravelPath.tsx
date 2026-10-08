import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';

interface TravelPathProps {
  activeBeat: SceneBeat;
  path: Array<{x: number; y: number}>;
  showTrail?: boolean;
  trailColor?: string;
  trailStyle?: 'solid' | 'dashed' | 'dotted';
  fps: number;
  children: React.ReactNode;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function positionOnPath(path: Array<{x: number; y: number}>, t: number): {x: number; y: number} {
  if (path.length < 2) return path[0] ?? {x: 0, y: 0};
  const segments = path.length - 1;
  const segIdx = Math.min(Math.floor(t * segments), segments - 1);
  const segT = (t * segments) - segIdx;
  return {
    x: lerp(path[segIdx].x, path[segIdx + 1].x, segT),
    y: lerp(path[segIdx].y, path[segIdx + 1].y, segT),
  };
}

export const TravelPath: React.FC<TravelPathProps> = ({
  activeBeat,
  path,
  showTrail = false,
  trailColor = '#a78bfa44',
  trailStyle = 'dashed',
  fps,
  children,
}) => {
  const frame = useCurrentFrame();
  const startF = Math.round(activeBeat.start * fps);
  const endF = Math.round(activeBeat.end * fps);

  const p = interpolate(frame, [startF, endF], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const ep = 1 - Math.pow(1 - p, 3);

  if (frame < startF) return null;

  const pos = positionOnPath(path, ep);

  return (
    <>
      {showTrail && path.length >= 2 && (
        <svg viewBox="0 0 1080 1920" width={1080} height={1920}
          style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
          <polyline
            points={path.map(pt => `${pt.x},${pt.y}`).join(' ')}
            fill="none"
            stroke={trailColor}
            strokeWidth={2}
            strokeDasharray={trailStyle === 'dashed' ? '8 6' : trailStyle === 'dotted' ? '3 6' : 'none'}
          />
        </svg>
      )}
      <div style={{
        position: 'absolute',
        left: pos.x,
        top: pos.y,
        transform: 'translate(-50%, -50%)',
      }}>
        {children}
      </div>
    </>
  );
};
