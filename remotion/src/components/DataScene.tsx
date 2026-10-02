/**
 * DataScene — Token cost visualization (v41 token-native).
 *
 * s06: 5.76s ≈ 173 frames at 30fps. 3 beats:
 *   Beat A (0–58f):   First token train appears (English word — short)
 *   Beat B (58–115f): Second train appears (Code snippet — medium)
 *   Beat C (115–173f): Third train appears (Rare word — long)
 *
 * Bars render as "token trains" — chains of token blocks — not plain gradient fills.
 * source_type=illustrative → qualitative=true → no precise numeric values shown.
 *
 * Supports: bars, counter, comparison sub-types (counter/comparison unchanged).
 */
import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import type {DataBar, DataSpec} from '../types';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const MONO = '"JetBrains Mono", "Fira Code", "SF Mono", monospace';
const BG = '#050510';

const TITLE_FADE_START = 5;
const TITLE_FADE_END = 15;

// Token train layout
const TRAIN_LEFT = 60;
const TRAIN_BLOCK_W = 64;
const TRAIN_BLOCK_H = 72;
const TRAIN_GAP = 8;
const ROWS_TOP = 420;
const ROW_SPACING = 380;

// Counter / comparison constants (kept from v3)
const COUNTER_GROW = 60;
const COUNTER_LABEL_FADE_START = 10;
const COUNTER_LABEL_FADE_END = 24;
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
  qualitative?: boolean;
}

export const DataScene: React.FC<DataSceneProps> = ({dataSpec, accentColor, durationInFrames, qualitative = false}) => {
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

      {dataSpec.type === 'bars' && <TokenTrainBars spec={dataSpec} accentColor={accentColor} frame={frame} durationInFrames={durationInFrames} qualitative={qualitative} />}
      {dataSpec.type === 'counter' && <CounterBody spec={dataSpec} accentColor={accentColor} frame={frame} qualitative={qualitative} />}
      {dataSpec.type === 'comparison' && <ComparisonBody spec={dataSpec} frame={frame} qualitative={qualitative} />}
    </AbsoluteFill>
  );
};

// ── Token Train Bars (v41) ──────────────────────────────────────────────────

interface TokenTrainBarsProps {
  spec: DataSpec;
  accentColor: string;
  frame: number;
  durationInFrames: number;
  qualitative?: boolean;
}

// Deterministic pseudo-token label
function tokenLabel(rowIdx: number, blockIdx: number): string {
  const labels = [
    ['hello', 'world', 'foo', 'bar', 'the', 'cat', 'sat', 'on', 'mat', 'run', 'big', 'go'],
    ['def', '(x)', ':', '\\n', 'ret', 'urn', 'val', '+=', 'int', '.py', 'fn', 'if'],
    ['über', '日本', 'café', 'naï', 've', 'sch', 'ön', 'straß', 'e', 'año', 'fête', 'cœur'],
  ];
  const row = labels[rowIdx % labels.length];
  return row[blockIdx % row.length];
}

