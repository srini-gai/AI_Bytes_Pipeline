/**
 * TransformScene — Visual Director v3 (data-driven)
 *
 * Shows an A→B transformation: items appear, change, combine or rearrange.
 * Beat-driven: each item stamps in on its own beat; final beat
 * reveals the assembled summary label.
 *
 * All display content comes from props — no topic-specific defaults.
 * Item icons come only from data.icons; items without one render no icon.
 * Optional data.frame='chat_widget' contains the items in a chatbot window;
 * optional data.task_card shows the continuity task card (upper right).
 * Production guard: throws if onScreenText has fewer than 3 entries.
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BG, ACCENT, ACCENT2, FONT, easeOut, linearProgress, smoothstep} from './beatUtils';
import {ChatWidget, TaskCard} from './WorkspaceUtils';
import type {SceneBeat, TransformSceneData} from '../types';
import type {ArtDirection} from '../themes';

interface TransformItem {
  /** Primary display text (the main visual — a token, a letter, a label) */
  primary: string;
  /** Secondary label below the primary */
  label: string;
  /** Icon/emoji between primary and label */
  icon: string;
  color: string;
}

interface TransformSceneProps {
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  artDirection?: ArtDirection;
  data?: TransformSceneData;
  /** Scene length; used to keep the summary label on screen long enough to read */
  durationInFrames?: number;
}

/** Minimum time the summary label stays fully visible before the scene fades out */
const SUMMARY_MIN_READ_SEC = 1.5;
const SUMMARY_RAMP_SEC = 0.4;
const SCENE_FADE_OUT_SEC = 0.3;

/**
 * Parse onScreenText entries like "un → 1726" into primary/label pairs.
 * Falls back to using the entry as-is for both primary and label.
 */
function parseTransformEntry(entry: string, color: string, icon: string): TransformItem {
  const arrowIdx = entry.indexOf('→');
  if (arrowIdx >= 0) {
    return {
      primary: entry.substring(0, arrowIdx).trim(),
      label: entry.substring(arrowIdx + 1).trim(),
      icon,
      color,
    };
  }
  return {primary: entry, label: '', icon, color};
}

const ITEM_COLORS = ['#6366f1', '#a78bfa', '#34d399'];

