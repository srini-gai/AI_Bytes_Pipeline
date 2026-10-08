import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

interface CardConfig {
  label: string;
  sublabel?: string;
  color?: string;
  icon?: string;
}

interface CardFanProps {
  activeBeat: SceneBeat;
  cards: CardConfig[];
  origin?: {x: number; y: number};
  cardWidth?: number;
  cardHeight?: number;
  spreadAngle?: number;
  holdAll?: boolean;
  artDirection?: ArtDirection;
  fps: number;
  durationInFrames: number;
}

export const CardFan: React.FC<CardFanProps> = ({
  activeBeat,
  cards,
  origin,
  cardWidth = 300,
  cardHeight = 420,
  spreadAngle = 12,
  holdAll = false,
  artDirection: ad,
  fps,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const ox = origin?.x ?? 540;
  const oy = origin?.y ?? 800;

  const bgColor = ad?.palette.bg ?? '#050510';
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.font ?? '-apple-system, sans-serif';
  const surfaceBg = ad?.palette.surface ?? '#1a1a2e';

  const startF = Math.round(activeBeat.start * fps);
  const endF = Math.round(activeBeat.end * fps);

  const fanP = interpolate(frame, [startF, endF], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const easedFan = 1 - Math.pow(1 - fanP, 3);

  if (frame < startF) return null;

  const N = cards.length;
  const totalSpread = (N - 1) * spreadAngle;

  return (
    <svg viewBox="0 0 1080 1920" width={1080} height={1920}
      style={{position: 'absolute', inset: 0}}>
      {cards.map((card, i) => {
        const angle = -totalSpread / 2 + i * spreadAngle;
        const currentAngle = angle * easedFan;
        const offsetX = (i - (N - 1) / 2) * (cardWidth * 0.35) * easedFan;
        const offsetY = Math.abs(i - (N - 1) / 2) * 30 * easedFan;
        const cardColor = card.color ?? ad?.palette.primary ?? '#a78bfa';

        const entryDelay = i * 4;
        const cardP = interpolate(frame, [startF + entryDelay, startF + entryDelay + 10], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });

        return (
          <g key={i}
            transform={`translate(${ox + offsetX}, ${oy + offsetY}) rotate(${currentAngle})`}
            opacity={cardP}>
            <rect
              x={-cardWidth / 2} y={-cardHeight / 2}
              width={cardWidth} height={cardHeight}
              fill={surfaceBg} stroke={`${cardColor}66`} strokeWidth={2}
              rx={16}
            />

            <line
              x1={-cardWidth / 2 + 20} y1={-cardHeight / 2 + 60}
              x2={cardWidth / 2 - 20} y2={-cardHeight / 2 + 60}
              stroke={`${cardColor}33`} strokeWidth={1}
            />

            {card.icon && (
              <text x={0} y={-cardHeight / 2 + 44} textAnchor="middle"
                fill={cardColor} fontSize={28}>
                {card.icon}
              </text>
            )}

            <text x={0} y={-cardHeight / 2 + (card.icon ? 95 : 44)} textAnchor="middle"
              fill={textColor} fontFamily={fontFamily} fontSize={26} fontWeight={700}>
              {card.label}
            </text>

            {card.sublabel && (
              <text x={0} y={-cardHeight / 2 + 130} textAnchor="middle"
                fill={`${textColor}66`} fontFamily={fontFamily} fontSize={16} fontWeight={500}>
                {card.sublabel}
              </text>
            )}

            {/* Document-like lines for visual density */}
            {[0, 1, 2].map(j => (
              <rect key={j}
                x={-cardWidth / 2 + 30} y={cardHeight / 2 - 140 + j * 32}
                width={cardWidth - 60 - j * 40} height={8}
                fill={`${textColor}15`} rx={4}
              />
            ))}
          </g>
        );
      })}
    </svg>
  );
};
