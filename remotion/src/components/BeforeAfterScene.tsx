/**
 * BeforeAfterScene — Verbose vs terse token trains (v41 token-native).
 *
 * s08: 5.88s ≈ 176 frames at 30fps. 3 beats:
 *   Beat A (0–59f):   Verbose prompt label + long token train slides in
 *   Beat B (59–117f): Terse prompt label + short token train slides in below
 *   Beat C (117–176f): "MORE TOKENS" / "FEWER TOKENS" labels + arrow comparison
 *
 * on_screen_text: ["VERBOSE PROMPT", "TERSE PROMPT", "MORE TOKENS", "FEWER TOKENS"]
 * source_type=illustrative for this episode.
 *
 * Production guard: throws if onScreenText < 4 entries.
 */
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, MONO} from './beatUtils';
import type {SceneBeat} from '../types';

interface BeforeAfterSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  accentColor?: string;
  accent2?: string;
  carryFrom?: string;
}

// Token train config
const BLOCK_W = 58;
const BLOCK_H = 58;
const BLOCK_GAP = 6;
const TRAIN_LEFT = 60;

// Verbose train: 14 blocks (long)
const VERBOSE_COUNT = 14;
// Terse train: 5 blocks (short)
const TERSE_COUNT = 5;

// Deterministic pseudo-token labels
const VERBOSE_LABELS = [
  'Can', 'you', 'please', 'explain', 'to', 'me', 'in',
  'great', 'detail', 'how', 'token', 'ization', 'works', '?',
];
const TERSE_LABELS = ['How', 'do', 'tokens', 'work', '?'];

