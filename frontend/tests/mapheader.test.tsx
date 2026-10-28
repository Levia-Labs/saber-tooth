import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { item, mockFetch, renderApp } from "./helpers";

const css = readFileSync(resolve(__dirname, "../src/styles/page.css"), "utf8");
const rule = (selector: string) => {
  const start = `\n${css}`.indexOf(`\n${selector} {`);
  if (start < 0) return "";
  const open = css.indexOf("{", start);
  return css.slice(open + 1, css.indexOf("}", open));
};

function fakeAudio() {
  const audio = new (class extends EventTarget {
    src = "";
    paused = true;
    duration = 200;
    currentTime = 0;
    pause() {
      this.paused = true;
    }
    play() {
      this.paused = false;
      return Promise.resolve();
    }
  })();
  vi.stubGlobal("Audio", function () {
    return audio;
  });
  return audio;
}

async function open(patch = {}) {
  mockFetch((url) => {
    if (url.pathname === "/api/maps/id0000000001") return item(1, patch);
    if (url.pathname.endsWith("/proposals")) return [];
    return {};
  });
  const view = renderApp("/maps/id0000000001");
  await screen.findByRole("heading", { name: "Song 1" });
  return view.container;
}

afterEach(() => vi.unstubAllGlobals());

describe("map page preview button", () => {
  test("sits last in the row with the BPM chip and toggles play and pause", async () => {
    const audio = fakeAudio();
    const container = await open({ audio_url: "/api/maps/x/audio", preview_start: 40 });
    const row = container.querySelector(".maphead .metarow") as HTMLElement;
    const btn = screen.getByRole("button", { name: "Play preview of Song 1" });
    expect(row.querySelector(".tempo")).not.toBeNull();
    expect(row.lastElementChild?.contains(btn)).toBe(true);
    expect(container.querySelector(".tempo-card")).toBeNull();
    await userEvent.click(btn);
    audio.dispatchEvent(new Event("loadedmetadata"));
    audio.currentTime = 42;
    audio.dispatchEvent(new Event("timeupdate"));
    await userEvent.click(await screen.findByRole("button", { name: "Pause preview" }));
    expect(await screen.findByRole("button", { name: "Play preview of Song 1" })).toBeVisible();
  });

  test("is absent without audio and the Tempo chip stays", async () => {
    const container = await open();
    expect(screen.queryByRole("button", { name: /preview/i })).toBeNull();
    expect(container.querySelector(".metarow .tempo")?.textContent).toContain("128 BPM");
  });

  test("is pushed to the right end of the row and centred vertically", () => {
    const r = rule(".metarow .preview-btn");
    expect(r).toMatch(/margin-left:\s*auto/);
    expect(r).toMatch(/align-self:\s*center/);
  });
});
