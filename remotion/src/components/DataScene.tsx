import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import type {DataBar, DataSpec} from '../types';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const BG = '#050510';

const TITLE_FADE_START = 5;
const TITLE_FADE_END = 15;

// ── bars ─────────────────────────────────────────────────────────────────────
const BAR_GROW = 25;
const BAR_GAP = 10;
const BAR_SLOT = BAR_GROW + BAR_GAP;
const BARS_START = 20;
const BAR_LEFT = 90;
const BAR_TRACK_W = 900;
const ROWS_TOP = 520;
const ROWS_BOTTOM = 1780;
const ROW_GAP = 44;

// ── counter ──────────────────────────────────────────────────────────────────
const COUNTER_GROW = 60;
const COUNTER_LABEL_FADE_START = 10;
const COUNTER_LABEL_FADE_END = 24;

// ── comparison ───────────────────────────────────────────────────────────────
const COMPARISON_START = 20;
const COMPARISON_GROW = 40;
const COMPARISON_COL_W = 260;
const COMPARISON_TOP = 560;
const COMPARISON_BASE_Y = 1560;
const COMPARISON_MAX_BAR_H = COMPARISON_BASE_Y - COMPARISON_TOP - 130;
const OLD_COLOR = '#ff3b3b';
const NEW_COLOR = '#34d399';

interface DataSceneProps {
  dataSpec: DataSpec;
  accentColor: string;
  durationInFrames: number;
}

export const DataScene: React.FC<DataSceneProps> = ({dataSpec, accentColor}) => {
  const frame = useCurrentFrame();
  const titleOpacity = interpolate(
    frame,
    [TITLE_FADE_START, TITLE_FADE_END],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill style={{backgroundColor: BG}}>
      <AbsoluteFill
        style={{background: `radial-gradient(ellipse 800px 500px at 50% 60%, ${accentColor}14 0%, transparent 70%)`}}
      />

      <div
        style={{
          position: 'absolute', top: 140, left: 0, right: 0,
          textAlign: 'center', opacity: titleOpacity, zIndex: 2,
          fontSize: 44, fontWeight: 800, color: '#ffffff',
          fontFamily: FONT, letterSpacing: -0.5, padding: '0 60px',
          textShadow: '0 4px 20px rgba(0,0,0,0.9)',
        }}
      >
        {dataSpec.title}
      </div>

      {dataSpec.type === 'bars' && <BarsBody spec={dataSpec} accentColor={accentColor} frame={frame} />}
      {dataSpec.type === 'counter' && <CounterBody spec={dataSpec} accentColor={accentColor} frame={frame} />}
      {dataSpec.type === 'comparison' && <ComparisonBody spec={dataSpec} frame={frame} />}
    </AbsoluteFill>
  );
};

// ── bars ─────────────────────────────────────────────────────────────────────

interface BarsBodyProps {
  spec: DataSpec;
  accentColor: string;
  frame: number;
}

const BarsBody: React.FC<BarsBodyProps> = ({spec, accentColor, frame}) => {
  const bars = spec.bars ?? [];
  const n = bars.length || 1;
  const rowH = Math.min(260, Math.max(120, (ROWS_BOTTOM - ROWS_TOP - (n - 1) * ROW_GAP) / n));

  return (
    <>
      {bars.map((bar, i) => {
        const start = BARS_START + i * BAR_SLOT;
        const growProgress = interpolate(
          frame,
          [start, start + BAR_GROW],
          [0, 1],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );
        const labelOpacity = interpolate(
          frame,
          [start, start + 10],
          [0, 1],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );
        const maxValue = bar.maxValue || 1;
        const fillW = Math.round(BAR_TRACK_W * Math.min(bar.value / maxValue, 1) * growProgress);
        const currentValue = Math.round(bar.value * growProgress);
        const color = bar.color ?? accentColor;
        const rowY = ROWS_TOP + i * (rowH + ROW_GAP);

        return (
          <React.Fragment key={i}>
            <div
              style={{
                position: 'absolute', left: BAR_LEFT, top: rowY,
                opacity: labelOpacity, zIndex: 2,
                fontSize: 30, fontWeight: 700, color: 'rgba(255,255,255,0.85)',
                fontFamily: FONT,
              }}
            >
              {bar.label}
            </div>

            <div
              style={{
                position: 'absolute', left: BAR_LEFT, top: rowY + 50,
                width: BAR_TRACK_W, height: 28, borderRadius: 14,
                background: 'rgba(255,255,255,0.08)',
                opacity: labelOpacity, zIndex: 2,
              }}
            />

            <div
              style={{
                position: 'absolute', left: BAR_LEFT, top: rowY + 50,
                width: fillW, height: 28, borderRadius: 14,
                background: `linear-gradient(90deg, ${color}, ${color}cc)`,
                boxShadow: `0 0 20px ${color}66`,
                zIndex: 3,
              }}
            />

            <div
              style={{
                position: 'absolute', left: BAR_LEFT + fillW + 16, top: rowY + 36,
                opacity: growProgress, zIndex: 3,
                fontSize: 26, fontWeight: 800, color,
                fontFamily: FONT, whiteSpace: 'nowrap',
              }}
            >
              {currentValue}{spec.unit ?? ''}
            </div>
          </React.Fragment>
        );
      })}
    </>
  );
};

