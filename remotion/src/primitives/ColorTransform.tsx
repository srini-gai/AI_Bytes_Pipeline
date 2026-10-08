import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';

interface ColorTransformProps {
  activeBeat: SceneBeat;
  fromColor: string;
  toColor: string;
  easing?: 'linear' | 'ease-out' | 'ease-in-out';
  fps: number;
  children: (currentColor: string) => React.ReactNode;
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [
    parseInt(h.substring(0, 2), 16),
    parseInt(h.substring(2, 4), 16),
    parseInt(h.substring(4, 6), 16),
  ];
}

function rgbToHex(r: number, g: number, b: number): string {
  return '#' + [r, g, b].map(c => Math.round(c).toString(16).padStart(2, '0')).join('');
}

function lerpColor(from: string, to: string, t: number): string {
  const [r1, g1, b1] = hexToRgb(from);
  const [r2, g2, b2] = hexToRgb(to);
  return rgbToHex(
    r1 + (r2 - r1) * t,
    g1 + (g2 - g1) * t,
    b1 + (b2 - b1) * t,
  );
}

export const ColorTransform: React.FC<ColorTransformProps> = ({
  activeBeat,
  fromColor,
  toColor,
  easing = 'ease-out',
  fps,
  children,
}) => {
  const frame = useCurrentFrame();

  const startF = Math.round(activeBeat.start * fps);
  const endF = Math.round(activeBeat.end * fps);

  let raw = interpolate(frame, [startF, endF], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  switch (easing) {
    case 'ease-out': raw = 1 - Math.pow(1 - raw, 3); break;
    case 'ease-in-out': raw = raw < 0.5 ? 4 * raw * raw * raw : 1 - Math.pow(-2 * raw + 2, 3) / 2; break;
  }

  const currentColor = frame < startF ? fromColor : lerpColor(fromColor, toColor, raw);
  return <>{children(currentColor)}</>;
};
