import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, test, vi } from "vitest";
import { makeQueryClient } from "../src/App";
import { LibraryRow } from "../src/components/LibraryRow";
import { TipProvider } from "../src/components/Tip";
import { item } from "./helpers";

describe("Library preview button", () => {
  const renderRow = (patch = {}) =>
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <MemoryRouter>
          <TipProvider>
            <LibraryRow item={item(1, patch)} index={0} />
          </TipProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

  test("is absent without an audio address and present with one", () => {
    const none = renderRow();
    expect(screen.queryByRole("button", { name: /preview/i })).toBeNull();
    none.unmount();
    renderRow({ audio_url: "/api/maps/x/audio", preview_start: 12 });
    const row = document.querySelector("[data-map]") as HTMLElement;
    expect(within(row).getByRole("button", { name: "Play preview of Song 1" })).toBeInTheDocument();
    expect(row.querySelector(".col-title.with-preview")).not.toBeNull();
  });

  test("play seeks to the preview start and stops after 15 seconds", async () => {
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
    renderRow({ audio_url: "/api/maps/x/audio", preview_start: 40 });
    await userEvent.click(screen.getByRole("button", { name: "Play preview of Song 1" }));
    expect(audio.src).toBe("/api/maps/x/audio");
    audio.dispatchEvent(new Event("loadedmetadata"));
    expect(audio.currentTime).toBe(40);
    audio.currentTime = 47.5;
    audio.dispatchEvent(new Event("timeupdate"));
    expect(await screen.findByRole("button", { name: "Pause preview" })).toBeInTheDocument();
    audio.currentTime = 55.1;
    audio.dispatchEvent(new Event("timeupdate"));
    expect(
      await screen.findByRole("button", { name: "Play preview of Song 1" }),
    ).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
