/**
 * WorkspaceUtils — shared workspace primitives (Visual Director v4).
 *
 *  TaskCard   — SVG checklist card; the multi-step task continuity object.
 *               Render inside an <svg> (1080×1920 viewBox).
 *  ChatWidget — HTML chat-window frame that visually contains a
 *               ChatbotCharacter. The chatbot lives inside UI; the agent does not.
 *
 * Both derive all colors from the active ArtDirection, with dark fallbacks.
 */
import React from 'react';
import {ChatbotCharacter} from './CharacterUtils';
import type {ChatbotState} from './CharacterUtils';
import type {ArtDirection} from '../themes';

// ─── TaskCard ────────────────────────────────────────────────────────────────

export const TASK_CARD_W = 380;
const CARD_H_BASE = 120;
const CARD_STEP_H = 48;

export function taskCardHeight(stepCount: number): number {
  return CARD_H_BASE + stepCount * CARD_STEP_H;
}

interface TaskCardProps {
  x: number;
  y: number;
  steps: string[];
  completedSteps: number;
  accent2: string;
  title?: string;
  opacity?: number;
  /** Opacity of the COMPLETE badge (shown only when all steps are checked) */
  completeBadgeOpacity?: number;
  artDirection?: ArtDirection;
}

export const TaskCard: React.FC<TaskCardProps> = ({
  x,
  y,
  steps,
  completedSteps,
  accent2,
  title = '📋 Task Progress',
  opacity = 1,
  completeBadgeOpacity = 1,
  artDirection: ad,
}) => {
  const isLight = ad?.light_or_dark === 'light';
  const struct = (a: number): string =>
    isLight ? `rgba(0,0,0,${a})` : `rgba(255,255,255,${a})`;
  const textColor = ad?.palette.text ?? '#ffffff';
  const cardBg = ad?.zones?.task_card_bg ?? struct(0.05);
  const cardBorder = ad?.zones?.task_card_border ?? struct(0.12);
  const cardText = ad?.zones?.task_card_text ?? textColor;
  const allDone = completedSteps >= steps.length;

  return (
    <g opacity={opacity}>
      <rect
        x={x}
        y={y}
        width={TASK_CARD_W}
        height={taskCardHeight(steps.length)}
        rx={12}
        fill={cardBg}
        stroke={allDone ? accent2 : cardBorder}
        strokeWidth={allDone ? 2 : 1}
      />

      <text x={x + 20} y={y + 36} fontSize={18} fontWeight={700} fill={cardText}>
        {title}
      </text>

      {/* Progress bar */}
      <rect x={x + 20} y={y + 52} width={TASK_CARD_W - 40} height={4} rx={2} fill={struct(0.1)} />
      <rect
        x={x + 20}
        y={y + 52}
        width={(TASK_CARD_W - 40) * (steps.length > 0 ? Math.min(completedSteps, steps.length) / steps.length : 0)}
        height={4}
        rx={2}
        fill={accent2}
      />

      {/* Checklist items */}
      {steps.map((step, i) => {
        const stepY = y + 80 + i * CARD_STEP_H;
        const isChecked = i < completedSteps;
        return (
          <g key={`step-${i}`}>
            <rect
              x={x + 20}
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
                d={`M ${x + 25} ${stepY + 11} L ${x + 30} ${stepY + 16} L ${x + 37} ${stepY + 7}`}
                fill="none"
                stroke="#fff"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}
            <text
              x={x + 52}
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
      {allDone && (
        <g opacity={completeBadgeOpacity}>
          <rect x={x + TASK_CARD_W - 110} y={y + 16} width={90} height={28} rx={14} fill={accent2} />
          <text
            x={x + TASK_CARD_W - 65}
            y={y + 35}
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
  );
};

// ─── ChatWidget ──────────────────────────────────────────────────────────────

const CHAT_HEADER_H = 64;

interface ChatWidgetProps {
  width: number;
  height: number;
  title?: string;
  chatbotState?: ChatbotState;
  stateProgress?: number;
  artDirection?: ArtDirection;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

/**
 * A lightweight chat-window frame: header bar with window dots, the chatbot
 * avatar and a title; body holds the conversation content (children).
 */
export const ChatWidget: React.FC<ChatWidgetProps> = ({
  width,
  height,
  title = 'Chatbot',
  chatbotState = 'idle',
  stateProgress = 1,
  artDirection: ad,
  style,
  children,
}) => {
  const isLight = ad?.light_or_dark === 'light';
  const surface = ad?.palette.surface ?? 'rgba(255,255,255,0.05)';
  const border = ad?.palette.border ?? 'rgba(255,255,255,0.12)';
  const muted = ad?.palette.muted ?? 'rgba(255,255,255,0.53)';
  const text = ad?.palette.text ?? '#ffffff';
  const radius = ad?.surface_style.borderRadius ?? 16;
  const shadow = ad?.depth.shadow_lg ?? 'none';
  const font = ad?.typography.font ?? '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  const headerBg = isLight ? 'rgba(0,0,0,0.025)' : 'rgba(255,255,255,0.03)';
  const dot = isLight ? 'rgba(0,0,0,0.14)' : 'rgba(255,255,255,0.2)';
  const avatar = 44;

  return (
    <div
      style={{
        width,
        height,
        background: surface,
        border: `1px solid ${border}`,
        borderRadius: radius,
        boxShadow: shadow,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: font,
        ...style,
      }}
    >
      {/* Header bar */}
      <div
        style={{
          height: CHAT_HEADER_H,
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          padding: '0 20px',
          background: headerBg,
          borderBottom: `1px solid ${border}`,
        }}
      >
        <div style={{display: 'flex', gap: 7}}>
          {[0, 1, 2].map((i) => (
            <div key={i} style={{width: 11, height: 11, borderRadius: '50%', background: dot}} />
          ))}
        </div>
        <svg width={avatar} height={avatar} viewBox={`0 0 ${avatar} ${avatar}`} style={{marginLeft: 8}}>
          <ChatbotCharacter
            x={avatar / 2}
            y={avatar / 2}
            size={avatar - 6}
            state={chatbotState}
            stateProgress={stateProgress}
            artDirection={ad}
          />
        </svg>
        <div style={{fontSize: 22, fontWeight: 700, color: text}}>{title}</div>
        <div style={{marginLeft: 'auto', fontSize: 16, color: muted}}>
          {chatbotState === 'frozen' ? 'waiting…' : 'online'}
        </div>
      </div>

      {/* Body */}
      <div style={{position: 'relative', flex: 1}}>{children}</div>
    </div>
  );
};
