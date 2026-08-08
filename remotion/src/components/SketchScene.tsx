import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {SketchEdge, SketchNode, SketchSpec} from '../types';

const FONT = 'Helvetica, Arial, sans-serif';
const BG = '#050510';

const NODE_DRAW = 20;   // frames to draw a node's outline
const NODE_GAP = 10;    // frames after draw — also the label fade-in duration
const NODE_SLOT = NODE_DRAW + NODE_GAP;

const EDGE_DRAW = 15;   // frames to draw an edge
const EDGE_LABEL_FADE = 10; // frames for the edge label to fade in after the edge completes
const EDGE_SLOT = EDGE_DRAW + EDGE_LABEL_FADE;

const CANVAS_W = 1080;
const CANVAS_H = 1920;
const DIAGRAM_TOP = 480;
const DIAGRAM_H = 1000;
const DIAGRAM_PADDING = 60;
const CURVE_OFFSET = 40; // perpendicular bezier control-point offset, px

const DEFAULT_NODE_W = 140;
const DEFAULT_NODE_H = 60;

interface SketchSceneProps {
  topic: string;
  sketchSpec: SketchSpec;
  accentColor: string;
  durationInFrames: number;
}

interface ScreenNode {
  node: SketchNode;
  cx: number;
  cy: number;
  hw: number;
  hh: number;
  pathD: string;
  pathLength: number;
}

function roundedRectPath(x: number, y: number, w: number, h: number, r: number): string {
  return `M ${x + r},${y} H ${x + w - r} A ${r},${r} 0 0 1 ${x + w},${y + r} V ${y + h - r} A ${r},${r} 0 0 1 ${x + w - r},${y + h} H ${x + r} A ${r},${r} 0 0 1 ${x},${y + h - r} V ${y + r} A ${r},${r} 0 0 1 ${x + r},${y} Z`;
}

function circlePath(cx: number, cy: number, r: number): string {
  return `M ${cx - r},${cy} A ${r},${r} 0 1 1 ${cx + r},${cy} A ${r},${r} 0 1 1 ${cx - r},${cy}`;
}

function diamondPath(cx: number, cy: number, hw: number, hh: number): string {
  return `M ${cx},${cy - hh} L ${cx + hw},${cy} L ${cx},${cy + hh} L ${cx - hw},${cy} Z`;
}

function buildScreenNode(node: SketchNode, offsetX: number, offsetY: number, scale: number): ScreenNode {
  const w = (node.width ?? DEFAULT_NODE_W) * scale;
  const h = (node.height ?? DEFAULT_NODE_H) * scale;
  const x = offsetX + node.x * scale;
  const y = offsetY + node.y * scale;
  const cx = x + w / 2;
  const cy = y + h / 2;

  if (node.shape === 'circle') {
    const r = w / 2;
    return {node, cx, cy, hw: r, hh: r, pathD: circlePath(cx, cy, r), pathLength: 2 * Math.PI * r};
  }
  if (node.shape === 'diamond') {
    const hw = w / 2;
    const hh = h / 2;
    const side = Math.hypot(hw, hh);
    return {node, cx, cy, hw, hh, pathD: diamondPath(cx, cy, hw, hh), pathLength: side * 4};
  }
  const rx = 8;
  const perimeter = 2 * (w + h) - 8 * rx + 2 * Math.PI * rx;
  return {node, cx, cy, hw: w / 2, hh: h / 2, pathD: roundedRectPath(x, y, w, h, rx), pathLength: perimeter};
}

// Distance from a shape's center to its boundary along a unit direction (ux, uy).
function boundaryDistance(shape: SketchNode['shape'], hw: number, hh: number, ux: number, uy: number): number {
  if (shape === 'circle') return hw;
  if (shape === 'diamond') {
    const denom = Math.abs(ux) / hw + Math.abs(uy) / hh;
    return denom === 0 ? 0 : 1 / denom;
  }
  const tx = ux !== 0 ? hw / Math.abs(ux) : Infinity;
  const ty = uy !== 0 ? hh / Math.abs(uy) : Infinity;
  return Math.min(tx, ty);
}

