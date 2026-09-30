/**
 * TokenStreamScene — Visual Director v3.1
 *
 * LLM is large (r=280), centred vertically on the canvas.
 * Context block is a tall rect on the LEFT side, from top of screen down.
 * Answer streams OUT to the right, building bottom-to-top (large text).
 *
 * v3.1 changes:
 * - LLM_R = 280 (was 120) — dominant and central
 * - LLM centred at canvas mid-point (540, 960) — uses full canvas
 * - Context block is 200×600 on the left, LLM right side → answer right side
 * - Answer text is 62px typewriter, builds from top to bottom of output panel
 * - Camera zooms in on LLM orb during processing beat (close-up)
 * - Action spans full vertical canvas, not a 200px strip
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
  carryFrom?: string;
}

const ANSWER_LINES = [
  'Answer grounded',
  'in your data',
  '+ citations',
];

export const TokenStreamScene: React.FC<TokenStreamSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 1.5}; // context flows in, LLM receives
  const b1 = beats[1] ?? {start: 1.5, end: 3.2}; // LLM processing (camera zoom)
  const b2 = beats[2] ?? {start: 3.2, end: 5.0}; // answer streams out

  // ── Animation ─────────────────────────────────────────────────────────────
  const pipeP   = easeOut(frame, fps, b0.start, b0.end);
  const thinkP  = linearProgress(frame, fps, b1.start, b1.end);
  const outP    = linearProgress(frame, fps, b2.start, b2.end);

  // Camera: zoom into LLM during processing, pull back as answer streams out
  const zoomIn  = easeOut(frame, fps, b1.start, b1.start + 0.8);
  const zoomOut = easeOut(frame, fps, b2.start, b2.start + 0.8);
  const camScale = interpolate(zoomIn, [0, 1], [1, 1.35])
                 * interpolate(zoomOut, [0, 1], [1, 0.82]);

  // ── Layout ─────────────────────────────────────────────────────────────────
  const LLM_CX = 540;
  const LLM_CY = 960;   // dead centre of 1920px canvas
  const LLM_R  = 280;

  // Context block on left
  const CTX_X = 30;
  const CTX_Y = LLM_CY - 380;
  const CTX_W = 180;
  const CTX_H = 760;

  // Output panel on right
  const OUT_X = LLM_CX + LLM_R + 40;
  const OUT_W = 1080 - OUT_X - 30;
  const OUT_Y = LLM_CY - 340;

  // Token particle trail (beat 0: context→LLM)
  const tokenCount = Math.floor(pipeP * 14);
  const gearRot = thinkP * 360 * 3;

  // Answer text reveal (beat 2)
  const totalAnswerChars = ANSWER_LINES.join('\n').length;
  const revealedChars = Math.floor(smoothstep(outP) * totalAnswerChars);

  // Build revealed lines from char count
  let charsLeft = revealedChars;
  const revealedLines = ANSWER_LINES.map(line => {
    if (charsLeft <= 0) return '';
    const shown = line.slice(0, charsLeft);
    charsLeft -= line.length;
    return shown;
  });

  return (
    <AbsoluteFill style={{backgroundColor: BG, overflow: 'hidden'}}>
      {/* Radial glow centred on LLM */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 700px 700px at ${LLM_CX}px ${LLM_CY}px,
          ${accentColor}18 0%, transparent 65%)`,
      }}/>

      <svg
        viewBox="0 0 1080 1920"
        width={1080}
        height={1920}
        style={{
          position: 'absolute', inset: 0,
          transform: `scale(${camScale})`,
          transformOrigin: `${LLM_CX}px ${LLM_CY}px`,
        }}
      >
        {/* ── Context block (carry-in) — left side, tall ──────────────────── */}
        <g opacity={smoothstep(pipeP)}>
          {/* Tall rect */}
          <rect x={CTX_X} y={CTX_Y} width={CTX_W} height={CTX_H}
            rx={16}
            fill={`${accentColor}10`} stroke={`${accentColor}66`} strokeWidth={2.5}/>
          {/* Label */}
          <text x={CTX_X + CTX_W / 2} y={CTX_Y - 18}
            textAnchor="middle"
            fill={accentColor} fontFamily={FONT} fontSize={26} fontWeight="700">
            Context
          </text>
          {/* Lines */}
          {Array.from({length: 8}, (_, l) => (
            <rect key={l}
              x={CTX_X + 14} y={CTX_Y + 28 + l * 80}
              width={CTX_W - 28 - (l % 3 === 2 ? 40 : 0)}
              height={12} rx={6}
              fill={`${accentColor}40`}
            />
          ))}
        </g>

        {/* ── Input pipe (beat 0): token chips flow right toward LLM ──────── */}
        <line x1={CTX_X + CTX_W} y1={LLM_CY}
              x2={LLM_CX - LLM_R} y2={LLM_CY}
          stroke={`${accentColor}33`} strokeWidth={3} strokeDasharray="8 6"
          opacity={smoothstep(pipeP)}/>

        {Array.from({length: tokenCount}, (_, i) => {
          const t = ((pipeP * 12) - i) / 12;
          if (t < 0 || t > 1) return null;
          const tx = (CTX_X + CTX_W) + t * (LLM_CX - LLM_R - CTX_X - CTX_W);
          return (
            <g key={i}>
              <rect x={tx - 28} y={LLM_CY - 18} width={56} height={36}
                rx={8} fill={`${accentColor}22`} stroke={accentColor} strokeWidth={1.5}/>
              <text x={tx} y={LLM_CY + 6} textAnchor="middle"
                fill={accentColor} fontFamily={MONO} fontSize={14} fontWeight="700">
                tok
              </text>
            </g>
          );
        })}

        {/* ── LLM orb — large, dominant ───────────────────────────────────── */}
        {/* Processing rings (beat 1) */}
        {thinkP > 0 && Array.from({length: 4}, (_, w) => {
          const wp = interpolate(thinkP, [w * 0.15, w * 0.15 + 0.7], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });
          const wR = LLM_R * 0.3 + wp * LLM_R * 0.8;
          return (
            <circle key={w} cx={LLM_CX} cy={LLM_CY} r={wR}
              fill="none" stroke={accentColor} strokeWidth={2}
              opacity={(1 - wp) * 0.5}/>
          );
        })}

        {/* Outer dashed ring */}
        <circle cx={LLM_CX} cy={LLM_CY} r={LLM_R + 30}
          fill="none" stroke={accentColor} strokeWidth={1.5}
          strokeDasharray="20 10" opacity={0.2 + thinkP * 0.4}
          transform={`rotate(${gearRot}, ${LLM_CX}, ${LLM_CY})`}/>

        {/* Body */}
        <circle cx={LLM_CX} cy={LLM_CY} r={LLM_R}
          fill={`${accentColor}${Math.round((0.08 + thinkP * 0.14) * 255).toString(16).padStart(2, '0')}`}
          stroke={accentColor} strokeWidth={4}/>

        {/* "LLM" label */}
        <text x={LLM_CX} y={LLM_CY + 20} textAnchor="middle"
          fill="#fff" fontFamily={FONT} fontSize={68} fontWeight="900">
          LLM
        </text>

        {/* "Processing…" during b1 */}
        {thinkP > 0.1 && outP < 0.2 && (
          <text x={LLM_CX} y={LLM_CY + LLM_R + 50} textAnchor="middle"
            fill={accentColor} fontFamily={FONT} fontSize={30} fontWeight="700"
            opacity={smoothstep(thinkP) * (1 - smoothstep(outP * 5))}>
            Processing context…
          </text>
        )}

        {/* ── Output pipe (beat 2) ─────────────────────────────────────────── */}
        {outP > 0 && (
          <>
            <line x1={LLM_CX + LLM_R} y1={LLM_CY}
                  x2={OUT_X + 10} y2={LLM_CY}
              stroke={`${accent2}88`} strokeWidth={3}
              opacity={smoothstep(outP)}/>

            {/* Output panel — full height on right side */}
            <rect x={OUT_X} y={OUT_Y} width={OUT_W} height={680}
              rx={18}
              fill={`${accent2}0e`} stroke={`${accent2}55`} strokeWidth={2.5}
              opacity={smoothstep(outP)}/>

            {/* Answer text streams in line by line */}
            {revealedLines.map((line, li) => (
              <text key={li}
                x={OUT_X + 22}
                y={OUT_Y + 70 + li * 120}
                fill={accent2}
                fontFamily={MONO}
                fontSize={52}
                fontWeight="800"
                opacity={smoothstep(outP)}
              >
                {line}
                {/* Cursor blink on the last non-empty line */}
                {li === revealedLines.filter(l => l.length > 0).length - 1 && (
                  <tspan
                    opacity={Math.floor(frame / 12) % 2 === 0 ? 1 : 0}
                    fill={accent2}>▌</tspan>
                )}
              </text>
            ))}

            {/* Source citation badge (appears after text fully revealed) */}
            {outP > 0.75 && (
              <g opacity={smoothstep(interpolate(outP, [0.75, 1], [0, 1], {extrapolateRight: 'clamp'}))}>
                <rect x={OUT_X + 10} y={OUT_Y + 480} width={OUT_W - 20} height={60}
                  rx={12} fill={`${accent2}22`} stroke={`${accent2}66`} strokeWidth={1.5}/>
                <text x={OUT_X + 32} y={OUT_Y + 520}
                  fill={accent2} fontFamily={FONT} fontSize={26} fontWeight="700">
                  ✓ {onScreenText[1] ?? '+ source citations'}
                </text>
              </g>
            )}
          </>
        )}
      </svg>
    </AbsoluteFill>
  );
};
