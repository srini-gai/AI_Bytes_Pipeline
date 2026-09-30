/**
 * beatUtils.ts — helpers for beat-driven Remotion components (Visual Director v3).
 *
 * A "beat" is a timed visual event within a scene. All timing is in seconds
 * relative to scene start. Remotion works in frames, so we convert via FPS.
 *
 * Usage:
 *   const {beatProgress, inBeat, beatFrame} = useBeat(fps, beat);
 *   // beatProgress: 0→1 over the beat's time window
 *   // inBeat:       true while the current frame falls inside this beat
 *   // beatFrame:    frames elapsed since beat started (0 when before beat)
 */
import {interpolate, useCurrentFrame} from 'remotion';
import type {SceneBeat} from '../types';

export interface BeatResult {
  /** 0→1 progress through this beat, clamped */
  beatProgress: number;
  /** frames elapsed since beat start, ≥0 */
  beatFrame: number;
  /** true while frame is within [start, end) */
  inBeat: boolean;
  /** true once beat has started (frame ≥ start) */
  started: boolean;
  /** true once beat has ended (frame ≥ end) */
  ended: boolean;
}

export function useBeat(fps: number, beat: SceneBeat): BeatResult {
  const frame = useCurrentFrame();
  const startF = Math.round(beat.start * fps);
  const endF   = Math.round(beat.end   * fps);
  const beatFrame   = Math.max(0, frame - startF);
  const beatProgress = interpolate(frame, [startF, endF], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return {
    beatProgress,
    beatFrame,
    inBeat:  frame >= startF && frame < endF,
    started: frame >= startF,
    ended:   frame >= endF,
  };
}

/**
 * Smooth ease-out interpolation 0→1, starting at `startSec` and completing
 * at `endSec` (both relative to scene start in seconds).
 */
export function easeOut(frame: number, fps: number, startSec: number, endSec: number): number {
  const raw = interpolate(
    frame,
    [Math.round(startSec * fps), Math.round(endSec * fps)],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  // Cubic ease-out: t→ 1-(1-t)^3
  return 1 - Math.pow(1 - raw, 3);
}

/**
 * Linear progress 0→1 over a time window (seconds relative to scene start).
 */
export function linearProgress(frame: number, fps: number, startSec: number, endSec: number): number {
  return interpolate(
    frame,
    [Math.round(startSec * fps), Math.round(endSec * fps)],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
}

/**
 * Spring-like ease-in-out (simple smoothstep).
 */
export function smoothstep(t: number): number {
  const c = Math.max(0, Math.min(1, t));
  return c * c * (3 - 2 * c);
}

/** Theme constants */
export const BG       = '#050510';
export const ACCENT   = '#a78bfa';
export const ACCENT2  = '#34d399';
export const FONT     = '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
export const MONO     = '"JetBrains Mono", "Fira Mono", monospace';
