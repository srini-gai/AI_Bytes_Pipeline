import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {BarChartSpec} from '../types';

interface SceneTheme { accent: string; accent2: string; }

const DEFAULT_THEME: SceneTheme = {accent: '#f59e0b', accent2: '#fb923c'};
const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

// Chart geometry
const AXIS_X   = 160;  // y-axis x
const AXIS_Y   = 1500; // x-axis y
const CHART_TOP = 340; // top of tallest bar
const CHART_W  = 760;  // AXIS_X to right edge
const MAX_BAR_H = AXIS_Y - CHART_TOP; // 1160px

const TITLE_FADE = [0, 20] as const;
const AXES_FADE  = [15, 38] as const;
const BAR_INTERVAL = 40;
const BAR_GROW_FRAMES = 38;

interface BarChartSceneProps {
  spec: BarChartSpec;
  theme?: SceneTheme;
}

export const BarChartScene: React.FC<BarChartSceneProps> = ({spec, theme}) => {
  const frame = useCurrentFrame();
  const t = theme ?? DEFAULT_THEME;
  const {title, bars} = spec;
  const n = bars.length;

  const maxVal = Math.max(...bars.map(b => b.value), 1);
  const gap = 36;
  const barW = Math.floor((CHART_W - (n - 1) * gap) / n);

  const titleOpacity = interpolate(frame, [...TITLE_FADE], [0, 1], {extrapolateRight: 'clamp'});
  const axisOpacity  = interpolate(frame, [...AXES_FADE],  [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: '#050510'}}>
      <AbsoluteFill
        style={{background: `radial-gradient(ellipse 800px 500px at 50% 65%, ${t.accent}14 0%, transparent 70%)`}}
      />
      <AbsoluteFill
        style={{background: 'linear-gradient(to bottom, transparent 78%, rgba(0,0,0,0.82) 100%)'}}
      />

      {/* Chart title */}
      <div
        style={{
          position: 'absolute', top: 136, left: 0, right: 0,
          textAlign: 'center', opacity: titleOpacity, zIndex: 2,
          fontSize: 48, fontWeight: 800, color: '#ffffff',
          fontFamily: FONT, letterSpacing: -0.5,
          textShadow: '0 4px 20px rgba(0,0,0,0.9)',
        }}
      >
        {title}
      </div>

      {/* Y axis */}
      <div
        style={{
          position: 'absolute',
          left: AXIS_X, top: CHART_TOP - 20,
          width: 2, height: AXIS_Y - CHART_TOP + 20,
          background: 'rgba(255,255,255,0.2)',
          opacity: axisOpacity, zIndex: 2,
        }}
      />

      {/* X axis */}
      <div
        style={{
          position: 'absolute',
          left: AXIS_X, top: AXIS_Y,
          width: CHART_W + 20, height: 2,
          background: 'rgba(255,255,255,0.2)',
          opacity: axisOpacity, zIndex: 2,
        }}
      />

      {/* Bars */}
      {bars.map((bar, i) => {
        const barStart = 38 + i * BAR_INTERVAL;
        const growProgress = interpolate(
          frame,
          [barStart, barStart + BAR_GROW_FRAMES],
          [0, 1],
          {extrapolateRight: 'clamp'},
        );
        const barH = Math.round((bar.value / maxVal) * MAX_BAR_H * 0.88 * growProgress);
        const barX = AXIS_X + i * (barW + gap) + gap / 2;
        const barY = AXIS_Y - barH;

        // Gradient color per bar — interpolate accent → accent2 by position
        const colorT = n > 1 ? i / (n - 1) : 0;
        const barColor = colorT < 0.5
          ? t.accent
          : t.accent2;

        const labelOpacity = interpolate(frame, [barStart, barStart + 16], [0, 1], {extrapolateRight: 'clamp'});
        const valueOpacity = interpolate(
          frame,
          [barStart + BAR_GROW_FRAMES - 8, barStart + BAR_GROW_FRAMES + 10],
          [0, 1],
          {extrapolateRight: 'clamp'},
        );

        return (
          <React.Fragment key={i}>
            {/* Bar body */}
            <div
              style={{
                position: 'absolute',
                left: barX, top: barY,
                width: barW, height: barH,
                background: `linear-gradient(to top, ${t.accent}, ${t.accent2})`,
                borderRadius: '8px 8px 0 0',
                boxShadow: `0 0 24px ${barColor}55`,
                zIndex: 2,
              }}
            />

            {/* Value at top of bar */}
            {barH > 40 && (
              <div
                style={{
                  position: 'absolute',
                  left: barX, top: barY - 52,
                  width: barW, textAlign: 'center',
                  opacity: valueOpacity, zIndex: 3,
                  fontSize: 36, fontWeight: 800,
                  color: t.accent2, fontFamily: FONT,
                  textShadow: `0 0 16px ${t.accent2}88`,
                }}
              >
                {bar.value}%
              </div>
            )}

            {/* Bar label */}
            <div
              style={{
                position: 'absolute',
                left: barX, top: AXIS_Y + 16,
                width: barW, textAlign: 'center',
                opacity: labelOpacity, zIndex: 2,
                fontSize: 28, fontWeight: 700,
                color: 'rgba(255,255,255,0.8)', fontFamily: FONT,
                lineHeight: 1.3,
              }}
            >
              {bar.label}
            </div>
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};
