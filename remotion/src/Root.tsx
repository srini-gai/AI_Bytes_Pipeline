import React from 'react';
import {Composition} from 'remotion';
import {AIBytesReel} from './AIBytesReel';
import type {AIBytesReelProps} from './types';

const defaultProps: AIBytesReelProps = {
  episode: '01',
  topic: 'What is RAG?',
  title: 'This Is How AI Reads YOUR Documents',
  hook: 'Your AI is lying to you. Here is why.',
  concept: 'Retrieval-Augmented Generation',
  slides: [
    {
      icon: '🧠',
      heading: 'The Problem',
      body: 'LLMs only know their training data. They hallucinate when asked about your documents.',
    },
    {
      icon: '📚',
      heading: 'The Fix',
      body: 'RAG fetches real documents at query time and injects them into the prompt as context.',
    },
    {
      icon: '⚡',
      heading: 'How It Works',
      body: 'Query → Embed → Vector Search → Retrieve → Inject → Answer. Fully automatic.',
    },
    {
      icon: '🎯',
      heading: 'Use Cases',
      body: 'Support bots, internal knowledge bases, document Q&A, and AI-powered code search.',
    },
  ],
  voiceover: 'Sample voiceover — replace with real script voiceover field.',
  takeaway: 'RAG = LLM + Your Real Data. No fine-tuning needed.',
  tags: '#AIBytes #RAG #LLM #GenerativeAI',
  diagram_spec: {
    type: 'flow',
    steps: [
      {icon: '🔍', label: 'Retrieve'},
      {icon: '📎', label: 'Augment'},
      {icon: '✨', label: 'Generate'},
      {icon: '✅', label: 'Answer'},
    ],
  },
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="AIBytesReel"
      // Cast required: Remotion's LooseComponentType expects Record<string,unknown>
      component={AIBytesReel as unknown as React.ComponentType<Record<string, unknown>>}
      durationInFrames={1800}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultProps as unknown as Record<string, unknown>}
    />
  );
};
