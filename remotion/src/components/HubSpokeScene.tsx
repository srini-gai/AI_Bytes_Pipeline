import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {HubSpokeSpec} from '../types';

interface SceneTheme { accent: string; accent2: string; }

const DEFAULT_THEME: SceneTheme = {accent: '#22d3ee', accent2: '#818cf8'};
const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

const CX = 540;  // screen center X
const CY = 940;  // hub center Y (slightly above mid to leave caption room)
const HUB_R = 90;
const SPOKE_R = 350;
const NODE_W = 210;
const NODE_H = 68;

interface HubSpokeSceneProps {
  spec: HubSpokeSpec;
  theme?: SceneTheme;
}

export const HubSpokeScene: React.FC<HubSpokeSceneProps> = ({spec, theme}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = theme ?? DEFAULT_THEME;
  const {hub, spokes} = spec;
  const n = spokes.length;

  const HUB_DURATION = 22;
  const SPOKES_START = 28;
  const spokeInterval = Math.floor(160 / n);

  const hubOpacity = interpolate(frame, [0, HUB_DURATION], [0, 1], {extrapolateRight: 'clamp'});
  const hubScale = spring({frame, fps, config: {damping: 12, mass: 0.7, stiffness: 200}, durationInFrames: 20});

  const titleOpacity = interpolate(frame, [0, 18], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: '#050510'}}>
      <AbsoluteFill
        style={{background: `radial-gradient(circle 520px at 50% 49%, ${t.accent}20 0%, transparent 70%)`}}
      />
      <AbsoluteFill
        style={{background: 'linear-gradient(to bottom, transparent 72%, rgba(0,0,0,0.82) 100%)'}}
      />

      {/* Section label */}
      <div
        style={{
          position: 'absolute', top: 136, left: 0, right: 0,
          textAlign: 'center',
          opacity: titleOpacity,
          zIndex: 2,
          fontSize: 24, letterSpacing: 6,
          textTransform: 'uppercase' as const,
          color: t.accent, fontFamily: FONT, fontWeight: 700,
          textShadow: `0 0 20px ${t.accent}88`,
        }}
      >
        Architecture
      </div>

      {/* SVG spoke lines */}
      <svg
        style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%'}}
        viewBox="0 0 1080 1920"
      >
        {spokes.map((_, i) => {
          const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
          const spokeStart = SPOKES_START + i * spokeInterval;
          const lineProgress = interpolate(frame, [spokeStart, spokeStart + 22], [0, 1], {extrapolateRight: 'clamp'});
          const lineEnd = HUB_R + (SPOKE_R - HUB_R - NODE_H / 2) * lineProgress;

          return (
            <line
              key={i}
              x1={CX + Math.cos(angle) * HUB_R}
              y1={CY + Math.sin(angle) * HUB_R}
              x2={CX + Math.cos(angle) * lineEnd}
              y2={CY + Math.sin(angle) * lineEnd}
              stroke={t.accent}
              strokeWidth={1.5}
              opacity={0.55}
            />
          );
        })}
      </svg>

      {/* Hub node */}
      <div
        style={{
          position: 'absolute',
          left: CX - HUB_R,
          top: CY - HUB_R,
          width: HUB_R * 2,
          height: HUB_R * 2,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${t.accent}66 0%, ${t.accent}22 100%)`,
          border: `3px solid ${t.accent}`,
          boxShadow: `0 0 40px ${t.accent}88, 0 0 80px ${t.accent}44`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 4,
          opacity: hubOpacity,
          transform: `scale(${hubScale})`,
        }}
      >
        <div
          style={{
            fontSize: hub.length > 6 ? 22 : 26,
            fontWeight: 800,
            color: '#ffffff',
            fontFamily: FONT,
            textAlign: 'center',
            padding: '0 10px',
            lineHeight: 1.2,
            textShadow: '0 2px 8px rgba(0,0,0,0.8)',
          }}
        >
          {hub}
        </div>
      </div>

      {/* Spoke nodes */}
      {spokes.map((spoke, i) => {
        const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
        const spokeStart = SPOKES_START + i * spokeInterval;
        const nodeStart = spokeStart + 20;
        const nodeOpacity = interpolate(frame, [nodeStart, nodeStart + 16], [0, 1], {extrapolateRight: 'clamp'});
        const nodeScale = spring({
          frame: Math.max(0, frame - nodeStart),
          fps,
          config: {damping: 14, mass: 0.6, stiffness: 240},
          durationInFrames: 16,
        });

        const nx = CX + Math.cos(angle) * SPOKE_R;
        const ny = CY + Math.sin(angle) * SPOKE_R;

        const isActive = frame >= nodeStart + 8;

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: nx - NODE_W / 2,
              top: ny - NODE_H / 2,
              width: NODE_W,
              height: NODE_H,
              borderRadius: NODE_H / 2,
              background: isActive
                ? `linear-gradient(135deg, ${t.accent}44, ${t.accent2}30)`
                : `${t.accent}18`,
              border: `1.5px solid ${isActive ? t.accent : t.accent + '55'}`,
              boxShadow: isActive ? `0 0 18px ${t.accent}55` : 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              opacity: nodeOpacity,
              transform: `scale(${nodeScale})`,
              zIndex: 3,
              transition: 'background 0.3s',
            }}
          >
            <div
              style={{
                fontSize: 27,
                fontWeight: 700,
                color: '#ffffff',
                fontFamily: FONT,
                textAlign: 'center',
                padding: '0 14px',
                textShadow: '0 2px 8px rgba(0,0,0,0.8)',
              }}
            >
              {spoke}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
