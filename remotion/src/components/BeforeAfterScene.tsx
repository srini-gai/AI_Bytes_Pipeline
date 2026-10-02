/**
 * BeforeAfterScene — Visual Director v3.1 (data-driven)
 *
 * Shows a before/after comparison. The "before" state dominates the screen,
 * gets struck through, then flips to the "after" state.
 *
 * All display content comes from onScreenText props:
 *   [0] = before label (e.g. "VERBOSE PROMPT")
 *   [1] = after label  (e.g. "TERSE PROMPT")
 *   [2] = before detail (e.g. "MORE TOKENS")
 *   [3] = after detail  (e.g. "FEWER TOKENS")
 *
 * Production guard: throws if onScreenText has fewer than 4 entries.
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface BeforeAfterSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  accentColor?: string;
  accent2?: string;
  carryFrom?: string;
}

export const BeforeAfterScene: React.FC<BeforeAfterSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Production guard: require at least 4 onScreenText entries
  if (onScreenText.length < 4) {
    throw new Error(
      `[PRODUCTION GUARD] BeforeAfterScene: onScreenText must have ≥4 entries ` +
      `[beforeLabel, afterLabel, beforeDetail, afterDetail], got ${onScreenText.length}. ` +
      `Populate the storyboard on_screen_text.`
    );
  }

  const beforeLabel  = onScreenText[0];
  const afterLabel   = onScreenText[1];
  const beforeDetail = onScreenText[2];
  const afterDetail  = onScreenText[3];

  const b0 = beats[0] ?? {start: 0, end: 0.8};
  const b1 = beats[1] ?? {start: 0.8, end: 1.6};
  const b2 = beats[2] ?? {start: 1.6, end: 3.0};

  // ── Beat 0: wrong answer card enters from top, settling in centre ────────
  const slamP  = easeOut(frame, fps, b0.start, b0.end);
  const cardY  = interpolate(slamP, [0, 1], [-80, 0]);
  // Screen shake on slam impact (frames around b0.end)
  const impactF  = Math.round(b0.end * fps);
  const shake    = interpolate(frame, [impactF, impactF + 6], [10, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const shakeX = Math.sin(frame * 5.1) * shake;

  // ── Beat 1: red diagonal strike-through across the answer ────────────────
  const strikeP  = linearProgress(frame, fps, b1.start, b1.end);
  // WRONG stamp drops down onto the card
  const wrongP   = easeOut(frame, fps, b1.start + 0.2, b1.end);
  const wrongY   = interpolate(wrongP, [0, 1], [-180, 0]);

  // ── Beat 2: card flips — grounded answer revealed ────────────────────────
  const flipP    = easeOut(frame, fps, b2.start, b2.end);
  // scaleX: 1 → 0 → 1 (3D card flip)
  const flipX    = interpolate(flipP, [0, 0.45, 0.55, 1], [1, 0.01, 0.01, 1]);
  const wrongAlpha = interpolate(flipP, [0, 0.42], [1, 0]);
  const rightAlpha = interpolate(flipP, [0.58, 1], [0, 1]);
  const sourceP    = easeOut(frame, fps, b2.start + 0.5, b2.end);

  // Camera: slow push-in during b0 to make wrong answer feel huge
  const camScale = interpolate(slamP, [0, 1], [1.12, 1]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        overflow: 'hidden',
        transform: `translateX(${shakeX}px)`,
      }}
    >
      {/* Vignette bg glow — red tint on wrong side */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 1080px 900px at 50% 48%,
          ${wrongAlpha > 0 ? 'rgba(239,68,68,0.12)' : `${accent2}10`} 0%,
          transparent 70%)`,
      }}/>

      {/* ── Main card area — scales with camera ─────────────────────────── */}
      <AbsoluteFill style={{
        transform: `scale(${camScale})`,
        transformOrigin: '50% 48%',
      }}>

        {/* ── WRONG STATE (beats 0–1 + first half of flip) ────────────────── */}
        <AbsoluteFill style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          paddingTop: 200,
          opacity: wrongAlpha,
          transform: `translateY(${cardY}px)`,
        }}>
          {/* Wrong answer — dominates 80% of screen width */}
          <div style={{
            width: 960,
            background: 'rgba(239,68,68,0.07)',
            border: '3px solid rgba(239,68,68,0.5)',
            borderRadius: 28,
            padding: '70px 64px 60px',
            position: 'relative',
            transform: `scaleX(${wrongAlpha > 0 ? flipX : 1})`,
            transformOrigin: '50% 50%',
          }}>
            {/* Before label chip */}
            <div style={{
              fontFamily: FONT, fontSize: 22, fontWeight: 700, color: 'rgba(255,255,255,0.4)',
              letterSpacing: 4, textTransform: 'uppercase', marginBottom: 32, textAlign: 'center',
            }}>{beforeLabel}</div>

            {/* Before detail */}
            <div style={{
              fontFamily: FONT, fontSize: 72, fontWeight: 900,
              color: 'rgba(255,255,255,0.88)', lineHeight: 1.25, textAlign: 'center',
              letterSpacing: -1,
            }}>
              {beforeDetail}
            </div>

            {/* Strike-through line (draws L→R across full card) */}
            {strikeP > 0 && (
              <div style={{
                position: 'absolute',
                top: '54%',
                left: 0,
                height: 6,
                width: `${smoothstep(strikeP) * 100}%`,
                background: 'linear-gradient(90deg, #ef4444, #ff6666)',
                borderRadius: 3,
                boxShadow: '0 0 18px rgba(239,68,68,0.8)',
              }}/>
            )}
          </div>

          {/* WRONG stamp — drops from above the card */}
          {wrongP > 0 && (
            <div style={{
              position: 'absolute',
              top: '28%',
              transform: `translateY(${wrongY}px)`,
              opacity: smoothstep(wrongP),
              fontFamily: FONT, fontSize: 180, fontWeight: 900,
              color: '#ef4444',
              letterSpacing: -8,
              textShadow: '0 0 80px rgba(239,68,68,0.5)',
              lineHeight: 1,
              userSelect: 'none',
            }}>
              ✗
            </div>
          )}
        </AbsoluteFill>

        {/* ── CORRECT STATE (second half of flip) ─────────────────────────── */}
        <AbsoluteFill style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          paddingTop: 200,
          opacity: rightAlpha,
        }}>
          <div style={{
            width: 960,
            background: `linear-gradient(135deg, ${accent2}10, ${accentColor}0a)`,
            border: `3px solid ${accent2}70`,
            borderRadius: 28,
            padding: '70px 64px 60px',
            position: 'relative',
            transform: `scaleX(${rightAlpha > 0 ? flipX : 1})`,
            transformOrigin: '50% 50%',
          }}>
            {/* After label chip */}
            <div style={{
              fontFamily: FONT, fontSize: 22, fontWeight: 700, color: accent2,
              letterSpacing: 4, textTransform: 'uppercase', marginBottom: 32, textAlign: 'center',
            }}>{afterLabel}</div>

            {/* After detail */}
            <div style={{
              fontFamily: FONT, fontSize: 72, fontWeight: 900,
              color: '#ffffff', lineHeight: 1.25, textAlign: 'center', letterSpacing: -1,
            }}>
              {afterDetail}
            </div>

            {/* Checkmark badge */}
            <div style={{
              marginTop: 40, display: 'flex', justifyContent: 'center',
              opacity: smoothstep(sourceP),
              transform: `scale(${interpolate(sourceP, [0, 1], [0.7, 1])})`,
            }}>
              <div style={{
                background: `${accent2}20`, border: `2px solid ${accent2}99`,
                borderRadius: 50, padding: '14px 36px',
                fontFamily: FONT, fontSize: 28, fontWeight: 700, color: accent2,
                boxShadow: `0 0 30px ${accent2}44`,
              }}>
                ✓ {afterLabel}
              </div>
            </div>
          </div>

          {/* Bottom label */}
          <div style={{
            marginTop: 36,
            opacity: smoothstep(sourceP),
            fontFamily: FONT, fontSize: 36, fontWeight: 700,
            color: accentColor, letterSpacing: 3, textTransform: 'uppercase',
          }}>
            {afterDetail}
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
