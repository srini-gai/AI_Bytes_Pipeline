/**
 * PipelineScene — Visual Director v3
 *
 * Shows the complete RAG pipeline flow as a connected system,
 * then reveals a "grounded answer" node that grows from the output.
 *
 * B0: pipeline nodes appear (user → retrieval → knowledge base)
 * B1: arrows draw connecting them
 * B2: LLM node appears with input connections
 * B3: grounded answer text grows from LLM output — source citations attach
 * B4: full pipeline glows — "complete" state
 *
 * Carry-in: grounded answer text (from TokenStreamScene)
 * Object for next scenes: pipeline diagram as context
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, MONO, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface PipelineSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  carryFrom?: string; // 'grounded answer text'
}

interface PNode {
  id:    string;
  x:     number;
  y:     number;
  r:     number;
  label: string;
  color: string;
  beat:  number; // which beat index reveals this node
}

export const PipelineScene: React.FC<PipelineSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 1.0};
  const b1 = beats[1] ?? {start: 1.0, end: 2.0};
  const b2 = beats[2] ?? {start: 2.0, end: 3.0};
  const b3 = beats[3] ?? {start: 3.0, end: 4.0};
  const b4 = beats[4] ?? {start: 4.0, end: 5.0};

  const P = [
    easeOut(frame, fps, b0.start, b0.end),
    linearProgress(frame, fps, b1.start, b1.end),
    easeOut(frame, fps, b2.start, b2.end),
    easeOut(frame, fps, b3.start, b3.end),
    linearProgress(frame, fps, b4.start, b4.end),
  ];

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  // Node positions — laid out across the canvas vertically
  const CX = 540;
  const nodes: PNode[] = [
    {id: 'user',    x: 120,  y: 400,  r: 64, label: 'User',           color: accentColor, beat: 0},
    {id: 'retrieve',x: 540,  y: 500,  r: 80, label: 'Retrieval',      color: accentColor, beat: 0},
    {id: 'kb',      x: 940,  y: 400,  r: 64, label: 'Knowledge base', color: accent2,     beat: 0},
    {id: 'llm',     x: 540,  y: 900,  r: 90, label: 'LLM',            color: accentColor, beat: 2},
    {id: 'answer',  x: 540,  y: 1380, r: 80, label: 'Answer',         color: accent2,     beat: 3},
  ];

  // Edges: [from, to, beat revealed]
  const edges: Array<[string, string, number]> = [
    ['user',     'retrieve', 1],
    ['kb',       'retrieve', 1],
    ['retrieve', 'llm',      2],
    ['llm',      'answer',   3],
  ];

  // Global glow on beat 4
  const glowP = P[4];

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
          background: `radial-gradient(ellipse 1000px 1200px at 50% 55%, ${accentColor}0a 0%, transparent 70%)`,
        }}
      />

      <svg viewBox="0 0 1080 1920" width={1080} height={1920}
        style={{position: 'absolute', inset: 0}}>

        {/* ── Edges ────────────────────────────────────────────────────── */}
        {edges.map(([fromId, toId, beatIdx]) => {
          const fromNode = nodes.find((n) => n.id === fromId)!;
          const toNode   = nodes.find((n) => n.id === toId)!;
          const edgeP = smoothstep(P[beatIdx]);
          if (edgeP < 0.01) return null;

          const dx = toNode.x - fromNode.x;
          const dy = toNode.y - fromNode.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const ux = dx / dist;
          const uy = dy / dist;
          const x1 = fromNode.x + ux * fromNode.r;
          const y1 = fromNode.y + uy * fromNode.r;
          const x2 = fromNode.x + dx * edgeP;
          const y2 = fromNode.y + dy * edgeP;
          const lineColor = beatIdx >= 3 ? accent2 : accentColor;

          return (
            <g key={`${fromId}-${toId}`}>
              <line x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={lineColor} strokeWidth={3}
                strokeDasharray="0"
                opacity={0.7 + glowP * 0.3}/>
              {/* Arrow head if edge complete */}
              {edgeP > 0.9 && (
                <circle cx={toNode.x - ux * toNode.r} cy={toNode.y - uy * toNode.r}
                  r={7} fill={lineColor} opacity={0.9}/>
              )}
            </g>
          );
        })}

        {/* ── Nodes ────────────────────────────────────────────────────── */}
        {nodes.map((node) => {
          const nodeP = smoothstep(P[node.beat]);
          if (nodeP < 0.01) return null;
          const glow = nodeP * (1 + glowP * 0.4);
          const fillAlpha = Math.round(nodeP * 0x18).toString(16).padStart(2, '0');
          const strokeAlpha = Math.round(nodeP * 0xff).toString(16).padStart(2, '0');

          return (
            <g key={node.id}
              transform={`scale(${0.6 + nodeP * 0.4}) translate(${node.x * (1 / (0.6 + nodeP * 0.4) - 1)}, ${node.y * (1 / (0.6 + nodeP * 0.4) - 1)})`}
              style={{transformOrigin: `${node.x}px ${node.y}px`}}
            >
              {/* Outer ring */}
              {glowP > 0.1 && (
                <circle cx={node.x} cy={node.y} r={node.r + 12}
                  fill="none" stroke={node.color} strokeWidth={2}
                  opacity={glowP * 0.4}/>
              )}
              <circle cx={node.x} cy={node.y} r={node.r}
                fill={`${node.color}${fillAlpha}`}
                stroke={`${node.color}${strokeAlpha}`}
                strokeWidth={node.id === 'llm' ? 3 : 2}/>
              <text x={node.x} y={node.y + 8} textAnchor="middle"
                fill="#fff" fontFamily={FONT}
                fontSize={node.id === 'llm' ? 26 : 20} fontWeight="700"
                opacity={nodeP}>
                {node.id === 'llm' ? 'LLM' : node.label.split(' ')[0]}
              </text>
              {node.id !== 'llm' && node.label.includes(' ') && (
                <text x={node.x} y={node.y + 32} textAnchor="middle"
                  fill="#fff" fontFamily={FONT} fontSize={16} fontWeight="600"
                  opacity={nodeP * 0.7}>
                  {node.label.split(' ').slice(1).join(' ')}
                </text>
              )}
            </g>
          );
        })}

        {/* ── Grounded answer detail (beat 3+) ─────────────────────────── */}
        {P[3] > 0.2 && (
          <g opacity={smoothstep(P[3])}>
            {/* Answer box */}
            <rect x={540 - 240} y={1380 + 90} width={480} height={130}
              rx={16} fill={`${accent2}12`} stroke={`${accent2}55`} strokeWidth={2}/>
            <text x={540} y={1420} textAnchor="middle"
              fill={accent2} fontFamily={MONO} fontSize={22} fontWeight="700">
              {onScreenText[0] ?? 'Grounded answer'}
            </text>
            {/* Source tag */}
            <rect x={380} y={1460} width={320} height={36}
              rx={18} fill={`${accent2}20`} stroke={`${accent2}66`} strokeWidth={1.5}
              opacity={smoothstep(interpolate(P[3], [0.5, 1], [0, 1], {extrapolateRight: 'clamp'}))}/>
            <text x={540} y={1485} textAnchor="middle"
              fill={accent2} fontFamily={FONT} fontSize={17} fontWeight="700"
              opacity={smoothstep(interpolate(P[3], [0.5, 1], [0, 1], {extrapolateRight: 'clamp'}))}>
              {onScreenText[1] ?? '✓ Verified from sources'}
            </text>
          </g>
        )}

        {/* ── "Complete" label (beat 4) ─────────────────────────────────── */}
        {glowP > 0.3 && (
          <text x={540} y={230} textAnchor="middle"
            fill={accentColor} fontFamily={FONT} fontSize={26} fontWeight="700"
            opacity={smoothstep(glowP)}>
            {onScreenText[2] ?? 'Complete RAG pipeline'}
          </text>
        )}
      </svg>
    </AbsoluteFill>
  );
};
