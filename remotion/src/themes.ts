/**
 * themes.ts — Art Direction manifests for AI Bytes episodes.
 *
 * Each episode selects an art direction that defines its entire visual world.
 * Components consume values from the active manifest rather than embedding
 * one universal dark-tech treatment.
 *
 * Two visual worlds ship initially:
 *   1. cinematic-dark   — EP00 RAG, EP01 Tokens (existing look)
 *   2. bright-workspace — EP02 Agents vs Chatbots (productivity editorial)
 *
 * The system is extensible: future episodes add new manifests here.
 */

// ─── ArtDirection Interface ─────────────────────────────────────────────────

export interface ArtDirectionPalette {
  /** Main canvas / page background */
  bg: string;
  /** Card / panel surface */
  surface: string;
  /** Divider / border color */
  border: string;
  /** Primary body text */
  text: string;
  /** Secondary / muted text */
  muted: string;
  /** Primary action / highlight color */
  primary: string;
  /** Secondary action color */
  secondary: string;
  /** Success / completion */
  success: string;
  /** Warning / incomplete */
  warning: string;
  /** Danger / rejection */
  danger: string;
  /** Structural / reasoning accent (wheel, flow diagrams) */
  structural: string;
  /** Passive / static element color (chatbot in EP02) */
  passive: string;
}

export interface ArtDirection {
  /** Unique identifier for this visual world */
  id: string;
  /** Human-readable name */
  name: string;

  // ── Core dimensions (14+) ─────────────────────────────────────────────

  /** Visual world description */
  visual_world: string;
  /** Light or dark base */
  light_or_dark: 'light' | 'dark';
  /** Full color palette */
  palette: ArtDirectionPalette;

  /** Background treatment description + CSS value */
  background: {
    description: string;
    /** CSS background value for the main canvas */
    css: string;
  };

  /** Surface style for cards and panels */
  surface_style: {
    background: string;
    border: string;
    borderRadius: number;
    /** CSS box-shadow for cards */
    shadow: string;
  };

  /** Border treatment */
  border_style: {
    width: number;
    color: string;
    /** For separator lines */
    separator: string;
  };

  /** Depth / shadow treatment */
  depth: {
    description: string;
    /** Primary element shadow */
    shadow_sm: string;
    shadow_md: string;
    shadow_lg: string;
    /** Whether to use glow effects */
    use_glow: boolean;
    /** Glow color (only when use_glow is true) */
    glow_color: string;
  };

  /** Typography personality */
  typography: {
    description: string;
    /** Primary font family */
    font: string;
    /** Monospace font family */
    mono: string;
    /** Heading color */
    heading_color: string;
    /** Whether headings use text-shadow */
    heading_glow: boolean;
  };

  /** Shape language */
  shape_language: string;
  /** Icon language */
  icon_language: string;

  /** Transition family */
  transition_family: string;
  /** Ambient motion family */
  ambient_motion: string;
  /** Camera language */
  camera_language: string;
  /** Framing rules */
  framing_rules: string;

  // ── Character treatment ───────────────────────────────────────────────

  /** Chatbot character colors */
  character_chatbot: {
    idle: string;
    active: string;
    frozen: string;
  };

  /** Agent character colors */
  character_agent: {
    idle: string;
    active: string;
    done: string;
  };

  // ── Component-level overrides ─────────────────────────────────────────

  /** Colors for multi-item displays (cards, flow quadrants, etc.) */
  item_colors: string[];

  /** Split-compare panel treatment */
  split_compare: {
    left_color: string;
    right_color: string;
    /** VS badge background */
    vs_bg: string;
    /** VS badge text color */
    vs_text: string;
    /** Panel text color */
    panel_text: string;
    /** Verdict box background opacity suffix (hex, e.g. '15') */
    verdict_bg_opacity: string;
  };