const TokenTrainBars: React.FC<TokenTrainBarsProps> = ({spec, accentColor, frame, durationInFrames, qualitative}) => {
  const bars = spec.bars ?? [];
  const n = bars.length;
  const beatLen = Math.round(durationInFrames / Math.max(n, 1));

  // Colors for each tier
  const tierColors = [accentColor, '#f59e0b', '#ef4444'];

  return (
    <>
      {bars.map((bar, i) => {
        const start = i * beatLen;
        const growEnd = start + Math.round(beatLen * 0.7);

        // Row appears with stagger
        const rowOpacity = interpolate(
          frame,
          [start + 4, start + 16],
          [0, 1],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );

        // Number of token blocks proportional to value
        const maxBlocks = 12;
        const maxVal = bar.maxValue || Math.max(...bars.map(b => b.value), 1);
        const targetBlocks = Math.max(2, Math.round((bar.value / maxVal) * maxBlocks));

        // Blocks appear sequentially
        const blockRevealProgress = interpolate(
          frame,
          [start + 10, growEnd],
          [0, 1],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );
        const visibleBlocks = Math.floor(blockRevealProgress * targetBlocks);

        const color = bar.color ?? tierColors[i % tierColors.length];
        const rowY = ROWS_TOP + i * ROW_SPACING;

        return (
          <React.Fragment key={i}>
            {/* Row label */}
            <div style={{
              position: 'absolute', left: TRAIN_LEFT, top: rowY,
              opacity: rowOpacity, zIndex: 2,
              fontSize: 28, fontWeight: 700,
              color: 'rgba(255,255,255,0.85)',
              fontFamily: FONT,
            }}>
              {bar.label}
            </div>

            {/* Token train */}
            <div style={{
              position: 'absolute', left: TRAIN_LEFT, top: rowY + 52,
              display: 'flex', gap: TRAIN_GAP, alignItems: 'center',
              opacity: rowOpacity, zIndex: 2,
              flexWrap: 'wrap',
            }}>
              {Array.from({length: targetBlocks}, (_, bi) => {
                const isVisible = bi < visibleBlocks;
                const blockDelay = bi * 2;
                const blockOpacity = interpolate(
                  frame,
                  [start + 10 + blockDelay, start + 10 + blockDelay + 8],
                  [0, 1],
                  {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
                );

                return (
                  <div key={bi} style={{
                    width: TRAIN_BLOCK_W,
                    height: TRAIN_BLOCK_H,
                    borderRadius: 10,
                    background: isVisible ? `${color}25` : 'transparent',
                    border: isVisible ? `2px solid ${color}88` : '2px solid transparent',
                    boxShadow: isVisible ? `0 0 12px ${color}33` : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity: isVisible ? blockOpacity : 0,
                  }}>
                    <span style={{
                      fontFamily: MONO,
                      fontSize: 14,
                      fontWeight: 600,
                      color: `${color}cc`,
                      letterSpacing: 0.5,
                    }}>
                      {tokenLabel(i, bi)}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Token count label (if not qualitative) */}
            {!qualitative && visibleBlocks > 0 && (
              <div style={{
                position: 'absolute',
                left: TRAIN_LEFT + visibleBlocks * (TRAIN_BLOCK_W + TRAIN_GAP) + 16,
                top: rowY + 66,
                fontSize: 26, fontWeight: 800,
                color, fontFamily: FONT,
                opacity: blockRevealProgress,
                zIndex: 3,
              }}>
                {Math.round(bar.value * blockRevealProgress)}{spec.unit ?? ''}
              </div>
            )}
          </React.Fragment>
        );
      })}
    </>
  );
};

// ── counter (unchanged from v3) ─────────────────────────────────────────────

interface CounterBodyProps {
  spec: DataSpec;
  accentColor: string;
  frame: number;
  qualitative?: boolean;
}

const CounterBody: React.FC<CounterBodyProps> = ({spec, accentColor, frame, qualitative = false}) => {
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
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 780,
        display: 'flex', justifyContent: 'center', alignItems: 'baseline', gap: 12,
        zIndex: 2,
      }}>
        <span style={{
          fontSize: 180, fontWeight: 900, color: accentColor,
          fontFamily: FONT, textShadow: `0 0 60px ${accentColor}88`,
        }}>
          {qualitative ? '▰'.repeat(Math.max(1, Math.round(progress * 5))) : current.toLocaleString()}
        </span>
        {spec.counterSuffix && (
          <span style={{
            fontSize: 90, fontWeight: 800, color: accentColor,
            fontFamily: FONT, opacity: labelOpacity,
          }}>
            {spec.counterSuffix}
          </span>
        )}
      </div>

      {spec.counterLabel && (
        <div style={{
          position: 'absolute', left: 0, right: 0, top: 1020,
          textAlign: 'center', opacity: labelOpacity, zIndex: 2,
          fontSize: 34, fontWeight: 700, color: 'rgba(255,255,255,0.8)',
          fontFamily: FONT, padding: '0 80px',
        }}>
          {spec.counterLabel}
        </div>
      )}
    </>
  );
};

// ── comparison (unchanged from v3) ──────────────────────────────────────────

interface ComparisonBodyProps {
  spec: DataSpec;
  frame: number;
  qualitative?: boolean;
}

const ComparisonBody: React.FC<ComparisonBodyProps> = ({spec, frame, qualitative = false}) => {
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
      <div style={{
        position: 'absolute', left: 539, top: COMPARISON_TOP,
        width: 1, height: COMPARISON_BASE_Y - COMPARISON_TOP,
        background: 'rgba(255,255,255,0.12)', zIndex: 1,
      }} />
      {oldBar && (
        <ComparisonColumn bar={oldBar} centerX={280} color={oldBar.color ?? OLD_COLOR} growProgress={growProgress} unit={spec.unit} qualitative={qualitative} />
      )}
      {newBar && (
        <ComparisonColumn bar={newBar} centerX={800} color={newBar.color ?? NEW_COLOR} growProgress={growProgress} unit={spec.unit} qualitative={qualitative} />
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
  qualitative?: boolean;
}

const ComparisonColumn: React.FC<ComparisonColumnProps> = ({bar, centerX, color, growProgress, unit, qualitative = false}) => {
  const maxValue = bar.maxValue || 1;
  const heightRatio = Math.min(bar.value / maxValue, 1);
  const barH = Math.round(COMPARISON_MAX_BAR_H * heightRatio * growProgress);
  const currentValue = Math.round(bar.value * growProgress);

  return (
    <>
      <div style={{
        position: 'absolute', left: centerX - COMPARISON_COL_W / 2, top: COMPARISON_TOP,
        width: COMPARISON_COL_W, textAlign: 'center', zIndex: 2,
        fontSize: 30, fontWeight: 700, color: 'rgba(255,255,255,0.85)',
        fontFamily: FONT,
      }}>
        {bar.label}
      </div>

      <div style={{
        position: 'absolute', left: centerX - COMPARISON_COL_W / 2, top: COMPARISON_BASE_Y - barH,
        width: COMPARISON_COL_W, height: barH,
        background: `linear-gradient(to top, ${color}, ${color}aa)`,
        borderRadius: '16px 16px 0 0',
        boxShadow: `0 0 30px ${color}66`,
        zIndex: 2,
      }} />

      {!qualitative && (
        <div style={{
          position: 'absolute', left: centerX - COMPARISON_COL_W / 2, top: COMPARISON_BASE_Y - barH - 70,
          width: COMPARISON_COL_W, textAlign: 'center', zIndex: 3,
          fontSize: 44, fontWeight: 900, color,
          fontFamily: FONT, textShadow: `0 0 20px ${color}88`,
          opacity: growProgress,
        }}>
          {currentValue}{unit ?? ''}
        </div>
      )}
    </>
  );
};
