import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

interface StampOverlayProps {
  activeBeat: SceneBeat;
  text: string;
  color?: string;
  angle?: number;
  target: {x: number; y: number};
  width?: number;
  height?: number;
  impact?: 'slam' | 'fade' | 'grow';
  fontSize?: number;
  artDirection?: ArtDirection;
  durationInFrames: number;
  fps: number;
}

export const StampOverlay: React.FC<StampOverlayProps> = ({
  activeBeat,
  text,
  color,
  angle = -12,
  target,
  width = 400,
  height = 120,
  impact = 'slam',
  fontSize = 48,
  artDirection: ad,
  durationInFrames,
  fps,
}) => {
  const frame = useCurrentFrame();
  const stampColor = color ?? ad?.palette.danger ?? '#ff3333';
  const fontFamily = ad?.typography.font ?? '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

  const startF = Math.round(activeBeat.start * fps);
  const endF = Math.round(activeBeat.end * fps);
  const elapsed = frame - startF;

  if (frame < startF) return null;

  let opacity = 1;
  let scale = 1;
  let extraTy = 0;

  switch (impact) {
    case 'slam': {
      const slamP = spring({
        fps,
        frame: Math.max(0, elapsed),
        config: {damping: 8, stiffness: 200, mass: 0.4},
        durationInFrames: 15,
      });
      scale = 0.3 + slamP * 0.7;
      opacity = Math.min(1, elapsed / 3);
      break;
    }
    case 'fade': {
      opacity = interpolate(elapsed, [0, 10], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
      break;
    }
    case 'grow': {
      const growP = interpolate(elapsed, [0, 12], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
      scale = growP;
      opacity = growP;
      break;
    }
  }

  return (
    <div style={{
      position: 'absolute',
      left: target.x - width / 2,
      top: target.y - height / 2,
      width,
      height,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transform: `rotate(${angle}deg) scale(${scale})`,
      opacity,
      pointerEvents: 'none',
      zIndex: 100,
    }}>
      <div style={{
        border: `4px solid ${stampColor}`,
        borderRadius: 8,
        padding: '8px 24px',
        color: stampColor,
        fontFamily,
        fontSize,
        fontWeight: 900,
        letterSpacing: 6,
        textTransform: 'uppercase',
        textAlign: 'center',
        whiteSpace: 'nowrap',
        textShadow: `0 0 20px ${stampColor}44`,
      }}>
        {text}
      </div>
    </div>
  );
};
