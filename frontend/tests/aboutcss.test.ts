import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";

const css = readFileSync(resolve(__dirname, "../src/styles/about.css"), "utf-8").replace(
  /\/\*[\s\S]*?\*\//g,
  "",
);

const escape = (selector: string) => selector.split(".").join("\\.");

/** The declarations of the first `selector` rule inside the media block that starts with `query`. */
function inMedia(query: string, selector: string): string {
  const start = css.indexOf(`@media ${query}`);
  expect(start, `media ${query}`).toBeGreaterThan(-1);
  const block = css.slice(css.indexOf("{", start));
  const rule = new RegExp(`${escape(selector)}\\s*\\{([^}]*)\\}`);
  return rule.exec(block)?.[1] ?? "";
}

const base = (selector: string) =>
  new RegExp(`^${escape(selector)}\\s*\\{([^}]*)\\}`, "m").exec(css)?.[1] ?? "";

describe("about.css", () => {
  test("the card grid is 4 across at the widest, then 3, 2 and 1 as the width shrinks", () => {
    expect(base(".about-grid")).toMatch(/grid-template-columns:\s*repeat\(4,/);
    expect(inMedia("(max-width: 1399px)", ".about-grid")).toMatch(/repeat\(3,/);
    expect(inMedia("(max-width: 1099px)", ".about-grid")).toMatch(/repeat\(2,/);
    expect(inMedia("(max-width: 719px)", ".about-grid")).toMatch(/repeat\(1,|1fr\b/);
  });

  test("cards in a row are the same height", () => {
    expect(base(".about-grid")).not.toMatch(/align-items:\s*(start|center)/);
    expect(base(".about-card")).toMatch(/height:\s*100%|align-content/);
  });

  test("the hero logo is aligned to the top of the card, with the title", () => {
    expect(base(".about-hero")).toMatch(/align-items:\s*flex-start/);
  });

  // The About content was a centred 72rem column, narrower than the tab bar and the mode toggle
  // above it; it spans the same width as the library table.
  test("the About content is not narrowed or centred", () => {
    const about = base(".about");
    expect(about).not.toBe("");
    expect(about).not.toMatch(/max-width/);
    expect(about).not.toMatch(/margin:\s*0 auto/);
  });

  // The brand once sat on a black bordered plate in red and blue; it is plain text in button ink.
  test("the masthead brand has no plate and uses the button text colour", () => {
    const brand = base(".masthead .brand");
    expect(brand).not.toMatch(/background|border:/);
    expect(base(".masthead .wordmark > span")).toMatch(/color:\s*var\(--ink\)/);
  });

  test("the timeline draws a line between the step markers", () => {
    expect(css).toMatch(/\.about-timeline li::after/);
  });
});