export const TransformScene: React.FC<TransformSceneProps> = ({
  beats,
  onScreenText,
  accentColor = ACCENT,
  accent2 = ACCENT2,
  artDirection: ad,
  data,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const icons = data?.icons ?? [];
  const chatFrame = data?.frame === 'chat_widget';
  const taskCard = data?.task_card;

  // Art-direction overrides with fallbacks to hardcoded defaults
  const ITEM_COLORS_THEMED = ad?.item_colors ?? ITEM_COLORS;
  const bgColor = ad?.palette.bg ?? BG;
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.font ?? FONT;
  const useGlow = ad?.depth.use_glow ?? true;

  // Production guard: require at least 3 onScreenText entries for transform items
  if (onScreenText.length < 3) {
    throw new Error(
      `[PRODUCTION GUARD] TransformScene: onScreenText must have ≥3 entries, got ${onScreenText.length}. ` +
      `Populate the storyboard on_screen_text with transform data.`
    );
  }

  // Build items from onScreenText — first N-1 entries are transform items, last is summary label
  const summaryLabel = onScreenText[onScreenText.length - 1];
  const itemEntries = onScreenText.slice(0, -1);

  const items: TransformItem[] = itemEntries.map((entry, i) =>
    parseTransformEntry(
      entry,
      ITEM_COLORS_THEMED[i % ITEM_COLORS_THEMED.length],
      icons[i] ?? '',
    )
  );

  // Each of the first N beats: one item stamps in
  const letterProgress = items.map((_, i) => {
    const beat = beats[i] ?? {start: i * 1.0, end: i * 1.0 + 1.0};
    return easeOut(frame, fps, beat.start, beat.end);
  });

  // Final beat: connector lines draw
  const finalBeatIdx = items.length;
  const b3 = beats[finalBeatIdx] ?? {start: finalBeatIdx * 1.0, end: finalBeatIdx * 1.0 + 2.0};
  const lineProgress = linearProgress(frame, fps, b3.start, b3.start + (b3.end - b3.start) * 0.6);
  const lineSmooth   = smoothstep(lineProgress);

  // Camera push-in on final beat: scale up slightly
  const camScale = interpolate(
    linearProgress(frame, fps, b3.start, b3.end),
    [0, 1],
    [1, 1.06],
  );

  // Summary label reveal: starts at the final beat, but early enough that it is
  // fully visible for SUMMARY_MIN_READ_SEC before the scene's fade-out.
  const sceneSec = durationInFrames ? durationInFrames / fps : b3.end;
  const latestReveal = sceneSec - SCENE_FADE_OUT_SEC - SUMMARY_MIN_READ_SEC - SUMMARY_RAMP_SEC;
  const summaryStart = Math.max(0, Math.min(b3.start, latestReveal));
  const summaryOpacity = linearProgress(frame, fps, summaryStart, summaryStart + SUMMARY_RAMP_SEC);

  const sceneOpacity = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  // Card width shrinks only when items would not fit the canvas (or chat frame)
  const CARD_GAP = 48;
  const MAX_ROW_W = chatFrame ? 900 : 1000;
  const CARD_W = Math.min(240, Math.floor((MAX_ROW_W - (items.length - 1) * CARD_GAP) / items.length));
  const TOTAL_W  = items.length * CARD_W + (items.length - 1) * CARD_GAP;

  // Chat widget frame geometry (relative to the item row container)
  const FRAME_PAD_X = 50;
  const FRAME_TOP = -60;
  const FRAME_H = 400;
  const firstBeat = beats[0] ?? {start: 0, end: 1};
  const chatbotActive = letterProgress.some((p) => p > 0 && p < 1);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: bgColor,
        opacity: sceneOpacity,
        overflow: 'hidden',
      }}
    >
      {/* Background glow */}
      {useGlow && (
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse 800px 500px at 50% 48%, ${accentColor}10 0%, transparent 70%)`,
          }}
        />
      )}

      {/* Main canvas — centred vertically at 46% */}
      <AbsoluteFill
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transform: `scale(${camScale})`,
          transformOrigin: '50% 46%',
        }}
      >
        <div style={{position: 'relative', width: TOTAL_W, paddingTop: 100}}>
          {/* Chat widget frame — the chatbot is contained inside its window */}
          {chatFrame && (
            <ChatWidget
              width={TOTAL_W + FRAME_PAD_X * 2}
              height={FRAME_H}
              title={data?.chat_title}
              chatbotState={chatbotActive ? 'active' : 'idle'}
              stateProgress={(frame % fps) / fps}
              artDirection={ad}
              style={{position: 'absolute', left: -FRAME_PAD_X, top: FRAME_TOP}}
            />
          )}

          {/* Transform item cards */}
          {items.map((item, i) => {
            const p = letterProgress[i];
            const x = i * (CARD_W + CARD_GAP);
            const y = interpolate(p, [0, 1], [-120, 0]);
            const scale = interpolate(p, [0, 0.7, 1], [0.3, 1.12, 1]);
            const alpha = interpolate(p, [0, 0.3], [0, 1], {extrapolateRight: 'clamp'});

            return (
              <div
                key={`item-${i}`}
                style={{
                  position: 'absolute',
                  left: x,
                  width: CARD_W,
                  opacity: alpha,
                  transform: `translateY(${y}px) scale(${scale})`,
                  transformOrigin: '50% 100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 16,
                }}
              >
                {/* Primary text */}
                <div
                  style={{
                    fontFamily: fontFamily,
                    fontSize: 72,
                    fontWeight: 900,
                    color: item.color,
                    lineHeight: 1,
                    textShadow: useGlow ? `0 0 80px ${item.color}66` : 'none',
                    letterSpacing: -2,
                    textAlign: 'center',
                  }}
                >
                  {item.primary}
                </div>

                {/* Icon below primary — only when scene data supplies one */}
                {item.icon && (
                <div
                  style={{
                    fontSize: 42,
                    transform: `scale(${interpolate(p, [0.5, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})})`,
                    filter: useGlow ? `drop-shadow(0 0 16px ${item.color}88)` : 'none',
                  }}
                >
                  {item.icon}
                </div>
                )}

                {/* Label */}
                {item.label && (
                  <div
                    style={{
                      fontFamily: fontFamily,
                      fontSize: 30,
                      fontWeight: 700,
                      color: item.color,
                      letterSpacing: 2,
                      opacity: interpolate(p, [0.6, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
                      textAlign: 'center',
                    }}
                  >
                    {item.label}
                  </div>
                )}
              </div>
            );
          })}

          {/* Connector arrows (draw on final beat) */}
          {items.slice(0, -1).map((_, i) => {
            const lineStart = i / (items.length - 1);
            const lineEnd   = (i + 1) / (items.length - 1);
            const segP = smoothstep(
              interpolate(lineSmooth, [lineStart * 0.8, lineEnd * 0.8], [0, 1], {
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              }),
            );
            const x1 = i * (CARD_W + CARD_GAP) + CARD_W;

            return (
              <div
                key={`line-${i}`}
                style={{
                  position: 'absolute',
                  left: x1,
                  top: 72,
                  width: segP * CARD_GAP,
                  height: 3,
                  background: `linear-gradient(90deg, ${items[i].color}, ${items[i + 1].color})`,
                  borderRadius: 2,
                  boxShadow: useGlow ? `0 0 10px ${accentColor}66` : 'none',
                  opacity: lineSmooth > 0.05 ? 1 : 0,
                }}
              />
            );
          })}
        </div>
      </AbsoluteFill>

      {/* Summary label that appears on final beat */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'flex-end',
          paddingBottom: 200,
          opacity: summaryOpacity,
        }}
      >
        <div
          style={{
            fontFamily: fontFamily,
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: 8,
            textTransform: 'uppercase',
            color: ad?.palette.primary ?? accentColor,
          }}
        >
          {summaryLabel}
        </div>
      </AbsoluteFill>

      {/* Continuity task card — same position as AgentTraversalScene */}
      {taskCard && (
        <AbsoluteFill>
          <svg viewBox="0 0 1080 1920" style={{width: '100%', height: '100%'}}>
            <g transform={`translate(${interpolate(easeOut(frame, fps, firstBeat.start, firstBeat.end), [0, 1], [160, 0])}, 0)`}>
              <TaskCard
                x={620}
                y={380}
                steps={taskCard.steps}
                completedSteps={taskCard.completed ?? 0}
                title={taskCard.title}
                accent2={accent2}
                opacity={easeOut(frame, fps, firstBeat.start, firstBeat.end)}
                artDirection={ad}
              />
            </g>
          </svg>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
