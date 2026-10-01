/**
 * AIBytesReel — root Remotion composition.
 *
 * Supports two rendering modes:
 *
 *  STORYBOARD MODE (new)
 *    When `props.storyboard` is provided, each scene in the array is rendered
 *    in order via `renderStoryboardScene()`, which routes to the matching
 *    Remotion component. This is the Visual Director pipeline path.
 *
 *  LEGACY MODE (backward-compatible)
 *    When `props.storyboard` is absent, falls back to the original fixed-section
 *    layout: HookScene (0–7s) → ConceptScene (7–15s) → SlideScene×N (15–50s) → CTA (50–60s).
 */
import React from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame} from 'remotion';

// Existing components (legacy + reused in storyboard mode)
import {HookScene} from './components/HookScene';
import {ConceptScene} from './components/ConceptScene';
import {SlideScene} from './components/SlideScene';
import {CTAScene} from './components/CTAScene';
import {FlowScene} from './components/FlowScene';
import {HubSpokeScene} from './components/HubSpokeScene';
import {SplitCompareScene} from './components/SplitCompareScene';
import {BarChartScene} from './components/BarChartScene';
import {ClusterScene} from './components/ClusterScene';
import {DialScene} from './components/DialScene';
import {SketchScene} from './components/SketchScene';
import {DataScene} from './components/DataScene';
import {TokenScene} from './components/TokenScene';

// New Visual Director components
import {KineticTypoScene} from './components/KineticTypoScene';
import {NumberCounterScene} from './components/NumberCounterScene';
import {TakeawayScene} from './components/TakeawayScene';

// Visual Director v3 — beat-driven scene primitives
import {BeforeAfterScene} from './components/BeforeAfterScene';
import {TransformScene} from './components/TransformScene';
import {DataFlowScene} from './components/DataFlowScene';
import {DocumentRetrievalScene} from './components/DocumentRetrievalScene';
import {ContextWindowScene} from './components/ContextWindowScene';
import {TokenStreamScene} from './components/TokenStreamScene';
import {PipelineScene} from './components/PipelineScene';
import {MeterScene} from './components/MeterScene';
import {NetworkBuildScene} from './components/NetworkBuildScene';
import {LayerRevealScene} from './components/LayerRevealScene';
import {TimelineScene} from './components/TimelineScene';
import {GraphGrowthScene} from './components/GraphGrowthScene';
import {CodeExecutionScene} from './components/CodeExecutionScene';
import {CardStackScene} from './components/CardStackScene';

import {GeneratedVideoBackground} from './components/GeneratedVideoBackground';

import type {
  AIBytesReelProps,
  ClipsMap,
  DataSpec,
  DiagramSpec,
  GeneratedVideoClipsMap,
  NumberCounterData,
  SketchSpec,
  StoryboardScene,
  Theme,
  TokenSpec,
} from './types';

// ─── Constants ────────────────────────────────────────────────────────────────

const FPS = 30;
const CROSSFADE = 9; // 0.3s at 30fps

// Legacy fixed-section timings
const HOOK_START      = 0;
const HOOK_DURATION   = 7 * FPS;   // 0–7s
const CONCEPT_START   = 7 * FPS;
const CONCEPT_DURATION = 8 * FPS;  // 7–15s
const SLIDES_START    = 15 * FPS;
const SLIDES_TOTAL    = 35 * FPS;  // 15–50s
const CTA_START       = 50 * FPS;
const CTA_DURATION    = 10 * FPS;  // 50–60s

const DEFAULT_THEME: Theme = {
  name: 'energy',
  accent: '#a78bfa',
  accent2: '#34d399',
  overlay: 'rgba(5,5,16,0.35)',
  pexels_mood: 'purple neon dark',
};

// ─── Fade wrapper ─────────────────────────────────────────────────────────────

