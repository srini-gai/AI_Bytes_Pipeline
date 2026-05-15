import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {SplitCompareSpec, SideBySideSpec} from '../types';

interface SceneTheme { accent: string; accent2: string; }

const DEFAULT_THEME: SceneTheme = {accent: '#a78bfa', accent2: '#34d399'};
const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

const COL_W = 466;
const COL_GAP = 60;
const COL_PADDING = 28;
const LEFT_X = 40;
const RIGHT_X = LEFT_X + COL_W + COL_GAP;

// Frame timing
const LEFT_SLIDE_IN  = [8,  40];
const LEFT_ICON      = [36, 52];
const LEFT_PTS_START = 50;
const RIGHT_SLIDE_IN = [80, 112];
const RIGHT_ICON     = [108, 124];
const RIGHT_PTS_START = 122;
const VERDICT_IN     = [180, 210];

interface SplitCompareSceneProps {
  spec: SplitCompareSpec | SideBySideSpec;
  theme?: SceneTheme;
}

const Panel: React.FC<{
  panel: {label: string; points: string[]};
  slideFrom: 'left' | 'right';
  slideFrames: [number, number];
  iconFrame: [number, number];
  ptsStart: number;
  icon: string;
  color: string;
  frame: number;
}> = ({panel, slideFrom, slideFrames, iconFrame, ptsStart, icon, color, frame}) => {
  const dir = slideFrom === 'left' ? -120 : 120;
  const slideX = interpolate(frame, slideFrames, [dir, 0], {extrapolateRight: 'clamp'});
  const slideOpacity = interpolate(frame, slideFrames, [0, 1], {extrapolateRight: 'clamp'});
  const iconOpacity = interpolate(frame, iconFrame, [0, 1], {extrapolateRight: 'clamp'});
  const iconScale = interpolate(frame, iconFrame, [0.4, 1], {extrapolateRight: 'clamp'});

  return (
    <div
      style={{
        position: 'absolute',
        top: 260,
        left: slideFrom === 'left' ? LEFT_X : RIGHT_X,
        width: COL_W,
        opacity: slideOpacity,
        transform: `translateX(${slideX}px)`,
        zIndex: 2,
      }}
    >
      {/* Column background */}
      <div
        style={{
          position: 'absolute', inset: 0,
          borderRadius: 24,
          background: `${color}12`,
          border: `1.5px solid ${color}44`,
          boxShadow: `0 0 40px ${color}22`,
        }}
      />

      {/* Content */}
      <div style={{position: 'relative', padding: `${COL_PADDING + 20}px ${COL_PADDING}px ${COL_PADDING}px`}}>
        {/* Result icon */}
        <div
          style={{
            fontSize: 60,
            textAlign: 'center',
            marginBottom: 16,
            opacity: iconOpacity,
            transform: `scale(${iconScale})`,
          }}
        >
          {icon}
        </div>

        {/* Panel label */}
        <div
          style={{
            fontSize: 34, fontWeight: 800, color, fontFamily: FONT,
            textAlign: 'center', marginBottom: 24,
            textShadow: `0 0 16px ${color}66`,
            letterSpacing: -0.3,
          }}
        >
          {panel.label}
        </div>

        {/* Divider */}
        <div
          style={{
            height: 1.5, background: `${color}44`, borderRadius: 1, marginBottom: 20,
          }}
        />

        {/* Points */}
        {panel.points.map((pt, pi) => {
          const ptStart = ptsStart + pi * 18;
          const ptOpacity = interpolate(frame, [ptStart, ptStart + 16], [0, 1], {extrapolateRight: 'clamp'});
          const ptX = interpolate(frame, [ptStart, ptStart + 16], [12, 0], {extrapolateRight: 'clamp'});
          return (
            <div
              key={pi}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 14,
                opacity: ptOpacity, transform: `translateX(${ptX}px)`,
              }}
            >
              <div style={{color, fontSize: 20, marginTop: 2, flexShrink: 0}}>▸</div>
              <div
                style={{
                  fontSize: 30, color: 'rgba(255,255,255,0.88)',
                  fontFamily: FONT, lineHeight: 1.4,
                  textShadow: '0 2px 10px rgba(0,0,0,0.8)',
                }}
              >
                {pt}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const SplitCompareScene: React.FC<SplitCompareSceneProps> = ({spec, theme}) => {
  const frame = useCurrentFrame();
  const t = theme ?? DEFAULT_THEME;

  const verdict: string | undefined = spec.type === 'split_compare' ? spec.verdict : undefined;
  const isSplitCompare = spec.type === 'split_compare';

  const leftColor  = isSplitCompare ? '#ff4444' : t.accent;
  const rightColor = isSplitCompare ? '#22c55e' : t.accent2;
  const leftIcon   = isSplitCompare ? '❌' : '◀';
  const rightIcon  = isSplitCompare ? '✅' : '▶';

  const verdictOpacity = interpolate(frame, VERDICT_IN, [0, 1], {extrapolateRight: 'clamp'});
  const verdictY = interpolate(frame, VERDICT_IN, [20, 0], {extrapolateRight: 'clamp'});

  const titleOpacity = interpolate(frame, [0, 18], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: '#050510'}}>
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
        Compare
      </div>

      {/* Left panel */}
      <Panel
        panel={spec.left}
        slideFrom="left"
        slideFrames={LEFT_SLIDE_IN as [number, number]}
        iconFrame={LEFT_ICON as [number, number]}
        ptsStart={LEFT_PTS_START}
        icon={leftIcon}
        color={leftColor}
        frame={frame}
      />

      {/* Right panel */}
      <Panel
        panel={spec.right}
        slideFrom="right"
        slideFrames={RIGHT_SLIDE_IN as [number, number]}
        iconFrame={RIGHT_ICON as [number, number]}
        ptsStart={RIGHT_PTS_START}
        icon={rightIcon}
        color={rightColor}
        frame={frame}
      />

      {/* VS badge */}
      <div
        style={{
          position: 'absolute',
          left: LEFT_X + COL_W + Math.round(COL_GAP / 2) - 22,
          top: 420,
          width: 44, height: 44,
          borderRadius: '50%',
          background: '#1a1a2e',
          border: `1.5px solid ${t.accent}66`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 5,
          fontSize: 16, fontWeight: 800, color: 'rgba(255,255,255,0.6)', fontFamily: FONT,
        }}
      >
        VS
      </div>

      {/* Verdict */}
      {verdict && (
        <div
          style={{
            position: 'absolute',
            bottom: 220,
            left: 40, right: 40,
            opacity: verdictOpacity,
            transform: `translateY(${verdictY}px)`,
            zIndex: 3,
            backgroundColor: 'rgba(255,68,68,0.15)',
            border: '1.5px solid rgba(255,68,68,0.4)',
            borderRadius: 16,
            padding: '18px 28px',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              fontSize: 34, fontWeight: 700, color: '#ff6666',
              fontFamily: FONT, letterSpacing: -0.3,
              textShadow: '0 0 20px rgba(255,68,68,0.6)',
            }}
          >
            {verdict}
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