  /** Zone / column treatment for traversal scenes */
  zones: {
    /** Zone track fill */
    track_fill: string;
    /** Zone track stroke */
    track_stroke: string;
    /** Zone label color */
    label_color: string;
    /** Task card background */
    task_card_bg: string;
    /** Task card border */
    task_card_border: string;
    /** Task card text color */
    task_card_text: string;
  };

  /** Overlay for video backgrounds (CTA scene, etc.) */
  overlay: string;
  /** Pexels mood keyword for video search */
  pexels_mood: string;
}

// ─── Cinematic Dark (EP00, EP01) ────────────────────────────────────────────

export const CINEMATIC_DARK: ArtDirection = {
  id: 'cinematic-dark',
  name: 'Cinematic Dark Tech',

  visual_world: 'cinematic dark-tech — neon accents on deep void',
  light_or_dark: 'dark',

  palette: {
    bg: '#050510',
    surface: 'rgba(255,255,255,0.05)',
    border: 'rgba(255,255,255,0.12)',
    text: '#ffffff',
    muted: 'rgba(255,255,255,0.53)',
    primary: '#a78bfa',
    secondary: '#34d399',
    success: '#34d399',
    warning: '#fbbf24',
    danger: '#ff4444',
    structural: '#6366f1',
    passive: '#475569',
  },

  background: {
    description: 'flat near-black void with radial accent glows',
    css: '#050510',
  },

  surface_style: {
    background: 'rgba(255,255,255,0.05)',
    border: '2px solid rgba(255,255,255,0.12)',
    borderRadius: 24,
    shadow: '0 0 60px rgba(167,139,250,0.1)',
  },

  border_style: {
    width: 2,
    color: 'rgba(255,255,255,0.12)',
    separator: 'rgba(255,255,255,0.08)',
  },

  depth: {
    description: 'flat 2D with glow halos simulating depth',
    shadow_sm: '0 0 20px rgba(167,139,250,0.08)',
    shadow_md: '0 0 40px rgba(167,139,250,0.12)',
    shadow_lg: '0 0 60px rgba(167,139,250,0.18)',
    use_glow: true,
    glow_color: 'rgba(167,139,250,0.25)',
  },

  typography: {
    description: 'futuristic command terminal — system sans + JetBrains Mono',
    font: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    mono: '"JetBrains Mono", "Fira Mono", monospace',
    heading_color: '#ffffff',
    heading_glow: true,
  },

  shape_language: 'rounded rectangles, panels, pill badges, hexagons',
  icon_language: 'emoji and geometric shapes',
  transition_family: 'crossfade + cut',
  ambient_motion: 'glow pulses, radial gradients',
  camera_language: 'static reveals, pan-follow, zoom-in',
  framing_rules: 'centered composition, symmetrical panels',

  character_chatbot: {
    idle: '#6366f1',
    active: '#818cf8',
    frozen: '#475569',
  },

  character_agent: {
    idle: '#a78bfa',
    active: '#c4b5fd',
    done: '#34d399',
  },

  item_colors: ['#a78bfa', '#818cf8', '#34d399', '#fbbf24', '#6366f1'],

  split_compare: {
    left_color: '#ff4444',
    right_color: '#22c55e',
    vs_bg: '#1a1a2e',
    vs_text: 'rgba(255,255,255,0.6)',
    panel_text: 'rgba(255,255,255,0.88)',
    verdict_bg_opacity: '15',
  },

  zones: {
    track_fill: 'rgba(255,255,255,0.03)',
    track_stroke: 'rgba(255,255,255,0.06)',
    label_color: 'rgba(255,255,255,0.5)',
    task_card_bg: 'rgba(255,255,255,0.05)',
    task_card_border: 'rgba(255,255,255,0.12)',
    task_card_text: '#ffffff',
  },

  overlay: 'rgba(5,5,16,0.35)',
  pexels_mood: 'purple neon dark',
};

// ─── Bright Workspace (EP02) ────────────────────────────────────────────────

