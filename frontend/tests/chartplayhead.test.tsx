import { act, fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { NpsChart } from "../src/components/NpsChart";
import { togglePreview } from "../src/lib/previewPlayer";
import { TIMELINE } from "./crophelpers";
import { audio, chart, mockAudio, type Props } from "./charthelpers";

mockAudio();

describe("playing the selection", () => {
  const play = () => screen.getByRole("button", { name: "Play selected section" });

  test("plays from the start, moves the playhead, pauses and stops at the end", async () => {
    const { container } = chart({ selection: { start_s: 14, end_s: 78 } });
    const user = userEvent.setup();
    await user.click(play());
    expect(audio.src).toBe("/api/maps/x/audio");
    audio.dispatchEvent(new Event("loadedmetadata"));
    expect(audio.currentTime).toBe(14);
    audio.currentTime = 46;
    act(() => void audio.dispatchEvent(new Event("timeupdate")));
    const head = container.querySelector(".nps-playhead") as SVGLineElement;
    expect(Number(head.getAttribute("x1"))).toBeCloseTo((46 / 140) * 1000, 0);
    await user.click(screen.getByRole("button", { name: "Pause selected section" }));
    expect(audio.paused).toBe(true);
    // Paused, the playhead stays where play stopped; that is where play starts next.
    expect(Number(container.querySelector(".nps-playhead")?.getAttribute("x1"))).toBeCloseTo(
      (46 / 140) * 1000,
      0,
    );
    await user.click(play());
    audio.currentTime = 78.2;
    act(() => void audio.dispatchEvent(new Event("timeupdate")));
    expect(play()).toBeInTheDocument();
    expect(audio.paused).toBe(true);
  });

  test("starting another audio stops this one", async () => {
    chart();
    await userEvent.click(play());
    expect(screen.getByRole("button", { name: "Pause selected section" })).toBeInTheDocument();
    act(() => togglePreview("/api/other"));
    expect(play()).toBeInTheDocument();
  });

  test("there is no play button without audio", () => {
    chart({ audioUrl: null });
    expect(screen.queryByRole("button", { name: /selected section/ })).toBeNull();
  });
});

describe("play button", () => {
  test("sits on the middle of the selected window and follows it", () => {
    const { rerender, container } = chart({ selection: { start_s: 20, end_s: 60 } });
    const button = screen.getByRole("button", { name: "Play selected section" });
    expect(button).toHaveClass("nps-play");
    expect(button).not.toHaveClass("btn");
    expect(parseFloat(button.style.left)).toBeCloseTo((40 / 140) * 100, 5);
    expect(container.querySelector(".nps-play svg")).toBeInTheDocument();
    rerender(<NpsChart {...propsFor({ selection: { start_s: 70, end_s: 130 } })} />);
    expect(parseFloat(button.style.left)).toBeCloseTo((100 / 140) * 100, 5);
  });
});

function propsFor(patch: Partial<Props>): Props {
  return {
    nps: TIMELINE.nps,
    hardest: "ExpertPlus",
    sections: TIMELINE.sections,
    duration: TIMELINE.duration_s,
    selection: { start_s: 0, end_s: 64 },
    faint: [],
    onMove: vi.fn(),
    onStep: vi.fn(),
    onShift: vi.fn(),
    onJump: vi.fn(),
    audioUrl: "/api/maps/x/audio",
    ...patch,
  };
}

describe("playhead triangle", () => {
  const cue = () => screen.getByRole("slider", { name: "Playback position" });

  test("is a slider at the start of the selection, with a line above it", () => {
    const { container } = chart({ selection: { start_s: 14, end_s: 78 } });
    expect(cue()).toHaveAttribute("aria-valuenow", "14");
    expect(cue()).toHaveAttribute("aria-valuemin", "14");
    expect(cue()).toHaveAttribute("aria-valuemax", "78");
    expect(cue().querySelector("svg path")).toBeInTheDocument();
    expect(Number(container.querySelector(".nps-playhead")?.getAttribute("x1"))).toBeCloseTo(
      100,
      0,
    );
  });

  test("is absent without audio or without a selection", () => {
    chart({ audioUrl: null });
    expect(screen.queryByRole("slider", { name: "Playback position" })).toBeNull();
  });

  test("dragging moves the playhead inside the selection and clamps at its ends", () => {
    const { container } = chart();
    fireEvent.pointerDown(cue(), { pointerId: 1 });
    fireEvent.pointerMove(cue(), { clientX: 300 });
    expect(cue()).toHaveAttribute("aria-valuenow", "42");
    expect(Number(container.querySelector(".nps-playhead")?.getAttribute("x1"))).toBeCloseTo(
      300,
      0,
    );
    fireEvent.pointerMove(cue(), { clientX: 900 });
    expect(cue()).toHaveAttribute("aria-valuenow", "64");
    fireEvent.pointerMove(cue(), { clientX: 0 });
    expect(cue()).toHaveAttribute("aria-valuenow", "0");
    fireEvent.pointerUp(cue(), { clientX: 300 });
    expect(cue()).toHaveAttribute("aria-valuenow", "42");
  });

  test("while paused the released position is where play starts", async () => {
    chart();
    fireEvent.pointerDown(cue(), { pointerId: 1 });
    fireEvent.pointerUp(cue(), { clientX: 300 });
    await userEvent.click(screen.getByRole("button", { name: "Play selected section" }));
    audio.dispatchEvent(new Event("loadedmetadata"));
    expect(audio.currentTime).toBe(42);
  });

  test("while playing a release seeks the audio there", async () => {
    chart({ selection: { start_s: 14, end_s: 78 } });
    await userEvent.click(screen.getByRole("button", { name: "Play selected section" }));
    audio.dispatchEvent(new Event("loadedmetadata"));
    expect(audio.currentTime).toBe(14);
    fireEvent.pointerDown(cue(), { pointerId: 1 });
    fireEvent.pointerMove(cue(), { clientX: 500 });
    fireEvent.pointerUp(cue(), { clientX: 500 });
    audio.dispatchEvent(new Event("loadedmetadata"));
    expect(audio.currentTime).toBe(70);
    expect(audio.paused).toBe(false);
    expect(screen.getByRole("button", { name: "Pause selected section" })).toBeInTheDocument();
  });

  test("arrow keys move it 0.1 s, Shift 1 s, never outside the selection", async () => {
    chart();
    const user = userEvent.setup();
    cue().focus();
    await user.keyboard("{ArrowRight}");
    expect(cue()).toHaveAttribute("aria-valuenow", "0.1");
    await user.keyboard("{Shift>}{ArrowRight}{/Shift}");
    expect(cue()).toHaveAttribute("aria-valuenow", "1.1");
    await user.keyboard("{ArrowLeft}{ArrowLeft}");
    expect(cue()).toHaveAttribute("aria-valuenow", "0.9");
    await user.keyboard("{Shift>}{ArrowLeft}{ArrowLeft}{/Shift}");
    expect(cue()).toHaveAttribute("aria-valuenow", "0");
  });
});
