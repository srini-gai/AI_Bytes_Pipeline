/**
 * NetworkBuildScene — Visual Director v3
 *
 * Nodes appear and edges connect them, building a graph live.
 * B0: nodes appear (staggered)
 * B1: edges draw between connected pairs
 * B2: cluster highlight — community reveals itself
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface NetworkBuildSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
}

const NODES = [
  {id: 0, x: 540,  y: 720,  cluster: 0},
  {id: 1, x: 280,  y: 580,  cluster: 0},
  {id: 2, x: 800,  y: 580,  cluster: 1},
  {id: 3, x: 200,  y: 880,  cluster: 0},
  {id: 4, x: 880,  y: 880,  cluster: 1},
  {id: 5, x: 400,  y: 1100, cluster: 2},
  {id: 6, x: 680,  y: 1100, cluster: 2},
  {id: 7, x: 160,  y: 640,  cluster: 0},
  {id: 8, x: 920,  y: 640,  cluster: 1},
];
const EDGES = [
  [0,1],[0,2],[1,3],[2,4],[0,5],[0,6],[1,7],[2,8],[5,6],[3,7],[4,8],
];

export const NetworkBuildScene: React.FC<NetworkBuildSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const b0 = beats[0] ?? {start: 0,   end: 2.0};
  const b1 = beats[1] ?? {start: 2.0, end: 4.0};
  const b2 = beats[2] ?? {start: 4.0, end: 5.5};

  const nodeP    = linearProgress(frame, fps, b0.start, b0.end);
  const edgeP    = linearProgress(frame, fps, b1.start, b1.end);
  const clusterP = easeOut(frame, fps, b2.start, b2.end);

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  const clusterColors = [accentColor, accent2, '#f59e0b'];

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity, overflow: 'hidden'}}>
      <svg viewBox="0 0 1080 1920" width={1080} height={1920} style={{position:'absolute',inset:0}}>

        {/* Edges */}
        {EDGES.map(([a, b], i) => {
          const segP = smoothstep(interpolate(edgeP, [i / EDGES.length * 0.7, i / EDGES.length * 0.7 + 0.35], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          }));
          if (segP < 0.01) return null;
          const na = NODES[a], nb = NODES[b];
          const ex = na.x + (nb.x - na.x) * segP;
          const ey = na.y + (nb.y - na.y) * segP;
          const clA = NODES[a].cluster;
          const clusterHighlight = clusterP > 0.1 && clA === NODES[b].cluster;
          return (
            <line key={i} x1={na.x} y1={na.y} x2={ex} y2={ey}
              stroke={clusterHighlight ? clusterColors[clA] : `${accentColor}55`}
              strokeWidth={clusterHighlight ? 3 : 1.5}
              opacity={clusterHighlight ? 0.9 : 0.6}/>
          );
        })}

        {/* Nodes */}
        {NODES.map((node, i) => {
          const np = smoothstep(interpolate(nodeP, [i / NODES.length * 0.6, i / NODES.length * 0.6 + 0.35], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          }));
          if (np < 0.01) return null;
          const isHighlighted = clusterP > 0.1;
          const col = isHighlighted ? clusterColors[node.cluster] : accentColor;
          return (
            <circle key={node.id} cx={node.x} cy={node.y} r={28 * np}
              fill={`${col}22`} stroke={col} strokeWidth={2.5} opacity={np}/>
          );
        })}

        {/* Label */}
        {clusterP > 0.3 && (
          <text x={540} y={1350} textAnchor="middle"
            fill={accentColor} fontFamily={FONT} fontSize={26} fontWeight="700"
            opacity={smoothstep(clusterP)}>
            {onScreenText[0] ?? 'Clusters emerge'}
          </text>
        )}
      </svg>
    </AbsoluteFill>
  );
};
