// Difficulty level chips in game order with beatsaver colours and AA-contrast text colours.
export interface Level {
  key: string;
  label: string;
  /** Short chip text. */
  abbr: string;
  bg: string;
}

export const LEVELS: readonly Level[] = [
  { key: "Easy", label: "Easy", abbr: "Ea", bg: "#3CB371" },
  { key: "Normal", label: "Normal", abbr: "No", bg: "#59B0F4" },
  { key: "Hard", label: "Hard", abbr: "Ha", bg: "#FF6347" },
  { key: "Expert", label: "Expert", abbr: "Ex", bg: "#BF2A42" },
  { key: "ExpertPlus", label: "Expert+", abbr: "Ex+", bg: "#8F48DB" },
];

const DARK = "#0d0a1a";
const LIGHT = "#ffffff";
/** The dark surface level chips sit on (the list panel). */
export const SURFACE = "#1a1630";
const AA = 4.5;

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

/** All five slots in game order; `present` says whether the map has that level. */
export function levelSlots(names: readonly string[]): { level: Level; present: boolean }[] {
  return LEVELS.map((level) => ({ level, present: names.includes(level.key) }));
}

function mix(hex: string, amount: number): string {
  const n = Number.parseInt(hex.slice(1), 16);
  const ch = (shift: number) => {
    const v = (n >> shift) & 255;
    return Math.round(v + (255 - v) * amount);
  };
  return `#${[16, 8, 0].map((s) => ch(s).toString(16).padStart(2, "0")).join("")}`;
}

/** The level colour lightened just enough to reach AA contrast as text on the dark surface. */
export function ringText(bg: string, surface: string = SURFACE): string {
  let amount = 0;
  let out = bg;
  while (contrast(out, surface) < AA && amount < 1) {
    amount = Math.min(1, amount + 0.05);
    out = mix(bg, amount);
  }
  return out;
}

/** The colour a level is drawn in, chips and chart lines alike; undefined for an unknown key. */
export function levelColor(key: string): string | undefined {
  const level = LEVELS.find((l) => l.key === key);
  return level ? ringText(level.bg) : undefined;
}
