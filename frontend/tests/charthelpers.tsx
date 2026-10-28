import { render } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";
import { NpsChart } from "../src/components/NpsChart";
import { stopPreview } from "../src/lib/previewPlayer";
import { TIMELINE } from "./crophelpers";

export const audio = new (class extends EventTarget {
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

export type Props = Parameters<typeof NpsChart>[0];

export function chart(patch: Partial<Props> = {}) {
  const fns = {
    onMove: vi.fn(),
    onStep: vi.fn(),
    onShift: vi.fn(),
    onJump: vi.fn(),
  };
  const view = render(
    <NpsChart
      nps={TIMELINE.nps}
      hardest="ExpertPlus"
      sections={TIMELINE.sections}
      duration={TIMELINE.duration_s}
      selection={{ start_s: 0, end_s: 64 }}
      faint={[]}
      audioUrl="/api/maps/x/audio"
      {...fns}
      {...patch}
    />,
  );
  const svg = view.container.querySelector("svg") as SVGSVGElement;
  vi.spyOn(svg, "getBoundingClientRect").mockReturnValue({
    left: 0,
    top: 0,
    right: 1000,
    bottom: 160,
    width: 1000,
    height: 160,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  });
  return { ...view, svg, ...fns };
}

/** Stub the shared audio element for each test; the setup file unstubs globals after each one. */
export function mockAudio(): void {
  beforeEach(() => {
    vi.stubGlobal("Audio", function () {
      return audio;
    });
  });
  afterEach(() => stopPreview());
}