export const BeforeAfterScene: React.FC<BeforeAfterSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Production guard
  if (onScreenText.length < 4) {
    throw new Error(
      `[PRODUCTION GUARD] BeforeAfterScene: onScreenText must have ≥4 entries ` +
      `[beforeLabel, afterLabel, beforeDetail, afterDetail], got ${onScreenText.length}. ` +
      `Populate the storyboard on_screen_text.`,
    );
  }

  const verboseLabel = onScreenText[0]; // "VERBOSE PROMPT"
  const terseLabel   = onScreenText[1]; // "TERSE PROMPT"
  const moreTokens   = onScreenText[2]; // "MORE TOKENS"
  const fewerTokens  = onScreenText[3]; // "FEWER TOKENS"

  const totalFrames = Math.round(fps * 5.88);
  const beatLen = Math.round(totalFrames / 3);

  // Beat boundaries (from props or proportional defaults)
  const b0End = beats[0]?.end ? Math.round(beats[0].end * fps) : beatLen;
  const b1Start = beats[1]?.start ? Math.round(beats[1].start * fps) : Math.round(beatLen * 0.85);
  const b1End = beats[1]?.end ? Math.round(beats[1].end * fps) : beatLen * 2;
  const b2Start = beats[2]?.start ? Math.round(beats[2].start * fps) : Math.round(beatLen * 1.85);

  // Scene fade
  const sceneOpacity = interpolate(
    frame,
    [0, 6, totalFrames - 6, totalFrames],
    [0, 1, 1, 0.3],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // ── Beat A: Verbose train ─────────────────────────────────────────────────
  const verboseLabelOpacity = interpolate(
    frame, [4, 16], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // ── Beat B: Terse train ───────────────────────────────────────────────────
  const terseLabelOpacity = interpolate(
    frame, [b1Start, b1Start + 14], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // ── Beat C: Comparison labels ─────────────────────────────────────────────
  const compLabelOpacity = interpolate(
    frame, [b2Start + 4, b2Start + 18], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Arrow from long to short
  const arrowProgress = interpolate(
    frame, [b2Start + 10, b2Start + 30], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Layout positions
  const verboseY = 320;
  const terseY = 960;

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity, overflow: 'hidden'}}>
      {/* Background glow */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 900px 600px at 50% 50%, ${accentColor}0c 0%, transparent 70%)`,
      }} />

      {/* ── Verbose Prompt Section ──────────────────────────────────────── */}
      <div style={{
        position: 'absolute', left: TRAIN_LEFT, top: verboseY - 60,
        opacity: verboseLabelOpacity, zIndex: 2,
      }}>
        <span style={{
          fontFamily: FONT, fontSize: 26, fontWeight: 800,
          color: 'rgba(239,68,68,0.8)', letterSpacing: 3,
        }}>
          {verboseLabel}
        </span>
      </div>

      {/* Verbose token train — wrapping across two rows */}
      <div style={{
        position: 'absolute', left: TRAIN_LEFT, top: verboseY,
        display: 'flex', flexWrap: 'wrap', gap: BLOCK_GAP,
        width: 960, opacity: verboseLabelOpacity, zIndex: 2,
      }}>
        {VERBOSE_LABELS.map((tok, i) => {
          const blockDelay = i * 2.5;
          const blockOpacity = interpolate(
            frame, [8 + blockDelay, 8 + blockDelay + 8], [0, 1],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
          );
          const slideX = interpolate(
            frame, [8 + blockDelay, 8 + blockDelay + 10], [60, 0],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
          );

          return (
            <div key={i} style={{
              width: BLOCK_W, height: BLOCK_H,
              borderRadius: 10,
              background: 'rgba(239,68,68,0.15)',
              border: '2px solid rgba(239,68,68,0.45)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              opacity: blockOpacity,
              transform: `translateX(${slideX}px)`,
            }}>
              <span style={{
                fontFamily: MONO, fontSize: 11, fontWeight: 600,
                color: 'rgba(239,68,68,0.7)', letterSpacing: 0.3,
              }}>
                {tok}
              </span>
            </div>
          );
        })}
      </div>

      {/* Verbose count badge */}
      {compLabelOpacity > 0.01 && (
        <div style={{
          position: 'absolute',
          left: TRAIN_LEFT + VERBOSE_COUNT * (BLOCK_W + BLOCK_GAP) - (BLOCK_W + BLOCK_GAP) * Math.max(0, VERBOSE_COUNT - 7),
          top: verboseY + BLOCK_H + BLOCK_GAP + BLOCK_H + 20,
          opacity: compLabelOpacity, zIndex: 3,
        }}>
          <span style={{
            fontFamily: FONT, fontSize: 22, fontWeight: 800,
            color: 'rgba(239,68,68,0.8)', letterSpacing: 2,
          }}>
            {moreTokens}
          </span>
        </div>
      )}

      {/* ── Divider ────────────────────────────────────────────────────── */}
      <div style={{
        position: 'absolute', left: 80, right: 80,
        top: (verboseY + BLOCK_H * 2 + BLOCK_GAP + 80 + terseY - 80) / 2,
        height: 1,
        background: `linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)`,
        opacity: terseLabelOpacity,
        zIndex: 1,
      }} />

      {/* ── Terse Prompt Section ────────────────────────────────────────── */}
      <div style={{
        position: 'absolute', left: TRAIN_LEFT, top: terseY - 60,
        opacity: terseLabelOpacity, zIndex: 2,
      }}>
        <span style={{
          fontFamily: FONT, fontSize: 26, fontWeight: 800,
          color: `${accent2}cc`, letterSpacing: 3,
        }}>
          {terseLabel}
        </span>
      </div>

      {/* Terse token train — single short row */}
      <div style={{
        position: 'absolute', left: TRAIN_LEFT, top: terseY,
        display: 'flex', gap: BLOCK_GAP,
        opacity: terseLabelOpacity, zIndex: 2,
      }}>
        {TERSE_LABELS.map((tok, i) => {
          const blockDelay = i * 3;
          const blockOpacity = interpolate(
            frame, [b1Start + 6 + blockDelay, b1Start + 6 + blockDelay + 8], [0, 1],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
          );
          const slideX = interpolate(
            frame, [b1Start + 6 + blockDelay, b1Start + 6 + blockDelay + 10], [40, 0],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
          );

          return (
            <div key={i} style={{
              width: BLOCK_W, height: BLOCK_H,
              borderRadius: 10,
              background: `${accent2}18`,
              border: `2px solid ${accent2}55`,
              boxShadow: `0 0 10px ${accent2}22`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              opacity: blockOpacity,
              transform: `translateX(${slideX}px)`,
            }}>
              <span style={{
                fontFamily: MONO, fontSize: 12, fontWeight: 600,
                color: `${accent2}99`, letterSpacing: 0.3,
              }}>
                {tok}
              </span>
            </div>
          );
        })}
      </div>

      {/* Terse count badge */}
      {compLabelOpacity > 0.01 && (
        <div style={{
          position: 'absolute',
          left: TRAIN_LEFT + TERSE_COUNT * (BLOCK_W + BLOCK_GAP) + 20,
          top: terseY + 14,
          opacity: compLabelOpacity, zIndex: 3,
        }}>
          <span style={{
            fontFamily: FONT, fontSize: 22, fontWeight: 800,
            color: `${accent2}cc`, letterSpacing: 2,
          }}>
            {fewerTokens}
          </span>
        </div>
      )}

      {/* ── Arrow: long train → short train (Beat C) ───────────────────── */}
      {arrowProgress > 0.01 && (
        <svg
          viewBox="0 0 1080 1920"
          width={1080} height={1920}
          style={{position: 'absolute', inset: 0, zIndex: 4, pointerEvents: 'none'}}
        >
          {/* Curved arrow from verbose area down to terse area */}
          <path
            d={`M ${540} ${verboseY + BLOCK_H * 2 + BLOCK_GAP + 60}
                C ${540} ${(verboseY + terseY) / 2},
                  ${540} ${(verboseY + terseY) / 2},
                  ${540} ${terseY - 70}`}
            fill="none"
            stroke={accentColor}
            strokeWidth={3}
            strokeDasharray={`${arrowProgress * 400} 600`}
            opacity={0.5}
          />
          {/* Arrowhead */}
          {arrowProgress > 0.8 && (
            <polygon
              points={`${540 - 10},${terseY - 80} ${540},${terseY - 65} ${540 + 10},${terseY - 80}`}
              fill={accentColor}
              opacity={0.6}
            />
          )}
        </svg>
      )}

      {/* Bottom label */}
      {compLabelOpacity > 0.01 && (
        <div style={{
          position: 'absolute', bottom: 250, left: 0, right: 0,
          textAlign: 'center', opacity: compLabelOpacity, zIndex: 5,
        }}>
          <span style={{
            fontFamily: FONT, fontSize: 28, fontWeight: 900,
            color: accentColor, letterSpacing: 4,
          }}>
            WRITE SHORT, SAVE TOKENS
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};
