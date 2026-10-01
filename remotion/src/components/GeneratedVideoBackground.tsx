/**
 * GeneratedVideoBackground — reusable background layer for Higgsfield-generated clips.
 *
 * Architecture:
 *   Generated MP4 (Higgsfield)
 *   ↓
 *   GeneratedVideoBackground  (this component — background layer)
 *   ↓
 *   Remotion overlay (hook text / branding / captions / transitions — parent scene)
 *
 * Usage:
 *   <GeneratedVideoBackground
 *     src="clips/gen_video_s01.mp4"   // public-relative staticFile path
 *     overlayOpacity={0.55}           // dark overlay strength (0–1)
 *     accentOverlay="rgba(5,5,16,0.15)"  // optional theme tint
 *   />
 *   {/* Parent renders branding / text ON TOP via AbsoluteFill with zIndex *\/}
 *
 * Rules enforced here (matching pipeline spec):
 *   - Generated video is a BACKGROUND layer only — no text from Higgsfield visible
 *   - A dark overlay always sits above the video to guarantee contrast for Remotion overlays
 *   - Falls back to dark gradient if src is absent (Remotion-only mode)
 *   - No letterboxing: objectFit: 'cover' fills 1080×1920 at any source aspect ratio
 */
import React from 'react';
import {AbsoluteFill, OffthreadVideo, staticFile} from 'remotion';

export interface GeneratedVideoBackgroundProps {
  /** Public-relative path (e.g. "clips/gen_video_s01.mp4"). When absent, shows dark gradient. */
  src?: string;
  /**
   * Opacity of the dark overlay placed above the video to ensure text contrast.
   * Range 0–1. Default: 0.55 (enough to guarantee white text readability).
   */
  overlayOpacity?: number;
  /**
   * Optional theme colour tint applied above the dark overlay.
   * Should be a low-opacity rgba string, e.g. "rgba(167,139,250,0.10)".
   */
  accentOverlay?: string;
  /** Fallback background colour shown when no src (default: #050510). */
  fallbackColor?: string;
}

const DEFAULT_OVERLAY_OPACITY = 0.55;
const DEFAULT_FALLBACK_COLOR  = '#050510';

export const GeneratedVideoBackground: React.FC<GeneratedVideoBackgroundProps> = ({
  src,
  overlayOpacity = DEFAULT_OVERLAY_OPACITY,
  accentOverlay,
  fallbackColor = DEFAULT_FALLBACK_COLOR,
}) => {
  return (
    <AbsoluteFill style={{backgroundColor: fallbackColor}}>
      {/* ── Generated video layer ──────────────────────────────────────────── */}
      {src && (
        <AbsoluteFill>
          <OffthreadVideo
            src={staticFile(src)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
            muted
          />
        </AbsoluteFill>
      )}

      {/* ── Dark contrast overlay — guarantees Remotion overlay readability ── */}
      <AbsoluteFill
        style={{
          backgroundColor: `rgba(5,5,16,${overlayOpacity})`,
        }}
      />

      {/* ── Optional theme tint (accent colour wash) ──────────────────────── */}
      {accentOverlay && (
        <AbsoluteFill style={{backgroundColor: accentOverlay}} />
      )}

      {/* ── Bottom gradient — caption/text readability at foot of frame ─────── */}
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(to bottom, transparent 55%, rgba(0,0,0,0.70) 100%)',
        }}
      />
    </AbsoluteFill>
  );
};
