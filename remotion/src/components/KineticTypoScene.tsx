/**
 * KineticTypoScene — HOOK scene (v41 token-native).
 *
 * 2-beat full-canvas shatter:
 *   Beat A (0–40%): Giant text SLAMS onto canvas from above with bounce
 *   Beat B (40%–100%): Text cracks down center, fragments fly outward;
 *                       subtitle (on_screen_text[1]) emerges from crack
 *
 * Props:
 *   text          — the bold word to display (e.g. "WORD")
 *   accentColor   — theme accent hex
 *   glitchColor   — optional second glitch colour (defaults to accent2)
 *   subtitle      — text that emerges during shatter (e.g. "NOT ONE.")
 *   durationInFrames — total frame count for the scene
 *   transparentBg — true when compositing over generated video
 *   subtitleStyle — 'stamp' renders the subtitle as a rejection stamp
 *                   (palette.danger border/text on a surface background)
 */
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {ArtDirection} from '../themes';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const BG = '#050510';

// Deterministic pseudo-random from seed
function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

interface KineticTypoSceneProps {
  text: string;
  accentColor: string;
  glitchColor?: string;
  subtitle?: string;
  durationInFrames: number;
  transparentBg?: boolean;
  artDirection?: ArtDirection;
  subtitleStyle?: 'stamp';
}

