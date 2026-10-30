import { describe, expect, test } from "vitest";
import { stageStates } from "../src/lib/genstages";

const states = (...args: Parameters<typeof stageStates>) =>
  stageStates(...args).map((s) => s.state);

describe("generate stages", () => {
  test("names the five stages, Upload for a file", () => {
    expect(stageStates({ status: "queued" }, "url").map((s) => s.label)).toEqual([
      "Download",
      "Analyse beats",
      "Map",
      "Fix",
      "Write",
    ]);
    expect(stageStates({ status: "queued" }, "file")[0]?.label).toBe("Upload");
  });

  test("a queued job has nothing done or current", () => {
    expect(states({ status: "queued", position: 3 }, "url")).toEqual(Array(5).fill("todo"));
  });

  test("progress text moves the current stage", () => {
    expect(states({ status: "running", progress: null }, "url")).toEqual([
      "now",
      "todo",
      "todo",
      "todo",
      "todo",
    ]);
    expect(states({ status: "running", progress: "analysing the song" }, "url")).toEqual([
      "done",
      "now",
      "todo",
      "todo",
      "todo",
    ]);
    expect(states({ status: "running", progress: "fixing the map: round 2" }, "url")).toEqual([
      "done",
      "done",
      "done",
      "now",
      "todo",
    ]);
    expect(states({ status: "running", progress: "saving the map" }, "file")[4]).toBe("now");
  });

  test("done finishes all, failed marks the current one", () => {
    expect(states({ status: "done" }, "url")).toEqual(Array(5).fill("done"));
    expect(states({ status: "failed", progress: "building the map" }, "url")).toEqual([
      "done",
      "done",
      "failed",
      "todo",
      "todo",
    ]);
  });
});
