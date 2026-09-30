/**
 * CodeExecutionScene — Visual Director v3
 *
 * Code lines appear token-by-token, then execute — output appears.
 * B0: code lines type out (each line its own beat-window)
 * B1: "run" highlight sweep — execution bar moves down
 * B2: output panel slides up with result
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, MONO, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface CodeExecutionSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
}

const CODE_LINES = [
  {text: 'query = "What is RAG?"',       indent: 0},
  {text: 'docs  = retriever.get(query)',  indent: 0},
  {text: 'ctx   = build_context(docs)',   indent: 0},
  {text: 'answer = llm.generate(',        indent: 0},
  {text: '  prompt=ctx, query=query',    indent: 1},
  {text: ')',                             indent: 0},
];

export const CodeExecutionScene: React.FC<CodeExecutionSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 2.5};
  const b1 = beats[1] ?? {start: 2.5, end: 3.8};
  const b2 = beats[2] ?? {start: 3.8, end: 5.5};

  const typeP   = linearProgress(frame, fps, b0.start, b0.end);
  const runP    = easeOut(frame, fps, b1.start, b1.end);
  const outputP = easeOut(frame, fps, b2.start, b2.end);

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  const LINE_H = 52;
  const CODE_X = 80;
  const CODE_Y = 500;
  const CODE_W = 920;
  const TOTAL_CHARS = CODE_LINES.reduce((a, l) => a + l.text.length, 0);
  let charsSoFar = 0;

  const execLineIdx = Math.floor(runP * CODE_LINES.length);
  const resultText = onScreenText[0] ?? '"RAG grounds LLM answers in data"';

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity, overflow: 'hidden'}}>
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 800px 600px at 50% 40%, ${accentColor}0a 0%, transparent 65%)`,
      }}/>

      {/* Code panel */}
      <div style={{
        position: 'absolute',
        left: CODE_X,
        top: CODE_Y,
        width: CODE_W,
        background: '#0a0a20',
        border: `1.5px solid ${accentColor}33`,
        borderRadius: 16,
        padding: '28px 32px',
        fontFamily: MONO,
        overflow: 'hidden',
      }}>
        {/* Execution highlight bar */}
        {runP > 0.01 && (
          <div style={{
            position: 'absolute',
            left: 0,
            top: 28 + execLineIdx * LINE_H - 4,
            width: '100%',
            height: LINE_H,
            background: `${accentColor}18`,
            borderLeft: `4px solid ${accentColor}`,
          }}/>
        )}

        {CODE_LINES.map((line, i) => {
          const lineChars  = line.text.length;
          const lineStart  = charsSoFar / TOTAL_CHARS;
          const lineEnd    = (charsSoFar + lineChars) / TOTAL_CHARS;
          charsSoFar += lineChars;

          const lineP = interpolate(typeP, [lineStart, lineEnd], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });
          const visLen = Math.floor(lineP * lineChars);
          const isActive = i === execLineIdx && runP > 0;

          return (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'center',
              height: LINE_H,
              paddingLeft: line.indent * 32,
            }}>
              {/* Line number */}
              <span style={{
                color: `${accentColor}44`,
                fontSize: 18,
                marginRight: 24,
                minWidth: 28,
                textAlign: 'right',
              }}>
                {i + 1}
              </span>
              <span style={{
                color: isActive ? '#fff' : accentColor,
                fontSize: 22,
                fontWeight: 600,
                opacity: lineP > 0 ? 1 : 0,
              }}>
                {line.text.slice(0, visLen)}
                {lineP < 1 && lineP > 0 && (
                  <span style={{
                    opacity: Math.floor(frame / 12) % 2 === 0 ? 1 : 0,
                    color: accent2,
                  }}>|</span>
                )}
              </span>
            </div>
          );
        })}
      </div>

      {/* Output panel slides up (beat 2) */}
      <div style={{
        position: 'absolute',
        left: CODE_X,
        top: CODE_Y + CODE_LINES.length * LINE_H + 80 + 68,
        width: CODE_W,
        background: `${accent2}0e`,
        border: `2px solid ${accent2}55`,
        borderRadius: 16,
        padding: '24px 32px',
        opacity: smoothstep(outputP),
        transform: `translateY(${interpolate(outputP, [0, 1], [60, 0])}px)`,
      }}>
        <div style={{
          fontFamily: FONT,
          fontSize: 18,
          fontWeight: 700,
          color: accent2,
          marginBottom: 12,
          letterSpacing: 3,
          textTransform: 'uppercase',
        }}>
          Output
        </div>
        <div style={{
          fontFamily: MONO,
          fontSize: 24,
          fontWeight: 700,
          color: '#fff',
          lineHeight: 1.5,
        }}>
          {resultText}
        </div>
      </div>
    </AbsoluteFill>
  );
};