export const KineticTypoScene: React.FC<KineticTypoSceneProps> = ({
  text,
  accentColor,
  glitchColor,
  subtitle,
  durationInFrames,
  transparentBg = false,
  artDirection: ad,
  subtitleStyle,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const accent2 = glitchColor ?? ad?.palette.secondary ?? '#34d399';

  // Art-direction-aware colors
  const bgColor = ad?.palette.bg ?? BG;
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.font ?? FONT;
  const useGlow = ad?.depth.use_glow ?? true;

  // ── Timing (relative to durationInFrames) ─────────────────────────────────
  const slamEnd = Math.round(durationInFrames * 0.35);      // ~31f for 88f scene
  const crackStart = Math.round(durationInFrames * 0.38);   // ~33f
  const shatterStart = Math.round(durationInFrames * 0.45); // ~40f
  const subtitleStart = Math.round(durationInFrames * 0.55);// ~48f

  // ── Beat A: Slam from above ───────────────────────────────────────────────
  const slamSpring = spring({
    fps,
    frame,
    config: {damping: 10, stiffness: 180, mass: 0.8},
    durationInFrames: slamEnd,
  });
  const slamY = interpolate(slamSpring, [0, 1], [-600, 0]);
  const slamScale = interpolate(slamSpring, [0, 1], [1.4, 1.0]);

  // Impact flash
  const impactFlash = frame >= slamEnd - 4 && frame <= slamEnd + 6
    ? interpolate(frame, [slamEnd - 4, slamEnd, slamEnd + 6], [0, 0.5, 0], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      })
    : 0;

  // ── Beat B: Crack and shatter ─────────────────────────────────────────────
  const crackProgress = interpolate(
    frame,
    [crackStart, shatterStart],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const shatterProgress = interpolate(
    frame,
    [shatterStart, durationInFrames - 4],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Subtitle emergence
  const subtitleOpacity = interpolate(
    frame,
    [subtitleStart, subtitleStart + 12],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const subtitleScale = interpolate(
    frame,
    [subtitleStart, subtitleStart + 12],
    [0.7, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Scene opacity envelope
  const sceneOpacity = interpolate(
    frame,
    [0, 4, durationInFrames - 4, durationInFrames],
    [0, 1, 1, 0.4],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Split text into halves for crack effect
  const chars = text.split('');
  const midpoint = Math.ceil(chars.length / 2);
  const leftChars = chars.slice(0, midpoint);
  const rightChars = chars.slice(midpoint);

  // Per-character shatter
  const renderShatterChar = (char: string, idx: number, side: 'left' | 'right') => {
    if (shatterProgress <= 0) return null;

    const globalIdx = side === 'left' ? idx : midpoint + idx;
    const delay = seededRand(globalIdx * 17) * 0.3;
    const charShatter = Math.max(0, Math.min(1, (shatterProgress - delay) / (1 - delay)));
    const eased = charShatter * charShatter;

    // Fragments fly outward from crack center
    const dirX = side === 'left' ? -1 : 1;
    const tx = dirX * (200 + seededRand(globalIdx * 7) * 400) * eased;
    const ty = (seededRand(globalIdx * 13) - 0.3) * 600 * eased;
    const rot = (seededRand(globalIdx * 19) - 0.5) * 120 * eased;
    const opacity = 1 - eased;

    return (
      <span
        key={`${side}-${idx}`}
        style={{
          display: 'inline-block',
          fontFamily: fontFamily,
          fontSize: 180,
          fontWeight: 900,
          color: textColor,
          letterSpacing: 4,
          lineHeight: 1,
          opacity,
          transform: `translate(${tx}px, ${ty}px) rotate(${rot}deg)`,
          textShadow: useGlow ? `0 0 40px ${accentColor}88` : `0 4px 12px rgba(0,0,0,0.15)`,
          willChange: 'transform',
        }}
      >
        {char}
      </span>
    );
  };

  return (
    <AbsoluteFill style={{backgroundColor: transparentBg ? 'transparent' : bgColor, opacity: sceneOpacity}}>
      {/* Impact flash */}
      {impactFlash > 0 && (
        <AbsoluteFill style={{
          backgroundColor: `rgba(255,255,255,${impactFlash})`,
          zIndex: 10,
        }} />
      )}

      {/* Background accent glow — intensifies at slam moment (dark theme only) */}
      {useGlow && (
        <AbsoluteFill style={{
          background: `radial-gradient(ellipse 900px 600px at 50% 48%, ${accentColor}${
            Math.round((0.06 + (frame < slamEnd ? 0 : 0.15) * (1 - shatterProgress)) * 255).toString(16).padStart(2, '0')
          } 0%, transparent 60%)`,
        }} />
      )}

      {/* Crack line down center */}
      {crackProgress > 0 && shatterProgress < 0.8 && (
        <div style={{
          position: 'absolute',
          left: '50%',
          top: `${50 - crackProgress * 40}%`,
          width: 3,
          height: `${crackProgress * 80}%`,
          background: `linear-gradient(to bottom, transparent, ${accentColor}, ${accent2}, transparent)`,
          transform: 'translateX(-50%)',
          opacity: 1 - shatterProgress,
          zIndex: 5,
        }} />
      )}

      {/* Main text — full canvas dominant */}
      <AbsoluteFill style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 3,
      }}>
        {shatterProgress <= 0 ? (
          // Pre-shatter: single unit, slamming from above
          <div style={{
            transform: `translateY(${slamY}px) scale(${slamScale})`,
            fontFamily: fontFamily,
            fontSize: 180,
            fontWeight: 900,
            color: textColor,
            letterSpacing: 4,
            lineHeight: 1,
            textShadow: useGlow
              ? `0 0 60px ${accentColor}66, 0 8px 30px rgba(0,0,0,0.8)`
              : `0 4px 16px rgba(0,0,0,0.12)`,
            // Crack gap during crack phase
            ...(crackProgress > 0 ? {
              display: 'flex',
              gap: `0 ${crackProgress * 20}px`,
            } : {}),
          }}>
            {crackProgress > 0 ? (
              <>
                <span>{leftChars.join('')}</span>
                <span>{rightChars.join('')}</span>
              </>
            ) : text}
          </div>
        ) : (
          // During shatter: per-character fragments
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            gap: `0 ${crackProgress * 20}px`,
          }}>
            <div style={{display: 'flex'}}>
              {leftChars.map((c, i) => renderShatterChar(c, i, 'left'))}
            </div>
            <div style={{display: 'flex'}}>
              {rightChars.map((c, i) => renderShatterChar(c, i, 'right'))}
            </div>
          </div>
        )}
      </AbsoluteFill>

      {/* Subtitle emerges from crack center */}
      {subtitle && subtitleOpacity > 0 && (
        <div style={{
          position: 'absolute',
          top: '58%',
          left: 0,
          right: 0,
          textAlign: 'center',
          zIndex: 6,
          opacity: subtitleOpacity,
          transform: `scale(${subtitleScale})`,
        }}>
          {subtitleStyle === 'stamp' ? (
            <span style={{
              display: 'inline-block',
              fontFamily: fontFamily,
              fontSize: 64,
              fontWeight: 900,
              color: ad?.palette.danger ?? '#ef4444',
              letterSpacing: 6,
              padding: '14px 32px',
              border: `7px solid ${ad?.palette.danger ?? '#ef4444'}`,
              borderRadius: 14,
              background: ad?.palette.surface ?? 'transparent',
              boxShadow: ad?.depth.shadow_md ?? 'none',
              transform: 'rotate(-6deg)',
            }}>
              {subtitle}
            </span>
          ) : (
          <span style={{
            fontFamily: fontFamily,
            fontSize: 64,
            fontWeight: 900,
            color: accentColor,
            letterSpacing: 6,
            textShadow: useGlow
              ? `0 0 40px ${accentColor}88, 0 4px 20px rgba(0,0,0,0.9)`
              : `0 2px 8px rgba(0,0,0,0.1)`,
          }}>
            {subtitle}
          </span>
          )}
        </div>
      )}
    </AbsoluteFill>
  );
};
