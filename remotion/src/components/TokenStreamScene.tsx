/**
 * TokenStreamScene — Visual Director v3
 *
 * The LLM processes tokens, building the answer character-by-character.
 *
 * B0: token stream flows into LLM (context window → LLM input pipe)
 * B1: LLM "thinking" — gears spin, activation waves pulse through
 * B2: answer tokens stream OUT of LLM, letters materialize one by one
 *
 * Carry-in: context window rectangle (arrives compressed from previous scene)
 * Carry-out: grounded answer text (for PipelineScene)
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, MONO, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface TokenStreamSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  carryFrom?: string; // 'context window rectangle'
}

const ANSWER_TEXT = 'Answer grounded in your data';

export const TokenStreamScene: React.FC<TokenStreamSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 1.5};
  const b1 = beats[1] ?? {start: 1.5, end: 3.0};
  const b2 = beats[2] ?? {start: 3.0, end: 5.0};

  // ── Beat 0: input pipe from context window ───────────────────────────────
  const pipeP  = easeOut(frame, fps, b0.start, b0.end);
  const inputP = linearProgress(frame, fps, b0.start, b0.end);

  // ── Beat 1: LLM internal processing ─────────────────────────────────────
  const thinkP = linearProgress(frame, fps, b1.start, b1.end);

  // ── Beat 2: output tokens stream out ────────────────────────────────────
  const outP   = linearProgress(frame, fps, b2.start, b2.end);

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  // Layout
  const LLM_X = 540;
  const LLM_Y = 820;
  const LLM_R = 120;

  const CTX_X = 100;  // context window (carry-in) centre x
  const CTX_Y = LLM_Y;

  const OUT_X = LLM_X + LLM_R + 40;
  const OUT_Y = LLM_Y;

  // How many input tokens are visible (flows in during beat 0)
  const tokenCountIn = Math.floor(inputP * 12);

  // How many answer chars revealed (beat 2)
  const answerLabel = onScreenText[0] ?? ANSWER_TEXT;
  const revealLen   = Math.floor(smoothstep(outP) * answerLabel.length);
  const revealedText = answerLabel.slice(0, revealLen);

  // Gear rotation (beat 1)
  const gearRot = thinkP * 360 * 2;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        opacity: sceneOpacity,
        overflow: 'hidden',
      }}
    >
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 900px 600px at 50% 43%, ${accentColor}0d 0%, transparent 65%)`,
        }}
      />

      <svg viewBox="0 0 1080 1920" width={1080} height={1920}
        style={{position: 'absolute', inset: 0}}>

        {/* ── Context window (carry-in, compressed form) ─────────────────── */}
        <g opacity={interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'})}>
          <rect x={CTX_X - 60} y={CTX_Y - 90} width={120} height={180}
            rx={10} fill={`${accentColor}10`} stroke={`${accentColor}55`} strokeWidth={2}/>
          <text x={CTX_X} y={CTX_Y - 110} textAnchor="middle"
            fill={accentColor} fontFamily={FONT} fontSize={18} fontWeight="700">
            Context
          </text>
        </g>

        {/* ── Input pipe (beat 0): tokens flowing from context → LLM ─────── */}
        {/* pipe track */}
        <line x1={CTX_X + 60} y1={LLM_Y}
              x2={LLM_X - LLM_R} y2={LLM_Y}
          stroke={`${accentColor}33`} strokeWidth={3} strokeDasharray="6 5"
          opacity={pipeP}/>

        {/* moving token chips on the pipe */}
        {Array.from({length: tokenCountIn}, (_, i) => {
          const progress = ((inputP * 10) - i) / 10;
          if (progress < 0 || progress > 1) return null;
          const tx = CTX_X + 60 + progress * (LLM_X - LLM_R - CTX_X - 60);
          return (
            <g key={i} opacity={0.9}>
              <rect x={tx - 22} y={LLM_Y - 14} width={44} height={28}
                rx={6} fill={`${accentColor}22`} stroke={accentColor} strokeWidth={1.5}/>
              <text x={tx} y={LLM_Y + 6} textAnchor="middle"
                fill={accentColor} fontFamily={MONO} fontSize={13} fontWeight="700">
                tok
              </text>
            </g>
          );
        })}

        {/* ── LLM circle ────────────────────────────────────────────────── */}
        {/* outer ring animates with processing */}
        <circle cx={LLM_X} cy={LLM_Y} r={LLM_R + 20}
          fill="none" stroke={accentColor}
          strokeWidth={2} strokeDasharray="12 8"
          opacity={0.3 + thinkP * 0.4}
          transform={`rotate(${gearRot}, ${LLM_X}, ${LLM_Y})`}/>

        {/* body */}
        <circle cx={LLM_X} cy={LLM_Y} r={LLM_R}
          fill={`${accentColor}${Math.round((0.08 + thinkP * 0.12) * 255).toString(16).padStart(2, '0')}`}
          stroke={accentColor} strokeWidth={3}/>

        {/* internal activation waves (beat 1) */}
        {thinkP > 0.05 && Array.from({length: 3}, (_, w) => {
          const waveP = interpolate(thinkP, [w * 0.2, w * 0.2 + 0.6], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });
          const wR = LLM_R * 0.3 + waveP * LLM_R * 0.6;
          return (
            <circle key={w} cx={LLM_X} cy={LLM_Y} r={wR}
              fill="none" stroke={accentColor} strokeWidth={1.5}
              opacity={(1 - waveP) * 0.5}/>
          );
        })}

        {/* "LLM" text */}
        <text x={LLM_X} y={LLM_Y + 10} textAnchor="middle"
          fill="#fff" fontFamily={FONT} fontSize={28} fontWeight="700">
          LLM
        </text>

        {/* ── Output pipe (beat 2): tokens stream out right ─────────────── */}
        {outP > 0 && (
          <>
            <line x1={LLM_X + LLM_R} y1={LLM_Y}
                  x2={LLM_X + LLM_R + 60} y2={LLM_Y}
              stroke={`${accent2}88`} strokeWidth={3}
              opacity={smoothstep(outP) * 0.8}/>

            {/* Answer text streaming out */}
            <rect x={LLM_X + LLM_R + 50} y={LLM_Y - 100} width={380} height={200}
              rx={16} fill={`${accent2}0e`} stroke={`${accent2}44`} strokeWidth={2}
              opacity={smoothstep(outP)}/>
            <text
              x={LLM_X + LLM_R + 65}
              y={LLM_Y - 20}
              fill={accent2}
              fontFamily={MONO}
              fontSize={24}
              fontWeight="700"
              opacity={smoothstep(outP)}
            >
              {revealedText}
              {/* Cursor blink */}
              <tspan
                opacity={Math.floor(frame / 15) % 2 === 0 ? 1 : 0}
                fill={accent2}
              >▌</tspan>
            </text>

            <text x={LLM_X + LLM_R + 65 + 190} y={LLM_Y + 70} textAnchor="middle"
              fill={accent2} fontFamily={FONT} fontSize={18} fontWeight="700"
              opacity={smoothstep(interpolate(outP, [0.6, 1], [0, 1], {extrapolateRight: 'clamp'}))}>
              {onScreenText[1] ?? '+ source citations'}
            </text>
          </>
        )}

        {/* ── Processing label (beat 1) ─────────────────────────────────── */}
        {thinkP > 0 && outP < 0.3 && (
          <text x={LLM_X} y={LLM_Y + LLM_R + 50} textAnchor="middle"
            fill={accentColor} fontFamily={FONT} fontSize={22} fontWeight="700"
            opacity={smoothstep(thinkP) * (1 - smoothstep(outP))}>
            Processing…
          </text>
        )}
      </svg>
    </AbsoluteFill>
  );
};