function cubicPoint(t: number, x0: number, y0: number, c1x: number, c1y: number, c2x: number, c2y: number, x1: number, y1: number) {
  const mt = 1 - t;
  const x = mt * mt * mt * x0 + 3 * mt * mt * t * c1x + 3 * mt * t * t * c2x + t * t * t * x1;
  const y = mt * mt * mt * y0 + 3 * mt * mt * t * c1y + 3 * mt * t * t * c2y + t * t * t * y1;
  return {x, y};
}

function cubicLength(x0: number, y0: number, c1x: number, c1y: number, c2x: number, c2y: number, x1: number, y1: number, segments = 40): number {
  let length = 0;
  let prev = {x: x0, y: y0};
  for (let i = 1; i <= segments; i++) {
    const pt = cubicPoint(i / segments, x0, y0, c1x, c1y, c2x, c2y, x1, y1);
    length += Math.hypot(pt.x - prev.x, pt.y - prev.y);
    prev = pt;
  }
  return length;
}

function wrapLabel(label: string, maxCharsPerLine = 14): string[] {
  if (label.length <= maxCharsPerLine) return [label];
  const words = label.split(' ');
  if (words.length === 1) return [label];
  let line1 = '';
  let i = 0;
  while (i < words.length) {
    const next = line1 ? `${line1} ${words[i]}` : words[i];
    if (next.length > maxCharsPerLine && line1) break;
    line1 = next;
    i++;
  }
  const line2 = words.slice(i).join(' ');
  return line2 ? [line1, line2] : [line1];
}

