import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

interface LaneConfig {
  label?: string;
  color?: string;
}

interface DualLaneLayoutProps {
  activeBeat: SceneBeat;
  topLane: LaneConfig;
  bottomLane: LaneConfig;
  dividerColor?: string;
  dividerStyle?: 'solid' | 'dashed' | 'none';
  artDirection?: ArtDirection;
  fps: number;
  topChildren?: React.ReactNode;
  bottomChildren?: React.ReactNode;
}

export const DualLaneLayout: React.FC<DualLaneLayoutProps> = ({
  activeBeat,
  topLane,
  bottomLane,
  dividerColor,
  dividerStyle = 'dashed',
  artDirection: ad,
  fps,
  topChildren,
  bottomChildren,
}) => {
  const frame = useCurrentFrame();
  const textColor = ad?.palette.text ?? '#ffffff';
  const mutedColor = ad?.palette.muted ?? '#888888';
  const fontFamily = ad?.typography.font ?? '-apple-system, sans-serif';
  const divColor = dividerColor ?? ad?.palette.border ?? '#ffffff22';

  const startF = Math.round(activeBeat.start * fps);
  const p = interpolate(frame, [startF, startF + 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  if (frame < startF) return null;

  const DIVIDER_Y = 960;
  const TOP_ZONE = {top: 100, bottom: DIVIDER_Y - 40};
  const BOTTOM_ZONE = {top: DIVIDER_Y + 40, bottom: 1820};

  return (
    <AbsoluteFill style={{opacity: p}}>
      {dividerStyle !== 'none' && (
        <svg viewBox="0 0 1080 1920" width={1080} height={1920}
          style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
          <line
            x1={60} y1={DIVIDER_Y} x2={1020} y2={DIVIDER_Y}
            stroke={divColor}
            strokeWidth={1.5}
            strokeDasharray={dividerStyle === 'dashed' ? '10 8' : 'none'}
            opacity={0.7}
          />
        </svg>
      )}

      {topLane.label && (
        <div style={{
          position: 'absolute',
          left: 60,
          top: TOP_ZONE.top,
          color: topLane.color ?? mutedColor,
          fontFamily,
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: 4,
          opacity: 0.85,
        }}>
          {topLane.label}
        </div>
      )}

      {/* Lane background tint for visual presence */}
      <div style={{
        position: 'absolute',
        left: 40, top: TOP_ZONE.top + 30,
        width: 1000, height: TOP_ZONE.bottom - TOP_ZONE.top - 30,
        background: `${topLane.color ?? mutedColor}08`,
        borderRadius: 16,
        border: `1px solid ${topLane.color ?? mutedColor}15`,
      }} />
      <div style={{
        position: 'absolute',
        left: 40, top: BOTTOM_ZONE.top,
        width: 1000, height: BOTTOM_ZONE.bottom - BOTTOM_ZONE.top,
        background: `${bottomLane.color ?? mutedColor}08`,
        borderRadius: 16,
        border: `1px solid ${bottomLane.color ?? mutedColor}15`,
      }} />

      <div style={{
        position: 'absolute',
        left: 0,
        top: TOP_ZONE.top + 40,
        width: 1080,
        height: TOP_ZONE.bottom - TOP_ZONE.top - 40,
        overflow: 'hidden',
      }}>
        {topChildren}
      </div>

      {bottomLane.label && (
        <div style={{
          position: 'absolute',
          left: 60,
          top: BOTTOM_ZONE.top - 30,
          color: bottomLane.color ?? mutedColor,
          fontFamily,
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: 4,
          opacity: 0.85,
        }}>
          {bottomLane.label}
        </div>
      )}

      <div style={{
        position: 'absolute',
        left: 0,
        top: BOTTOM_ZONE.top + 10,
        width: 1080,
        height: BOTTOM_ZONE.bottom - BOTTOM_ZONE.top - 10,
        overflow: 'hidden',
      }}>
        {bottomChildren}
      </div>
    </AbsoluteFill>
  );
};
