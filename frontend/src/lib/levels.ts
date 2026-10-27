// Difficulty level chips in game order with beatsaver colours and AA-contrast text colours.
export interface Level {
  key: string;
  label: string;
  bg: string;
}

export const LEVELS: readonly Level[] = [
  { key: "Easy", label: "Easy", bg: "#3CB371" },
  { key: "Normal", label: "Normal", bg: "#59B0F4" },
  { key: "Hard", label: "Hard", bg: "#FF6347" },
  { key: "Expert", label: "Expert", bg: "#BF2A42" },
  { key: "ExpertPlus", label: "Expert+", bg: "#8F48DB" },
];

const DARK = "#0d0a1a";
const LIGHT = "#ffffff";

function channel(v: number): number {
  const s = v / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

export function luminance(hex: string): number {
  const n = Number.parseInt(hex.slice(1), 16);
  const r = channel((n >> 16) & 255);
  const g = channel((n >> 8) & 255);
  const b = channel(n & 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

/** Dark or white text, whichever contrasts more with the background. */
export function textColor(bg: string): string {
  return contrast(bg, DARK) >= contrast(bg, LIGHT) ? DARK : LIGHT;
}

/** Levels present in the given Info difficulty names, in game order; unknown names are dropped. */
export function levelsFor(names: readonly string[]): Level[] {
  return LEVELS.filter((l) => names.includes(l.key));
}
