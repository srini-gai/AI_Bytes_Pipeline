/**
 * CharacterUtils — Shared SVG character primitives for AI Bytes.
 *
 * Two character archetypes used across multiple scenes in the
 * Agents vs Chatbots episode (and reusable in future episodes):
 *
 *  ChatbotCharacter — round, static, simple
 *    States: idle (neutral), active (talking/responding), frozen (stuck/waiting)
 *
 *  AgentCharacter — angular, dynamic, tool slots
 *    States: idle (neutral), active (executing), done (task complete)
 *
 * Both characters are pure SVG, accept size/position props, and animate
 * state transitions via interpolation helpers.
 */
import React from 'react';
import {interpolate} from 'remotion';
import type {ArtDirection} from '../themes';

// ─── Types ───────────────────────────────────────────────────────────────────

export type ChatbotState = 'idle' | 'active' | 'frozen';
export type AgentState = 'idle' | 'active' | 'done';

interface CharacterBaseProps {
  x: number;
  y: number;
  size?: number;
  opacity?: number;
}

export interface ChatbotCharacterProps extends CharacterBaseProps {
  state: ChatbotState;
  /** 0→1 progress through current state transition */
  stateProgress?: number;
  accentColor?: string;
  artDirection?: ArtDirection;
}

export interface AgentCharacterProps extends CharacterBaseProps {
  state: AgentState;
  stateProgress?: number;
  accentColor?: string;
  accent2?: string;
  /** Which tool slot is active (0-based index, -1 = none) */
  activeToolSlot?: number;
  /** Tool icons to show in belt slots */
  toolIcons?: string[];
  artDirection?: ArtDirection;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const CHATBOT_COLOR_IDLE    = '#6366f1';
const CHATBOT_COLOR_ACTIVE  = '#818cf8';
const CHATBOT_COLOR_FROZEN  = '#475569';

const AGENT_COLOR_IDLE   = '#a78bfa';
const AGENT_COLOR_ACTIVE = '#c4b5fd';
const AGENT_COLOR_DONE   = '#34d399';

// ─── ChatbotCharacter ────────────────────────────────────────────────────────

/**
 * Round, simple chatbot character.
 * - Circular body with a chat-bubble "mouth"
 * - Eyes that blink in active state
 * - Greys out and shows ellipsis in frozen state
 */
export const ChatbotCharacter: React.FC<ChatbotCharacterProps> = ({
  x,
  y,
  size = 80,
  opacity = 1,
  state,
  stateProgress = 1,
  accentColor,
  artDirection: ad,
}) => {
  const r = size / 2;

  // Derive chatbot colors from art direction with fallbacks
  const idleColor = ad?.character_chatbot?.idle ?? CHATBOT_COLOR_IDLE;
  const activeColor = ad?.character_chatbot?.active ?? CHATBOT_COLOR_ACTIVE;
  const frozenColor = ad?.character_chatbot?.frozen ?? CHATBOT_COLOR_FROZEN;
  const isLight = ad?.light_or_dark === 'light';
  // Explicit accentColor prop wins; otherwise use the themed idle color
  const baseColor = accentColor ?? idleColor;

  // Foreground alpha helper: dark themes use white, light themes use black
  const fgAlpha = (a: number) =>
    isLight ? `rgba(0,0,0,${a})` : `rgba(255,255,255,${a})`;

  const eyeFill = ad?.palette?.text ?? '#fff';
  const pupilFill = ad?.palette?.bg ?? '#1e1b4b';

  // Color by state
  const bodyColor = state === 'frozen'
    ? lerpColor(baseColor, frozenColor, stateProgress)
    : state === 'active'
      ? lerpColor(baseColor, activeColor, stateProgress)
      : baseColor;

  // Frozen state: subtle pulse
  const frozenScale = state === 'frozen'
    ? 1 - 0.03 * Math.sin(stateProgress * Math.PI * 2)
    : 1;

  // Active state: gentle bob
  const bobY = state === 'active'
    ? Math.sin(stateProgress * Math.PI * 4) * 3
    : 0;

  return (
    <g
      transform={`translate(${x}, ${y + bobY}) scale(${frozenScale})`}
      opacity={opacity}
    >
      {/* Body — circle */}
      <circle
        cx={0}
        cy={0}
        r={r}
        fill={bodyColor}
        stroke={fgAlpha(0.15)}
        strokeWidth={2}
      />

      {/* Inner glow ring */}
      <circle
        cx={0}
        cy={0}
        r={r * 0.85}
        fill="none"
        stroke={fgAlpha(0.08)}
        strokeWidth={1}
      />

      {/* Eyes */}
      <circle cx={-r * 0.3} cy={-r * 0.15} r={r * 0.1} fill={eyeFill} />
      <circle cx={r * 0.3} cy={-r * 0.15} r={r * 0.1} fill={eyeFill} />

      {/* Pupils — shift slightly based on state */}
      <circle
        cx={-r * 0.3 + (state === 'active' ? 2 : 0)}
        cy={-r * 0.15}
        r={r * 0.05}
        fill={pupilFill}
      />
      <circle
        cx={r * 0.3 + (state === 'active' ? 2 : 0)}
        cy={-r * 0.15}
        r={r * 0.05}
        fill={pupilFill}
      />

      {/* Mouth — chat bubble or ellipsis */}
      {state === 'frozen' ? (
        // Frozen: ellipsis dots
        <g>
          <circle cx={-r * 0.2} cy={r * 0.25} r={r * 0.06} fill={fgAlpha(0.5)} />
          <circle cx={0}        cy={r * 0.25} r={r * 0.06} fill={fgAlpha(0.5)} />
          <circle cx={r * 0.2}  cy={r * 0.25} r={r * 0.06} fill={fgAlpha(0.5)} />
        </g>
      ) : (
        // Normal/active: small smile arc
        <path
          d={`M ${-r * 0.2} ${r * 0.2} Q 0 ${r * 0.4} ${r * 0.2} ${r * 0.2}`}
          fill="none"
          stroke={eyeFill}
          strokeWidth={2}
          strokeLinecap="round"
        />
      )}

      {/* Speech indicator when active */}
      {state === 'active' && (
        <g opacity={0.6 + 0.4 * Math.sin(stateProgress * Math.PI * 6)}>
          <rect
            x={r * 0.7}
            y={-r * 0.5}
            width={r * 0.4}
            height={r * 0.08}
            rx={2}
            fill={eyeFill}
            opacity={0.6}
          />
          <rect
            x={r * 0.7}
            y={-r * 0.3}
            width={r * 0.3}
            height={r * 0.08}
            rx={2}
            fill={eyeFill}
            opacity={0.4}
          />
        </g>
      )}
    </g>
  );
};

// ─── AgentCharacter ──────────────────────────────────────────────────────────

/**
 * Angular, dynamic agent character.
 * - Hexagonal/angular body shape
 * - Tool belt with up to 3 tool slots
 * - Active state: glowing edges, tool slot highlighted
 * - Done state: checkmark overlay, green tint
 */
export const AgentCharacter: React.FC<AgentCharacterProps> = ({
  x,
  y,
  size = 80,
  opacity = 1,
  state,
  stateProgress = 1,
  accentColor,
  accent2,
  activeToolSlot = -1,
  toolIcons = [],
  artDirection: ad,
}) => {
  const r = size / 2;

  // Derive agent colors from art direction with fallbacks
  const idleColor = ad?.character_agent?.idle ?? AGENT_COLOR_IDLE;
  const activeColor = ad?.character_agent?.active ?? AGENT_COLOR_ACTIVE;
  const doneColor = ad?.character_agent?.done ?? AGENT_COLOR_DONE;
  const isLight = ad?.light_or_dark === 'light';
  // Explicit props win; otherwise use themed colors
  const baseColor = accentColor ?? idleColor;
  const finalDoneColor = accent2 ?? doneColor;

  // Foreground alpha helper: dark themes use white, light themes use black
  const fgAlpha = (a: number) =>
    isLight ? `rgba(0,0,0,${a})` : `rgba(255,255,255,${a})`;
  // Eyes/icons stay white (bodies are saturated colors in both themes);
  // pupils stay dark so they contrast with the white eyes. Active-slot outline
  // darkens on light themes so it stays visible against a light canvas.
  const eyeFill = '#fff';
  const pupilFill = '#1e1b4b';
  const outlineColor = isLight ? '#0f172a' : '#fff';

  // Body color by state
  const bodyColor = state === 'done'
    ? lerpColor(baseColor, finalDoneColor, stateProgress)
    : state === 'active'
      ? lerpColor(baseColor, activeColor, stateProgress * 0.5)
      : baseColor;

  // Active state: slight forward lean
  const leanX = state === 'active' ? 4 * stateProgress : 0;

  // Done state: scale-up pulse
  const doneScale = state === 'done'
    ? 1 + 0.05 * Math.sin(stateProgress * Math.PI)
    : 1;

  // Hexagonal body path (pointy-top hex)
  const hexPoints = hexagonPoints(0, 0, r * 0.95);

  // Glow intensity for active state
  const glowOpacity = state === 'active'
    ? 0.3 + 0.2 * Math.sin(stateProgress * Math.PI * 4)
    : 0;

  return (
    <g
      transform={`translate(${x + leanX}, ${y}) scale(${doneScale})`}
      opacity={opacity}
    >
      {/* Active glow */}
      {state === 'active' && (
        <polygon
          points={hexagonPoints(0, 0, r * 1.15)}
          fill="none"
          stroke={baseColor}
          strokeWidth={3}
          opacity={glowOpacity}
        />
      )}

      {/* Body — hexagon */}
      <polygon
        points={hexPoints}
        fill={bodyColor}
        stroke={fgAlpha(0.2)}
        strokeWidth={2}
        strokeLinejoin="round"
      />

      {/* Inner facet lines for angular feel */}
      <line
        x1={-r * 0.3} y1={-r * 0.6}
        x2={-r * 0.6} y2={0}
        stroke={fgAlpha(0.06)}
        strokeWidth={1}
      />
      <line
        x1={r * 0.3} y1={-r * 0.6}
        x2={r * 0.6} y2={0}
        stroke={fgAlpha(0.06)}
        strokeWidth={1}
      />

      {/* Eyes — angular/determined */}
      <rect
        x={-r * 0.35}
        y={-r * 0.25}
        width={r * 0.2}
        height={r * 0.12}
        rx={2}
        fill={eyeFill}
      />
      <rect
        x={r * 0.15}
        y={-r * 0.25}
        width={r * 0.2}
        height={r * 0.12}
        rx={2}
        fill={eyeFill}
      />

      {/* Pupils */}
      <rect
        x={-r * 0.3 + (state === 'active' ? 3 : 0)}
        y={-r * 0.22}
        width={r * 0.08}
        height={r * 0.08}
        rx={1}
        fill={pupilFill}
      />
      <rect
        x={r * 0.2 + (state === 'active' ? 3 : 0)}
        y={-r * 0.22}
        width={r * 0.08}
        height={r * 0.08}
        rx={1}
        fill={pupilFill}
      />

      {/* Tool belt — row of slots below body */}
      <g transform={`translate(0, ${r * 0.75})`}>
        {[0, 1, 2].map((slot) => {
          const slotX = (slot - 1) * (r * 0.5);
          const isActive = slot === activeToolSlot;
          const icon = toolIcons[slot] ?? '';
          return (
            <g key={slot}>
              <rect
                x={slotX - r * 0.18}
                y={-r * 0.12}
                width={r * 0.36}
                height={r * 0.24}
                rx={3}
                fill={isActive ? fgAlpha(0.25) : fgAlpha(0.08)}
                stroke={isActive ? outlineColor : fgAlpha(0.15)}
                strokeWidth={isActive ? 2 : 1}
              />
              {icon && (
                <text
                  x={slotX}
                  y={r * 0.04}
                  textAnchor="middle"
                  fontSize={r * 0.2}
                  fill={isLight ? '#0f172a' : '#fff'}
                >
                  {icon}
                </text>
              )}
            </g>
          );
        })}
      </g>

      {/* Done state: checkmark */}
      {state === 'done' && stateProgress > 0.3 && (
        <g opacity={interpolate(stateProgress, [0.3, 0.7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}>
          <circle
            cx={r * 0.5}
            cy={-r * 0.55}
            r={r * 0.25}
            fill={finalDoneColor}
            stroke="#fff"
            strokeWidth={2}
          />
          <path
            d={`M ${r * 0.37} ${-r * 0.55} L ${r * 0.47} ${-r * 0.45} L ${r * 0.63} ${-r * 0.65}`}
            fill="none"
            stroke="#fff"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>
      )}
    </g>
  );
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Generate SVG polygon points string for a pointy-top hexagon */
function hexagonPoints(cx: number, cy: number, r: number): string {
  const pts: string[] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2; // start at top
    pts.push(`${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`);
  }
  return pts.join(' ');
}

/** Linear color interpolation between two hex colors */
function lerpColor(from: string, to: string, t: number): string {
  const f = parseHex(from);
  const tt = parseHex(to);
  const r = Math.round(f[0] + (tt[0] - f[0]) * t);
  const g = Math.round(f[1] + (tt[1] - f[1]) * t);
  const b = Math.round(f[2] + (tt[2] - f[2]) * t);
  return `rgb(${r},${g},${b})`;
}

function parseHex(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [
    parseInt(h.substring(0, 2), 16),
    parseInt(h.substring(2, 4), 16),
    parseInt(h.substring(4, 6), 16),
  ];
}
