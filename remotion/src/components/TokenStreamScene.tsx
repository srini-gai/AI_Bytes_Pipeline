/**
 * TokenStreamScene — Beat-driven token stream with phase primitives.
 *
 * Supports these visual phases (detected from beat action keywords):
 *   emission     — tokens emit left-to-right from a transformer block
 *   probability  — arrow bounces between candidate tokens, snaps to winner
 *   void         — dark zone slides in; normal tokens thin out
 *   fabrication  — new tokens self-generate in danger color inside void
 *   output       — tokens exit void into an output container, masking their origin
 *   stamp        — text stamp slams over content (e.g. HALLUCINATION)
 *   dim          — all elements except a focused label dim down
 *
 * Duration-aware: scales to actual durationInFrames, never hardcoded.
 */
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, MONO, smoothstep} from './beatUtils';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

interface TokenStreamSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  carryFrom?: string;
  durationInFrames?: number;
  artDirection?: ArtDirection;
}

// ── Phase detection from beat action text ──────────────────────────────────

type Phase =
  | 'emission'
  | 'probability'
  | 'void'
  | 'fabrication'
  | 'output'
  | 'stamp'
  | 'dim';

function detectPhases(action: string): Phase[] {
  const a = action.toLowerCase();
  const phases: Phase[] = [];
  if (/void|sparse|dark|thin\s*out/.test(a)) phases.push('void');
  if (/fabricat|self-generat|wrong\s*color/.test(a)) phases.push('fabrication');
  if (/output|exit.*void|indistinguish/.test(a)) phases.push('output');
  if (/stamp|hallucin/.test(a)) phases.push('stamp');
  if (/bounce|candidate|probability|arrow/.test(a)) phases.push('probability');
  if (/dim|predict.*lock|label.*lock/.test(a)) phases.push('dim');
  if (phases.length === 0) phases.push('emission');
  return phases;
}

// ── Token data ────────────────────────────────────────────────────────────

const NORMAL_TOKENS = ['The', 'cat', 'sat', 'on', 'the'];
const FABRICATED_TOKENS = ['mat', '—', 'sure', 'it', 'did'];
const DANGER_COLOR = '#ff3333';

