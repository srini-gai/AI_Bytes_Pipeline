import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {FlowSpec} from '../types';

interface SceneTheme { accent: string; accent2: string; }

const DEFAULT_THEME: SceneTheme = {accent: '#a78bfa', accent2: '#34d399'};
const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const CIRCLE = 88;
const ARROW_H = 68;

interface FlowSceneProps {
  spec: FlowSpec;
  theme?: SceneTheme;
}

export const FlowScene: React.FC<FlowSceneProps> = ({spec, theme}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = theme ?? DEFAULT_THEME;
  const {steps} = spec;
  const n = steps.length;

  const STEPS_START = 28;
  const stepInterval = Math.floor(180 / n);
  const totalH = n * CIRCLE + (n - 1) * ARROW_H;
  const containerW = 700;

  const titleOpacity = interpolate(frame, [0, 18], [0, 1], {extrapolateRight: 'clamp'});
  const titleY = interpolate(frame, [0, 18], [16, 0], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: '#050510'}}>
      <AbsoluteFill
        style={{background: `radial-gradient(ellipse 700px 700px at 50% 52%, ${t.accent}18 0%, transparent 70%)`}}
      />
      <AbsoluteFill
        style={{background: 'linear-gradient(to bottom, transparent 72%, rgba(0,0,0,0.8) 100%)'}}
      />

      {/* Section label */}
      <div
        style={{
          position: 'absolute', top: 136, left: 0, right: 0,
          textAlign: 'center',
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
          zIndex: 2,
          fontSize: 24, letterSpacing: 6,
          textTransform: 'uppercase' as const,
          color: t.accent, fontFamily: FONT, fontWeight: 700,
          textShadow: `0 0 20px ${t.accent}88`,
        }}
      >
        How It Works
      </div>

      {/* Steps container — centered vertically */}
      <div
        style={{
          position: 'absolute',
          left: `calc(50% - ${containerW / 2}px)`,
          top: `calc(50% - ${totalH / 2}px)`,
          width: containerW,
          height: totalH,
          zIndex: 2,
        }}
      >
        {steps.map((step, i) => {
          const stepStart = STEPS_START + i * stepInterval;
          const stepOpacity = interpolate(frame, [stepStart, stepStart + 16], [0, 1], {extrapolateRight: 'clamp'});
          const stepScale = spring({
            frame: Math.max(0, frame - stepStart),
            fps,
            config: {damping: 14, mass: 0.6, stiffness: 260},
            durationInFrames: 18,
          });
          const labelX = interpolate(frame, [stepStart, stepStart + 16], [20, 0], {extrapolateRight: 'clamp'});

          const circleTop = i * (CIRCLE + ARROW_H);
          const arrowStart = stepStart + 14;
          const arrowH = interpolate(
            frame,
            [arrowStart, arrowStart + stepInterval - 10],
            [0, ARROW_H],
            {extrapolateRight: 'clamp'},
          );
          const arrowVisible = frame >= arrowStart + stepInterval - 12;

          return (
            <React.Fragment key={i}>
              {/* Icon circle */}
              <div
                style={{
                  position: 'absolute',
                  left: 0, top: circleTop,
                  width: CIRCLE, height: CIRCLE,
                  borderRadius: '50%',
                  background: `radial-gradient(circle, ${t.accent}44 0%, ${t.accent}18 100%)`,
                  border: `2.5px solid ${t.accent}`,
                  boxShadow: `0 0 24px ${t.accent}66, 0 0 48px ${t.accent}22`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 42,
                  opacity: stepOpacity,
                  transform: `scale(${stepScale})`,
                }}
              >
                {step.icon}
              </div>

              {/* Step label */}
              <div
                style={{
                  position: 'absolute',
                  left: CIRCLE + 30,
                  top: circleTop + Math.round((CIRCLE - 52) / 2),
                  right: 0,
                  opacity: stepOpacity,
                  transform: `translateX(${labelX}px)`,
                  fontSize: 46,
                  fontWeight: 700,
                  color: '#ffffff',
                  fontFamily: FONT,
                  letterSpacing: -0.5,
                  textShadow: '0 2px 14px rgba(0,0,0,0.9)',
                  lineHeight: 1.15,
                }}
              >
                {step.label}
              </div>

              {/* Connector arrow */}
              {i < n - 1 && (
                <>
                  <div
                    style={{
                      position: 'absolute',
                      left: Math.round(CIRCLE / 2) - 1,
                      top: circleTop + CIRCLE,
                      width: 2,
                      height: arrowH,
                      background: `linear-gradient(to bottom, ${t.accent}, ${t.accent2})`,
                      boxShadow: `0 0 8px ${t.accent}88`,
                    }}
                  />
                  {arrowVisible && (
                    <div
                      style={{
                        position: 'absolute',
                        left: Math.round(CIRCLE / 2) - 7,
                        top: circleTop + CIRCLE + ARROW_H - 2,
                        width: 0, height: 0,
                        borderLeft: '7px solid transparent',
                        borderRight: '7px solid transparent',
                        borderTop: `10px solid ${t.accent2}`,
                      }}
                    />
                  )}
                </>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
