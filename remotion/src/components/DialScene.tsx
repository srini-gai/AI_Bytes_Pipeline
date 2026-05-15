import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {DialSpec} from '../types';

interface SceneTheme { accent: string; accent2: string; }

const DEFAULT_THEME: SceneTheme = {accent: '#60a5fa', accent2: '#f59e0b'};
const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

// Bar geometry
const BAR_X   = 100;  // left edge
const BAR_Y   = 860;  // vertical center of bar
const BAR_W   = 880;  // total width
const BAR_H   = 28;
const CARD_W  = 300;
const CARD_H  = 160;
const CARD_Y  = 560;  // top of callout cards

// Frame timing
const LABEL_FADE   = [0, 20]   as const;
const BAR_GROW     = [18, 42]  as const;
const NEEDLE_START = 50;
const NEEDLE_END   = 210;

interface DialSceneProps {
  spec: DialSpec;
  theme?: SceneTheme;
}

export const DialScene: React.FC<DialSceneProps> = ({spec, theme}) => {
  const frame = useCurrentFrame();
  const t = theme ?? DEFAULT_THEME;
  const {label, min_label, max_label, ticks} = spec;

  const values = ticks.map(tk => tk.value);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range  = maxVal > minVal ? maxVal - minVal : 1;

  const labelOpacity = interpolate(frame, [...LABEL_FADE], [0, 1], {extrapolateRight: 'clamp'});
  const barWidth     = interpolate(frame, [...BAR_GROW],   [0, BAR_W], {extrapolateRight: 'clamp'});

  // Needle sweeps from 0 to 1 (normalised position along bar)
  const needleNorm = interpolate(frame, [NEEDLE_START, NEEDLE_END], [0, 1], {extrapolateRight: 'clamp'});
  const needleX    = BAR_X + needleNorm * BAR_W;

  // Which tick is "active" (most recently passed by needle)
  const activeTick = ticks.reduce<number>((best, tk, i) => {
    const tickNorm = (tk.value - minVal) / range;
    return needleNorm >= tickNorm ? i : best;
  }, -1);

  const axisOpacity = interpolate(frame, [...BAR_GROW], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: '#050510'}}>
      <AbsoluteFill
        style={{background: `radial-gradient(ellipse 900px 400px at 50% 45%, ${t.accent}14 0%, transparent 70%)`}}
      />
      <AbsoluteFill
        style={{background: 'linear-gradient(to bottom, transparent 72%, rgba(0,0,0,0.82) 100%)'}}
      />

      {/* Parameter label */}
      <div
        style={{
          position: 'absolute', top: 200, left: 0, right: 0,
          textAlign: 'center', opacity: labelOpacity, zIndex: 2,
          fontSize: 68, fontWeight: 900, color: '#ffffff',
          fontFamily: FONT, letterSpacing: -1,
          textShadow: '0 4px 28px rgba(0,0,0,0.95)',
        }}
      >
        {label}
      </div>

      {/* Tick callout cards */}
      {ticks.map((tick, i) => {
        const tickNorm  = (tick.value - minVal) / range;
        const tickFrame = NEEDLE_START + tickNorm * (NEEDLE_END - NEEDLE_START);
        const cardOpacity = interpolate(frame, [tickFrame, tickFrame + 16], [0, 1], {extrapolateRight: 'clamp'});
        const isActive = i === activeTick;
        const cardX = BAR_X + tickNorm * BAR_W;
        const color = i === 0 ? t.accent : t.accent2;

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: Math.min(Math.max(cardX - CARD_W / 2, 20), 1080 - CARD_W - 20),
              top: CARD_Y,
              width: CARD_W,
              height: CARD_H,
              opacity: cardOpacity * (isActive ? 1 : 0.45),
              zIndex: isActive ? 5 : 3,
              borderRadius: 16,
              background: `${color}22`,
              border: `1.5px solid ${color}${isActive ? '88' : '44'}`,
              boxShadow: isActive ? `0 0 28px ${color}44` : 'none',
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center',
              padding: '0 16px',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                fontSize: 34, fontWeight: 800, color,
                fontFamily: FONT, marginBottom: 8,
                textShadow: `0 0 16px ${color}88`,
              }}
            >
              {tick.value.toFixed(1)}
            </div>
            <div
              style={{
                fontSize: 26, color: 'rgba(255,255,255,0.80)',
                fontFamily: FONT, lineHeight: 1.3,
              }}
            >
              {tick.description}
            </div>
          </div>
        );
      })}

      {/* Bar track */}
      <div
        style={{
          position: 'absolute',
          left: BAR_X, top: BAR_Y - Math.round(BAR_H / 2),
          width: BAR_W, height: BAR_H,
          borderRadius: BAR_H / 2,
          background: 'rgba(255,255,255,0.10)',
          overflow: 'hidden',
          opacity: axisOpacity, zIndex: 2,
        }}
      >
        {/* Filled gradient portion */}
        <div
          style={{
            position: 'absolute', left: 0, top: 0, bottom: 0,
            width: barWidth,
            background: `linear-gradient(to right, ${t.accent}, ${t.accent2})`,
            borderRadius: BAR_H / 2,
          }}
        />
      </div>

      {/* Tick dots on bar */}
      {ticks.map((tick, i) => {
        const tickNorm = (tick.value - minVal) / range;
        const dotX = BAR_X + tickNorm * BAR_W;
        const dotOpacity = interpolate(frame, [BAR_GROW[1] + 5, BAR_GROW[1] + 20], [0, 1], {extrapolateRight: 'clamp'});
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: dotX - 5, top: BAR_Y - 5,
              width: 10, height: 10,
              borderRadius: '50%',
              background: '#ffffff',
              opacity: dotOpacity,
              zIndex: 4,
            }}
          />
        );
      })}

      {/* Needle */}
      <div
        style={{
          position: 'absolute',
          left: needleX - 3,
          top: BAR_Y - 48,
          width: 6,
          height: 96,
          borderRadius: 3,
          background: `linear-gradient(to bottom, ${t.accent2}, ${t.accent2}88)`,
          boxShadow: `0 0 20px ${t.accent2}CC, 0 0 40px ${t.accent2}66`,
          opacity: axisOpacity,
          zIndex: 5,
        }}
      />

      {/* Min / max endpoint labels */}
      <div style={{opacity: axisOpacity, zIndex: 2}}>
        <div
          style={{
            position: 'absolute',
            left: BAR_X, top: BAR_Y + BAR_H / 2 + 20,
            fontSize: 26, color: 'rgba(255,255,255,0.55)', fontFamily: FONT,
          }}
        >
          {min_label}
        </div>
        <div
          style={{
            position: 'absolute',
            right: 1080 - (BAR_X + BAR_W), top: BAR_Y + BAR_H / 2 + 20,
            fontSize: 26, color: 'rgba(255,255,255,0.55)', fontFamily: FONT,
            textAlign: 'right',
          }}
        >
          {max_label}
        </div>
      </div>
    </AbsoluteFill>
  );
};
