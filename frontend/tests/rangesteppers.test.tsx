import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

function api() {
  return mockFetch((url) => {
    if (url.pathname === "/api/maps/facets") {
      return { ...FACETS, duration: { min: 61, max: 300 }, bpm: { min: 90, max: 220 } };
    }
    return { items: [item(1)], total: 1, offset: 0, limit: 40 };
  });
}

async function open(path: string, column: string) {
  api();
  const app = renderApp(path);
  await screen.findByRole("link", { name: "Song 1" });
  await userEvent.click(screen.getByRole("button", { name: new RegExp(`^Filter ${column}`) }));
  const dialog = await screen.findByRole("dialog", { name: `${column} filter` });
  return { ...app, dialog };
}

const press = (el: HTMLElement) => {
  fireEvent.pointerDown(el, { button: 0 });
  fireEvent.pointerUp(el);
};

describe("range inputs", () => {
  test("Length placeholders show the library min and max as mm:ss", async () => {
    const { dialog } = await open("/", "Length");
    expect(within(dialog).getByLabelText("Minimum length")).toHaveAttribute("placeholder", "01:01");
    expect(within(dialog).getByLabelText("Maximum length")).toHaveAttribute("placeholder", "05:00");
  });

  test("BPM takes integers only: letters and a decimal point are refused", async () => {
    const { dialog } = await open("/", "BPM");
    const min = within(dialog).getByLabelText("BPM, at least");
    await userEvent.type(min, "12.5x");
    expect(min).toHaveValue("125");
    await userEvent.clear(min);
    await userEvent.click(min);
    await userEvent.paste("120.5");
    expect(min).toHaveValue("");
  });

  test("arrow buttons step BPM by 1, clamp at the other bound, and are not tab stops", async () => {
    const { dialog, router } = await open("/?bpm_min=100&bpm_max=101", "BPM");
    const upMin = within(dialog).getByRole("button", { name: "Increase minimum BPM" });
    expect(upMin).toHaveAttribute("tabindex", "-1");
    press(upMin);
    await waitFor(() => expect(router.state.location.search).toContain("bpm_min=101"));
    press(upMin);
    expect(router.state.location.search).toContain("bpm_min=101");
    const downMax = within(dialog).getByRole("button", { name: "Decrease maximum BPM" });
    press(downMax);
    await waitFor(() => expect(router.state.location.search).toContain("bpm_max=101"));
    expect(within(dialog).getByLabelText("BPM, at most")).toHaveValue("101");
  });

  test("ArrowUp and ArrowDown on the focused input step the same way", async () => {
    const { dialog, router } = await open("/?bpm_min=0&bpm_max=50", "BPM");
    const max = within(dialog).getByLabelText("BPM, at most");
    max.focus();
    await userEvent.keyboard("{ArrowUp}{ArrowUp}");
    await waitFor(() => expect(router.state.location.search).toContain("bpm_max=52"));
    const min = within(dialog).getByLabelText("BPM, at least");
    min.focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(min).toHaveValue("0");
  });

  test("Length arrows step by one second and show mm:ss", async () => {
    const { dialog, router } = await open("/?duration_min=210", "Length");
    press(within(dialog).getByRole("button", { name: "Increase minimum length" }));
    await waitFor(() => expect(router.state.location.search).toContain("duration_min=211"));
    expect(within(dialog).getByLabelText("Minimum length")).toHaveValue("03:31");
    press(within(dialog).getByRole("button", { name: "Decrease maximum length" }));
    await waitFor(() => expect(router.state.location.search).toContain("duration_max=299"));
  });
});
