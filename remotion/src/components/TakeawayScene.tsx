/**
 * TakeawayScene — the "Key Takeaway" summary scene.
 *
 * Shows a single bold statement with animated visual summary.
 * Sits just before the CTA scene at the end of every episode.
 *
 * Props:
 *   text          — the takeaway statement (≤ 10 words)
 *   accentColor   — theme accent hex
 *   durationInFrames
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {SceneBeat} from '../types';
import {easeOut, smoothstep} from './beatUtils';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const BG = '#050510';

interface TakeawaySceneProps {
  text: string;
  accentColor: string;
  accent2?: string;
  durationInFrames: number;
  // v3 props
  beats?: SceneBeat[];
  onScreenText?: string[];
}

export const TakeawayScene: React.FC<TakeawaySceneProps> = ({
  text,
  accentColor,
  accent2 = '#34d399',
  durationInFrames,
  beats,
  onScreenText,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // ── v3 icon-row mode ─────────────────────────────────────────────────────
  if (beats && beats.length >= 2) {
    // B0: 3 concept icons slide in from bottom (staggered)
    // B1: connector lines draw between them
    // B2: takeaway text rises below
    const iconP     = easeOut(frame, fps, beats[0].start, beats[0].end);
    const connP     = easeOut(frame, fps, beats[1].start, beats[1].end);
    const textBeatP = beats[2] ? easeOut(frame, fps, beats[2].start, beats[2].end) : connP;

    const sceneOp = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

    const ICONS  = ['🔍', '📚', '🤖'];
    const LABELS = onScreenText?.slice(0, 3) ?? ['Retrieve', 'Context', 'Generate'];
    const ICON_Y = 820;
    const ICON_XS = [200, 540, 880];
    const ICON_R = 80;

    return (
      <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOp}}>
        <AbsoluteFill style={{
          background: `radial-gradient(ellipse 900px 700px at 50% 43%, ${accentColor}0c 0%, transparent 65%)`,
        }}/>

        <svg viewBox="0 0 1080 1920" width={1080} height={1920} style={{position:'absolute',inset:0}}>
          {/* Connector lines draw L→R */}
          {[0, 1].map(i => {
            const x1 = ICON_XS[i] + ICON_R;
            const x2 = ICON_XS[i + 1] - ICON_R;
            const lineP = smoothstep(interpolate(connP, [i * 0.3, i * 0.3 + 0.6], [0, 1], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
            }));
            return (
              <line key={i} x1={x1} y1={ICON_Y} x2={x1 + (x2 - x1) * lineP} y2={ICON_Y}
                stroke={`${accentColor}88`} strokeWidth={3} strokeDasharray="8 4"/>
            );
          })}

          {/* Icon circles */}
          {ICONS.map((icon, i) => {
            const delay = i / ICONS.length * 0.5;
            const ip = smoothstep(interpolate(iconP, [delay, delay + 0.5], [0, 1], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
            }));
            const ty = interpolate(ip, [0, 1], [60, 0]);
            const col = i === 1 ? accent2 : accentColor;

            return (
              <g key={i} opacity={ip} transform={`translate(0, ${ty})`}>
                <circle cx={ICON_XS[i]} cy={ICON_Y} r={ICON_R}
                  fill={`${col}15`} stroke={col} strokeWidth={2.5}/>
                <text x={ICON_XS[i]} y={ICON_Y + 10} textAnchor="middle" dominantBaseline="middle"
                  fontSize={40}>{icon}</text>
                <text x={ICON_XS[i]} y={ICON_Y + ICON_R + 36} textAnchor="middle"
                  fill={col} fontFamily={FONT} fontSize={22} fontWeight="700">
                  {LABELS[i]}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Takeaway text rises from below */}
        <div style={{
          position: 'absolute', bottom: 300, left: 60, right: 60,
          opacity: smoothstep(textBeatP),
          transform: `translateY(${interpolate(textBeatP, [0, 1], [40, 0])}px)`,
          textAlign: 'center',
        }}>
          <div style={{
            fontSize: 18, fontWeight: 700, color: accentColor, letterSpacing: 6,
            textTransform: 'uppercase', fontFamily: FONT, marginBottom: 20,
          }}>Key Takeaway</div>
          <div style={{
            fontSize: 52, fontWeight: 800, color: '#fff', lineHeight: 1.3,
            fontFamily: FONT, letterSpacing: -0.5, textShadow: `0 0 60px ${accentColor}44`,
          }}>{text}</div>
        </div>
      </AbsoluteFill>
    );
  }

  // ── Legacy spring-based mode (unchanged) ────────────────────────────────
  const sceneOpacity = interpolate(
    frame,
    [0, 8, durationInFrames - 10, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const ruleWidth = interpolate(frame, [8, 30], [0, 80], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const labelOpacity = interpolate(frame, [10, 25], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const labelY = interpolate(frame, [10, 25], [12, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const textOpacity = interpolate(frame, [22, 40], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const textY = interpolate(frame, [22, 40], [50, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const glowSize = 600 + 80 * Math.sin((frame / 50) * 2 * Math.PI);
  const checkOpacity = interpolate(frame, [38, 55], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const checkScale = interpolate(frame, [38, 55], [0.3, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: BG, opacity: sceneOpacity}}>
      <AbsoluteFill style={{background: `radial-gradient(ellipse ${glowSize}px ${glowSize * 0.6}px at 50% 50%, ${accentColor}0f 0%, transparent 70%)`}}/>
      <AbsoluteFill style={{backgroundImage: `linear-gradient(${accentColor}08 1px, transparent 1px), linear-gradient(90deg, ${accentColor}08 1px, transparent 1px)`, backgroundSize: '80px 80px'}}/>
      <AbsoluteFill style={{display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',padding:'0 80px',gap:0}}>
        <div style={{width:72,height:72,borderRadius:'50%',background:`linear-gradient(135deg, ${accentColor} 0%, ${accent2} 100%)`,display:'flex',alignItems:'center',justifyContent:'center',marginBottom:36,opacity:checkOpacity,transform:`scale(${checkScale})`,boxShadow:`0 0 40px ${accentColor}55`}}>
          <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
            <path d="M7 18L15 26L29 10" stroke="#ffffff" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div style={{opacity:labelOpacity,transform:`translateY(${labelY}px)`,fontFamily:FONT,fontSize:18,fontWeight:700,color:accentColor,letterSpacing:6,textTransform:'uppercase',marginBottom:20}}>Key Takeaway</div>
        <div style={{width:`${ruleWidth}%`,height:2,background:`linear-gradient(90deg, transparent, ${accentColor}, ${accent2}, transparent)`,marginBottom:32,opacity:0.8}}/>
        <div style={{opacity:textOpacity,transform:`translateY(${textY}px)`,fontFamily:FONT,fontSize:56,fontWeight:800,color:'#ffffff',lineHeight:1.3,textAlign:'center',letterSpacing:-0.5,textShadow:`0 0 60px ${accentColor}44`}}>{text}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
