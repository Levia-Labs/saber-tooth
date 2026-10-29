import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { item, mockFetch, renderApp } from "./helpers";

const ENVS = ["BigMirrorEnvironment", "NiceEnvironment", "Origins"];

function open(patch = {}) {
  const mock = mockFetch((url, init) => {
    if (url.pathname === "/api/maps/id0000000001") return item(1, patch);
    if (url.pathname === "/api/lightshow/environments") return { environments: ENVS };
    if (url.pathname === "/api/maps/id0000000001/relight") return { job: "a".repeat(32) };
    if (url.pathname.startsWith("/api/jobs/")) {
      return { id: "a".repeat(32), kind: "relight", status: "running", result: null, init };
    }
    if (url.pathname.endsWith("/proposals")) return [];
    return {};
  });
  renderApp("/maps/id0000000001");
  return mock;
}

afterEach(() => vi.unstubAllGlobals());

describe("map page environment dropdown", () => {
  test("lists the template environments and preselects the current one", async () => {
    open();
    const select = await screen.findByRole<HTMLSelectElement>("combobox", { name: /environment/i });
    await waitFor(() => expect(select.options.length).toBe(3));
    expect(select.value).toBe("Origins");
    expect([...select.options].map((o) => o.text)).toEqual(["Big Mirror", "Nice", "Origins"]);
  });

  test("a change asks first and starts a relight job on confirm", async () => {
    const { fn } = open();
    const select = await screen.findByRole("combobox", { name: /environment/i });
    await waitFor(() => expect(screen.getAllByRole("option").length).toBe(3));
    await userEvent.selectOptions(select, "NiceEnvironment");
    expect(await screen.findByText(/Relight in Nice\?/)).toBeVisible();
    expect(fn.mock.calls.some(([u]) => String(u).endsWith("/relight"))).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Relight" }));
    await waitFor(() => {
      const call = fn.mock.calls.find(([u]) => String(u).endsWith("/relight"));
      expect(call).toBeDefined();
      expect(JSON.parse(String(call?.[1]?.body))).toEqual({ environment: "NiceEnvironment" });
    });
  });

  test("cancelling the confirm starts nothing and keeps the current environment", async () => {
    const { fn } = open();
    const select = await screen.findByRole<HTMLSelectElement>("combobox", {
      name: /environment/i,
    });
    await waitFor(() => expect(select.options.length).toBe(3));
    await userEvent.selectOptions(select, "NiceEnvironment");
    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(fn.mock.calls.some(([u]) => String(u).endsWith("/relight"))).toBe(false);
    expect(select.value).toBe("Origins");
  });
});
