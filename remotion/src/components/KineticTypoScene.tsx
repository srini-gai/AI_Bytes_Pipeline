/**
 * KineticTypoScene — HOOK scene (v43 visual-dominance hero typography).
 *
 * 2-beat full-canvas shatter:
 *   Beat A (0–35%): Giant text SLAMS onto canvas from above with bounce
 *   Beat B (45%–100%): Text cracks down center, fragments fly outward;
 *                       subtitle emerges from crack
 *
 * Hero text is viewport-fitted via browser measurement with a visual
 * dominance rule: if width-fit produces < 8% frame height, the system
 * applies scaleX compression or switches to two-line stacked layout.
 */
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {ArtDirection} from '../themes';
import {useHeroTextFit, heroMeasureStyle, HERO_SAFE_AREA} from '../utils/fitHeroText';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const BG = '#050510';
const LETTER_SPACING = 4;

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

  const bgColor = ad?.palette.bg ?? BG;
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.font ?? FONT;
  const useGlow = ad?.depth.use_glow ?? true;

  // ── Viewport-fitted hero typography with dominance rule ────────────────
  const {fit: heroFit, singleRef, line1Ref, line2Ref} = useHeroTextFit(
    text,
    HERO_SAFE_AREA.width * 0.92,
    HERO_SAFE_AREA.height * 0.35,
    fontFamily,
    900,
    LETTER_SPACING,
  );
  const heroFontSize = heroFit.measured ? heroFit.fontSize : 180;
  const heroScaleX = heroFit.scaleX;
  const isTwoLine = heroFit.lineCount === 2;

  // ── Timing ────────────────────────────────────────────────────────────
  const slamEnd = Math.round(durationInFrames * 0.35);
  const crackStart = Math.round(durationInFrames * 0.38);
  const shatterStart = Math.round(durationInFrames * 0.45);
  const subtitleStart = Math.round(durationInFrames * 0.55);

  // ── Beat A: Slam from above ───────────────────────────────────────────
  const slamSpring = spring({
    fps,
    frame,
    config: {damping: 10, stiffness: 180, mass: 0.8},
    durationInFrames: slamEnd,
  });
  const slamY = interpolate(slamSpring, [0, 1], [-600, 0]);
  const slamScale = interpolate(slamSpring, [0, 1], [1.4, 1.0]);

  const impactFlash = frame >= slamEnd - 4 && frame <= slamEnd + 6
    ? interpolate(frame, [slamEnd - 4, slamEnd, slamEnd + 6], [0, 0.5, 0], {
        extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      })
    : 0;

  // ── Beat B: Crack and shatter ─────────────────────────────────────────
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

  const sceneOpacity = interpolate(
    frame,
    [0, 4, durationInFrames - 4, durationInFrames],
    [0, 1, 1, 0.4],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Characters for shatter — respects single vs two-line layout
  const shatterLines: string[][] = isTwoLine
    ? [heroFit.lines[0].split(''), heroFit.lines[1].split('')]
    : [text.replace(/\s+/g, '').split('')];

  const heroTextStyle: React.CSSProperties = {
    fontFamily,
    fontSize: heroFontSize,
    fontWeight: 900,
    color: textColor,
    letterSpacing: LETTER_SPACING,
    lineHeight: 1,
    textShadow: useGlow
      ? `0 0 60px ${accentColor}66, 0 8px 30px rgba(0,0,0,0.8)`
      : `0 4px 16px rgba(0,0,0,0.12)`,
  };

  const renderShatterChar = (char: string, globalIdx: number, side: 'left' | 'right') => {
    if (shatterProgress <= 0) return null;

    const delay = seededRand(globalIdx * 17) * 0.3;
    const charShatter = Math.max(0, Math.min(1, (shatterProgress - delay) / (1 - delay)));
    const eased = charShatter * charShatter;

    const dirX = side === 'left' ? -1 : 1;
    const tx = dirX * (200 + seededRand(globalIdx * 7) * 400) * eased;
    const ty = (seededRand(globalIdx * 13) - 0.3) * 600 * eased;
    const rot = (seededRand(globalIdx * 19) - 0.5) * 120 * eased;
    const opacity = 1 - eased;

    return (
      <span
        key={`${side}-${globalIdx}`}
        style={{
          display: 'inline-block',
          fontFamily,
          fontSize: heroFontSize,
          fontWeight: 900,
          color: textColor,
          letterSpacing: LETTER_SPACING,
          lineHeight: 1,
          opacity,
          transform: `translate(${tx}px, ${ty}px) rotate(${rot}deg) scaleX(${heroScaleX})`,
          textShadow: useGlow ? `0 0 40px ${accentColor}88` : `0 4px 12px rgba(0,0,0,0.15)`,
          willChange: 'transform',
        }}
      >
        {char}
      </span>
    );
  };

  const renderShatterLine = (chars: string[], globalOffset: number) => {
    const mid = Math.ceil(chars.length / 2);
    const left = chars.slice(0, mid);
    const right = chars.slice(mid);
    return (
      <div style={{display: 'flex', justifyContent: 'center', gap: `0 ${crackProgress * 20}px`}}>
        <div style={{display: 'flex'}}>
          {left.map((c, i) => renderShatterChar(c, globalOffset + i, 'left'))}
        </div>
        <div style={{display: 'flex'}}>
          {right.map((c, i) => renderShatterChar(c, globalOffset + mid + i, 'right'))}
        </div>
      </div>
    );
  };

  // ── Pre-shatter text rendering ────────────────────────────────────────

  const renderPreShatterText = () => {
    const baseTransform = `translateY(${slamY}px) scale(${slamScale}) scaleX(${heroScaleX})`;

    if (isTwoLine) {
      const lineGap = heroFontSize * 0.15;
      return (
        <div style={{
          transform: baseTransform,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: lineGap,
        }}>
          {heroFit.lines.map((line, lineIdx) => (
            <div key={lineIdx} style={{
              ...heroTextStyle,
              ...(crackProgress > 0 ? {
                display: 'flex',
                gap: `0 ${crackProgress * 20}px`,
              } : {}),
            }}>
              {crackProgress > 0 ? (() => {
                const lChars = line.split('');
                const lMid = Math.ceil(lChars.length / 2);
                return (
                  <>
                    <span>{lChars.slice(0, lMid).join('')}</span>
                    <span>{lChars.slice(lMid).join('')}</span>
                  </>
                );
              })() : line}
            </div>
          ))}
        </div>
      );
    }

    // Single line
    return (
      <div style={{
        transform: baseTransform,
        ...heroTextStyle,
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
    );
  };

  const measureStyle = heroMeasureStyle(fontFamily, 900, LETTER_SPACING);

  return (
    <AbsoluteFill style={{backgroundColor: transparentBg ? 'transparent' : bgColor, opacity: sceneOpacity}}>
      {/* Hidden measurement spans — always render both line options */}
      <span ref={singleRef} style={measureStyle}>{text}</span>
      <span ref={line1Ref} style={measureStyle}>{heroFit.l1Text}</span>
      <span ref={line2Ref} style={measureStyle}>{heroFit.l2Text}</span>

      {/* Impact flash */}
      {impactFlash > 0 && (
        <AbsoluteFill style={{
          backgroundColor: `rgba(255,255,255,${impactFlash})`,
          zIndex: 10,
        }} />
      )}

      {/* Background accent glow */}
      {useGlow && (
        <AbsoluteFill style={{
          background: `radial-gradient(ellipse 900px 600px at 50% 48%, ${accentColor}${
            Math.round((0.06 + (frame < slamEnd ? 0 : 0.15) * (1 - shatterProgress)) * 255).toString(16).padStart(2, '0')
          } 0%, transparent 60%)`,
        }} />
      )}

      {/* Crack line */}
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

      {/* Main text — viewport-fitted hero with visual dominance */}
      <AbsoluteFill style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 3,
      }}>
        {shatterProgress <= 0 ? (
          renderPreShatterText()
        ) : (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: isTwoLine ? heroFontSize * 0.15 : 0,
          }}>
            {shatterLines.map((lineChars, lineIdx) => {
              const offset = shatterLines.slice(0, lineIdx).reduce((s, l) => s + l.length, 0);
              return <React.Fragment key={lineIdx}>{renderShatterLine(lineChars, offset)}</React.Fragment>;
            })}
          </div>
        )}
      </AbsoluteFill>

      {/* Subtitle */}
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
              fontFamily,
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
            fontFamily,
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
