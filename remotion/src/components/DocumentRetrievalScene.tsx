/**
 * DocumentRetrievalScene — Visual Director v3
 *
 * Beat-driven document retrieval animation:
 *   B0: document cards fan out from cylinder (carry-in)
 *   B1: three cards glow teal, rank badges appear
 *   B2: highlighted cards lift and fly right
 *   B3: cards stack in staging area — context preview visible
 *
 * Scene continuity: receives "knowledge base cylinder" from previous scene,
 * ends with "document cards" in staging area for next scene (ContextWindowScene).
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, MONO, easeOut, linearProgress, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';

interface DocumentRetrievalSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  carryFrom?: string; // 'knowledge base cylinder'
}

const TOTAL_DOCS = 15;
const TOP_3 = [2, 7, 11]; // indices of the "relevant" documents

export const DocumentRetrievalScene: React.FC<DocumentRetrievalSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // ── Beat 0: cards fan out from cylinder (0–1.5s) ────────────────────────
  const b0 = beats[0] ?? {start: 0, end: 1.5};
  const fanP = easeOut(frame, fps, b0.start, b0.end);

  // ── Beat 1: three cards glow + rank badges (1.5–3.0s) ───────────────────
  const b1 = beats[1] ?? {start: 1.5, end: 3.0};
  const glowP = linearProgress(frame, fps, b1.start, b1.end);
  const badgeP = easeOut(frame, fps, b1.start + 0.3, b1.end);

  // ── Beat 2: selected cards fly right (3.0–4.5s) ─────────────────────────
  const b2 = beats[2] ?? {start: 3.0, end: 4.5};
  const flyP = easeOut(frame, fps, b2.start, b2.end);

  // ── Beat 3: cards stack in staging area (4.5–6.0s) ──────────────────────
  const b3 = beats[3] ?? {start: 4.5, end: 6.0};
  const stackP = easeOut(frame, fps, b3.start, b3.end);

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  // Canvas constants
  const CY      = 920; // vertical centre of action
  const CYL_X   = 160; // knowledge base cylinder x (carry-in position)
  const STAGE_X = 860; // staging area x
  const STAGE_Y = CY;

  // Camera: zoom-out on beat 0, focus-shift on beat 1
  const camScale = interpolate(
    linearProgress(frame, fps, b0.start, b0.end),
    [0, 1], [1.08, 1],
  );

  // For each document card, compute position in fan, then in-flight, then stacked
  const docCards = Array.from({length: TOTAL_DOCS}, (_, i) => {
    const isTop = TOP_3.includes(i);
    const rank  = TOP_3.indexOf(i) + 1; // 1,2,3 or 0 if not top

    // Fan arc: cards spread from cylinder in a semicircle
    const angle  = (-60 + (i / (TOTAL_DOCS - 1)) * 120) * (Math.PI / 180);
    const radius = 240;
    const fanX   = CYL_X + Math.sin(angle) * radius * fanP;
    const fanY   = CY   - Math.cos(angle) * radius * fanP + (1 - fanP) * 120;
    const fanAlpha = smoothstep(interpolate(fanP, [i / TOTAL_DOCS * 0.5, (i / TOTAL_DOCS) * 0.5 + 0.4], [0, 1], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    }));

    // Glow on top 3
    const glowStrength = isTop ? smoothstep(glowP) : 0;

    // Flight path: top 3 fly to staging area
    const flyProgress = isTop ? flyP : 0;
    const stackOffset = rank > 0 ? (rank - 1) * 12 : 0;
    const stackedX = STAGE_X + stackOffset;
    const stackedY = STAGE_Y + stackOffset;

    // Position: fan → flight → stacked
    const afterFly  = frame >= Math.round(b2.start * fps) && isTop;
    const afterStack = frame >= Math.round(b3.start * fps) && isTop;

    const cx = afterFly
      ? interpolate(flyP, [0, 1], [fanX, stackedX])
      : fanX;
    const cy = afterFly
      ? interpolate(flyP, [0, 0.6, 1], [fanY, fanY - 120, stackedY])
      : fanY;

    // Non-top cards fade as flying cards leave
    const cardAlpha = (!isTop && afterFly)
      ? interpolate(flyP, [0, 0.5], [1, 0.15], {extrapolateRight: 'clamp'})
      : fanAlpha;

    return {i, isTop, rank, cx, cy, cardAlpha, glowStrength, flyProgress, stackedX, stackedY, afterFly, afterStack};
  });

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
          background: `radial-gradient(ellipse 900px 700px at 30% 48%, ${accentColor}0e 0%, transparent 65%)`,
        }}
      />

      <svg
        viewBox="0 0 1080 1920"
        width={1080}
        height={1920}
        style={{
          position: 'absolute',
          inset: 0,
          transform: `scale(${camScale})`,
          transformOrigin: '40% 48%',
        }}
      >
        {/* ── Knowledge base cylinder (carry-in from previous scene) ─── */}
        <g opacity={interpolate(frame, [0, 10], [0, 1], {extrapolateRight: 'clamp'})}>
          <rect x={CYL_X - 70} y={CY - 110} width={140} height={220}
            rx={8} fill={`${accent2}10`} stroke={`${accent2}44`} strokeWidth={1.5}/>
          <ellipse cx={CYL_X} cy={CY - 110} rx={70} ry={22}
            fill={`${accent2}22`} stroke={`${accent2}88`} strokeWidth={2}/>
          <ellipse cx={CYL_X} cy={CY + 110} rx={70} ry={22}
            fill={`${accent2}18`} stroke={`${accent2}66`} strokeWidth={2}/>
          <text x={CYL_X} y={CY + 160} textAnchor="middle"
            fill={accent2} fontFamily={FONT} fontSize={20} fontWeight="700">
            Knowledge base
          </text>
        </g>

        {/* ── Document cards ────────────────────────────────────────────── */}
        {docCards.map(({i, isTop, rank, cx, cy, cardAlpha, glowStrength}) => (
          <g key={i} opacity={cardAlpha} transform={`translate(${cx - 38}, ${cy - 52})`}>
            {/* Card body */}
            <rect
              x={0} y={0} width={76} height={104}
              rx={6}
              fill={isTop ? `${accent2}18` : `${accentColor}0e`}
              stroke={isTop ? accent2 : `${accentColor}33`}
              strokeWidth={isTop ? 2 : 1}
              filter={glowStrength > 0.1 ? `url(#glow-${i})` : undefined}
            />
            {/* Card lines */}
            {[0, 1, 2, 3].map((l) => (
              <rect key={l} x={10} y={16 + l * 20} width={56} height={6}
                rx={3}
                fill={isTop ? accent2 : '#ffffff'}
                opacity={isTop ? 0.5 + glowStrength * 0.4 : 0.12}
              />
            ))}

            {/* Rank badge */}
            {isTop && glowStrength > 0.3 && (
              <g transform={`translate(-12, -12)`}
                opacity={smoothstep(interpolate(glowP, [0.3, 0.7], [0, 1], {
                  extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
                }))}>
                <circle cx={12} cy={12} r={14}
                  fill={accent2} stroke="#050510" strokeWidth={2}/>
                <text x={12} y={18} textAnchor="middle"
                  fill="#050510" fontFamily={FONT} fontSize={14} fontWeight="900">
                  {rank}
                </text>
              </g>
            )}

            {/* Glow filter defs (only for top docs) */}
            {isTop && (
              <defs>
                <filter id={`glow-${i}`} x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation={`${glowStrength * 8}`} result="blur"/>
                  <feMerge>
                    <feMergeNode in="blur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>
            )}
          </g>
        ))}

        {/* ── Staging area (appears on beat 2) ────────────────────────── */}
        {frame >= Math.round(b2.start * fps) && (
          <g opacity={interpolate(linearProgress(frame, fps, b2.start, b2.start + 0.5), [0, 1], [0, 1])}>
            <rect x={STAGE_X - 80} y={STAGE_Y - 130} width={200} height={260}
              rx={16} fill="none" stroke={`${accent2}44`} strokeWidth={1.5} strokeDasharray="8 5"/>
            <text x={STAGE_X + 20} y={STAGE_Y - 155} textAnchor="middle"
              fill={accent2} fontFamily={FONT} fontSize={20} fontWeight="700">
              {onScreenText[0] ?? 'Top 3 chunks'}
            </text>
          </g>
        )}

        {/* ── "Most relevant" label on beat 3 ─────────────────────────── */}
        {frame >= Math.round(b3.start * fps) && (
          <text
            x={STAGE_X + 20} y={STAGE_Y + 170}
            textAnchor="middle"
            fill={accentColor}
            fontFamily={FONT}
            fontSize={22}
            fontWeight="700"
            opacity={smoothstep(linearProgress(frame, fps, b3.start, b3.start + 0.5))}
          >
            {onScreenText[1] ?? 'Most relevant'}
          </text>
        )}
      </svg>
    </AbsoluteFill>
  );
};
