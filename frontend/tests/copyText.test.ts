import { afterEach, describe, expect, test, vi } from "vitest";
import { copyText } from "../src/lib/copyText";

afterEach(() => {
  vi.unstubAllGlobals();
  Reflect.deleteProperty(document, "execCommand");
});

describe("copyText", () => {
  test("uses the async clipboard when present", async () => {
    const writeText = vi.fn(async () => undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    expect(await copyText("X:\\Maps\\Song")).toBe(true);
    expect(writeText).toHaveBeenCalledWith("X:\\Maps\\Song");
  });

  test("falls back to a hidden textarea and execCommand without a clipboard", async () => {
    vi.stubGlobal("navigator", {});
    let copied = "";
    document.execCommand = vi.fn(() => {
      copied = (document.querySelector("textarea") as HTMLTextAreaElement).value;
      return true;
    });
    expect(await copyText("/srv/maps/Song")).toBe(true);
    expect(copied).toBe("/srv/maps/Song");
    expect(document.querySelector("textarea")).toBeNull();
  });

  test("falls back when the clipboard rejects", async () => {
    vi.stubGlobal("navigator", {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    document.execCommand = vi.fn(() => true);
    expect(await copyText("p")).toBe(true);
    expect(document.execCommand).toHaveBeenCalledWith("copy");
  });

  test("reports failure when every route fails", async () => {
    vi.stubGlobal("navigator", {});
    document.execCommand = vi.fn(() => false);
    expect(await copyText("p")).toBe(false);
    expect(document.querySelector("textarea")).toBeNull();
  });
});
