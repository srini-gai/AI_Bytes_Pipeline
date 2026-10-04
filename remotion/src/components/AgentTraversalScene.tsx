/**
 * AgentTraversalScene — Visual Director v4
 *
 * The visual centerpiece of the Agents vs Chatbots episode.
 *
 * An AgentCharacter moves rightward through labeled zones, picks up tool
 * icons from a utility belt, interacts with each zone's tool, and a task
 * card in the corner gains checkmarks as steps complete.
 *
 * Beat structure (flexible, driven by storyboard beats):
 *   B0: Scene establishes — zones visible, agent at start, task card appears
 *   B1: Agent enters zone 1, picks up tool, zone highlights
 *   B2: Agent enters zone 2, picks up tool, checkmark on step 1
 *   B3: Agent enters zone 3, picks up tool, checkmark on step 2
 *   B4: Agent reaches DONE zone, final checkmark, task card glows complete
 *
 * Props:
 *   - beats: timed visual events
 *   - onScreenText: zone labels [zone1, zone2, zone3, zone4] (e.g. SEARCH, BOOK, COMPOSE, DONE)
 *   - objects: tool icons per zone [tool1, tool2, tool3]
 *   - data.task_steps?: string[] — labels for the task card checklist
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {ACCENT, ACCENT2, FONT, easeOut, linearProgress} from './beatUtils';
import {AgentCharacter} from './CharacterUtils';
import type {SceneBeat} from '../types';
import type {ArtDirection} from '../themes';

interface AgentTraversalSceneProps {
  artDirection?: ArtDirection;
  beats: SceneBeat[];
  onScreenText: string[];
  objects: string[];
  accentColor?: string;
  accent2?: string;
  data?: {
    task_steps?: string[];
  };
}

// ─── Zone layout constants ───────────────────────────────────────────────────

const CANVAS_W = 1080;
const CANVAS_H = 1920;

// Zones are laid out horizontally across the middle band
const ZONE_Y = 850;
const ZONE_H = 280;
const ZONE_W = 220;
const ZONE_GAP = 30;
const ZONES_TOTAL_W = ZONE_W * 4 + ZONE_GAP * 3;
const ZONE_START_X = (CANVAS_W - ZONES_TOTAL_W) / 2;

// Agent vertical center within zone band
const AGENT_Y = ZONE_Y + ZONE_H / 2;

// Task card position (upper-right area)
const CARD_X = 620;
const CARD_Y = 380;
const CARD_W = 380;
const CARD_H_BASE = 120;
const CARD_STEP_H = 48;

function zoneX(index: number): number {
  return ZONE_START_X + index * (ZONE_W + ZONE_GAP) + ZONE_W / 2;
}

// ─── Component ───────────────────────────────────────────────────────────────

export const AgentTraversalScene: React.FC<AgentTraversalSceneProps> = ({
  beats,
  onScreenText,
  objects,
  accentColor = ACCENT,
  accent2 = ACCENT2,
  data,
  artDirection: ad,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const bgColor = ad?.palette.bg ?? '#050510';
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.font ?? 'Inter';
  const useGlow = ad?.depth.use_glow ?? true;
  const isLight = ad?.light_or_dark === 'light';
  const struct = (a: number): string =>
    isLight ? `rgba(0,0,0,${a})` : `rgba(255,255,255,${a})`;
  const trackFill = ad?.zones?.track_fill ?? struct(0.03);
  const trackStroke = ad?.zones?.track_stroke ?? struct(0.06);
  const zoneLabelColor = ad?.zones?.label_color ?? textColor;
  const cardBg = ad?.zones?.task_card_bg ?? struct(0.05);
  const cardBorder = ad?.zones?.task_card_border ?? struct(0.12);
  const cardText = ad?.zones?.task_card_text ?? textColor;

  // Zone labels from onScreenText
  const zones = [
    onScreenText[0] ?? 'SEARCH',
    onScreenText[1] ?? 'BOOK',
    onScreenText[2] ?? 'COMPOSE',
    onScreenText[3] ?? 'DONE',
  ];

  // Tool icons from objects
  const tools = [
    objects[0] ?? '🔍',
    objects[1] ?? '📅',
    objects[2] ?? '✉️',
  ];

  // Task card steps
  const taskSteps = data?.task_steps ?? [
    'Find flights',
    'Book hotel',
    'Send itinerary',
  ];

  // Beat progress values
  const b = beats.map((beat) => ({
    progress: easeOut(frame, fps, beat.start, beat.end),
    linear: linearProgress(frame, fps, beat.start, beat.end),
    started: frame >= Math.round(beat.start * fps),
    ended: frame >= Math.round(beat.end * fps),
  }));

  // Ensure we have 5 beats (pad with defaults if fewer)
  while (b.length < 5) {
    b.push({progress: 0, linear: 0, started: false, ended: false});
  }

  // ── Agent position (interpolates across zones)
  const agentZoneIndex = b[4].started ? 3
    : b[3].started ? 2
    : b[2].started ? 1
    : b[1].started ? 0
    : -0.5; // start position: left of zone 0

  const prevZoneX = agentZoneIndex <= 0 ? ZONE_START_X - 60 : zoneX(Math.floor(agentZoneIndex));
  const nextZoneX = zoneX(Math.min(3, Math.max(0, Math.ceil(agentZoneIndex))));

  // Use the current beat's progress for smooth movement
  const currentBeatIdx = b[4].started ? 4
    : b[3].started ? 3
    : b[2].started ? 2
    : b[1].started ? 1 : 0;
  const moveProgress = b[currentBeatIdx]?.progress ?? 0;

  const agentX = agentZoneIndex < 0
    ? interpolate(b[0].progress, [0, 1], [ZONE_START_X - 100, zoneX(0) - ZONE_W * 0.3], {extrapolateRight: 'clamp'})
    : interpolate(moveProgress, [0, 0.5], [prevZoneX, nextZoneX], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // Active tool slot
  const activeSlot = b[4].started ? -1
    : b[3].started ? 2
    : b[2].started ? 1
    : b[1].started ? 0 : -1;

  // Agent state
  const agentState = b[4].ended ? 'done' as const
    : b[1].started ? 'active' as const
    : 'idle' as const;

  // How many checkmarks to show
  const checksComplete = (b[4].started ? 3 : 0)
    + (b[3].started && !b[4].started ? 2 : 0)
    + (b[2].started && !b[3].started ? 1 : 0);
  const completedSteps = b[4].started ? 3 : b[3].started ? 2 : b[2].started ? 1 : 0;

  // Scene entrance
  const sceneOpacity = interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: bgColor, fontFamily: ad ? `${fontFamily}, sans-serif` : FONT}}>
      <svg
        viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
        style={{width: '100%', height: '100%', opacity: sceneOpacity}}
      >
        {/* ── Zone track (background lane) ── */}
        <rect
          x={ZONE_START_X - 20}
          y={ZONE_Y - 10}
          width={ZONES_TOTAL_W + 40}
          height={ZONE_H + 20}
          rx={16}
          fill={trackFill}
          stroke={trackStroke}
          strokeWidth={1}
        />

        {/* ── Connecting arrows between zones ── */}
        {[0, 1, 2].map((i) => {
          const x1 = zoneX(i) + ZONE_W / 2 - 10;
          const x2 = zoneX(i + 1) - ZONE_W / 2 + 10;
          const arrowY = ZONE_Y + ZONE_H / 2;
          const showArrow = b[i + 1]?.started ?? false;
          return (
            <g key={`arrow-${i}`} opacity={showArrow ? 1 : 0.2}>
              <line
                x1={x1} y1={arrowY}
                x2={x2 - 8} y2={arrowY}
                stroke={showArrow ? accentColor : struct(0.15)}
                strokeWidth={2}
                strokeDasharray={showArrow ? 'none' : '4 4'}
              />
              <polygon
                points={`${x2 - 8},${arrowY - 5} ${x2},${arrowY} ${x2 - 8},${arrowY + 5}`}
                fill={showArrow ? accentColor : struct(0.15)}
              />
            </g>
          );
        })}

        {/* ── Zones ── */}
        {zones.map((label, i) => {
          const cx = zoneX(i);
          const isActive = i < 3 ? b[i + 1]?.started ?? false : b[4]?.started ?? false;
          const isComplete = i < 3 ? (completedSteps > i) : b[4]?.ended ?? false;
          const isDone = i === 3;

          const zoneColor = isComplete
            ? accent2
            : isActive
              ? accentColor
              : struct(0.08);

          const borderColor = isComplete
            ? accent2
            : isActive
              ? accentColor
              : struct(0.12);

          return (
            <g key={`zone-${i}`}>
              {/* Zone box */}
              <rect
                x={cx - ZONE_W / 2}
                y={ZONE_Y}
                width={ZONE_W}
                height={ZONE_H}
                rx={12}
                fill={isActive || isComplete ? `${zoneColor}15` : struct(0.02)}
                stroke={borderColor}
                strokeWidth={isActive ? 2 : 1}
                style={useGlow && isActive ? {filter: `drop-shadow(0 0 12px ${zoneColor})`} : undefined}
              />

              {/* Zone label */}
              <text
                x={cx}
                y={ZONE_Y + 36}
                textAnchor="middle"
                fontSize={20}
                fontWeight={700}
                letterSpacing={2}
                fill={isActive || isComplete ? zoneLabelColor : (isLight ? 'rgba(0,0,0,0.4)' : 'rgba(255,255,255,0.4)')}
              >
                {label}
              </text>

              {/* Tool icon in zone (for zones 0-2) */}
              {i < 3 && (
                <text
                  x={cx}
                  y={ZONE_Y + ZONE_H - 50}
                  textAnchor="middle"
                  fontSize={36}
                  opacity={isActive || isComplete ? 1 : 0.3}
                >
                  {tools[i]}
                </text>
              )}

              {/* DONE zone: checkmark when complete */}
              {isDone && isComplete && (
                <g>
                  <circle
                    cx={cx}
                    cy={ZONE_Y + ZONE_H / 2 + 20}
                    r={30}
                    fill={accent2}
                    opacity={b[4].progress}
                  />
                  <path
                    d={`M ${cx - 12} ${ZONE_Y + ZONE_H / 2 + 20} L ${cx - 2} ${ZONE_Y + ZONE_H / 2 + 30} L ${cx + 14} ${ZONE_Y + ZONE_H / 2 + 8}`}
                    fill="none"
                    stroke="#fff"
                    strokeWidth={3.5}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    opacity={b[4].progress}
                  />
                </g>
              )}
            </g>
          );
        })}

        {/* ── Agent character ── */}
        <AgentCharacter
          x={agentX}
          y={AGENT_Y + 30}
          size={90}
          state={agentState}
          stateProgress={b[currentBeatIdx]?.linear ?? 0}
          artDirection={ad}
          accentColor={accentColor}
          accent2={accent2}
          activeToolSlot={activeSlot}
          toolIcons={tools}
        />

        {/* ── Task card (upper right) ── */}
        <g opacity={b[0].progress}>
          {/* Card background */}
          <rect
            x={CARD_X}
            y={CARD_Y}
            width={CARD_W}
            height={CARD_H_BASE + taskSteps.length * CARD_STEP_H}
            rx={12}
            fill={cardBg}
            stroke={completedSteps >= taskSteps.length ? accent2 : cardBorder}
            strokeWidth={completedSteps >= taskSteps.length ? 2 : 1}
          />

          {/* Card title */}
          <text
            x={CARD_X + 20}
            y={CARD_Y + 36}
            fontSize={18}
            fontWeight={700}
            fill={cardText}
          >
            📋 Task Progress
          </text>

          {/* Progress bar */}
          <rect
            x={CARD_X + 20}
            y={CARD_Y + 52}
            width={CARD_W - 40}
            height={4}
            rx={2}
            fill={struct(0.1)}
          />
          <rect
            x={CARD_X + 20}
            y={CARD_Y + 52}
            width={(CARD_W - 40) * (completedSteps / taskSteps.length)}
            height={4}
            rx={2}
            fill={accent2}
          />

          {/* Checklist items */}
          {taskSteps.map((step, i) => {
            const stepY = CARD_Y + 80 + i * CARD_STEP_H;
            const isChecked = i < completedSteps;
            return (
              <g key={`step-${i}`}>
                {/* Checkbox */}
                <rect
                  x={CARD_X + 20}
                  y={stepY}
                  width={22}
                  height={22}
                  rx={4}
                  fill={isChecked ? accent2 : 'transparent'}
                  stroke={isChecked ? accent2 : struct(0.2)}
                  strokeWidth={1.5}
                />
                {isChecked && (
                  <path
                    d={`M ${CARD_X + 25} ${stepY + 11} L ${CARD_X + 30} ${stepY + 16} L ${CARD_X + 37} ${stepY + 7}`}
                    fill="none"
                    stroke="#fff"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                )}
                {/* Step label */}
                <text
                  x={CARD_X + 52}
                  y={stepY + 16}
                  fontSize={16}
                  fill={isChecked ? cardText : (isLight ? 'rgba(0,0,0,0.5)' : 'rgba(255,255,255,0.5)')}
                  textDecoration={isChecked ? 'line-through' : 'none'}
                >
                  {step}
                </text>
              </g>
            );
          })}

          {/* Complete badge */}
          {completedSteps >= taskSteps.length && (
            <g opacity={b[4].progress}>
              <rect
                x={CARD_X + CARD_W - 110}
                y={CARD_Y + 16}
                width={90}
                height={28}
                rx={14}
                fill={accent2}
              />
              <text
                x={CARD_X + CARD_W - 65}
                y={CARD_Y + 35}
                textAnchor="middle"
                fontSize={13}
                fontWeight={700}
                fill="#fff"
              >
                COMPLETE
              </text>
            </g>
          )}
        </g>

        {/* ── Scene title (top area) ── */}
        <text
          x={CANVAS_W / 2}
          y={300}
          textAnchor="middle"
          fontSize={28}
          fontWeight={700}
          fill={textColor}
          opacity={b[0].progress}
        >
          {onScreenText[4] ?? ''}
        </text>
      </svg>
    </AbsoluteFill>
  );
};