export const TokenStreamScene: React.FC<TokenStreamSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
  durationInFrames: durationProp,
  artDirection: ad,
}) => {
  const frame = useCurrentFrame();
  const config = useVideoConfig();
  const fps = config.fps;
  const totalFrames = durationProp ?? config.durationInFrames;

  // Art direction derivations
  const bgColor = ad?.palette.bg ?? BG;
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.font ?? FONT;
  const monoFamily = ad?.typography.mono ?? MONO;

  // ── Beat timing ──────────────────────────────────────────────────────────

  const beatPhases = beats.map((b) => ({
    ...b,
    startF: Math.round(b.start * fps),
    endF: Math.round(b.end * fps),
    phases: detectPhases(b.action),
  }));

  const hasPhase = (phase: Phase): boolean =>
    beatPhases.some((b) => b.phases.includes(phase));

  const phaseActive = (phase: Phase): boolean =>
    beatPhases.some(
      (b) => b.phases.includes(phase) && frame >= b.startF && frame < b.endF,
    );

  const phaseProgress = (phase: Phase): number => {
    for (const b of beatPhases) {
      if (b.phases.includes(phase) && frame >= b.startF) {
        return interpolate(frame, [b.startF, b.endF], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
      }
    }
    return 0;
  };

  const phaseStarted = (phase: Phase): boolean =>
    beatPhases.some((b) => b.phases.includes(phase) && frame >= b.startF);

  // ── Scene opacity ────────────────────────────────────────────────────────

  const sceneOpacity = interpolate(
    frame,
    [0, 8, totalFrames - 8, totalFrames],
    [0, 1, 1, 0.4],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // ── Dim phase ────────────────────────────────────────────────────────────

  const dimActive = phaseActive('dim');
  const dimProgress = phaseProgress('dim');
  const contentDim = dimActive ? interpolate(dimProgress, [0, 0.3], [1, 0.40], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  }) : 1;

  // ── Transformer block ────────────────────────────────────────────────────

  const TX_CX = 200;
  const TX_CY = 800;
  const TX_W = 220;
  const TX_H = 300;
  const processPulse = 0.5 + 0.5 * Math.sin(frame * 0.18);

  // ── Token emission ───────────────────────────────────────────────────────
  // Tokens emit across the full scene duration, paced to beats

  const tokenStartX = TX_CX + TX_W / 2 + 80;
  const tokenSpacing = 200;

  // Determine which tokens to show based on phases
  const showFabricated = hasPhase('fabrication');
  const allTokens = showFabricated
    ? [...NORMAL_TOKENS, ...FABRICATED_TOKENS]
    : NORMAL_TOKENS;

  // Fabrication starts at the fabrication beat
  const fabricationBeat = beatPhases.find((b) => b.phases.includes('fabrication'));
  const fabricationStartF = fabricationBeat?.startF ?? totalFrames;
  const voidBeat = beatPhases.find((b) => b.phases.includes('void'));

  const tokenEmissions = allTokens.map((_, i) => {
    const emitFraction = i / Math.max(allTokens.length - 1, 1);
    // Spread emissions across ~80% of total duration
    const emitFrame = Math.round(emitFraction * totalFrames * 0.75);
    const emitProgress = spring({
      fps,
      frame: Math.max(0, frame - emitFrame),
      config: {damping: 14, stiffness: 100, mass: 0.5},
      durationInFrames: 20,
    });
    const isEmitted = frame >= emitFrame;
    const isFabricated = i >= NORMAL_TOKENS.length;
    return {emitProgress, isEmitted, emitFrame, isFabricated};
  });

  // Camera pan
  const emittedCount = tokenEmissions.filter((t) => t.isEmitted).length;
  const camPanX = interpolate(
    emittedCount,
    [0, 2, 4, 6, 8, 10],
    [0, 0, -100, -220, -340, -440],
  );

  // ── Void zone ────────────────────────────────────────────────────────────

  const voidProgress = phaseProgress('void');
  const voidOpacity = hasPhase('void')
    ? interpolate(voidProgress, [0, 0.4], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      })
    : 0;

  // During void phase, normal tokens should fade
  const normalTokenFade = hasPhase('void') && voidProgress > 0.3
    ? interpolate(voidProgress, [0.3, 0.8], [1, 0.2], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      })
    : 1;

  // ── Output block ─────────────────────────────────────────────────────────

  const outputProgress = phaseProgress('output');
  const outputOpacity = hasPhase('output')
    ? interpolate(outputProgress, [0, 0.3], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      })
    : 0;

  // ── Stamp overlay ────────────────────────────────────────────────────────

  const stampProgress = phaseProgress('stamp');
  const stampScale = hasPhase('stamp') && phaseStarted('stamp')
    ? interpolate(stampProgress, [0, 0.15, 0.25], [3, 1, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      })
    : 0;
  const stampOpacity = hasPhase('stamp') && phaseStarted('stamp')
    ? interpolate(stampProgress, [0, 0.15], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      })
    : 0;

  // Stamp text from on_screen_text (last item for s04, or beat focus hint)
  const stampBeat = beatPhases.find((b) => b.phases.includes('stamp'));
  const stampText =
    (stampBeat?.focus ?? '')
      .replace(/[-_]/g, ' ')
      .replace(/stamp/i, '')
      .trim()
      .toUpperCase() ||
    onScreenText[onScreenText.length - 1] ||
    'HALLUCINATION';

  // ── Probability arrow ────────────────────────────────────────────────────

  const probActive = phaseActive('probability');
  const probProgress = phaseProgress('probability');
  const probBeat = beatPhases.find((b) => b.phases.includes('probability'));
  const probStartF = probBeat?.startF ?? 0;

  // Arrow bounces between 3 candidate positions then snaps
  const candidateY = [TX_CY - 200, TX_CY - 260, TX_CY - 230];
  const candidateX = [tokenStartX + 50, tokenStartX + 200, tokenStartX + 350];

  // ── Labels ───────────────────────────────────────────────────────────────
  // Map on_screen_text to beats for timing

  const labelTimings = onScreenText.map((text, i) => {
    const matchBeat = beatPhases[Math.min(i, beatPhases.length - 1)];
    if (!matchBeat) return {text, opacity: 0, y: 300};
    const showStart = matchBeat.startF + 8;
    const showEnd = matchBeat.endF;
    const opacity = interpolate(
      frame,
      [showStart, showStart + 12, showEnd - 6, showEnd],
      [0, 0.85, 0.85, 0.3],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
    );
    return {text, opacity, y: 260 + i * 80};
  });

  return (
    <AbsoluteFill style={{backgroundColor: bgColor, opacity: sceneOpacity, overflow: 'hidden'}}>
      {/* Background glow follows transformer */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 700px 700px at ${TX_CX + camPanX}px ${TX_CY}px, ${accentColor}25 0%, transparent 55%)`,
          opacity: contentDim,
        }}
      />

      {/* Animated scan lines for visual activity */}
      <AbsoluteFill style={{opacity: 0.08 + 0.04 * Math.sin(frame * 0.1)}}>
        {Array.from({length: 6}, (_, i) => {
          const lineY = ((frame * 1.5 + i * 320) % 1920);
          return (
            <div key={`scan-${i}`} style={{
              position: 'absolute',
              left: 0, right: 0,
              top: lineY,
              height: 2,
              background: `linear-gradient(90deg, transparent, ${accentColor}40, transparent)`,
            }} />
          );
        })}
      </AbsoluteFill>

      {/* ── Void zone overlay ──────────────────────────────────────────── */}
      {voidOpacity > 0.01 && (
        <AbsoluteFill
          style={{
            background: `linear-gradient(90deg, transparent 25%, ${DANGER_COLOR}15 40%, ${bgColor}dd 50%, ${bgColor} 100%)`,
            opacity: voidOpacity * 0.9,
            zIndex: 1,
          }}
        >
          {/* Void zone label */}
          {voidProgress > 0.2 && (
            <div
              style={{
                position: 'absolute',
                top: TX_CY - 380,
                right: 80,
                opacity: interpolate(voidProgress, [0.2, 0.5], [0, 0.9], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                }),
              }}
            >
              <span
                style={{
                  fontFamily,
                  fontSize: 36,
                  fontWeight: 900,
                  color: DANGER_COLOR,
                  letterSpacing: 5,
                }}
              >
                {onScreenText.find((t) =>
                  /sparse|void|data/i.test(t),
                ) ?? 'SPARSE DATA'}
              </span>
            </div>
          )}
        </AbsoluteFill>
      )}

      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `translateX(${camPanX}px)`,
          opacity: contentDim,
        }}
      >
        <svg
          viewBox="0 0 1080 1920"
          width={1080}
          height={1920}
          style={{position: 'absolute', inset: 0}}
        >
          {/* ── Transformer block ────────────────────────────────────────── */}
          <rect
            x={TX_CX - TX_W / 2 - 8}
            y={TX_CY - TX_H / 2 - 8}
            width={TX_W + 16}
            height={TX_H + 16}
            rx={24}
            fill="none"
            stroke={accentColor}
            strokeWidth={2}
            opacity={0.15 + processPulse * 0.15}
          />
          <rect
            x={TX_CX - TX_W / 2}
            y={TX_CY - TX_H / 2}
            width={TX_W}
            height={TX_H}
            rx={18}
            fill={`${accentColor}30`}
            stroke={accentColor}
            strokeWidth={3}
          />
          {Array.from({length: 5}, (_, i) => {
            const ly = TX_CY - TX_H / 2 + 50 + i * 50;
            const phase = (frame * 0.08 + i * 0.7) % 1;
            return (
              <rect
                key={`proc-${i}`}
                x={TX_CX - TX_W / 2 + 24}
                y={ly}
                width={(TX_W - 48) * (0.3 + phase * 0.7)}
                height={6}
                rx={3}
                fill={accentColor}
                opacity={0.3 + phase * 0.4}
              />
            );
          })}
          <text
            x={TX_CX}
            y={TX_CY + TX_H / 2 + 45}
            textAnchor="middle"
            fontFamily={fontFamily}
            fontSize={22}
            fontWeight={700}
            fill={accentColor}
            opacity={0.6}
          >
            TRANSFORMER
          </text>

          {/* ── Emission arrow ────────────────────────────────────────────── */}
          <line
            x1={TX_CX + TX_W / 2 + 4}
            y1={TX_CY}
            x2={tokenStartX - 10}
            y2={TX_CY}
            stroke={accent2}
            strokeWidth={3}
            opacity={0.4}
            strokeDasharray="6 4"
          />
          <polygon
            points={`${tokenStartX - 10},${TX_CY - 8} ${tokenStartX},${TX_CY} ${tokenStartX - 10},${TX_CY + 8}`}
            fill={accent2}
            opacity={0.5}
          />

          {/* ── Emitted tokens ───────────────────────────────────────────── */}
          {allTokens.map((tok, i) => {
            const {emitProgress, isEmitted, isFabricated} = tokenEmissions[i];
            if (!isEmitted) return null;

            // During void phase, normal tokens fade out
            const tokenAlpha = isFabricated ? emitProgress : emitProgress * normalTokenFade;
            if (tokenAlpha < 0.01) return null;

            const x = tokenStartX + i * tokenSpacing;
            const y = TX_CY;
            const isLatest = i === emittedCount - 1;
            const tokenColor = isFabricated ? DANGER_COLOR : accent2;

            return (
              <g
                key={`tok-${i}`}
                transform={`translate(${x}, ${y}) scale(${emitProgress})`}
                opacity={tokenAlpha}
              >
                <rect
                  x={-65}
                  y={-45}
                  width={130}
                  height={90}
                  rx={14}
                  fill={isLatest ? `${tokenColor}55` : `${tokenColor}35`}
                  stroke={isLatest ? tokenColor : `${tokenColor}bb`}
                  strokeWidth={isLatest ? 3 : 2}
                />
                {isLatest && (
                  <rect
                    x={-69}
                    y={-49}
                    width={138}
                    height={98}
                    rx={18}
                    fill="none"
                    stroke={tokenColor}
                    strokeWidth={2}
                    opacity={0.5 + processPulse * 0.3}
                  />
                )}
                <text
                  x={0}
                  y={10}
                  textAnchor="middle"
                  fontFamily={monoFamily}
                  fontSize={38}
                  fontWeight={800}
                  fill={isFabricated ? DANGER_COLOR : textColor}
                >
                  {tok}
                </text>
                <text
                  x={0}
                  y={-52}
                  textAnchor="middle"
                  fontFamily={monoFamily}
                  fontSize={14}
                  fontWeight={600}
                  fill={tokenColor}
                  opacity={0.5}
                >
                  t{i + 1}
                </text>
              </g>
            );
          })}

          {/* ── Probability arrow ─────────────────────────────────────────── */}
          {probActive && (
            <>
              {candidateX.map((cx, ci) => {
                const bouncePhase = ((frame - probStartF) * 0.15 + ci * 2.1) % 3;
                const isActive = Math.floor(bouncePhase) === 0;
                const snapped = probProgress > 0.7 && ci === 1;
                return (
                  <g key={`cand-${ci}`} opacity={isActive || snapped ? 0.9 : 0.3}>
                    <rect
                      x={cx - 50}
                      y={candidateY[ci] - 25}
                      width={100}
                      height={50}
                      rx={10}
                      fill={snapped ? `${accent2}30` : `${accentColor}15`}
                      stroke={snapped ? accent2 : `${accentColor}44`}
                      strokeWidth={snapped ? 3 : 1.5}
                    />
                    <text
                      x={cx}
                      y={candidateY[ci] + 8}
                      textAnchor="middle"
                      fontFamily={monoFamily}
                      fontSize={22}
                      fill={snapped ? accent2 : `${accentColor}88`}
                    >
                      {['mat', 'the', 'a'][ci]}
                    </text>
                    {(isActive || snapped) && (
                      <polygon
                        points={`${cx},${candidateY[ci] + 30} ${cx - 8},${candidateY[ci] + 42} ${cx + 8},${candidateY[ci] + 42}`}
                        fill={snapped ? accent2 : accentColor}
                        opacity={0.6}
                      />
                    )}
                  </g>
                );
              })}
            </>
          )}

        </svg>
      </div>

      {/* ── Output block (fixed viewport position) ─────────────────────── */}
      {outputOpacity > 0.01 && (
        <div style={{
          position: 'absolute',
          bottom: 280,
          left: '50%',
          transform: `translateX(-50%) scale(${interpolate(outputProgress, [0, 0.2], [0.8, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})})`,
          opacity: outputOpacity,
          zIndex: 3,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 12,
        }}>
          <div style={{
            fontFamily: fontFamily,
            fontSize: 22,
            fontWeight: 700,
            color: `${textColor}aa`,
            letterSpacing: 4,
          }}>
            {onScreenText.find((t) => /output/i.test(t)) ?? 'OUTPUT'}
          </div>
          <div style={{
            width: 320,
            minHeight: 120,
            borderRadius: 18,
            background: `${textColor}15`,
            border: `2px solid ${textColor}44`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 20,
            padding: '16px 24px',
          }}>
            {outputProgress > 0.3 &&
              FABRICATED_TOKENS.slice(0, 3).map((tok, fi) => (
                <span key={`out-${fi}`} style={{
                  fontFamily: monoFamily,
                  fontSize: 34,
                  fontWeight: 800,
                  color: textColor,
                  opacity: interpolate(outputProgress, [0.3 + fi * 0.1, 0.5 + fi * 0.1], [0, 0.95], {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                  }),
                }}>{tok}</span>
              ))}
          </div>
          {outputProgress > 0.6 && (
            <div style={{
              fontFamily: fontFamily,
              fontSize: 18,
              color: accent2,
              opacity: interpolate(outputProgress, [0.6, 0.8], [0, 0.8], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              }),
            }}>
              indistinguishable from real output
            </div>
          )}
        </div>
      )}

      {/* ── Dim-phase spotlight (keeps content above QA threshold) ──────── */}
      {dimActive && (
        <AbsoluteFill style={{
          background: `radial-gradient(ellipse 600px 400px at 50% 260px, ${accentColor}20 0%, transparent 70%)`,
          zIndex: 4,
          opacity: interpolate(dimProgress, [0, 0.3], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          }),
        }} />
      )}

      {/* ── Stamp overlay ──────────────────────────────────────────────── */}
      {stampOpacity > 0.01 && (
        <AbsoluteFill
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10,
          }}
        >
          <div
            style={{
              transform: `scale(${stampScale}) rotate(-8deg)`,
              opacity: stampOpacity,
              padding: '20px 50px',
              border: `6px solid ${DANGER_COLOR}`,
              borderRadius: 12,
            }}
          >
            <span
              style={{
                fontFamily,
                fontSize: 64,
                fontWeight: 900,
                color: DANGER_COLOR,
                letterSpacing: 8,
              }}
            >
              {stampText}
            </span>
          </div>
        </AbsoluteFill>
      )}

      {/* ── Phase labels ───────────────────────────────────────────────── */}
      {labelTimings.map(
        (lt, i) =>
          lt.opacity > 0.01 && (
            <div
              key={`label-${i}`}
              style={{
                position: 'absolute',
                top: lt.y,
                left: 0,
                right: 0,
                textAlign: 'center',
                opacity: dimActive && !/predict/i.test(lt.text) ? lt.opacity * contentDim : lt.opacity,
                zIndex: 5,
              }}
            >
              <span
                style={{
                  fontFamily,
                  fontSize: 34,
                  fontWeight: 900,
                  color: /predict/i.test(lt.text) ? accent2 : textColor,
                  letterSpacing: 4,
                }}
              >
                {lt.text}
              </span>
            </div>
          ),
      )}
    </AbsoluteFill>
  );
};
