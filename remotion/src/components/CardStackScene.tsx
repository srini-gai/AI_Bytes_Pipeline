/**
 * CardStackScene — Visual Director v3
 *
 * A deck of cards fans out, front card zooms for detail, others recede.
 * B0: cards fan from a stack (each slides out from behind)
 * B1: front card enlarges — detail text appears
 * B2: remaining cards fly off — front card stays
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

interface CardStackSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  artDirection?: ArtDirection;
}

export const CardStackScene: React.FC<CardStackSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
  artDirection: ad,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const bgColor = ad?.palette.bg ?? BG;
  const fontFamily = ad?.typography.font ?? FONT;
  const useGlow = ad?.depth.use_glow ?? true;
  const themedItemColors = ad?.item_colors ?? undefined;

  const b0 = beats[0] ?? {start: 0,   end: 1.5};
  const b1 = beats[1] ?? {start: 1.5, end: 3.0};
  const b2 = beats[2] ?? {start: 3.0, end: 5.0};

  const fanP    = easeOut(frame, fps, b0.start, b0.end);
  const zoomP   = easeOut(frame, fps, b1.start, b1.end);
  const flyP    = easeOut(frame, fps, b2.start, b2.end);

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  const CX = 540;
  const CY = 960;
  const CARD_W = 380;
  const CARD_H = 520;

  // Derive card labels and summary from onScreenText.
  // Convention: when onScreenText has content, the last item is the summary/subtitle
  // (shown on the front card when zoomed), all preceding items are card labels.
  // Falls back to generic defaults only when onScreenText is empty.
  const DEFAULT_LABELS = ['Key concept', 'Example', 'Trade-off', 'Best practice', 'Summary'];
  const hasContent = onScreenText.length >= 2; // at least 1 card + 1 summary
  const cardLabels = hasContent ? onScreenText.slice(0, -1) : DEFAULT_LABELS;
  const summaryText = hasContent ? onScreenText[onScreenText.length - 1] : 'Core insight';
  const N = cardLabels.length;
  const labels = cardLabels;
  const BASE_COLORS = themedItemColors && themedItemColors.length > 0
    ? themedItemColors
    : [accentColor, accent2, '#6366f1', '#f59e0b', accentColor];
  const colors = Array.from({length: N}, (_, i) => BASE_COLORS[i % BASE_COLORS.length]);

  return (
    <AbsoluteFill style={{backgroundColor: bgColor, opacity: sceneOpacity, overflow: 'hidden'}}>
      <AbsoluteFill style={{
        background: useGlow
          ? `radial-gradient(ellipse 800px 800px at 50% 50%, ${accentColor}0c 0%, transparent 65%)`
          : 'none',
      }}/>

      {/* Render back-to-front */}
      {Array.from({length: N}, (_, i) => N - 1 - i).map((idx) => {
        const isFront = idx === 0;
        const fanOffset = idx * 60;
        const fanAngle  = (idx - (N - 1) / 2) * 8;

        const p = smoothstep(interpolate(fanP, [idx / N * 0.5, idx / N * 0.5 + 0.45], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        }));

        const x = CX + fanOffset * p * (isFront ? 0 : 1);
        const y = CY - idx * 18 * p;
        const rot = fanAngle * p;
        const scale = isFront ? 1 + zoomP * 0.3 : 1 - flyP * 0.3;
        const flyX  = isFront ? 0 : (idx - 2) * 600 * flyP;
        const alpha = isFront ? 1 : 1 - flyP * 0.8;

        return (
          <div key={idx}
            style={{
              position: 'absolute',
              left: x - CARD_W / 2 + flyX,
              top:  y - CARD_H / 2,
              width:  CARD_W,
              height: CARD_H,
              background: `${colors[idx]}15`,
              border: `2px solid ${colors[idx]}${isFront ? 'dd' : '66'}`,
              borderRadius: 24,
              transform: `rotate(${rot}deg) scale(${scale})`,
              transformOrigin: '50% 100%',
              opacity: p * alpha,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 16,
            }}
          >
            <div style={{
              fontFamily,
              fontSize: isFront && zoomP > 0.3 ? 28 : 22,
              fontWeight: 700,
              color: colors[idx],
              textAlign: 'center',
              padding: '0 32px',
              lineHeight: 1.3,
            }}>
              {labels[idx] ?? `Item ${idx + 1}`}
            </div>
            {isFront && zoomP > 0.4 && (
              <div style={{
                fontFamily,
                fontSize: 19,
                color: ad?.palette.muted ?? '#ffffff88',
                textAlign: 'center',
                padding: '0 32px',
                opacity: smoothstep(zoomP),
              }}>
                {summaryText}
              </div>
            )}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