const Fade: React.FC<{duration: number; noFadeIn?: boolean; children: React.ReactNode}> = ({
  duration,
  noFadeIn,
  children,
}) => {
  const frame = useCurrentFrame();
  const fadeIn  = noFadeIn ? 1 : interpolate(frame, [0, CROSSFADE], [0, 1], {extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [duration - CROSSFADE, duration], [1, 0], {extrapolateRight: 'clamp'});
  const opacity = Math.min(fadeIn, fadeOut);
  return <AbsoluteFill style={{opacity}}>{children}</AbsoluteFill>;
};

// ─── Legacy helpers ────────────────────────────────────────────────────────────

const slideKey = (i: number): keyof ClipsMap =>
  `slide_${i}` as keyof ClipsMap;

function renderConceptScene(
  spec: DiagramSpec,
  concept: string,
  clips: ClipsMap | undefined,
  t: Theme,
  sketchSpec: SketchSpec | undefined,
  dataSpec: DataSpec | undefined,
  tokenSpec: TokenSpec | undefined,
  durationInFrames: number,
): React.ReactNode {
  switch (spec.type) {
    case 'flow':          return <FlowScene spec={spec} theme={t} />;
    case 'hub_spoke':     return <HubSpokeScene spec={spec} theme={t} />;
    case 'split_compare': return <SplitCompareScene spec={spec} theme={t} />;
    case 'side_by_side':  return <SplitCompareScene spec={spec} theme={t} />;
    case 'bar_chart':     return <BarChartScene spec={spec} theme={t} />;
    case 'cluster':       return <ClusterScene spec={spec} theme={t} />;
    case 'dial':          return <DialScene spec={spec} theme={t} />;
    case 'sketch':
      return sketchSpec
        ? <SketchScene topic={concept} sketchSpec={sketchSpec} accentColor={t.accent} durationInFrames={durationInFrames} />
        : <ConceptScene concept={concept} videoSrc={clips?.concept} theme={t} />;
    case 'data':
      return dataSpec
        ? <DataScene dataSpec={dataSpec} accentColor={t.accent} durationInFrames={durationInFrames} />
        : <ConceptScene concept={concept} videoSrc={clips?.concept} theme={t} />;
    case 'token':
      return tokenSpec
        ? <TokenScene tokenSpec={tokenSpec} accentColor={t.accent} durationInFrames={durationInFrames} />
        : <ConceptScene concept={concept} videoSrc={clips?.concept} theme={t} />;
    default:
      return <ConceptScene concept={concept} videoSrc={clips?.concept} theme={t} />;
  }
}

// ─── Storyboard scene router ──────────────────────────────────────────────────

function renderStoryboardScene(
  scene: StoryboardScene,
  t: Theme,
  durationInFrames: number,
  topic: string,
  hook: string,
  takeaway: string,
  clips: ClipsMap | undefined,
  episode: string,
  generatedVideoClips?: GeneratedVideoClipsMap,
): React.ReactNode {
  const accent  = t.accent;
  const accent2 = t.accent2;

  // ── Phase 3B: for GENERATIVE_VIDEO scenes, use GeneratedVideoBackground ───
  // Resolve the scene_id key — storyboard may use numeric id (e.g. 1) or string (e.g. "s01").
  const sceneKey = String(scene.scene_id);
  const genVideoSrc =
    generatedVideoClips
      ? (generatedVideoClips[sceneKey] ??
         generatedVideoClips[`s${sceneKey.padStart(2, '0')}`] ??
         generatedVideoClips[sceneKey.replace(/^s0*/, '')])
      : undefined;

  // When a generated video clip is available for this scene, wrap the component
  // in a GeneratedVideoBackground layer. The component itself sits above it via zIndex.
  const withGeneratedBackground = (children: React.ReactNode): React.ReactNode => {
    if (!genVideoSrc) return <>{children}</>;
    return (
      <AbsoluteFill>
        {/* Background: Higgsfield-generated cinematic clip */}
        <GeneratedVideoBackground
          src={genVideoSrc}
          overlayOpacity={0.50}
          accentOverlay={`${accent}12`}
        />
        {/* Foreground: deterministic Remotion component (text / branding) */}
        <AbsoluteFill style={{zIndex: 2}}>
          {children}
        </AbsoluteFill>
      </AbsoluteFill>
    );
  };

  switch (scene.component) {
    // ── Kinetic typography (HOOK / key statements)
    case 'KineticTypoScene':
      return (
        <KineticTypoScene
          text={scene.on_screen_text[0] ?? hook}
          accentColor={accent}
          glitchColor={accent2}
          subtitle={scene.on_screen_text[1]}
          durationInFrames={durationInFrames}
        />
      );

    // ── Token transformation animation
    case 'TokenScene': {
      const tokenSpec = scene.data as TokenSpec | undefined;
      if (tokenSpec?.tokens) {
        return <TokenScene tokenSpec={tokenSpec} accentColor={accent} durationInFrames={durationInFrames} />;
      }
      // Fall back: synthesise a basic TokenSpec from objects list
      return (
        <TokenScene
          tokenSpec={{
            sentence: scene.objects.join(' '),
            tokens: scene.objects.map((o) => ({text: o})),
            title: scene.on_screen_text[0],
            showIds: true,
          }}
          accentColor={accent}
          durationInFrames={durationInFrames}
        />
      );
    }

    // ── Sketch / diagram
    case 'SketchScene': {
      const sketchSpec = scene.data as SketchSpec | undefined;
      if (sketchSpec?.nodes) {
        return (
          <SketchScene
            topic={scene.visual_goal}
            sketchSpec={sketchSpec}
            accentColor={accent}
            durationInFrames={durationInFrames}
          />
        );
      }
      return <ConceptScene concept={scene.visual_goal} theme={t} />;
    }

    // ── Data visualization (bars / comparison)
    case 'DataScene': {
      const dataSpec = scene.data as DataSpec | undefined;
      if (dataSpec) {
        return <DataScene dataSpec={dataSpec} accentColor={accent} durationInFrames={durationInFrames} />;
      }
      return <ConceptScene concept={scene.visual_goal} theme={t} />;
    }

    // ── Animated hero-number counter
    case 'NumberCounterScene': {
      const counterData = scene.data as NumberCounterData | undefined;
      if (counterData?.type === 'counter') {
        return (
          <NumberCounterScene
            data={counterData}
            accentColor={accent}
            durationInFrames={durationInFrames}
          />
        );
      }
      return <ConceptScene concept={scene.visual_goal} theme={t} />;
    }

    // ── Side-by-side comparison
    case 'SplitCompareScene': {
      // Labels come from on_screen_text[0] and on_screen_text[3].
      // NEVER use scene.objects[] as UI text — it contains internal identifiers
      // (e.g. "without_rag_panel", "with_rag_panel") that must never appear on screen.
      const leftLabel  = scene.on_screen_text[0] ?? 'Before';
      const rightLabel = scene.on_screen_text[3] ?? 'After';
      return (
        <SplitCompareScene
          spec={{
            type: 'split_compare',
            left:  {label: leftLabel,  points: scene.on_screen_text.slice(1, 3)},
            right: {label: rightLabel, points: scene.on_screen_text.slice(4, 6)},
            verdict: scene.on_screen_text[6] ?? '',
          }}
          theme={t}
          beats={scene.beats}
          onScreenText={scene.on_screen_text}
        />
      );
    }

    // ── Pipeline / flow diagram
    case 'FlowScene':
      return (
        <FlowScene
          spec={{
            type: 'flow',
            steps: scene.objects.map((o, i) => ({
              icon: scene.on_screen_text[i] ?? '→',
              label: o,
            })),
          }}
          theme={t}
        />
      );

    // ── Hub-and-spoke diagram
    case 'HubSpokeScene':
      return (
        <HubSpokeScene
          spec={{
            type: 'hub_spoke',
            hub: scene.objects[0] ?? scene.visual_goal,
            spokes: scene.objects.slice(1),
          }}
          theme={t}
        />
      );

    // ── Cluster / grouping diagram
    case 'ClusterScene':
      return (
        <ClusterScene
          spec={{
            type: 'cluster',
            groups: [{label: scene.on_screen_text[0] ?? 'Group', items: scene.objects}],
          }}
          theme={t}
        />
      );

    // ── Dial / gauge
    case 'DialScene':
      return (
        <DialScene
          spec={{
            type: 'dial',
            label: scene.on_screen_text[0] ?? scene.visual_goal,
            min_label: scene.objects[0] ?? 'Low',
            max_label: scene.objects[1] ?? 'High',
            ticks: [],
          }}
          theme={t}
        />
      );

    // ── Bar chart
    case 'BarChartScene':
      return (
        <BarChartScene
          spec={{
            type: 'bar_chart',
            title: scene.on_screen_text[0] ?? '',
            bars: scene.objects.map((o, i) => ({label: o, value: (i + 1) * 25})),
          }}
          theme={t}
        />
      );

    // ── v3 beat-driven primitives ────────────────────────────────────────────

    case 'BeforeAfterScene':
      return (
        <BeforeAfterScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          accentColor={accent}
          accent2={accent2}
          carryFrom={scene.carry_object_from ?? undefined}
        />
      );

    case 'TransformScene':
      return (
        <TransformScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'DataFlowScene':
      return (
        <DataFlowScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'DocumentRetrievalScene':
      return (
        <DocumentRetrievalScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'ContextWindowScene':
      return (
        <ContextWindowScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'TokenStreamScene':
      return (
        <TokenStreamScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'PipelineScene':
      return (
        <PipelineScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'MeterScene':
      return (
        <MeterScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'NetworkBuildScene':
      return (
        <NetworkBuildScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'LayerRevealScene':
      return (
        <LayerRevealScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'TimelineScene':
      return (
        <TimelineScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'GraphGrowthScene':
      return (
        <GraphGrowthScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'CodeExecutionScene':
      return (
        <CodeExecutionScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    case 'CardStackScene':
      return (
        <CardStackScene
          beats={scene.beats ?? []}
          onScreenText={scene.on_screen_text}
          objects={scene.objects}
          accentColor={accent}
          accent2={accent2}
        />
      );

    // ── Key takeaway scene
    case 'TakeawayScene':
      return (
        <TakeawayScene
          text={scene.on_screen_text[0] ?? takeaway}
          accentColor={accent}
          accent2={accent2}
          durationInFrames={durationInFrames}
          beats={scene.beats}
          onScreenText={scene.on_screen_text}
        />
      );

    // ── CTA (always the last scene)
    case 'CTAScene':
      return (
        <CTAScene
          takeaway={takeaway}
          videoSrc={clips?.cta}
          theme={t}
        />
      );

    // ── Hook scene (can appear in storyboard too)
    // Phase 3B: when a generated video clip is available for this scene,
    // GeneratedVideoBackground provides the cinematic background and HookScene
    // receives no videoSrc (its own video layer stays disabled — the generated
    // clip already provides the full-canvas background via withGeneratedBackground).
    case 'HookScene':
      return withGeneratedBackground(
        <HookScene
          hook={hook}
          videoSrc={genVideoSrc ? undefined : clips?.hook}
          theme={t}
          emoji={scene.objects[0] ?? '🧠'}
          episode={episode}
          topic={topic}
        />
      );

    // ── Fallback: concept text card
    case 'ConceptScene':
    case 'SlideScene':
    default:
      return (
        <ConceptScene
          concept={scene.on_screen_text[0] ?? scene.visual_goal}
          theme={t}
        />
      );
  }
}

// ─── Storyboard renderer ───────────────────────────────────────────────────────

interface StoryboardProps {
  storyboard: StoryboardScene[];
  theme: Theme;
  topic: string;
  hook: string;
  takeaway: string;
  episode: string;
  clips?: ClipsMap;
  /** Phase 3B: Higgsfield-generated clips keyed by scene_id. */
  generatedVideoClips?: GeneratedVideoClipsMap;
}

const StoryboardReel: React.FC<StoryboardProps> = ({
  storyboard,
  theme,
  topic,
  hook,
  takeaway,
  episode,
  clips,
  generatedVideoClips,
}) => {
  // Pre-compute cumulative start frames
  let cursor = 0;
  const scenes = storyboard.map((scene) => {
    const startFrame    = cursor;
    const durationFrames = Math.round(scene.duration_seconds * FPS);
    cursor += durationFrames;
    return {scene, startFrame, durationFrames};
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#050510'}}>
      {scenes.map(({scene, startFrame, durationFrames}, i) => (
        <Sequence key={scene.scene_id} from={startFrame} durationInFrames={durationFrames}>
          <Fade duration={durationFrames} noFadeIn={i === 0}>
            {renderStoryboardScene(
              scene, theme, durationFrames, topic, hook, takeaway,
              clips, episode, generatedVideoClips,
            )}
          </Fade>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

// ─── Main composition ──────────────────────────────────────────────────────────

export const AIBytesReel: React.FC<AIBytesReelProps> = (props) => {
  const {
    episode,
    topic,
    hook,
    concept,
    slides,
    takeaway,
    clips,
    theme,
    diagram_spec,
    sketch_spec,
    data_spec,
    token_spec,
    storyboard,
    generatedVideoClips,
  } = props;

  const t = theme ?? DEFAULT_THEME;

  // ── STORYBOARD MODE ────────────────────────────────────────────────────────
  if (storyboard && storyboard.length > 0) {
    return (
      <StoryboardReel
        storyboard={storyboard}
        theme={t}
        topic={topic}
        hook={hook}
        takeaway={takeaway}
        episode={episode}
        clips={clips}
        generatedVideoClips={generatedVideoClips}
      />
    );
  }

  // ── LEGACY MODE ───────────────────────────────────────────────────────────
  const slideCount    = slides.length;
  const slideDuration = Math.floor(SLIDES_TOTAL / Math.max(slideCount, 1));

  return (
    <AbsoluteFill style={{backgroundColor: '#050510'}}>
      {/* Hook: 0–7s */}
      <Sequence from={HOOK_START} durationInFrames={HOOK_DURATION}>
        <Fade duration={HOOK_DURATION} noFadeIn>
          <HookScene
            hook={hook}
            videoSrc={clips?.hook}
            theme={t}
            emoji={slides[0]?.icon ?? '🧠'}
            episode={episode}
            topic={topic}
          />
        </Fade>
      </Sequence>

      {/* Concept / Diagram: 7–15s */}
      <Sequence from={CONCEPT_START} durationInFrames={CONCEPT_DURATION}>
        <Fade duration={CONCEPT_DURATION}>
          {diagram_spec
            ? renderConceptScene(diagram_spec, concept, clips, t, sketch_spec, data_spec, token_spec, CONCEPT_DURATION)
            : <ConceptScene concept={concept} videoSrc={clips?.concept} theme={t} />}
        </Fade>
      </Sequence>

      {/* Slides: 15–50s */}
      {slides.map((slide, i) => (
        <Sequence
          key={i}
          from={SLIDES_START + i * slideDuration}
          durationInFrames={slideDuration}
        >
          <Fade duration={slideDuration}>
            <SlideScene
              icon={slide.icon}
              heading={slide.heading}
              body={slide.body}
              slideIndex={i}
              totalSlides={slideCount}
              videoSrc={clips?.[slideKey(i)]}
              theme={t}
            />
          </Fade>
        </Sequence>
      ))}

      {/* CTA: 50–60s */}
      <Sequence from={CTA_START} durationInFrames={CTA_DURATION}>
        <Fade duration={CTA_DURATION}>
          <CTAScene takeaway={takeaway} videoSrc={clips?.cta} theme={t} />
        </Fade>
      </Sequence>
    </AbsoluteFill>
  );
};