// ── counter ──────────────────────────────────────────────────────────────────

interface CounterBodyProps {
  spec: DataSpec;
  accentColor: string;
  frame: number;
}

const CounterBody: React.FC<CounterBodyProps> = ({spec, accentColor, frame}) => {
  const target = spec.counterValue ?? 0;
  const progress = interpolate(
    frame,
    [0, COUNTER_GROW],
    [0, 1],
    {easing: Easing.out(Easing.cubic), extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const current = Math.round(target * progress);
  const labelOpacity = interpolate(
    frame,
    [COUNTER_LABEL_FADE_START, COUNTER_LABEL_FADE_END],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <>
      <div
        style={{
          position: 'absolute', left: 0, right: 0, top: 780,
          display: 'flex', justifyContent: 'center', alignItems: 'baseline', gap: 12,
          zIndex: 2,
        }}
      >
        <span
          style={{
            fontSize: 180, fontWeight: 900, color: accentColor,
            fontFamily: FONT, textShadow: `0 0 60px ${accentColor}88`,
          }}
        >
          {current.toLocaleString()}
        </span>
        {spec.counterSuffix && (
          <span
            style={{
              fontSize: 90, fontWeight: 800, color: accentColor,
              fontFamily: FONT, opacity: labelOpacity,
            }}
          >
            {spec.counterSuffix}
          </span>
        )}
      </div>

      {spec.counterLabel && (
        <div
          style={{
            position: 'absolute', left: 0, right: 0, top: 1020,
            textAlign: 'center', opacity: labelOpacity, zIndex: 2,
            fontSize: 34, fontWeight: 700, color: 'rgba(255,255,255,0.8)',
            fontFamily: FONT, padding: '0 80px',
          }}
        >
          {spec.counterLabel}
        </div>
      )}
    </>
  );
};

// ── comparison ───────────────────────────────────────────────────────────────

interface ComparisonBodyProps {
  spec: DataSpec;
  frame: number;
}

const ComparisonBody: React.FC<ComparisonBodyProps> = ({spec, frame}) => {
  const bars = spec.bars ?? [];
  const oldBar = bars[0];
  const newBar = bars[1];
  const growProgress = interpolate(
    frame,
    [COMPARISON_START, COMPARISON_START + COMPARISON_GROW],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <>
      <div
        style={{
          position: 'absolute', left: 539, top: COMPARISON_TOP,
          width: 1, height: COMPARISON_BASE_Y - COMPARISON_TOP,
          background: 'rgba(255,255,255,0.12)', zIndex: 1,
        }}
      />
      {oldBar && (
        <ComparisonColumn bar={oldBar} centerX={280} color={oldBar.color ?? OLD_COLOR} growProgress={growProgress} unit={spec.unit} />
      )}
      {newBar && (
        <ComparisonColumn bar={newBar} centerX={800} color={newBar.color ?? NEW_COLOR} growProgress={growProgress} unit={spec.unit} />
      )}
    </>
  );
};

interface ComparisonColumnProps {
  bar: DataBar;
  centerX: number;
  color: string;
  growProgress: number;
  unit?: string;
}

const ComparisonColumn: React.FC<ComparisonColumnProps> = ({bar, centerX, color, growProgress, unit}) => {
  const maxValue = bar.maxValue || 1;
  const heightRatio = Math.min(bar.value / maxValue, 1);
  const barH = Math.round(COMPARISON_MAX_BAR_H * heightRatio * growProgress);
  const currentValue = Math.round(bar.value * growProgress);

  return (
    <>
      <div
        style={{
          position: 'absolute', left: centerX - COMPARISON_COL_W / 2, top: COMPARISON_TOP,
          width: COMPARISON_COL_W, textAlign: 'center', zIndex: 2,
          fontSize: 30, fontWeight: 700, color: 'rgba(255,255,255,0.85)',
          fontFamily: FONT,
        }}
      >
        {bar.label}
      </div>

      <div
        style={{
          position: 'absolute', left: centerX - COMPARISON_COL_W / 2, top: COMPARISON_BASE_Y - barH,
          width: COMPARISON_COL_W, height: barH,
          background: `linear-gradient(to top, ${color}, ${color}aa)`,
          borderRadius: '16px 16px 0 0',
          boxShadow: `0 0 30px ${color}66`,
          zIndex: 2,
        }}
      />

      <div
        style={{
          position: 'absolute', left: centerX - COMPARISON_COL_W / 2, top: COMPARISON_BASE_Y - barH - 70,
          width: COMPARISON_COL_W, textAlign: 'center', zIndex: 3,
          fontSize: 44, fontWeight: 900, color,
          fontFamily: FONT, textShadow: `0 0 20px ${color}88`,
          opacity: growProgress,
        }}
      >
        {currentValue}{unit ?? ''}
      </div>
    </>
  );
};
