import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {ClusterSpec} from '../types';

interface SceneTheme { accent: string; accent2: string; }

const DEFAULT_THEME: SceneTheme = {accent: '#22d3ee', accent2: '#818cf8'};
const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

// Deterministic pseudo-random in [0, 1) using fractional part of sin hash
function frac(n: number): number {
  const v = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return v - Math.floor(v);
}

function scatterPos(idx: number): {x: number; y: number} {
  return {
    x: 100 + frac(idx * 3)     * 880,
    y: 260 + frac(idx * 3 + 1) * 1280,
  };
}

function groupCenter(groupIdx: number, totalGroups: number): {x: number; y: number} {
  if (totalGroups <= 2) {
    return groupIdx === 0 ? {x: 290, y: 720} : {x: 790, y: 1200};
  }
  const angle = (groupIdx / totalGroups) * 2 * Math.PI - Math.PI / 2;
  return {x: 540 + Math.cos(angle) * 290, y: 900 + Math.sin(angle) * 370};
}

function itemClusterPos(
  itemIdx: number, totalInGroup: number,
  center: {x: number; y: number},
): {x: number; y: number} {
  const angle = (itemIdx / Math.max(totalInGroup, 1)) * 2 * Math.PI;
  const r = totalInGroup <= 3 ? 80 : 110;
  return {
    x: center.x + Math.cos(angle) * r,
    y: center.y + Math.sin(angle) * r,
  };
}

const GROUP_COLORS = ['#22d3ee', '#818cf8', '#f59e0b'];

// Frame constants
const APPEAR_START   = 10;
const APPEAR_GAP     = 5;   // frames between each item appearing
const FLY_START      = 70;
const FLY_END        = 170;
const HALO_START     = 158;
const LABEL_START    = 178;

interface ClusterSceneProps {
  spec: ClusterSpec;
  theme?: SceneTheme;
}

export const ClusterScene: React.FC<ClusterSceneProps> = ({spec, theme}) => {
  const frame = useCurrentFrame();
  const t = theme ?? DEFAULT_THEME;
  const {groups} = spec;

  const allItems = groups.flatMap((group, gi) =>
    group.items.map((text, ii) => ({text, groupIndex: gi, itemIndex: ii, totalInGroup: group.items.length}))
  );
  const totalGroups = groups.length;

  // Smoothstep for flying animation
  const rawFly = interpolate(frame, [FLY_START, FLY_END], [0, 1], {extrapolateRight: 'clamp'});
  const flyT = rawFly * rawFly * (3 - 2 * rawFly);

  const titleOpacity = interpolate(frame, [0, 18], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: '#050510'}}>
      <AbsoluteFill
        style={{background: `radial-gradient(ellipse 900px 900px at 50% 55%, ${t.accent}14 0%, transparent 65%)`}}
      />
      <AbsoluteFill
        style={{background: 'linear-gradient(to bottom, transparent 72%, rgba(0,0,0,0.82) 100%)'}}
      />

      {/* Section label */}
      <div
        style={{
          position: 'absolute', top: 136, left: 0, right: 0,
          textAlign: 'center', opacity: titleOpacity, zIndex: 2,
          fontSize: 24, letterSpacing: 6,
          textTransform: 'uppercase' as const,
          color: t.accent, fontFamily: FONT, fontWeight: 700,
          textShadow: `0 0 20px ${t.accent}88`,
        }}
      >
        Embeddings
      </div>

      {/* Group halo circles */}
      {groups.map((_, gi) => {
        const center = groupCenter(gi, totalGroups);
        const totalInGroup = groups[gi].items.length;
        const haloR = totalInGroup <= 3 ? 160 : 200;
        const color = GROUP_COLORS[gi % GROUP_COLORS.length] ?? t.accent;
        const haloOpacity = interpolate(frame, [HALO_START + gi * 10, HALO_START + gi * 10 + 20], [0, 0.35], {extrapolateRight: 'clamp'});

        return (
          <div
            key={gi}
            style={{
              position: 'absolute',
              left: center.x - haloR,
              top: center.y - haloR,
              width: haloR * 2,
              height: haloR * 2,
              borderRadius: '50%',
              border: `2px solid ${color}55`,
              background: `radial-gradient(circle, ${color}18 0%, transparent 70%)`,
              opacity: haloOpacity,
              zIndex: 1,
            }}
          />
        );
      })}

      {/* Group labels */}
      {groups.map((group, gi) => {
        const center = groupCenter(gi, totalGroups);
        const color = GROUP_COLORS[gi % GROUP_COLORS.length] ?? t.accent;
        const labelOpacity = interpolate(frame, [LABEL_START + gi * 12, LABEL_START + gi * 12 + 18], [0, 1], {extrapolateRight: 'clamp'});

        return (
          <div
            key={gi}
            style={{
              position: 'absolute',
              left: center.x - 160,
              top: center.y - 250,
              width: 320,
              textAlign: 'center',
              opacity: labelOpacity,
              zIndex: 5,
              fontSize: 30,
              fontWeight: 800,
              color,
              fontFamily: FONT,
              letterSpacing: 1,
              textTransform: 'uppercase' as const,
              textShadow: `0 0 20px ${color}88`,
            }}
          >
            {group.label}
          </div>
        );
      })}

      {/* Word items */}
      {allItems.map((item, globalIdx) => {
        const scatter = scatterPos(globalIdx);
        const center  = groupCenter(item.groupIndex, totalGroups);
        const cluster  = itemClusterPos(item.itemIndex, item.totalInGroup, center);
        const color    = GROUP_COLORS[item.groupIndex % GROUP_COLORS.length] ?? t.accent;

        const appearFrame = APPEAR_START + globalIdx * APPEAR_GAP;
        const itemOpacity = interpolate(frame, [appearFrame, appearFrame + 14], [0, 1], {extrapolateRight: 'clamp'});

        const cx = scatter.x + (cluster.x - scatter.x) * flyT;
        const cy = scatter.y + (cluster.y - scatter.y) * flyT;

        // Chip shrinks slightly during flight
        const chipScale = interpolate(frame, [FLY_START, FLY_END], [1, 0.85], {extrapolateRight: 'clamp'});

        return (
          <div
            key={globalIdx}
            style={{
              position: 'absolute',
              left: cx,
              top: cy,
              transform: `translate(-50%, -50%) scale(${chipScale})`,
              opacity: itemOpacity,
              zIndex: 3,
            }}
          >
            <div
              style={{
                backgroundColor: `${color}28`,
                border: `1.5px solid ${color}77`,
                borderRadius: 40,
                padding: '10px 22px',
                fontSize: 34,
                fontWeight: 700,
                color: '#ffffff',
                fontFamily: FONT,
                whiteSpace: 'nowrap' as const,
                textShadow: '0 2px 10px rgba(0,0,0,0.8)',
                boxShadow: `0 0 14px ${color}44`,
              }}
            >
              {item.text}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
