/**
 * BeforeAfterScene — Visual Director v3
 *
 * Beat-driven animated wipe comparing two states.
 * Beats control: slam-in → strike-through → flip to correct state.
 * Used for HOOK scenes where a wrong state transforms into a right one.
 *
 * The canvas is used fully: wrong state card enters from off-screen top,
 * strike animation draws across it, then the card flips in 3D to reveal
 * the correct state rising from the bottom half of the canvas.
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
  /** Carry-in object name (unused visually but documented) */
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

  // ── Beat 0: wrong answer card slams in from top (0–1.2s) ──────────────────
  const b0 = beats[0] ?? {start: 0, end: 1.2};
  const cardSlam = easeOut(frame, fps, b0.start, b0.end);
  const cardY    = interpolate(cardSlam, [0, 1], [-700, 0]); // enters from above canvas
  const cardRot  = interpolate(cardSlam, [0, 1], [-8, 0]);   // slight rotation on impact

  // Screen shake on slam (only during first 8 frames of beat 0)
  const slamStart = Math.round(b0.end * fps);
  const shakeAmt  = interpolate(frame, [slamStart, slamStart + 8], [12, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const shakeX = Math.sin(frame * 3.7) * shakeAmt;

  // ── Beat 1: red X strike-through (1.2–2.0s) ──────────────────────────────
  const b1 = beats[1] ?? {start: 1.2, end: 2.0};
  const strikeP = linearProgress(frame, fps, b1.start, b1.end);
  const strikeW = smoothstep(strikeP) * 100; // % of card width

  const xOpacity = interpolate(frame, [
    Math.round(b1.start * fps),
    Math.round(b1.start * fps) + 6,
  ], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // ── Beat 2: card flips + grounded answer rises (2.0–3.0s) ────────────────
  const b2 = beats[2] ?? {start: 2.0, end: 3.0};
  const flipP      = easeOut(frame, fps, b2.start, b2.end);
  const flipScale  = interpolate(flipP, [0, 0.5, 1], [1, 0.02, 1]);   // 3-D flip via scaleX
  const wrongAlpha = interpolate(flipP, [0, 0.45], [1, 0]);
  const rightAlpha = interpolate(flipP, [0.55, 1], [0, 1]);

  // Answer rises from below centre while flip reveals it
  const answerY = interpolate(easeOut(frame, fps, b2.start + 0.3, b2.end), [0, 1], [180, 0]);

  // Source badge glow
  const badgeScale = interpolate(easeOut(frame, fps, b2.start + 0.6, b2.end), [0, 1], [0.3, 1]);

  // Scene fade in
  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  const label = onScreenText[0] ?? 'AI that KNOWS';

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        opacity: sceneOpacity,
        overflow: 'hidden',
        transform: `translateX(${shakeX}px)`,
      }}
    >
      {/* Subtle radial glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 900px 600px at 50% 40%, ${accentColor}12 0%, transparent 70%)`,
        }}
      />

      {/* ── WRONG STATE card (beats 0–1, first half of flip) ──────────── */}
      <AbsoluteFill
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transform: `translateY(${cardY}px) rotate(${cardRot}deg)`,
          opacity: wrongAlpha,
        }}
      >
        <div
          style={{
            width: 860,
            background: 'rgba(239,68,68,0.08)',
            border: '2px solid rgba(239,68,68,0.55)',
            borderRadius: 24,
            padding: '60px 72px',
            position: 'relative',
            transform: `scaleX(${flipScale})`,
            transformOrigin: '50% 50%',
          }}
        >
          {/* Wrong answer text */}
          <div
            style={{
              fontFamily: FONT,
              fontSize: 44,
              fontWeight: 700,
              color: 'rgba(255,255,255,0.75)',
              lineHeight: 1.4,
              textAlign: 'center',
            }}
          >
            "The Eiffel Tower was built in 1756."
          </div>

          {/* Strike-through line (draws left → right) */}
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: 36,
              height: 4,
              width: `${strikeW}%`,
              background: '#ef4444',
              borderRadius: 2,
              boxShadow: '0 0 12px rgba(239,68,68,0.7)',
              opacity: strikeP > 0 ? 1 : 0,
            }}
          />

          {/* Red X badge */}
          {strikeP > 0.3 && (
            <div
              style={{
                position: 'absolute',
                top: -28,
                right: -28,
                width: 72,
                height: 72,
                borderRadius: '50%',
                background: '#ef4444',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                opacity: xOpacity,
                boxShadow: '0 0 24px rgba(239,68,68,0.6)',
              }}
            >
              <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
                <path d="M10 10L26 26M26 10L10 26" stroke="#fff" strokeWidth="4" strokeLinecap="round"/>
              </svg>
            </div>
          )}
        </div>
      </AbsoluteFill>

      {/* ── CORRECT STATE (second half of flip, beat 2) ───────────────── */}
      <AbsoluteFill
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: rightAlpha,
          transform: `translateY(${answerY}px)`,
        }}
      >
        <div
          style={{
            width: 860,
            background: `linear-gradient(135deg, ${accent2}12, ${accentColor}12)`,
            border: `2px solid ${accent2}77`,
            borderRadius: 24,
            padding: '60px 72px',
            position: 'relative',
            transform: `scaleX(${flipScale < 0.5 ? flipScale * 2 : 1})`,
            transformOrigin: '50% 50%',
          }}
        >
          {/* Correct answer text */}
          <div
            style={{
              fontFamily: FONT,
              fontSize: 44,
              fontWeight: 700,
              color: '#ffffff',
              lineHeight: 1.4,
              textAlign: 'center',
              marginBottom: 28,
            }}
          >
            "The Eiffel Tower was built in 1889."
          </div>

          {/* Source badge */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
              transform: `scale(${badgeScale})`,
              transformOrigin: 'center',
            }}
          >
            <div
              style={{
                background: `${accent2}22`,
                border: `1.5px solid ${accent2}88`,
                borderRadius: 40,
                padding: '10px 28px',
                fontFamily: FONT,
                fontSize: 24,
                fontWeight: 700,
                color: accent2,
                boxShadow: `0 0 20px ${accent2}44`,
              }}
            >
              ✓ Sourced — Wikipedia / Eiffel Tower
            </div>
          </div>

          {/* Check badge */}
          <div
            style={{
              position: 'absolute',
              top: -28,
              right: -28,
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: accent2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 0 24px ${accent2}88`,
              transform: `scale(${badgeScale})`,
            }}
          >
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
              <path d="M8 18L15 25L28 11" stroke="#fff" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>
      </AbsoluteFill>

      {/* ── Scene label (top) ─────────────────────────────────────────────── */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'flex-start',
          paddingTop: 120,
          opacity: interpolate(frame, [6, 20], [0, 1], {extrapolateRight: 'clamp'}),
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: 26,
            fontWeight: 900,
            letterSpacing: 6,
            textTransform: 'uppercase',
            color: accentColor,
          }}
        >
          {label}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
