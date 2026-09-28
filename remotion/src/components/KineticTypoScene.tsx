/**
 * KineticTypoScene — HOOK and key-statement scenes.
 *
 * Behaviour:
 *  Phase 1 (0–18 frames):  Text assembles char-by-char with a glitch flicker
 *  Phase 2 (18–36 frames): Text holds fully visible, slight scale pulse
 *  Phase 3 (36–54 frames): Text shatters / dissolves outward
 *
 * Props:
 *   text          — the bold statement to display (≤ 10 words)
 *   accentColor   — theme accent hex
 *   glitchColor   — optional second glitch colour (defaults to accent2)
 *   durationInFrames — total frame count for the scene
 */
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const BG = '#050510';

// Deterministic pseudo-random from seed
function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// Characters for glitch substitution
const GLITCH_CHARS = '!@#$%^&*<>?/\\|[]{}0123456789';

interface KineticTypoSceneProps {
  text: string;
  accentColor: string;
  glitchColor?: string;
  subtitle?: string;
  durationInFrames: number;
}

const ASSEMBLE_START = 0;
const ASSEMBLE_END = 18;
const HOLD_START = 18;
const HOLD_END = 42;
const SHATTER_START = 42;
const SHATTER_END = 60;

const CHAR_STAGGER = 2; // frames per character reveal

export const KineticTypoScene: React.FC<KineticTypoSceneProps> = ({
  text,
  accentColor,
  glitchColor,
  subtitle,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const glitch2 = glitchColor ?? '#34d399';

  const chars = text.split('');
  const n = chars.length;

  // Overall opacity envelope for the whole scene
  const sceneOpacity = interpolate(
    frame,
    [0, 8, durationInFrames - 12, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Subtle background glow that intensifies during HOLD phase
  const glowOpacity = interpolate(
    frame,
    [HOLD_START, HOLD_END, SHATTER_START + 10],
    [0.08, 0.25, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Scale pulse during HOLD
  const scaleSpring = spring({
    fps,
    frame: Math.max(0, frame - HOLD_START),
    config: {damping: 14, stiffness: 60, mass: 0.6},
    durationInFrames: 30,
  });
  const holdScale = interpolate(scaleSpring, [0, 1], [0.93, 1.0]);

  // Shatter progress [0,1]
  const shatterProgress = interpolate(
    frame,
    [SHATTER_START, SHATTER_END],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity}}>
      {/* Background accent glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 700px 400px at 50% 48%, ${accentColor}${Math.round(glowOpacity * 255).toString(16).padStart(2, '0')} 0%, transparent 65%)`,
        }}
      />

      {/* Main text container */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 80px',
          transform: `scale(${frame >= HOLD_START && frame < SHATTER_START ? holdScale : 1})`,
        }}
      >
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '0 4px',
            textAlign: 'center',
          }}
        >
          {chars.map((char, i) => {
            const charStart = ASSEMBLE_START + i * CHAR_STAGGER;
            const charRevealFrame = charStart + 6;

            // During assembly: show glitch char, then real char
            const revealed = frame >= charRevealFrame;
            const inGlitch = frame >= charStart && frame < charRevealFrame;

            // Which glitch char to show (changes every 2 frames for flicker)
            const glitchIdx = Math.floor(frame / 2) + i;
            const glitchChar = GLITCH_CHARS[glitchIdx % GLITCH_CHARS.length];

            // Per-char shatter: translate + fade outward
            const shatterDelay = seededRand(i * 17) * 0.4;
            const charShatter = Math.max(
              0,
              Math.min(1, (shatterProgress - shatterDelay) / (1 - shatterDelay)),
            );
            const shatterX = (seededRand(i * 7) - 0.5) * 300 * charShatter * charShatter;
            const shatterY = (seededRand(i * 13) - 0.5) * 200 * charShatter * charShatter;
            const shatterRotate = (seededRand(i * 19) - 0.5) * 60 * charShatter;
            const charOpacity = frame >= SHATTER_START ? 1 - charShatter * charShatter : 1;

            const displayChar = !revealed && !inGlitch
              ? ' '
              : inGlitch
              ? glitchChar
              : char;

            const isSpace = char === ' ';
            if (isSpace && !inGlitch) {
              return <span key={i} style={{display: 'inline-block', width: '0.3em'}} />;
            }

            const charColor = inGlitch
              ? (i % 3 === 0 ? accentColor : glitch2)
              : '#ffffff';

            return (
              <span
                key={i}
                style={{
                  display: 'inline-block',
                  fontFamily: FONT,
                  fontSize: 72,
                  fontWeight: 900,
                  color: charColor,
                  letterSpacing: 2,
                  lineHeight: 1.1,
                  opacity: charOpacity,
                  textShadow: inGlitch
                    ? `0 0 20px ${accentColor}, 0 0 40px ${glitch2}`
                    : revealed
                    ? `0 0 30px ${accentColor}55`
                    : 'none',
                  transform: frame >= SHATTER_START
                    ? `translate(${shatterX}px, ${shatterY}px) rotate(${shatterRotate}deg)`
                    : 'none',
                  transition: 'none',
                  willChange: 'transform',
                }}
              >
                {displayChar}
              </span>
            );
          })}
        </div>

        {subtitle && (
          <div
            style={{
              marginTop: 40,
              fontFamily: FONT,
              fontSize: 28,
              fontWeight: 400,
              color: 'rgba(255,255,255,0.65)',
              textAlign: 'center',
              opacity: interpolate(
                frame,
                [HOLD_START + 5, HOLD_START + 20, SHATTER_START, SHATTER_START + 15],
                [0, 1, 1, 0],
                {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
              ),
              letterSpacing: 1,
            }}
          >
            {subtitle}
          </div>
        )}
      </AbsoluteFill>

      {/* Scanline overlay — subtle CRT effect */}
      <AbsoluteFill
        style={{
          background: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.04) 3px, rgba(0,0,0,0.04) 4px)',
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  );
};