export const SketchScene: React.FC<SketchSceneProps> = ({topic, sketchSpec, accentColor}) => {
  const frame = useCurrentFrame();
  const {nodes, edges, title} = sketchSpec;

  // Fit the spec's coordinate space into the vertical canvas.
  const minX = Math.min(...nodes.map((n) => n.x));
  const minY = Math.min(...nodes.map((n) => n.y));
  const maxX = Math.max(...nodes.map((n) => n.x + (n.width ?? DEFAULT_NODE_W)));
  const maxY = Math.max(...nodes.map((n) => n.y + (n.height ?? DEFAULT_NODE_H)));
  const bboxW = Math.max(maxX - minX, 1);
  const bboxH = Math.max(maxY - minY, 1);
  const targetW = CANVAS_W - DIAGRAM_PADDING * 2;
  const targetH = DIAGRAM_H - DIAGRAM_PADDING * 2;
  const scale = Math.min(targetW / bboxW, targetH / bboxH, 1.6);
  const offsetX = (CANVAS_W - bboxW * scale) / 2 - minX * scale;
  const offsetY = DIAGRAM_TOP + (DIAGRAM_H - bboxH * scale) / 2 - minY * scale;

  const screenNodes = new Map<string, ScreenNode>();
  nodes.forEach((node) => screenNodes.set(node.id, buildScreenNode(node, offsetX, offsetY, scale)));

  const nodesEndFrame = nodes.length * NODE_SLOT;

  const titleOpacity = interpolate(frame, [5, 15], [0, 1], {extrapolateRight: 'clamp'});
  const titleText = title ?? topic;

  return (
    <AbsoluteFill style={{backgroundColor: BG}}>
      <div
        style={{
          position: 'absolute', top: 140, left: 0, right: 0,
          textAlign: 'center',
          opacity: titleOpacity,
          fontSize: 22, fontWeight: 700,
          color: '#ffffff',
          fontFamily: FONT,
          letterSpacing: 0.5,
          padding: '0 60px',
        }}
      >
        {titleText}
      </div>

      <svg
        style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%'}}
        viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
      >
        <defs>
          <marker id="sketch-arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto" markerUnits="userSpaceOnUse">
            <path d="M0,0 L8,4 L0,8 Z" fill={accentColor} />
          </marker>
        </defs>

        {edges.map((edge, i) => {
          const from = screenNodes.get(edge.from);
          const to = screenNodes.get(edge.to);
          if (!from || !to) return null;

          const start = nodesEndFrame + i * EDGE_SLOT;
          return (
            <EdgePath
              key={`${edge.from}-${edge.to}-${i}`}
              edge={edge}
              from={from}
              to={to}
              startFrame={start}
              frame={frame}
              accentColor={accentColor}
            />
          );
        })}

        {nodes.map((node, i) => {
          const screen = screenNodes.get(node.id);
          if (!screen) return null;
          const start = i * NODE_SLOT;
          const drawOffset = interpolate(
            frame,
            [start, start + NODE_DRAW],
            [screen.pathLength, 0],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
          );
          const labelOpacity = interpolate(
            frame,
            [start + NODE_DRAW, start + NODE_SLOT],
            [0, 1],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
          );
          const lines = wrapLabel(node.label);

          return (
            <React.Fragment key={node.id}>
              <path
                d={screen.pathD}
                fill="none"
                stroke={accentColor}
                strokeWidth={2}
                vectorEffect="non-scaling-stroke"
                strokeDasharray={screen.pathLength}
                strokeDashoffset={drawOffset}
              />
              <text
                x={screen.cx}
                y={screen.cy}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#ffffff"
                fontFamily={FONT}
                fontSize={16}
                opacity={labelOpacity}
              >
                {lines.map((line, li) => (
                  <tspan key={li} x={screen.cx} dy={li === 0 ? (lines.length > 1 ? -8 : 0) : 16}>
                    {line}
                  </tspan>
                ))}
              </text>
            </React.Fragment>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};

interface EdgePathProps {
  edge: SketchEdge;
  from: ScreenNode;
  to: ScreenNode;
  startFrame: number;
  frame: number;
  accentColor: string;
}

const EdgePath: React.FC<EdgePathProps> = ({edge, from, to, startFrame, frame, accentColor}) => {
  const dx = to.cx - from.cx;
  const dy = to.cy - from.cy;
  const dist = Math.hypot(dx, dy) || 1;
  const ux = dx / dist;
  const uy = dy / dist;

  const startDist = boundaryDistance(from.node.shape, from.hw, from.hh, ux, uy);
  const endDist = boundaryDistance(to.node.shape, to.hw, to.hh, -ux, -uy);

  const x0 = from.cx + ux * startDist;
  const y0 = from.cy + uy * startDist;
  const x1 = to.cx - ux * endDist;
  const y1 = to.cy - uy * endDist;

  const perpX = -uy * CURVE_OFFSET;
  const perpY = ux * CURVE_OFFSET;
  const c1x = x0 + (x1 - x0) / 3 + perpX;
  const c1y = y0 + (y1 - y0) / 3 + perpY;
  const c2x = x0 + ((x1 - x0) * 2) / 3 + perpX;
  const c2y = y0 + ((y1 - y0) * 2) / 3 + perpY;

  const pathD = `M ${x0},${y0} C ${c1x},${c1y} ${c2x},${c2y} ${x1},${y1}`;
  const pathLength = cubicLength(x0, y0, c1x, c1y, c2x, c2y, x1, y1);

  const drawOffset = interpolate(
    frame,
    [startFrame, startFrame + EDGE_DRAW],
    [pathLength, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const complete = frame >= startFrame + EDGE_DRAW;

  const labelOpacity = interpolate(
    frame,
    [startFrame + EDGE_DRAW, startFrame + EDGE_DRAW + EDGE_LABEL_FADE],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const mid = cubicPoint(0.5, x0, y0, c1x, c1y, c2x, c2y, x1, y1);

  return (
    <>
      <path
        d={pathD}
        fill="none"
        stroke={accentColor}
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
        strokeDasharray={pathLength}
        strokeDashoffset={drawOffset}
        markerEnd={complete ? 'url(#sketch-arrowhead)' : undefined}
      />
      {edge.label && (
        <text
          x={mid.x - perpY * 0.35}
          y={mid.y + perpX * 0.35}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#ffffff"
          fontFamily={FONT}
          fontSize={12}
          opacity={labelOpacity}
        >
          {edge.label}
        </text>
      )}
    </>
  );
};
