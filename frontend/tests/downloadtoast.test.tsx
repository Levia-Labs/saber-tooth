import { useEffect } from "react";
import { act, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { AnnouncerProvider, useAnnounce } from "../src/components/Announcer";
import { DownloadSummary } from "../src/components/beatsaver/DownloadSummary";
import type { Downloads } from "../src/components/beatsaver/downloads";
import type { BsOutcome } from "../src/api/beatsaver";
import type { JobRunner } from "../src/api/jobs";

const runner = (busy: boolean): JobRunner => ({
  state: busy ? "running" : "done",
  busy,
  error: null,
  job: null,
  run: async () => null,
});
const make = (busy: boolean, results: BsOutcome[]): Downloads => ({
  runner: runner(busy),
  pending: new Set(),
  results: Object.fromEntries(results.map((o) => [o.id, o])),
  start: async () => undefined,
  status: () => ({ kind: "none" }),
});

const handle: { progress: () => void } = { progress: () => undefined };
function Grab() {
  const announce = useAnnounce();
  useEffect(() => {
    handle.progress = () =>
      announce({ key: "Download maps", variant: "progress", title: "Download maps" });
  }, [announce]);
  return null;
}
const sendProgress = () => handle.progress();
function Probe({ downloads }: { downloads: Downloads }) {
  return (
    <>
      <Grab />
      <DownloadSummary downloads={downloads} />
    </>
  );
}
const ui = (d: Downloads) => (
  <AnnouncerProvider>
    <Probe downloads={d} />
  </AnnouncerProvider>
);

describe("download batch toast", () => {
  test("a running batch shows the progress toast with the spinner and no inline text", () => {
    const { container } = render(ui(make(true, [])));
    act(() => sendProgress());
    expect(document.querySelector(".toast-stack .alert-spin")).not.toBeNull();
    expect(container.querySelector(".result")).toBeNull();
  });

  test("the finished batch replaces the progress toast in place, with no inline summary", () => {
    const view = render(ui(make(true, [])));
    act(() => sendProgress());
    view.rerender(
      ui(
        make(false, [
          { id: "k1", status: "installed" },
          { id: "k3", status: "failed", reason: "Needs Noodle" },
        ]),
      ),
    );
    expect(document.querySelectorAll(".toast-stack .alert")).toHaveLength(1);
    expect(document.querySelector(".alert-spin")).toBeNull();
    expect(screen.getByText(/Installed 1, skipped 0, failed 1\./)).toBeInTheDocument();
    expect(screen.getByText(/k3: Needs Noodle/)).toBeInTheDocument();
    expect(document.querySelector(".alert-warning")).not.toBeNull();
    expect(document.querySelector(".result")).toBeNull();
  });
});
