import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import type {StoryboardScene, PrimitiveInstance, ComposedSceneSpec} from './types';
import type {ArtDirection} from './themes';
import type {SceneBeat} from './types';
import {
  EnterExit,
  StampOverlay,
  ColorTransform,
  CameraTransform,
  ConnectArrow,
  TravelPath,
  SpatialZone,
  DualLaneLayout,
  GaugeArc,
  ObjectBlock,
  CardFan,
  RibbonObject,
} from './primitives';

interface ComposedSceneProps {
  scene: StoryboardScene;
  artDirection: ArtDirection;
}

function resolveBeat(scene: StoryboardScene, beatIndex: number): SceneBeat {
  const beats = scene.beats ?? [];
  if (beatIndex >= 0 && beatIndex < beats.length) {
    return beats[beatIndex];
  }
  return {start: 0, end: scene.duration_seconds, action: 'hold'};
}

function renderPrimitive(
  layer: PrimitiveInstance,
  scene: StoryboardScene,
  ad: ArtDirection,
  fps: number,
  durationInFrames: number,
  key: string,
): React.ReactNode {
  const beat = resolveBeat(scene, layer.activeBeat);
  const cfg = layer.config;

  switch (layer.primitive) {
    case 'ObjectBlock':
      return (
        <ObjectBlock
          key={key}
          activeBeat={beat}
          label={cfg.label as string}
          position={cfg.position as {x: number; y: number}}
          width={cfg.width as number | undefined}
          height={cfg.height as number | undefined}
          color={cfg.color as string | undefined}
          blockStyle={cfg.blockStyle as 'solid' | 'outlined' | 'ghosted' | 'crossed-out' | undefined}
          icon={cfg.icon as string | undefined}
          sublabel={cfg.sublabel as string | undefined}
          artDirection={ad}
          fps={fps}
        />
      );

    case 'StampOverlay':
      return (
        <StampOverlay
          key={key}
          activeBeat={beat}
          text={cfg.text as string}
          target={cfg.target as {x: number; y: number}}
          impact={cfg.impact as 'slam' | 'fade' | 'grow' | undefined}
          color={cfg.color as string | undefined}
          angle={cfg.angle as number | undefined}
          fontSize={cfg.fontSize as number | undefined}
          width={cfg.width as number | undefined}
          height={cfg.height as number | undefined}
          artDirection={ad}
          fps={fps}
          durationInFrames={durationInFrames}
        />
      );

    case 'ConnectArrow':
      return (
        <ConnectArrow
          key={key}
          activeBeat={beat}
          from={cfg.from as {x: number; y: number}}
          to={cfg.to as {x: number; y: number}}
          color={cfg.color as string | undefined}
          label={cfg.label as string | undefined}
          style={cfg.style as 'solid' | 'dashed' | 'animated' | undefined}
          artDirection={ad}
          fps={fps}
        />
      );

    case 'GaugeArc':
      return (
        <GaugeArc
          key={key}
          activeBeat={beat}
          center={cfg.center as {x: number; y: number}}
          radius={cfg.radius as number | undefined}
          targetValue={cfg.targetValue as number}
          fillColor={cfg.fillColor as string | undefined}
          zones={cfg.zones as Array<{start: number; end: number; color: string; label?: string}> | undefined}
          title={cfg.title as string | undefined}
          valueLabel={cfg.valueLabel as string | undefined}
          pulse={cfg.pulse as boolean | undefined}
          artDirection={ad}
          fps={fps}
        />
      );

    case 'SpatialZone':
      return (
        <SpatialZone
          key={key}
          activeBeat={beat}
          bounds={cfg.bounds as {x: number; y: number; width: number; height: number}}
          label={cfg.label as string | undefined}
          labelPosition={cfg.labelPosition as 'top' | 'inside' | 'bottom' | undefined}
          borderStyle={cfg.borderStyle as 'solid' | 'dashed' | 'glow' | undefined}
          color={cfg.color as string | undefined}
          pulse={cfg.pulse as boolean | undefined}
          artDirection={ad}
          fps={fps}
        />
      );

    case 'CardFan':
      return (
        <CardFan
          key={key}
          activeBeat={beat}
          cards={cfg.cards as Array<{label: string; sublabel?: string; color?: string; icon?: string}>}
          origin={cfg.origin as {x: number; y: number} | undefined}
          cardWidth={cfg.cardWidth as number | undefined}
          cardHeight={cfg.cardHeight as number | undefined}
          spreadAngle={cfg.spreadAngle as number | undefined}
          holdAll={cfg.holdAll as boolean | undefined}
          artDirection={ad}
          fps={fps}
          durationInFrames={durationInFrames}
        />
      );

    case 'RibbonObject':
      return (
        <RibbonObject
          key={key}
          activeBeat={beat}
          tokens={cfg.tokens as Array<{text: string; color: string; fabricated?: boolean}>}
          startPos={cfg.startPos as {x: number; y: number}}
          endPos={cfg.endPos as {x: number; y: number}}
          emissionRate={cfg.emissionRate as number | undefined}
          tokenSize={cfg.tokenSize as number | undefined}
          tokenSpacing={cfg.tokenSpacing as number | undefined}
          showConnector={cfg.showConnector as boolean | undefined}
          artDirection={ad}
          fps={fps}
          durationInFrames={durationInFrames}
        />
      );

    case 'EnterExit':
      return (
        <EnterExit
          key={key}
          activeBeat={beat}
          enterStyle={cfg.enterStyle as 'fade' | 'slide-up' | 'slide-down' | 'slide-left' | 'slide-right' | 'scale' | 'slam' | 'none' | undefined}
          exitStyle={cfg.exitStyle as 'fade' | 'slide-up' | 'slide-right' | 'scale' | 'none' | undefined}
          exitBeat={cfg.exitBeatIndex != null ? resolveBeat(scene, cfg.exitBeatIndex as number) : undefined}
          artDirection={ad}
          fps={fps}
          durationInFrames={durationInFrames}
        >
          {cfg.children != null ? (
            <div style={{
              position: 'absolute',
              left: (cfg.position as {x: number; y: number})?.x ?? 540,
              top: (cfg.position as {x: number; y: number})?.y ?? 960,
              transform: 'translate(-50%, -50%)',
              color: (cfg.color as string) ?? ad.palette.text,
              fontFamily: ad.typography.font,
              fontSize: (cfg.fontSize as number) ?? 36,
              fontWeight: 700,
              whiteSpace: 'nowrap',
              ...((cfg.width as number | undefined) != null ? {
                width: cfg.width as number,
                height: (cfg.height as number | undefined) ?? (cfg.width as number),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: `${(cfg.color as string) ?? ad.palette.primary}22`,
                border: `2px solid ${(cfg.color as string) ?? ad.palette.primary}66`,
                borderRadius: 12,
              } : {}),
            }}>
              {cfg.children as string}
            </div>
          ) : null}
        </EnterExit>
      );

    case 'ColorTransform':
      return (
        <ColorTransform
          key={key}
          activeBeat={beat}
          fromColor={cfg.fromColor as string}
          toColor={cfg.toColor as string}
          easing={cfg.easing as 'linear' | 'ease-out' | 'ease-in-out' | undefined}
          fps={fps}
        >
          {(currentColor: string) => (
            <div style={{
              position: 'absolute',
              left: (cfg.position as {x: number; y: number})?.x ?? 540,
              top: (cfg.position as {x: number; y: number})?.y ?? 960,
              transform: 'translate(-50%, -50%)',
              color: currentColor,
              fontFamily: ad.typography.font,
              fontSize: (cfg.fontSize as number) ?? 36,
              fontWeight: 700,
            }}>
              {cfg.label as string ?? ''}
            </div>
          )}
        </ColorTransform>
      );

    case 'TravelPath': {
      const trailCfg = cfg.trail as {show?: boolean; style?: string; color?: string} | undefined;
      const waypoints = (cfg.waypoints as Array<{x: number; y: number}>) ??
        (cfg.from && cfg.to
          ? [cfg.from as {x: number; y: number}, cfg.to as {x: number; y: number}]
          : [{x: 100, y: 960}, {x: 980, y: 960}]);
      return (
        <TravelPath
          key={key}
          activeBeat={beat}
          path={waypoints}
          showTrail={trailCfg?.show}
          trailStyle={trailCfg?.style as 'solid' | 'dashed' | 'dotted' | undefined}
          trailColor={trailCfg?.color}
          fps={fps}
        >
          <div style={{
            width: (cfg.objectWidth as number) ?? 80,
            height: (cfg.objectHeight as number) ?? 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: `${(cfg.color as string) ?? ad.palette.primary}22`,
            border: `2px solid ${(cfg.color as string) ?? ad.palette.primary}66`,
            borderRadius: 8,
            color: (cfg.color as string) ?? ad.palette.primary,
            fontFamily: ad.typography.font,
            fontSize: 16,
            fontWeight: 700,
          }}>
            {(cfg.label as string) ?? ''}
          </div>
        </TravelPath>
      );
    }

    case 'DualLaneLayout':
      return (
        <DualLaneLayout
          key={key}
          activeBeat={beat}
          topLane={cfg.topLane as {label?: string; color?: string}}
          bottomLane={cfg.bottomLane as {label?: string; color?: string}}
          dividerStyle={cfg.dividerStyle as 'solid' | 'dashed' | 'none' | undefined}
          artDirection={ad}
          fps={fps}
        />
      );

    case 'CameraTransform':
      return null;

    default:
      return null;
  }
}

