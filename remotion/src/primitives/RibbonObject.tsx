import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

interface RibbonToken {
  text: string;
  color: string;
  fabricated?: boolean;
}

interface RibbonObjectProps {
  activeBeat: SceneBeat;
  tokens: RibbonToken[];
  startPos: {x: number; y: number};
  endPos: {x: number; y: number};
  emissionRate?: number;
  tokenSize?: number;
  tokenSpacing?: number;
  showConnector?: boolean;
  artDirection?: ArtDirection;
  fps: number;
  durationInFrames: number;
}

export const RibbonObject: React.FC<RibbonObjectProps> = ({
  activeBeat,
  tokens,
  startPos,
  endPos,
  emissionRate = 2,
  tokenSize = 48,
  tokenSpacing = 12,
  showConnector = true,
  artDirection: ad,
  fps,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const bgColor = ad?.palette.bg ?? '#050510';
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.mono ?? '"JetBrains Mono", monospace';

  const startF = Math.round(activeBeat.start * fps);
  const endF = Math.round(activeBeat.end * fps);
  const elapsed = Math.max(0, frame - startF);
  const beatDur = endF - startF;

  if (frame < startF) return null;

  const N = tokens.length;
  const tokenW = tokenSize * 2.2;
  const totalWidth = N * (tokenW + tokenSpacing);
  const travelDist = endPos.x - startPos.x;
  const travelDistY = endPos.y - startPos.y;

  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden'}}>
      {showConnector && (
        <svg viewBox="0 0 1080 1920" width={1080} height={1920}
          style={{position: 'absolute', inset: 0}}>
          <line
            x1={startPos.x} y1={startPos.y}
            x2={startPos.x + travelDist * Math.min(1, elapsed / Math.max(1, beatDur))}
            y2={startPos.y + travelDistY * Math.min(1, elapsed / Math.max(1, beatDur))}
            stroke={`${textColor}15`}
            strokeWidth={2}
          />
        </svg>
      )}

      {tokens.map((tok, i) => {
        const emitFrame = startF + Math.round((i / Math.max(N - 1, 1)) * beatDur * 0.8);
        const tokElapsed = Math.max(0, frame - emitFrame);
        if (tokElapsed <= 0) return null;

        const entryP = Math.min(1, tokElapsed / 8);
        const travelP = Math.min(1, tokElapsed / Math.max(1, beatDur * 0.9));
        const ep = 1 - Math.pow(1 - travelP, 2);

        const x = startPos.x + i * (tokenW + tokenSpacing) * 0.6;
        const y = startPos.y + travelDistY * ep;

        return (
          <div key={i} style={{
            position: 'absolute',
            left: x - tokenW / 2,
            top: y - tokenSize / 2,
            width: tokenW,
            height: tokenSize,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: `${tok.color}28`,
            border: `2px solid ${tok.color}77`,
            borderRadius: 8,
            color: tok.color,
            fontFamily,
            fontSize: tokenSize * 0.45,
            fontWeight: 700,
            opacity: entryP,
            transform: `scale(${0.5 + entryP * 0.5})`,
          }}>
            {tok.text}
          </div>
        );
      })}
    </div>
  );
};
