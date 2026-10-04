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
 *
 * v4 workspace extras (beat mode, opt-in via `workspace`):
 * - left/right_character 'chatbot' → ChatbotCharacter contained in a ChatWidget frame
 * - left/right_character 'agent'   → free-moving AgentCharacter (no frame)
 * - agent_motion 'enter_plan_go'   → agent enters (beat 1), pauses, exits right (beat 2)
 * - task_card                      → continuity task card hands off left → right (beat 1)
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SplitCompareSpec, SideBySideSpec} from '../types';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';
import {easeOut, linearProgress, smoothstep} from './beatUtils';
import {AgentCharacter, ChatbotCharacter} from './CharacterUtils';
import {ChatWidget, TaskCard, TASK_CARD_W} from './WorkspaceUtils';
import type {PanelCharacter, SplitCompareWorkspace} from '../types';

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
  artDirection?: ArtDirection;
  workspace?: SplitCompareWorkspace;
}

// Workspace extras layout (beat mode)
const CHAT_WIDGET_TOP = PANEL_TOP + 360;
const CHAT_WIDGET_H = 300;
const AGENT_HOME_Y = PANEL_TOP + 520;
const TASK_CARD_Y = PANEL_TOP + 720;

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

export const SplitCompareScene: React.FC<SplitCompareSceneProps> = ({spec, theme, beats, onScreenText, artDirection: ad, workspace}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = theme ?? DEFAULT_THEME;

  // Art-direction derived values with backward-compatible fallbacks
  const bgColor = ad?.palette.bg ?? '#050510';
  const fontFamily = ad?.typography.font ?? FONT;
  const useGlow = ad?.depth.use_glow ?? true;
  const panelText = ad?.split_compare?.panel_text ?? 'rgba(255,255,255,0.88)';
  const vsBg = ad?.split_compare?.vs_bg ?? '#1a1a2e';
  const vsText = ad?.split_compare?.vs_text ?? 'rgba(255,255,255,0.6)';
  const verdictColor = ad?.palette.danger ?? '#ff4444';
  const verdictBgOpacity = ad?.split_compare?.verdict_bg_opacity ?? '15';

  // ── v3 beat-driven mode ──────────────────────────────────────────────────
  if (beats && beats.length >= 2) {
    const leftP  = easeOut(frame, fps, beats[0].start, beats[0].end);
    const rightP = easeOut(frame, fps, beats[1].start, beats[1].end);
    const verdP  = beats[2] ? easeOut(frame, fps, beats[2].start, beats[2].end) : rightP;
    // No fade-in: content present from frame 1
    const isSplit   = spec.type === 'split_compare';
    const leftCol   = isSplit ? (ad?.split_compare?.left_color ?? '#ff4444') : t.accent;
    const rightCol  = isSplit ? (ad?.split_compare?.right_color ?? '#22c55e') : t.accent2;
    const verdict   = spec.type === 'split_compare' ? spec.verdict : undefined;

    return (
      <AbsoluteFill style={{backgroundColor: bgColor}}>
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
              fontFamily: fontFamily, fontSize: 38, fontWeight: 900, color: leftCol,
              textAlign: 'center', marginBottom: 28,
              textShadow: useGlow ? `0 0 24px ${leftCol}66` : 'none',
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
                <div style={{fontSize: 30, color: panelText, fontFamily: fontFamily, lineHeight: 1.45}}>
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
          width: 52, height: 52, borderRadius: '50%', background: vsBg,
          border: `2px solid ${t.accent}66`, display: 'flex', alignItems: 'center',
          justifyContent: 'center', zIndex: 5, fontSize: 18, fontWeight: 900,
          color: vsText, fontFamily: fontFamily,
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
              fontFamily: fontFamily, fontSize: 38, fontWeight: 900, color: rightCol,
              textAlign: 'center', marginBottom: 28,
              textShadow: useGlow ? `0 0 24px ${rightCol}66` : 'none',
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
                <div style={{fontSize: 30, color: panelText, fontFamily: fontFamily, lineHeight: 1.45}}>
                  {pt}
                </div>
              </div>
            ))}
          </div>
        </div>

        {workspace && renderWorkspace(workspace, beats, frame, fps, leftP, rightP, ad)}

        {/* Verdict */}
        {verdict && verdP > 0.1 && (
          <div style={{
            position: 'absolute', bottom: 160, left: 40, right: 40,
            opacity: smoothstep(verdP),
            transform: `translateY(${interpolate(verdP, [0, 1], [24, 0])}px)`,
            zIndex: 3,
            backgroundColor: `${verdictColor}${verdictBgOpacity}`,
            border: '2px solid rgba(255,68,68,0.4)',
            borderRadius: 20, padding: '22px 32px', textAlign: 'center',
          }}>
            <div style={{fontSize: 40, fontWeight: 900, color: ad?.palette.danger ?? '#ff6666', fontFamily: fontFamily}}>
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
    <AbsoluteFill style={{backgroundColor: bgColor}}>
      <AbsoluteFill style={{
        background: 'linear-gradient(to bottom, transparent 72%, rgba(0,0,0,0.82) 100%)',
      }}/>
      <div style={{
        position: 'absolute', top: 136, left: 0, right: 0,
        textAlign: 'center', opacity: titleOpacity, zIndex: 2,
        fontSize: 26, letterSpacing: 6, textTransform: 'uppercase' as const,
        color: t.accent, fontFamily: fontFamily, fontWeight: 700,
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
        color: 'rgba(255,255,255,0.6)', fontFamily: fontFamily,
      }}>VS</div>

      {verdict && (
        <div style={{
          position: 'absolute', bottom: 220, left: 40, right: 40,
          opacity: verdictOpacity, transform: `translateY(${verdictY}px)`,
          zIndex: 3, backgroundColor: 'rgba(255,68,68,0.15)',
          border: '1.5px solid rgba(255,68,68,0.4)', borderRadius: 16,
          padding: '18px 28px', textAlign: 'center',
        }}>
          <div style={{fontSize: 36, fontWeight: 700, color: '#ff6666', fontFamily: fontFamily}}>
            {verdict}
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ─── v4 workspace extras ─────────────────────────────────────────────────────

function panelLeft(side: 'left' | 'right'): number {
  return side === 'left' ? LEFT_X : RIGHT_X;
}

function renderWorkspace(
  ws: SplitCompareWorkspace,
  beats: SceneBeat[],
  frame: number,
  fps: number,
  leftP: number,
  rightP: number,
  ad: ArtDirection | undefined,
): React.ReactNode {
  const accent2 = ad?.palette.success ?? '#34d399';
  const b1 = beats[1];
  const b2 = beats[2];
  const sides: Array<['left' | 'right', PanelCharacter | undefined, number]> = [
    ['left', ws.left_character, leftP],
    ['right', ws.right_character, rightP],
  ];

  // Agent motion: enter during beat 1, pause, head off-panel right during beat 2
  const agentHomeX = (side: 'left' | 'right'): number => panelLeft(side) + COL_W / 2;
  const enterP = b1 ? easeOut(frame, fps, b1.start, b1.start + (b1.end - b1.start) * 0.5) : 1;
  const exitP = b2 ? easeOut(frame, fps, b2.start, b2.end) : 0;
  const moving = ws.agent_motion === 'enter_plan_go';

  // Task card handoff: second half of beat 1, after the agent has arrived
  const handoffP = b1 ? easeOut(frame, fps, b1.start + (b1.end - b1.start) * 0.5, b1.end) : 0;
  const cardX = (side: 'left' | 'right'): number => panelLeft(side) + (COL_W - TASK_CARD_W) / 2;

  return (
    <>
      {/* Chatbot: always contained inside a chat widget frame */}
      {sides.map(([side, character, p]) => character === 'chatbot' && (
        <div
          key={`chat-${side}`}
          style={{
            position: 'absolute',
            top: CHAT_WIDGET_TOP,
            left: panelLeft(side) + 32,
            opacity: p,
            transform: `translateX(${interpolate(p, [0, 1], [side === 'left' ? -180 : 180, 0])}px)`,
            zIndex: 3,
          }}
        >
          <ChatWidget
            width={COL_W - 64}
            height={CHAT_WIDGET_H}
            title={ws.chat_title}
            chatbotState="frozen"
            stateProgress={(frame % (fps * 2)) / (fps * 2)}
            artDirection={ad}
          >
            <svg width={COL_W - 64} height={CHAT_WIDGET_H - 64}>
              <ChatbotCharacter
                x={90}
                y={(CHAT_WIDGET_H - 64) / 2}
                size={110}
                state="frozen"
                stateProgress={(frame % (fps * 2)) / (fps * 2)}
                artDirection={ad}
              />
              {/* Last reply bubble — the chatbot waits for the next prompt */}
              <rect
                x={170}
                y={(CHAT_WIDGET_H - 64) / 2 - 30}
                width={190}
                height={60}
                rx={20}
                fill={ad?.light_or_dark === 'light' ? '#F1F5F9' : 'rgba(255,255,255,0.08)'}
              />
              {[0, 1, 2].map((i) => (
                <circle
                  key={i}
                  cx={235 + i * 30}
                  cy={(CHAT_WIDGET_H - 64) / 2}
                  r={7}
                  fill={ad?.palette.passive ?? '#94A3B8'}
                  opacity={0.4 + 0.6 * Math.abs(Math.sin((frame / fps) * Math.PI + i * 0.6))}
                />
              ))}
            </svg>
          </ChatWidget>
        </div>
      ))}

      {/* Agent + task card share one full-canvas SVG so they can cross panel borders */}
      <svg
        viewBox="0 0 1080 1920"
        style={{position: 'absolute', inset: 0, width: '100%', height: '100%', zIndex: 4, pointerEvents: 'none'}}
      >
        {ws.task_card && (
          <TaskCard
            x={interpolate(handoffP, [0, 1], [cardX('left'), cardX('right')])}
            y={TASK_CARD_Y}
            steps={ws.task_card.steps}
            completedSteps={ws.task_card.completed ?? 0}
            title={ws.task_card.title}
            accent2={accent2}
            opacity={leftP}
            artDirection={ad}
          />
        )}

        {sides.map(([side, character, p]) => {
          if (character !== 'agent') return null;
          const home = agentHomeX(side);
          const x = moving
            ? interpolate(enterP, [0, 1], [1180, home]) + interpolate(exitP, [0, 1], [0, 420])
            : home;
          const state = moving ? (exitP > 0 ? 'active' as const : 'idle' as const) : 'active' as const;
          return (
            <AgentCharacter
              key={`agent-${side}`}
              x={x}
              y={AGENT_HOME_Y}
              size={120}
              state={state}
              stateProgress={(frame % fps) / fps}
              opacity={moving ? Math.min(1, enterP * 1.5) : p}
              artDirection={ad}
            />
          );
        })}
      </svg>
    </>
  );
}
