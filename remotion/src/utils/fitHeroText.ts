/**
 * fitHeroText — viewport-fitting hero typography for 9:16 Shorts.
 *
 * Uses browser measurement (via hidden span in Chromium/Remotion) to
 * compute the largest font size that fills the target bounding box.
 *
 * Enforces a visual-dominance rule: if width-fitting alone produces
 * a word that is too shallow (< 8% of frame height), the system
 * automatically applies scaleX compression or switches to a two-line
 * stacked layout to achieve visual dominance.
 */
import {useLayoutEffect, useRef, useState} from 'react';

// ── Constants ──────────────────────────────────────────────────────────────

const FRAME_W = 1080;
const FRAME_H = 1920;
const REF_SIZE = 200;
const MIN_HERO_HEIGHT_FRAC = 0.08;
const TARGET_HERO_HEIGHT_FRAC = 0.12;
const MIN_SCALE_X = 0.65;

export const HERO_SAFE_AREA = {
  marginX: 54,
  marginY: 96,
  get width() { return FRAME_W - 2 * this.marginX; },
  get height() { return FRAME_H - 2 * this.marginY; },
};

// ── Types ──────────────────────────────────────────────────────────────────

export interface HeroFit {
  fontSize: number;
  scaleX: number;
  lineCount: 1 | 2;
  lines: string[];
  l1Text: string;
  l2Text: string;
  boundingWidth: number;
  boundingHeight: number;
  measured: boolean;
}

export interface HeroQAResult {
  pass: boolean;
  fontSize: number;
  scaleX: number;
  lineCount: number;
  widthPercent: number;
  heightPercent: number;
  clipped: boolean;
  reason?: string;
}

// ── Break-point finder ─────────────────────────────────────────────────────

function findBreak(text: string): number {
  const mid = Math.ceil(text.length / 2);
  let bestPos = -1;
  let bestDist = text.length;
  for (let i = 1; i < text.length; i++) {
    if (text[i] === ' ' || text[i] === '-') {
      const d = Math.abs(i - mid);
      if (d < bestDist) { bestDist = d; bestPos = i; }
    }
  }
  if (bestPos >= 0) return bestPos;
  // No whitespace — break at midpoint
  return mid;
}

// ── Browser-measured hook ──────────────────────────────────────────────────