export const BRIGHT_WORKSPACE: ArtDirection = {
  id: 'bright-workspace',
  name: 'Bright Workspace — Productivity Editorial',

  visual_world: 'bright workspace — productivity editorial',
  light_or_dark: 'light',

  palette: {
    bg: '#F7F8FA',
    surface: '#FFFFFF',
    border: '#E2E5EB',
    text: '#1A1D24',
    muted: '#6B7280',
    primary: '#3B82F6',
    secondary: '#10B981',
    success: '#10B981',
    warning: '#F59E0B',
    danger: '#EF4444',
    structural: '#6366F1',
    passive: '#94A3B8',
  },

  background: {
    description: 'off-white with subtle dot grid, card shadows',
    css: '#F7F8FA',
  },

  surface_style: {
    background: '#FFFFFF',
    border: '1px solid #E2E5EB',
    borderRadius: 12,
    shadow: '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)',
  },

  border_style: {
    width: 1,
    color: '#E2E5EB',
    separator: '#E2E5EB',
  },

  depth: {
    description: 'layered cards with drop shadows, no glow halos',
    shadow_sm: '0 1px 2px rgba(0,0,0,0.05)',
    shadow_md: '0 2px 8px rgba(0,0,0,0.08)',
    shadow_lg: '0 4px 16px rgba(0,0,0,0.10)',
    use_glow: false,
    glow_color: 'transparent',
  },

  typography: {
    description: 'clean productivity — Inter/system sans, no glow, weight-based hierarchy',
    font: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    mono: '"JetBrains Mono", "Fira Code", "SF Mono", monospace',
    heading_color: '#1A1D24',
    heading_glow: false,
  },

  shape_language: 'rounded rectangles (8-12px), checkboxes, kanban columns, card stacks',
  icon_language: 'minimal line icons — search, calendar, email, checkmark',
  transition_family: 'horizontal slide (panels slide over), cut for hook',
  ambient_motion: 'subtle parallax on dot grid, micro-hover card states',
  camera_language: 'static for chatbot, pan-follow for agent, static splits for comparison',
  framing_rules: 'chatbot contained inside chat widget frame; agent moves freely across workspace',

  character_chatbot: {
    idle: '#94A3B8',
    active: '#64748B',
    frozen: '#CBD5E1',
  },

  character_agent: {
    idle: '#3B82F6',
    active: '#60A5FA',
    done: '#10B981',
  },

  item_colors: ['#3B82F6', '#6366F1', '#10B981', '#F59E0B', '#3B82F6'],

  split_compare: {
    left_color: '#94A3B8',
    right_color: '#3B82F6',
    vs_bg: '#F1F5F9',
    vs_text: '#6B7280',
    panel_text: '#1A1D24',
    verdict_bg_opacity: '12',
  },

  zones: {
    track_fill: 'rgba(59,130,246,0.04)',
    track_stroke: '#E2E5EB',
    label_color: '#6B7280',
    task_card_bg: '#FFFFFF',
    task_card_border: '#E2E5EB',
    task_card_text: '#1A1D24',
  },

  overlay: 'rgba(247,248,250,0.75)',
  pexels_mood: 'bright workspace productivity',
};

// ─── Registry ───────────────────────────────────────────────────────────────

export const ART_DIRECTIONS: Record<string, ArtDirection> = {
  'cinematic-dark': CINEMATIC_DARK,
  'bright-workspace': BRIGHT_WORKSPACE,
};

/**
 * Look up an art direction manifest by id.
 * Falls back to cinematic-dark when the id is unknown.
 */
export function getArtDirection(id: string): ArtDirection {
  return ART_DIRECTIONS[id] ?? CINEMATIC_DARK;
}

/**
 * Build a legacy Theme object from an ArtDirection manifest,
 * for backward compatibility with components that still accept Theme.
 */
export function artDirectionToTheme(ad: ArtDirection): {
  name: string;
  accent: string;
  accent2: string;
  overlay: string;
  pexels_mood: string;
} {
  return {
    name: ad.id,
    accent: ad.palette.primary,
    accent2: ad.palette.secondary,
    overlay: ad.overlay,
    pexels_mood: ad.pexels_mood,
  };
}
