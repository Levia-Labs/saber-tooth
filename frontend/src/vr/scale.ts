import { useSyncExternalStore } from "react";
import { mediaFor } from "../lib/breakpoint";

/**
 * The VR scale: the root font size over the desktop 16 px. `vr.css` makes the root size fluid, so
 * the scale follows the window. Every px media query (CSS rules and `matchMedia` calls) is
 * evaluated against the effective width, the window width over the scale, so the desktop tiers
 * (wide, mid, compact, mobile) apply at the width the desktop would have after the same zoom.
 */
const DESKTOP_FONT_PX = 16;
const NUM_PX = /(\d*\.?\d+)px/g;

/** The root font size as a scale over the desktop; 1 when it is not a usable number. */
export function scaleOf(fontPx: number): number {
  return Number.isFinite(fontPx) && fontPx >= DESKTOP_FONT_PX ? fontPx / DESKTOP_FONT_PX : 1;
}

/** A media query with every px length multiplied by the scale; scale 1 returns it unchanged. */
export function scaleMediaText(text: string, scale: number): string {
  if (scale === 1) return text;
  return text.replace(NUM_PX, (_, n: string) => `${Math.round(Number(n) * scale * 100) / 100}px`);
}

/** A desktop px width at the scale, to two decimals. */
export const scaledPx = (px: number, scale: number): number => Math.round(px * scale * 100) / 100;

/** A rendered px width back in desktop px. */
export const unscaledPx = (px: number, scale: number): number => px / scale;

let scale = 1;
let vr = false;
const listeners = new Set<() => void>();
const originals = new WeakMap<CSSMediaRule, string>();

export const currentScale = (): number => scale;

function measure(): number {
  const root = document.documentElement;
  if (root.dataset.ui !== "vr") return 1;
  return scaleOf(parseFloat(getComputedStyle(root).fontSize));
}

function rewriteRules(rules: CSSRuleList): void {
  for (const rule of Array.from(rules)) {
    if (rule instanceof CSSMediaRule) {
      const text = originals.get(rule) ?? rule.media.mediaText;
      originals.set(rule, text);
      const next = scaleMediaText(mediaFor(text, vr), scale);
      if (rule.media.mediaText !== next) rule.media.mediaText = next;
    }
    if ("cssRules" in rule) rewriteRules((rule as CSSGroupingRule).cssRules);
  }
}

function rewriteSheets(): void {
  for (const sheet of Array.from(document.styleSheets)) {
    try {
      rewriteRules(sheet.cssRules);
    } catch {
      /* a cross-origin sheet cannot be read; it has no rules of ours */
    }
  }
}

/** Re-read the scale and, when it changed, rewrite the CSS media rules and tell the listeners. */
export function refreshScale(): void {
  const next = measure();
  const nextVr = document.documentElement.dataset.ui === "vr";
  const changed = next !== scale || nextVr !== vr;
  scale = next;
  vr = nextVr;
  document.documentElement.style.setProperty("--ui-scale", String(next));
  rewriteSheets();
  if (changed) for (const each of Array.from(listeners)) each();
}

function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

/** The scale as state; re-renders when the window or the layout mode changes it. */
export const useUiScale = (): number => useSyncExternalStore(subscribe, currentScale, () => 1);

let installed = false;

/**
 * Make `window.matchMedia` evaluate px lengths against the effective width, and keep the CSS media
 * rules and the scale in step with the window. Idempotent; call it once at start.
 */
export function installScale(): void {
  if (installed || typeof window === "undefined") return;
  installed = true;
  window.addEventListener("resize", refreshScale);
  if (typeof window.matchMedia !== "function") return;
  const native = window.matchMedia.bind(window);
  window.matchMedia = (query: string): MediaQueryList => {
    const mq = native(scaleMediaText(mediaFor(query, vr), scale));
    return scaledList(native, query, mq);
  };
}

/** A MediaQueryList whose `matches` follows the scale: listeners fire when the answer changes. */
function scaledList(
  native: (q: string) => MediaQueryList,
  query: string,
  first: MediaQueryList,
): MediaQueryList {
  let last = first.matches;
  const ask = () => native(scaleMediaText(mediaFor(query, vr), scale));
  const fns = new Map<EventListenerOrEventListenerObject, () => void>();
  const poke = () => {
    const now = ask().matches;
    if (now === last) return;
    last = now;
    for (const fn of Array.from(fns.keys())) {
      const event = { matches: now, media: query, type: "change" } as MediaQueryListEvent;
      if (typeof fn === "function") fn.call(list, event);
      else fn.handleEvent(event);
    }
  };
  const list = {
    media: query,
    get matches() {
      return ask().matches;
    },
    onchange: null,
    addEventListener(type: string, fn: EventListenerOrEventListenerObject) {
      if (type !== "change" || fns.has(fn)) return;
      fns.set(fn, () => undefined);
      if (fns.size === 1) listeners.add(poke);
      first.addEventListener("change", poke);
    },
    removeEventListener(type: string, fn: EventListenerOrEventListenerObject) {
      if (type !== "change" || !fns.delete(fn)) return;
      first.removeEventListener("change", poke);
      if (fns.size === 0) listeners.delete(poke);
    },
    addListener(fn: EventListenerOrEventListenerObject) {
      list.addEventListener("change", fn);
    },
    removeListener(fn: EventListenerOrEventListenerObject) {
      list.removeEventListener("change", fn);
    },
    dispatchEvent: () => false,
  } as unknown as MediaQueryList;
  return list;
}
