import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";

const read = (f: string) => readFileSync(resolve(__dirname, "../src", f), "utf8");
const css = read("styles/datepicker.css").replace(/\/\*[\s\S]*?\*\//g, "");
const rule = (sel: string) => {
  const i = css.indexOf(`${sel} {`);
  return i < 0 ? "" : css.slice(i, css.indexOf("}", i));
};

describe("More filters sheet", () => {
  test("body is padded and clips horizontal overflow", () => {
    const body = rule(".bs-sheet .sheet-body");
    expect(body).toMatch(/padding:\s*1rem/);
    expect(body).toMatch(/overflow-x:\s*hidden/);
    expect(body).toMatch(/min-width:\s*0/);
    expect(rule(".sheet.bs-sheet")).toMatch(/max-width:\s*100dvw/);
  });

  test("every widget is capped at the panel width", () => {
    const w = rule(".bs-sheet .sheet-body :is(input, select, .date-trigger)");
    expect(w).toMatch(/width:\s*100%/);
    expect(w).toMatch(/min-width:\s*0/);
    expect(css).toMatch(/\.range-field|\.filter-row/);
    expect(rule(".bs-sheet .sheet-body :is(label, .field-label, .checks > *)")).toMatch(
      /overflow-wrap:\s*anywhere/,
    );
  });

  test("the footer sits outside the scrolling body with a safe-area inset", () => {
    expect(rule(".bs-sheet .sheet-foot")).toMatch(/safe-area-inset-bottom/);
    for (const [file, label] of [
      ["components/beatsaver/BsToolbar.tsx", "Show maps"],
      ["components/beatsaver/PlaylistToolbar.tsx", "Show playlists"],
    ] as const) {
      const src = read(file);
      const bodyEnd = src.indexOf('<div className="sheet-foot">');
      expect(src.indexOf('<div className="sheet-body">')).toBeGreaterThan(0);
      expect(bodyEnd).toBeGreaterThan(src.indexOf('<div className="sheet-body">'));
      expect(src.indexOf(label)).toBeGreaterThan(bodyEnd);
    }
    const base = read("styles/overlays.css");
    expect(base).toMatch(/\.sheet-body \{[^}]*overflow-y:\s*auto/);
    expect(base).toMatch(/\.sheet-foot \{[^}]*flex:\s*none/);
  });

  test("the date picker renders above the sheet and has no native date input", () => {
    expect(rule(".popover.date-pop")).toMatch(/z-index:\s*60/);
    for (const f of ["BsFilterBodies.tsx", "PlaylistFilterBodies.tsx"]) {
      expect(read(`components/beatsaver/${f}`)).not.toContain('type="date"');
    }
  });
});
