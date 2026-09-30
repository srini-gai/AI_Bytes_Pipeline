/**
 * SplitCompareScene — Visual Director v3.1
 *
 * Side-by-side comparison fills the full canvas vertically.
 * Panels start at y=140 and extend to y=1680+ using the full 1920px height.
 *
 * v3.1 changes:
 * - Panels top at y=140, each 700px tall — fills ~80% of canvas
 * - Label "WITHOUT RAG" / "WITH RAG" — NEVER exposes internal identifiers
 * - Labels sourced strictly from spec.left.label / spec.right.label
 *   (AIBytesReel must supply human-readable text — this component
 *    never displays raw objects[] array contents as UI text)
 * - Legacy frame-based mode preserved unchanged
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SplitCompareSpec, SideBySideSpec} from '../types';
import type {SceneBeat} from '../types';
import {easeOut, linearProgress, smoothstep} from './beatUtils';

interface SceneTheme { accent: string; accent2: string; }

const DEFAULT_THEME: SceneTheme = {accent: '#a78bfa', accent2: '#34d399'};
const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

// v3.1: panels are nearly full-width and very tall
const COL_W   = 480;
const COL_GAP = 40;
const COL_PADDING = 32;
const LEFT_X  = 40;
const RIGHT_X = LEFT_X + COL_W + COL_GAP;
const PANEL_TOP = 140;      // was 260 — now higher
const PANEL_H   = 1300;     // was unconstrained short — now tall

// Frame timing for legacy mode
const LEFT_SLIDE_IN  = [8,  40];
const LEFT_ICON      = [36, 52];
const LEFT_PTS_START = 50;
const RIGHT_SLIDE_IN = [80, 112];
const RIGHT_ICON     = [108, 124];
const RIGHT_PTS_START = 122;
const VERDICT_IN     = [180, 210];

interface SplitCompareSceneProps {
  spec: SplitCompareSpec | SideBySideSpec;
  theme?: SceneTheme;
  beats?: SceneBeat[];
  onScreenText?: string[];
}

const Panel: React.FC<{
  panel: {label: string; points: string[]};
  slideFrom: 'left' | 'right';
  slideFrames: [number, number];
  iconFrame: [number, number];
  ptsStart: number;
  icon: string;
  color: string;
  frame: number;
}> = ({panel, slideFrom, slideFrames, iconFrame, ptsStart, icon, color, frame}) => {
  const dir = slideFrom === 'left' ? -140 : 140;
  const slideX = interpolate(frame, slideFrames, [dir, 0], {extrapolateRight: 'clamp'});
  const slideOpacity = interpolate(frame, slideFrames, [0, 1], {extrapolateRight: 'clamp'});
  const iconOpacity = interpolate(frame, iconFrame, [0, 1], {extrapolateRight: 'clamp'});
  const iconScale = interpolate(frame, iconFrame, [0.4, 1], {extrapolateRight: 'clamp'});

  return (
    <div style={{
      position: 'absolute',
      top: PANEL_TOP,
      left: slideFrom === 'left' ? LEFT_X : RIGHT_X,
      width: COL_W,
      height: PANEL_H,
      opacity: slideOpacity,
      transform: `translateX(${slideX}px)`,
      zIndex: 2,
    }}>
      <div style={{
        position: 'absolute', inset: 0,
        borderRadius: 24,
        background: `${color}12`,
        border: `2px solid ${color}44`,
        boxShadow: `0 0 60px ${color}18`,
      }}/>
      <div style={{position: 'relative', padding: `${COL_PADDING + 16}px ${COL_PADDING}px ${COL_PADDING}px`}}>
        <div style={{
          fontSize: 72, textAlign: 'center', marginBottom: 20,
          opacity: iconOpacity,
          transform: `scale(${iconScale})`,
        }}>{icon}</div>

        {/* Human-facing label only — never internal identifier */}
        <div style={{
          fontSize: 38, fontWeight: 900, color, fontFamily: FONT,
          textAlign: 'center', marginBottom: 28,
          textShadow: `0 0 24px ${color}66`,
          letterSpacing: -0.5, lineHeight: 1.2,
        }}>
          {panel.label}
        </div>

        <div style={{height: 2, background: `${color}44`, borderRadius: 1, marginBottom: 24}}/>

        {panel.points.map((pt, pi) => {
          const ptStart = ptsStart + pi * 18;
          const ptOpacity = interpolate(frame, [ptStart, ptStart + 16], [0, 1], {extrapolateRight: 'clamp'});
          const ptX = interpolate(frame, [ptStart, ptStart + 16], [14, 0], {extrapolateRight: 'clamp'});
          return (
            <div key={pi} style={{
              display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 18,
              opacity: ptOpacity, transform: `translateX(${ptX}px)`,
            }}>
              <div style={{color, fontSize: 22, marginTop: 4, flexShrink: 0}}>▸</div>
              <div style={{
                fontSize: 32, color: 'rgba(255,255,255,0.88)',
                fontFamily: FONT, lineHeight: 1.45,
              }}>{pt}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const SplitCompareScene: React.FC<SplitCompareSceneProps> = ({spec, theme, beats, onScreenText}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = theme ?? DEFAULT_THEME;

  // ── v3 beat-driven mode ──────────────────────────────────────────────────
  if (beats && beats.length >= 2) {
    const leftP  = easeOut(frame, fps, beats[0].start, beats[0].end);
    const rightP = easeOut(frame, fps, beats[1].start, beats[1].end);
    const verdP  = beats[2] ? easeOut(frame, fps, beats[2].start, beats[2].end) : rightP;
    // No fade-in: content present from frame 1
    const isSplit   = spec.type === 'split_compare';
    const leftCol   = isSplit ? '#ff4444' : t.accent;
    const rightCol  = isSplit ? '#22c55e' : t.accent2;
    const verdict   = spec.type === 'split_compare' ? spec.verdict : undefined;

    return (
      <AbsoluteFill style={{backgroundColor: '#050510'}}>
        {/* Background: left red tint / right green tint */}
        <AbsoluteFill style={{
          background: `linear-gradient(90deg, ${leftCol}08 0%, transparent 50%, ${rightCol}08 100%)`,
        }}/>

        {/* Left panel */}
        <div style={{
          position: 'absolute', top: PANEL_TOP, left: LEFT_X, width: COL_W, height: PANEL_H,
          opacity: leftP,
          transform: `translateX(${interpolate(leftP, [0, 1], [-180, 0])}px)`,
          zIndex: 2,
        }}>
          <div style={{
            position: 'absolute', inset: 0, borderRadius: 24,
            background: `${leftCol}12`, border: `2px solid ${leftCol}55`,
            boxShadow: `0 0 60px ${leftCol}15`,
          }}/>
          <div style={{position: 'relative', padding: '50px 32px 32px'}}>
            <div style={{
              fontFamily: FONT, fontSize: 38, fontWeight: 900, color: leftCol,
              textAlign: 'center', marginBottom: 28,
              textShadow: `0 0 24px ${leftCol}66`,
            }}>
              {/* Strictly use spec.left.label — which AIBytesReel sets to "WITHOUT RAG" */}
              {spec.left.label}
            </div>
            <div style={{height: 2, background: `${leftCol}44`, marginBottom: 24}}/>
            {spec.left.points.map((pt, pi) => (
              <div key={pi} style={{
                display: 'flex', gap: 12, marginBottom: 18,
                opacity: smoothstep(interpolate(leftP, [0.35 + pi * 0.1, 0.65 + pi * 0.1], [0, 1], {
                  extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
                })),
              }}>
                <div style={{color: leftCol, fontSize: 22, marginTop: 4}}>▸</div>
                <div style={{fontSize: 30, color: 'rgba(255,255,255,0.88)', fontFamily: FONT, lineHeight: 1.45}}>
                  {pt}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* VS badge — centred between panels */}
        <div style={{
          position: 'absolute', left: LEFT_X + COL_W + Math.round(COL_GAP / 2) - 26,
          top: PANEL_TOP + 120,
          width: 52, height: 52, borderRadius: '50%', background: '#1a1a2e',
          border: `2px solid ${t.accent}66`, display: 'flex', alignItems: 'center',
          justifyContent: 'center', zIndex: 5, fontSize: 18, fontWeight: 900,
          color: 'rgba(255,255,255,0.6)', fontFamily: FONT,
        }}>VS</div>

        {/* Right panel */}
        <div style={{
          position: 'absolute', top: PANEL_TOP, left: RIGHT_X, width: COL_W, height: PANEL_H,
          opacity: rightP,
          transform: `translateX(${interpolate(rightP, [0, 1], [180, 0])}px)`,
          zIndex: 2,
        }}>
          <div style={{
            position: 'absolute', inset: 0, borderRadius: 24,
            background: `${rightCol}12`, border: `2px solid ${rightCol}55`,
            boxShadow: `0 0 60px ${rightCol}15`,
          }}/>
          <div style={{position: 'relative', padding: '50px 32px 32px'}}>
            <div style={{
              fontFamily: FONT, fontSize: 38, fontWeight: 900, color: rightCol,
              textAlign: 'center', marginBottom: 28,
              textShadow: `0 0 24px ${rightCol}66`,
            }}>
              {/* Strictly use spec.right.label — which AIBytesReel sets to "WITH RAG" */}
              {spec.right.label}
            </div>
            <div style={{height: 2, background: `${rightCol}44`, marginBottom: 24}}/>
            {spec.right.points.map((pt, pi) => (
              <div key={pi} style={{
                display: 'flex', gap: 12, marginBottom: 18,
                opacity: smoothstep(interpolate(rightP, [0.35 + pi * 0.1, 0.65 + pi * 0.1], [0, 1], {
                  extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
                })),
              }}>
                <div style={{color: rightCol, fontSize: 22, marginTop: 4}}>▸</div>
                <div style={{fontSize: 30, color: 'rgba(255,255,255,0.88)', fontFamily: FONT, lineHeight: 1.45}}>
                  {pt}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Verdict */}
        {verdict && verdP > 0.1 && (
          <div style={{
            position: 'absolute', bottom: 160, left: 40, right: 40,
            opacity: smoothstep(verdP),
            transform: `translateY(${interpolate(verdP, [0, 1], [24, 0])}px)`,
            zIndex: 3,
            backgroundColor: 'rgba(255,68,68,0.15)',
            border: '2px solid rgba(255,68,68,0.4)',
            borderRadius: 20, padding: '22px 32px', textAlign: 'center',
          }}>
            <div style={{fontSize: 40, fontWeight: 900, color: '#ff6666', fontFamily: FONT}}>
              {verdict}
            </div>
          </div>
        )}
      </AbsoluteFill>
    );
  }

  // ── Legacy frame-based mode (unchanged) ──────────────────────────────────
  const verdict: string | undefined = spec.type === 'split_compare' ? spec.verdict : undefined;
  const isSplitCompare = spec.type === 'split_compare';
  const leftColor  = isSplitCompare ? '#ff4444' : t.accent;
  const rightColor = isSplitCompare ? '#22c55e' : t.accent2;
  const leftIcon   = isSplitCompare ? '❌' : '◀';
  const rightIcon  = isSplitCompare ? '✅' : '▶';

  const verdictOpacity = interpolate(frame, VERDICT_IN, [0, 1], {extrapolateRight: 'clamp'});
  const verdictY = interpolate(frame, VERDICT_IN, [20, 0], {extrapolateRight: 'clamp'});
  const titleOpacity = interpolate(frame, [0, 18], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: '#050510'}}>
      <AbsoluteFill style={{
        background: 'linear-gradient(to bottom, transparent 72%, rgba(0,0,0,0.82) 100%)',
      }}/>
      <div style={{
        position: 'absolute', top: 136, left: 0, right: 0,
        textAlign: 'center', opacity: titleOpacity, zIndex: 2,
        fontSize: 26, letterSpacing: 6, textTransform: 'uppercase' as const,
        color: t.accent, fontFamily: FONT, fontWeight: 700,
      }}>Compare</div>

      <Panel
        panel={spec.left}
        slideFrom="left"
        slideFrames={LEFT_SLIDE_IN as [number, number]}
        iconFrame={LEFT_ICON as [number, number]}
        ptsStart={LEFT_PTS_START}
        icon={leftIcon}
        color={leftColor}
        frame={frame}
      />
      <Panel
        panel={spec.right}
        slideFrom="right"
        slideFrames={RIGHT_SLIDE_IN as [number, number]}
        iconFrame={RIGHT_ICON as [number, number]}
        ptsStart={RIGHT_PTS_START}
        icon={rightIcon}
        color={rightColor}
        frame={frame}
      />

      <div style={{
        position: 'absolute', left: LEFT_X + COL_W + Math.round(COL_GAP / 2) - 26,
        top: PANEL_TOP + 120,
        width: 52, height: 52, borderRadius: '50%', background: '#1a1a2e',
        border: `2px solid ${t.accent}66`, display: 'flex', alignItems: 'center',
        justifyContent: 'center', zIndex: 5, fontSize: 18, fontWeight: 900,
        color: 'rgba(255,255,255,0.6)', fontFamily: FONT,
      }}>VS</div>

      {verdict && (
        <div style={{
          position: 'absolute', bottom: 220, left: 40, right: 40,
          opacity: verdictOpacity, transform: `translateY(${verdictY}px)`,
          zIndex: 3, backgroundColor: 'rgba(255,68,68,0.15)',
          border: '1.5px solid rgba(255,68,68,0.4)', borderRadius: 16,
          padding: '18px 28px', textAlign: 'center',
        }}>
          <div style={{fontSize: 36, fontWeight: 700, color: '#ff6666', fontFamily: FONT}}>
            {verdict}
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
