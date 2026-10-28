import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { cropApi } from "./crophelpers";
import { renderApp } from "./helpers";

const PAGE = "/maps/id0000000001";
const timelineCalls = (calls: URL[]) => calls.filter((u) => u.pathname.endsWith("/timeline"));
const tab = (name: string) => screen.findByRole("tab", { name });

describe("map page tabs", () => {
  test("a tablist with Status, Crop and Delete; Status is the default and shows the fix actions", async () => {
    const { calls } = cropApi();
    renderApp(PAGE);
    const list = await screen.findByRole("tablist");
    const tabs = within(list).getAllByRole("tab");
    expect(tabs.map((t) => t.textContent)).toEqual(["Status", "Crop", "Delete"]);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(tabs[1]).toHaveAttribute("aria-selected", "false");
    expect(tabs[0]).toHaveAttribute("aria-controls", "map-panel-status");
    const panel = screen.getByRole("tabpanel");
    expect(panel).toHaveAttribute("aria-labelledby", tabs[0]?.id);
    expect(await within(panel).findByRole("toolbar", { name: "Fix actions" })).toBeVisible();
    expect(screen.queryByRole("slider", { name: "Crop end" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Delete permanently?" })).toBeNull();
    expect(timelineCalls(calls)).toHaveLength(0);
  });

  test("the title and header sit above the tabs, and the toolbar has no Crop or Delete", async () => {
    cropApi();
    renderApp(PAGE);
    const heading = await screen.findByRole("heading", { level: 1 });
    const list = await screen.findByRole("tablist");
    expect(heading.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const bar = await screen.findByRole("toolbar", { name: "Fix actions" });
    expect(within(bar).queryByRole("button", { name: /Crop/ })).toBeNull();
    expect(within(bar).queryByRole("button", { name: "Delete" })).toBeNull();
  });

  test("?tab=crop opens Crop and loads the timeline only then", async () => {
    const { calls } = cropApi();
    renderApp(`${PAGE}?tab=crop`);
    expect((await tab("Crop")).getAttribute("aria-selected")).toBe("true");
    expect(await screen.findByRole("slider", { name: "Crop end" })).toBeInTheDocument();
    expect(timelineCalls(calls)).toHaveLength(1);
  });

  test("choosing Crop writes ?tab=crop, fetches once and survives a trip to Status", async () => {
    const { calls } = cropApi();
    const { router } = renderApp(PAGE);
    const user = userEvent.setup();
    await user.click(await tab("Crop"));
    expect(router.state.location.search).toBe("?tab=crop");
    await screen.findByRole("slider", { name: "Crop end" });
    await user.click(await tab("Status"));
    expect(router.state.location.search).toBe("");
    expect(screen.queryByRole("slider", { name: "Crop end" })).toBeNull();
    await user.click(await tab("Crop"));
    expect(await screen.findByRole("slider", { name: "Crop end" })).toBeVisible();
    expect(timelineCalls(calls)).toHaveLength(1);
  });

  test("arrow keys, Home and End move between tabs", async () => {
    cropApi();
    renderApp(PAGE);
    const user = userEvent.setup();
    (await tab("Status")).focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Crop" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Crop" })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Delete" })).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Status" })).toHaveFocus();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Delete" })).toHaveFocus();
    await user.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Status" })).toHaveFocus();
  });

  test("only the selected tab is in the tab order", async () => {
    cropApi();
    renderApp(`${PAGE}?tab=delete`);
    expect(await tab("Delete")).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("tab", { name: "Status" })).toHaveAttribute("tabindex", "-1");
  });

  test("an unknown tab falls back to Status", async () => {
    cropApi();
    renderApp(`${PAGE}?tab=nope`);
    expect((await tab("Status")).getAttribute("aria-selected")).toBe("true");
  });

  test("an unreadable map has no Crop tab", async () => {
    cropApi({ map: { status: "unreadable", parse_error: "bad json" } });
    renderApp(`${PAGE}?tab=crop`);
    await screen.findByRole("tablist");
    expect(screen.queryByRole("tab", { name: "Crop" })).toBeNull();
    expect(screen.getByRole("tab", { name: "Status" })).toHaveAttribute("aria-selected", "true");
  });

  test("a clean fixed copy hides the Fix toolbar on Status but keeps the tabs", async () => {
    cropApi({ map: { status: "ok", original_id: "id0000000002" } });
    renderApp(PAGE);
    await screen.findByRole("tablist");
    await screen.findByRole("tab", { name: "Crop" });
    expect(screen.queryByRole("toolbar", { name: "Fix actions" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Fix/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Scan" })).toBeNull();
  });
});

describe("delete tab", () => {
  test("shows the confirmation inline, and Back returns to Status", async () => {
    cropApi();
    const { router } = renderApp(PAGE);
    const user = userEvent.setup();
    await user.click(await tab("Delete"));
    expect(router.state.location.search).toBe("?tab=delete");
    const panel = screen.getByRole("tabpanel");
    expect(within(panel).getByText("Delete permanently?")).toBeVisible();
    expect(panel).toHaveTextContent("Folder 1");
    expect(panel).toHaveTextContent("cannot be undone");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(within(panel).getByRole("button", { name: "Delete" })).toHaveClass("danger");
    await user.click(within(panel).getByRole("button", { name: "Back" }));
    expect((await tab("Status")).getAttribute("aria-selected")).toBe("true");
    expect(router.state.location.search).toBe("");
    expect(screen.queryByRole("heading", { name: "Delete permanently?" })).toBeNull();
  });

  test("Back sends no DELETE", async () => {
    const { fn } = cropApi();
    renderApp(`${PAGE}?tab=delete`);
    await userEvent.click(await screen.findByRole("button", { name: "Back" }));
    await waitFor(() =>
      expect(screen.queryByRole("heading", { name: "Delete permanently?" })).toBeNull(),
    );
    expect(fn.mock.calls.filter(([, init]) => init?.method === "DELETE")).toHaveLength(0);
  });

  test("Delete is disabled while a job runs", async () => {
    cropApi({ map: { job: { id: "j", kind: "scan", status: "running" } } });
    renderApp(`${PAGE}?tab=delete`);
    const panel = await screen.findByRole("tabpanel");
    expect(within(panel).getByRole("button", { name: "Delete" })).toBeDisabled();
  });
});
