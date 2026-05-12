export interface Slide {
  icon: string;
  heading: string;
  body: string;
}

export interface Theme {
  name: string;
  accent: string;
  accent2: string;
  overlay: string;
  pexels_mood: string;
}

export interface ClipsMap {
  hook?: string;
  concept?: string;
  slide_0?: string;
  slide_1?: string;
  slide_2?: string;
  slide_3?: string;
  cta?: string;
}

export interface AIBytesReelProps {
  episode: string;
  topic: string;
  title: string;
  hook: string;
  concept: string;
  slides: Slide[];
  voiceover: string;
  takeaway: string;
  tags: string;
  theme?: Theme;
  clips?: ClipsMap;
}
