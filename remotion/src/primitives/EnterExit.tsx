import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';

interface EnterExitProps {
  activeBeat: SceneBeat;
  exitBeat?: SceneBeat;
  enterStyle?: 'fade' | 'slide-up' | 'slide-down' | 'slide-left' | 'slide-right' | 'scale' | 'slam' | 'none';
  exitStyle?: 'fade' | 'slide-up' | 'slide-right' | 'scale' | 'none';
  children: React.ReactNode;
  style?: React.CSSProperties;
}

export const EnterExit: React.FC<EnterExitProps> = ({
  activeBeat,
  exitBeat,
  enterStyle = 'fade',
  exitStyle = 'none',
  children,
  style,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const enterStart = Math.round(activeBeat.start * fps);
  const enterEnd = Math.round(activeBeat.end * fps);
  const enterDur = Math.max(enterEnd - enterStart, 1);
  const enterP = interpolate(frame, [enterStart, enterStart + Math.min(enterDur, 12)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  let exitP = 0;
  if (exitBeat) {
    const exitStart = Math.round(exitBeat.start * fps);
    const exitEnd = Math.round(exitBeat.end * fps);
    exitP = interpolate(frame, [exitStart, exitEnd], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
  }

  const visible = frame >= enterStart;
  if (!visible) return null;

  let opacity = 1;
  let tx = 0;
  let ty = 0;
  let sc = 1;

  switch (enterStyle) {
    case 'fade': opacity *= enterP; break;
    case 'slide-up': ty = (1 - enterP) * 60; opacity *= enterP; break;
    case 'slide-down': ty = -(1 - enterP) * 60; opacity *= enterP; break;
    case 'slide-left': tx = (1 - enterP) * 120; opacity *= enterP; break;
    case 'slide-right': tx = -(1 - enterP) * 120; opacity *= enterP; break;
    case 'scale': sc = 0.3 + enterP * 0.7; opacity *= enterP; break;
    case 'slam': {
      const slamP = Math.min(1, enterP * 1.3);
      sc = 1 + (1 - slamP) * 0.8;
      opacity *= Math.min(1, enterP * 2);
      break;
    }
    case 'none': break;
  }

  if (exitBeat && exitP > 0) {
    switch (exitStyle) {
      case 'fade': opacity *= (1 - exitP); break;
      case 'slide-up': ty -= exitP * 80; opacity *= (1 - exitP); break;
      case 'slide-right': tx += exitP * 200; opacity *= (1 - exitP); break;
      case 'scale': sc *= (1 - exitP * 0.6); opacity *= (1 - exitP); break;
      case 'none': break;
    }
  }

  return (
    <div style={{
      position: 'absolute',
      inset: 0,
      opacity,
      transform: `translate(${tx}px, ${ty}px) scale(${sc})`,
      ...style,
    }}>
      {children}
    </div>
  );
};
