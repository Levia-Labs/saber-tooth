import type { CropEnd, CropPlan, CropWindow, EndKind, Timeline } from "../src/api/types";
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";
import { makeQueryClient } from "../src/App";
import { AnnouncerProvider } from "../src/components/Announcer";
import { TipProvider } from "../src/components/Tip";
import type { MapItem } from "../src/api/types";
import { item, mockFetch } from "./helpers";

const series = (scale: number): number[] =>
  Array.from({ length: 140 }, (_, i) => Math.round(((i % 20) / 20) * scale * 10) / 10);

/** An end at `beat` on a 120 bpm map: seconds are half the beats. */
const end = (beat: number, kind: EndKind): CropEnd => ({ beat, seconds: beat / 2, kind });

const win = (start: number, stop: number, kind: EndKind): CropWindow => ({
  start_beat: start,
  end_beat: stop,
  start_s: start / 2,
  end_s: stop / 2,
  length_s: (stop - start) / 2,
  end_kind: kind,
  score: 0.5,
});

const PLAN_60: CropPlan = {
  enabled: true,
  reason: null,
  band: [54, 66],
  suggestions: [win(0, 128, "section"), win(128, 256, "phrase")],
  starts: [
    {
      beat: 0,
      seconds: 0,
      ends: [end(112, "bar4"), end(116, "bar"), end(128, "section"), end(132, "bar")],
    },
    { beat: 128, seconds: 64, ends: [end(240, "bar4"), end(256, "phrase")] },
  ],
};

const PLAN_120: CropPlan = {
  enabled: true,
  reason: null,
  band: [108, 132],
  suggestions: [win(0, 224, "section")],
  starts: [{ beat: 0, seconds: 0, ends: [end(224, "section"), end(240, "phrase")] }],
};

/** A 140 s song at 120 bpm with three sections and both lengths enabled. */
export const TIMELINE: Timeline = {
  map_id: "id0000000001",
  duration_s: 140,
  min_length_s: 1,
  bpm: 120,
  hardest: "ExpertPlus",
  map_only: false,
  grid_drift_s: 0,
  nps: { Expert: series(4), ExpertPlus: series(6) },
  sections: [
    { start_beat: 0, end_beat: 128, start_s: 0, end_s: 64, nps: 3, intensity: 0.4 },
    { start_beat: 128, end_beat: 224, start_s: 64, end_s: 112, nps: 6, intensity: 1 },
    { start_beat: 224, end_beat: 280, start_s: 112, end_s: 140, nps: 2, intensity: 0.3 },
  ],
  lengths: { "60": PLAN_60, "120": PLAN_120 },
};

const proposal = (rank: number, start: number, stop: number, target: string, score: number) => ({
  rank,
  start_beat: start * 2,
  end_beat: stop * 2,
  start_s: start,
  end_s: stop,
  length_s: stop - start,
  target,
  score,
  reason: `rise from ${start}, peak at ${start + 20}, release at ${stop}`,
});

/** Three Auto proposals on the 140 s song; the first equals the 1 min plan's best window. */
export const SUGGESTIONS = {
  map_id: "id0000000001",
  duration_s: 140,
  reason: null,
  suggestions: [
    proposal(1, 0, 64, "1 min", 0.9),
    proposal(2, 70, 136, "1 min", 0.7),
    proposal(3, 10, 130, "2 min", 0.5),
  ],
};

export function renderPanel(ui: ReactElement, route = "/") {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <TipProvider delayDuration={0}>
        <MemoryRouter initialEntries={[route]}>
          <AnnouncerProvider>{ui}</AnnouncerProvider>
        </MemoryRouter>
      </TipProvider>
    </QueryClientProvider>,
  );
}

interface ApiOptions {
  timeline?: unknown;
  suggestions?: unknown;
  jobStatus?: string;
  jobError?: string | null;
  map?: Partial<MapItem>;
}

export function cropApi(options: ApiOptions = {}) {
  const posts: { path: string; body: unknown }[] = [];
  const mock = mockFetch((url, init) => {
    if (init?.method === "POST") {
      posts.push({ path: url.pathname, body: JSON.parse(String(init.body ?? "{}")) });
      return { job: "jc" };
    }
    if (url.pathname === "/api/maps/id0000000001") return item(1, options.map);
    if (url.pathname === "/api/maps/id0000000001/proposals") return [];
    if (url.pathname === "/api/maps/id0000000001/timeline") return options.timeline ?? TIMELINE;
    if (url.pathname === "/api/maps/id0000000001/crop/suggestions") {
      return options.suggestions ?? SUGGESTIONS;
    }
    if (url.pathname === "/api/jobs/j") {
      return { id: "j", kind: "scan", status: "running", error: null, result: null };
    }
    if (url.pathname === "/api/jobs/jc") {
      return {
        id: "jc",
        kind: "crop",
        status: options.jobStatus ?? "done",
        error: options.jobError ?? null,
        result: {
          map_id: "id0000000001",
          folder: "Folder 1 [1 min]",
          cropped_id: "id0000000099",
          label: "1 min",
          start_beat: 0,
          end_beat: 128,
          length_s: 64,
        },
      };
    }
    return { items: [item(1)], total: 1, offset: 0, limit: 40 };
  });
  return { ...mock, posts };
}

export const startHandle = () => screen.getByRole("slider", { name: "Crop start" });
export const endHandle = () => screen.getByRole("slider", { name: "Crop end" });

/** The chart svg, 1000 px wide in a 140 s song: one pixel is 0.14 s. */
export function chartSvg(): SVGSVGElement {
  const svg = document.querySelector(".nps-stage > svg") as SVGSVGElement;
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
  return svg;
}