export function useHeroTextFit(
  text: string,
  targetWidth: number,
  targetHeight: number,
  fontFamily: string,
  fontWeight: number,
  letterSpacing: number,
): {
  fit: HeroFit;
  singleRef: React.RefObject<HTMLSpanElement | null>;
  line1Ref: React.RefObject<HTMLSpanElement | null>;
  line2Ref: React.RefObject<HTMLSpanElement | null>;
} {
  const singleRef = useRef<HTMLSpanElement | null>(null);
  const line1Ref = useRef<HTMLSpanElement | null>(null);
  const line2Ref = useRef<HTMLSpanElement | null>(null);

  const bp = findBreak(text);
  const l1Text = text.slice(0, bp).trim();
  const l2Text = text.slice(bp).trim();

  const [fit, setFit] = useState<HeroFit>({
    fontSize: 180,
    scaleX: 1,
    lineCount: 1,
    lines: [text],
    l1Text,
    l2Text,
    boundingWidth: 0,
    boundingHeight: 0,
    measured: false,
  });

  useLayoutEffect(() => {
    const singleEl = singleRef.current;
    if (!singleEl) return;

    const singleW = singleEl.offsetWidth;
    const singleH = singleEl.offsetHeight;
    if (singleW === 0 || singleH === 0) return;

    // Single-line width-fit
    const sScale = Math.min(targetWidth / singleW, targetHeight / singleH);
    const sFontSize = Math.floor(REF_SIZE * sScale);
    const sResultH = singleH * sScale;
    const sHeightFrac = sResultH / FRAME_H;

    // If height is sufficient, use single line as-is
    if (sHeightFrac >= MIN_HERO_HEIGHT_FRAC) {
      setFit({
        fontSize: sFontSize,
        scaleX: 1,
        lineCount: 1,
        lines: [text],
        l1Text, l2Text,
        boundingWidth: singleW * sScale,
        boundingHeight: sResultH,
        measured: true,
      });
      return;
    }

    // Height too shallow — try scaleX compression
    const targetH = FRAME_H * TARGET_HERO_HEIGHT_FRAC;
    const heightScale = targetH / singleH;
    const compressedScale = Math.min(heightScale, targetHeight / singleH);
    const compressedW = singleW * compressedScale;
    const neededScaleX = targetWidth / compressedW;

    if (neededScaleX >= MIN_SCALE_X) {
      const cFontSize = Math.floor(REF_SIZE * compressedScale);
      setFit({
        fontSize: cFontSize,
        scaleX: neededScaleX,
        lineCount: 1,
        lines: [text],
        l1Text, l2Text,
        boundingWidth: targetWidth,
        boundingHeight: singleH * compressedScale,
        measured: true,
      });
      return;
    }

    // ScaleX too extreme — try two-line layout
    const el1 = line1Ref.current;
    const el2 = line2Ref.current;
    if (!el1 || !el2) {
      // Fallback: use maximum scaleX compression
      const fbHeightScale = targetWidth / (singleW * MIN_SCALE_X);
      const fbFontSize = Math.floor(REF_SIZE * fbHeightScale);
      setFit({
        fontSize: fbFontSize,
        scaleX: MIN_SCALE_X,
        lineCount: 1,
        lines: [text],
        l1Text, l2Text,
        boundingWidth: targetWidth,
        boundingHeight: singleH * fbHeightScale,
        measured: true,
      });
      return;
    }

    const w1 = el1.offsetWidth;
    const w2 = el2.offsetWidth;
    const longerW = Math.max(w1, w2);
    const lineH = singleH;

    // Fit the longer line to targetWidth
    const twoLineScale = targetWidth / longerW;
    const twoFontSize = Math.floor(REF_SIZE * twoLineScale);
    const lineGap = twoFontSize * 0.15;
    const totalH = lineH * twoLineScale * 2 + lineGap;

    // If two-line is too tall, scale down
    const maxTwoLineH = targetHeight;
    let finalTwoScale = twoLineScale;
    if (totalH > maxTwoLineH) {
      finalTwoScale = (maxTwoLineH - lineGap) / (lineH * 2);
    }
    const finalTwoFontSize = Math.floor(REF_SIZE * finalTwoScale);
    const finalTotalH = lineH * finalTwoScale * 2 + finalTwoFontSize * 0.15;

    // Pick two-line if it gives better dominance than max-scaleX single line
    const maxScaleXHeightScale = targetWidth / (singleW * MIN_SCALE_X);
    const maxScaleXH = singleH * maxScaleXHeightScale;

    if (finalTotalH > maxScaleXH) {
      setFit({
        fontSize: finalTwoFontSize,
        scaleX: 1,
        lineCount: 2,
        lines: [l1Text, l2Text],
        l1Text, l2Text,
        boundingWidth: longerW * finalTwoScale,
        boundingHeight: finalTotalH,
        measured: true,
      });
    } else {
      const fbFontSize = Math.floor(REF_SIZE * maxScaleXHeightScale);
      setFit({
        fontSize: fbFontSize,
        scaleX: MIN_SCALE_X,
        lineCount: 1,
        lines: [text],
        l1Text, l2Text,
        boundingWidth: targetWidth,
        boundingHeight: maxScaleXH,
        measured: true,
      });
    }
  }, [text, l1Text, l2Text, targetWidth, targetHeight, fontFamily, fontWeight, letterSpacing]);

  return {fit, singleRef, line1Ref, line2Ref};
}

// Hidden measurement span style
export function heroMeasureStyle(
  fontFamily: string,
  fontWeight: number,
  letterSpacing: number,
): React.CSSProperties {
  return {
    position: 'absolute',
    visibility: 'hidden',
    whiteSpace: 'nowrap',
    fontSize: REF_SIZE,
    fontFamily,
    fontWeight,
    letterSpacing,
    lineHeight: 1,
    pointerEvents: 'none',
    top: 0,
    left: 0,
  };
}

// ── QA check ───────────────────────────────────────────────────────────────

const MIN_WIDTH_PERCENT = 55;
const MIN_AREA_PERCENT = 3.5;

export function checkHeroComposition(fit: HeroFit): HeroQAResult {
  const widthPct = (fit.boundingWidth / FRAME_W) * 100;
  const heightPct = (fit.boundingHeight / FRAME_H) * 100;
  const areaPct = widthPct * heightPct / 100;
  const clipped = fit.boundingWidth > HERO_SAFE_AREA.width ||
                  fit.boundingHeight > HERO_SAFE_AREA.height;

  const reasons: string[] = [];
  if (widthPct < MIN_WIDTH_PERCENT) reasons.push(`width ${widthPct.toFixed(1)}% < ${MIN_WIDTH_PERCENT}%`);
  if (areaPct < MIN_AREA_PERCENT) reasons.push(`area ${areaPct.toFixed(1)}% < ${MIN_AREA_PERCENT}%`);
  if (clipped) reasons.push('exceeds safe bounds');

  return {
    pass: reasons.length === 0,
    fontSize: fit.fontSize,
    scaleX: fit.scaleX,
    lineCount: fit.lineCount,
    widthPercent: widthPct,
    heightPercent: heightPct,
    clipped,
    reason: reasons.length > 0 ? reasons.join('; ') : undefined,
  };
}
