/**
 * AssetScene — Renders a hero image or video clip with editorial motion.
 *
 * Tail-fill: when a video is shorter than its scene allocation,
 * the extracted end-frame is displayed with subtle continuation motion
 * so there is never a blank/background gap.
 */
import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {ArtDirection} from '../themes';

const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

type MotionType = 'push' | 'pan_left' | 'pan_right' | 'parallax' | 'zoom_center' | 'crop_left' | 'crop_right' | 'none';

interface AssetSceneProps {
  src: string;
  mediaType: 'video' | 'image';
  motion?: MotionType;
  label?: string;
  labelPosition?: 'bottom' | 'top' | 'center';
  subtitle?: string;
  durationInFrames: number;
  artDirection?: ArtDirection;
  accentColor?: string;
  videoDurationS?: number;
  endframeSrc?: string;
}

export const AssetScene: React.FC<AssetSceneProps> = ({
  src,
  mediaType,
  motion = 'push',
  label,
  labelPosition = 'bottom',
  subtitle,
  durationInFrames,
  artDirection: ad,
  accentColor,
  videoDurationS,
  endframeSrc,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const accent = accentColor ?? ad?.palette.primary ?? '#a78bfa';
  const bgColor = ad?.palette.bg ?? '#050510';
  const textColor = ad?.palette.text ?? '#ffffff';
  const fontFamily = ad?.typography.font ?? FONT;

  // Scene fade-in
  const sceneOpacity = interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'});

  // Video tail-fill: determine if we're past the video's end
  const videoEndFrame = videoDurationS ? Math.floor(videoDurationS * fps) : durationInFrames;
  const isVideoTail = mediaType === 'video' && frame >= videoEndFrame;

  // Motion transforms — continuous across video and tail-fill
  const progress = frame / Math.max(durationInFrames, 1);
  let transform = '';

  switch (motion) {
    case 'push': {
      const s = interpolate(progress, [0, 1], [1.0, 1.12]);
      transform = `scale(${s})`;
      break;
    }
    case 'pan_left': {
      const panL = interpolate(progress, [0, 1], [3, -3]);
      transform = `scale(1.15) translateX(${panL}%)`;
      break;
    }
    case 'pan_right': {
      const panR = interpolate(progress, [0, 1], [-3, 3]);
      transform = `scale(1.15) translateX(${panR}%)`;
      break;
    }
    case 'parallax': {
      const parY = interpolate(progress, [0, 1], [2, -2]);
      transform = `scale(1.2) translateY(${parY}%)`;
      break;
    }
    case 'zoom_center': {
      const zs = interpolate(progress, [0, 1], [1.3, 1.45]);
      transform = `scale(${zs})`;
      break;
    }
    case 'crop_left': {
      const clPan = interpolate(progress, [0, 1], [-15, -18]);
      transform = `scale(1.8) translateX(${clPan}%)`;
      break;
    }
    case 'crop_right': {
      const crPan = interpolate(progress, [0, 1], [15, 18]);
      transform = `scale(1.8) translateX(${crPan}%)`;
      break;
    }
    case 'none':
    default:
      transform = 'scale(1.15)';
      break;
  }

  // Label animation
  const labelDelay = Math.min(12, Math.floor(durationInFrames * 0.08));
  const labelOpacity = label
    ? interpolate(frame, [labelDelay, labelDelay + 12], [0, 1], {extrapolateRight: 'clamp'})
    : 0;
  const labelY = label
    ? interpolate(frame, [labelDelay, labelDelay + 12], [20, 0], {extrapolateRight: 'clamp'})
    : 0;

  // Subtitle animation
  const subDelay = labelDelay + 8;
  const subOpacity = subtitle
    ? interpolate(frame, [subDelay, subDelay + 10], [0, 1], {extrapolateRight: 'clamp'})
    : 0;

  // Gradient overlay for text readability
  const gradientPosition = labelPosition === 'top'
    ? 'linear-gradient(to bottom, rgba(0,0,0,0.7) 0%, transparent 40%)'
    : 'linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 40%)';

  const labelContainerStyle: React.CSSProperties = {
    position: 'absolute',
    left: 0,
    right: 0,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 12,
    padding: '0 48px',
    zIndex: 3,
    ...(labelPosition === 'top' ? {top: 160} : {}),
    ...(labelPosition === 'center' ? {top: '50%', transform: 'translateY(-50%)'} : {}),
    ...(labelPosition === 'bottom' ? {bottom: 200} : {}),
  };

  const mediaStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover' as const,
  };

  const renderMedia = () => {
    if (mediaType === 'image') {
      return <Img src={staticFile(src)} style={mediaStyle} />;
    }

    // Video with tail-fill
    if (isVideoTail && endframeSrc) {
      return <Img src={staticFile(endframeSrc)} style={mediaStyle} />;
    }

    return (
      <OffthreadVideo
        src={staticFile(src)}
        style={mediaStyle}
        muted
        endAt={videoDurationS ? videoEndFrame : undefined}
      />
    );
  };

  return (
    <AbsoluteFill style={{backgroundColor: bgColor, opacity: sceneOpacity, overflow: 'hidden'}}>
      {/* Media layer — video, endframe hold, or image */}
      <AbsoluteFill style={{transform, transformOrigin: '50% 50%'}}>
        {renderMedia()}
      </AbsoluteFill>

      {/* Gradient overlay for text */}
      {(label || subtitle) && (
        <AbsoluteFill style={{background: gradientPosition, zIndex: 2}} />
      )}

      {/* Label overlay */}
      {(label || subtitle) && (
        <div style={labelContainerStyle}>
          {label && (
            <div
              style={{
                fontFamily,
                fontSize: 42,
                fontWeight: 800,
                color: textColor,
                textAlign: 'center',
                lineHeight: 1.2,
                opacity: labelOpacity,
                transform: `translateY(${labelY}px)`,
                textShadow: '0 2px 20px rgba(0,0,0,0.8)',
                letterSpacing: 1,
              }}
            >
              {label}
            </div>
          )}
          {subtitle && (
            <div
              style={{
                fontFamily,
                fontSize: 26,
                fontWeight: 600,
                color: accent,
                textAlign: 'center',
                opacity: subOpacity,
                textShadow: '0 1px 12px rgba(0,0,0,0.6)',
                letterSpacing: 2,
                textTransform: 'uppercase',
              }}
            >
              {subtitle}
            </div>
          )}
        </div>
      )}
    </AbsoluteFill>
  );
};
