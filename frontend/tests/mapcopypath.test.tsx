import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { item, mockFetch, renderApp, toasts } from "./helpers";

const PAGE = "/maps/id0000000001";
const LABEL = "Copy folder path to clipboard";
const PATH = "X:\\Beat Saber\\CustomLevels\\Folder 1";

afterEach(() => vi.unstubAllGlobals());

function api(folderPath: string | null) {
  mockFetch((url) => {
    if (url.pathname === "/api/maps/id0000000001") return { ...item(1), folder_path: folderPath };
    if (url.pathname.endsWith("/proposals")) return [];
    return { items: [], total: 0, offset: 0, limit: 40 };
  });
}

describe("copy folder path button", () => {
  test("renders after the tablist, outside it, with its label", async () => {
    api(PATH);
    renderApp(PAGE);
    const list = await screen.findByRole("tablist");
    const button = await screen.findByRole("button", { name: LABEL });
    expect(button).toHaveAttribute("title", LABEL);
    expect(within(list).queryByRole("button", { name: LABEL })).toBeNull();
    expect(list.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  test("click copies the path and toasts success", async () => {
    api(PATH);
    const user = userEvent.setup();
    renderApp(PAGE);
    const writeText = vi.fn(async () => undefined);
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });
    await user.click(await screen.findByRole("button", { name: LABEL }));
    expect(writeText).toHaveBeenCalledWith(PATH);
    expect(await toasts().findByText("Folder path copied")).toBeInTheDocument();
    expect(await toasts().findByText(PATH)).toBeInTheDocument();
  });

  test("a failed copy toasts the path for manual selection", async () => {
    api(PATH);
    const user = userEvent.setup();
    renderApp(PAGE);
    vi.stubGlobal("navigator", { clipboard: undefined });
    document.execCommand = vi.fn(() => false);
    await user.click(await screen.findByRole("button", { name: LABEL }));
    expect(await toasts().findByText("Could not copy the folder path")).toBeInTheDocument();
    expect(await toasts().findByText(PATH)).toBeInTheDocument();
  });

  test("is hidden without a folder path", async () => {
    api(null);
    renderApp(PAGE);
    await screen.findByRole("tablist");
    expect(screen.queryByRole("button", { name: LABEL })).toBeNull();
  });
});
