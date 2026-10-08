import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';

interface CameraTransformProps {
  activeBeat: SceneBeat;
  operation: 'zoom-in' | 'zoom-out' | 'pan-left' | 'pan-right' | 'pan-follow' | 'push-in' | 'static';
  fromScale?: number;
  toScale?: number;
  panX?: number;
  panY?: number;
  fps: number;
  children: React.ReactNode;
}

export const CameraTransform: React.FC<CameraTransformProps> = ({
  activeBeat,
  operation,
  fromScale = 1,
  toScale = 1,
  panX = 0,
  panY = 0,
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

  let scale = 1;
  let tx = 0;
  let ty = 0;

  switch (operation) {
    case 'zoom-in': scale = fromScale + (toScale - fromScale) * ep; break;
    case 'zoom-out': scale = fromScale + (toScale - fromScale) * ep; break;
    case 'push-in': scale = fromScale + (toScale - fromScale) * ep; break;
    case 'pan-left': tx = -panX * ep; break;
    case 'pan-right': tx = panX * ep; break;
    case 'pan-follow': tx = panX * ep; ty = panY * ep; break;
    case 'static': break;
  }

  return (
    <AbsoluteFill style={{
      transform: `scale(${scale}) translate(${tx}px, ${ty}px)`,
      transformOrigin: '50% 50%',
    }}>
      {children}
    </AbsoluteFill>
  );
};