export const ComposedScene: React.FC<ComposedSceneProps> = ({scene, artDirection: ad}) => {
  const {fps, durationInFrames} = useVideoConfig();
  const spec = scene.data as ComposedSceneSpec | undefined;
  if (!spec || spec.type !== 'composed') {
    return <AbsoluteFill style={{background: ad.palette.bg}} />;
  }

  const sorted = [...spec.layers].sort((a, b) => a.zIndex - b.zIndex);

  let cameraLayer: PrimitiveInstance | undefined;
  const nonCameraLayers = sorted.filter(l => {
    if (l.primitive === 'CameraTransform') {
      cameraLayer = l;
      return false;
    }
    return true;
  });

  const content = (
    <AbsoluteFill style={{background: ad.palette.bg}}>
      {/* Background grid — must survive 108×192 downscale with CONTENT_DELTA=18 */}
      <AbsoluteFill style={{opacity: 0.25}}>
        <svg viewBox="0 0 1080 1920" width={1080} height={1920}>
          {Array.from({length: 12}, (_, i) => (
            <line key={`h${i}`}
              x1={0} y1={160 * (i + 1)} x2={1080} y2={160 * (i + 1)}
              stroke={ad.palette.primary ?? '#a78bfa'} strokeWidth={3}
            />
          ))}
          {Array.from({length: 6}, (_, i) => (
            <line key={`v${i}`}
              x1={180 * (i + 1)} y1={0} x2={180 * (i + 1)} y2={1920}
              stroke={ad.palette.primary ?? '#a78bfa'} strokeWidth={3}
            />
          ))}
        </svg>
      </AbsoluteFill>
      {/* Background radial glow */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse 1000px 1000px at 540px 960px, ${ad.palette.primary ?? '#a78bfa'}30 0%, transparent 60%)`,
      }} />
      {/* Corner accent marks */}
      <svg viewBox="0 0 1080 1920" width={1080} height={1920}
        style={{position: 'absolute', inset: 0, opacity: 0.25}}>
        <rect x={20} y={20} width={120} height={4} fill={ad.palette.primary ?? '#a78bfa'} />
        <rect x={20} y={20} width={4} height={120} fill={ad.palette.primary ?? '#a78bfa'} />
        <rect x={940} y={20} width={120} height={4} fill={ad.palette.primary ?? '#a78bfa'} />
        <rect x={1056} y={20} width={4} height={120} fill={ad.palette.primary ?? '#a78bfa'} />
        <rect x={20} y={1896} width={120} height={4} fill={ad.palette.primary ?? '#a78bfa'} />
        <rect x={20} y={1780} width={4} height={120} fill={ad.palette.primary ?? '#a78bfa'} />
        <rect x={940} y={1896} width={120} height={4} fill={ad.palette.primary ?? '#a78bfa'} />
        <rect x={1056} y={1780} width={4} height={120} fill={ad.palette.primary ?? '#a78bfa'} />
      </svg>
      {nonCameraLayers.map((layer, i) =>
        renderPrimitive(layer, scene, ad, fps, durationInFrames, `layer-${i}-${layer.primitive}`)
      )}
    </AbsoluteFill>
  );

  if (cameraLayer) {
    const camBeat = resolveBeat(scene, cameraLayer.activeBeat);
    const camCfg = cameraLayer.config;
    return (
      <CameraTransform
        activeBeat={camBeat}
        operation={camCfg.operation as 'zoom-in' | 'zoom-out' | 'pan-left' | 'pan-right' | 'pan-follow' | 'push-in' | 'static'}
        intensity={camCfg.intensity as number | undefined}
        artDirection={ad}
        fps={fps}
        durationInFrames={durationInFrames}
      >
        {content}
      </CameraTransform>
    );
  }

  return content;
};
