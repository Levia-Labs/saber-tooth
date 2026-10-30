import { screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { isCleanCopy } from "../src/lib/status";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const original = item(1, {
  status: "error",
  fixed_copy_id: "id0000000099",
  fixed_copy_folder: "Folder 1 [saber-tooth]",
});
const copy = (status: "ok" | "error" | "unscanned") =>
  item(99, {
    folder: "Folder 1 [saber-tooth]",
    status,
    errors: status === "error" ? 2 : 0,
    original_id: "id0000000001",
    original_folder: "Folder 1",
  });

function serve(map: ReturnType<typeof item>, list = [map]) {
  mockFetch((url) => {
    if (url.pathname === "/api/maps/facets") return FACETS;
    if (url.pathname === `/api/maps/${map.id}`) return map;
    if (url.pathname.endsWith("/proposals")) return [];
    if (url.pathname.endsWith("/findings")) return { scanned: false, findings: [] };
    return { items: list, total: list.length, offset: 0, limit: 40 };
  });
}

describe("isCleanCopy", () => {
  test("needs original_id and an ok status", () => {
    expect(isCleanCopy({ status: "ok", original_id: "a" })).toBe(true);
    expect(isCleanCopy({ status: "ok", original_id: null })).toBe(false);
    expect(isCleanCopy({ status: "ok" })).toBe(false);
    expect(isCleanCopy({ status: "error", original_id: "a" })).toBe(false);
    expect(isCleanCopy({ status: "unscanned", original_id: "a" })).toBe(false);
  });
});

describe("fixed copy links", () => {
  test("library rows have no inline fixed-copy link", async () => {
    serve(original, [original]);
    renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(screen.queryByText(/Fixed copy:/)).toBeNull();
    expect(screen.queryByRole("link", { name: "Folder 1 [saber-tooth]" })).toBeNull();
  });

  test("original page shows the fixed copy banner with a link to it", async () => {
    serve(original);
    renderApp("/maps/id0000000001");
    const banner = (await screen.findByText("Fixed copy ready")).closest(".alert") as HTMLElement;
    expect(banner).toHaveClass("alert-success");
    expect(banner.closest(".toast-stack")).toBeNull();
    expect(within(banner).getByRole("link", { name: "Folder 1 [saber-tooth]" })).toHaveAttribute(
      "href",
      "/maps/id0000000099",
    );
  });

  test("copy page shows a Fixed copy of banner linking to the original", async () => {
    serve(copy("error"));
    renderApp("/maps/id0000000099");
    const banner = (await screen.findByText("Fixed copy of")).closest(".alert") as HTMLElement;
    expect(banner).toHaveClass("alert-info");
    expect(banner.closest(".toast-stack")).toBeNull();
    expect(within(banner).getByRole("link", { name: "Folder 1" })).toHaveAttribute(
      "href",
      "/maps/id0000000001",
    );
  });
});

describe("clean copy page", () => {
  test("hides fix controls and the empty alert, keeps the Delete tab and the banner", async () => {
    serve(copy("ok"));
    renderApp("/maps/id0000000099");
    await screen.findByText("Fixed copy of");
    await screen.findByRole("tab", { name: "Delete" });
    for (const name of [
      /^Fix/,
      /^Scan/,
      /Approve all/,
      /Apply approved/,
      /Expand all/,
      /Collapse all/,
    ]) {
      expect(screen.queryByRole("button", { name })).toBeNull();
    }
    expect(screen.queryByText("No fixes yet")).toBeNull();
  });

  test("a copy with findings keeps every control", async () => {
    serve(copy("error"));
    renderApp("/maps/id0000000099");
    await screen.findByText("Fixed copy of");
    for (const name of [/Approve all/, /Apply approved/, /Expand all/, /Collapse all/]) {
      expect(await screen.findByRole("button", { name })).toBeInTheDocument();
    }
    expect(screen.getByRole("tab", { name: "Delete" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Scan/ }).length).toBeGreaterThan(0);
    expect(screen.getByText("Not scanned yet")).toBeInTheDocument();
  });

  test("an unscanned copy keeps every control", async () => {
    serve(copy("unscanned"));
    renderApp("/maps/id0000000099");
    expect(await screen.findByRole("button", { name: /Apply approved/ })).toBeInTheDocument();
    expect(await screen.findByText("Not scanned yet")).toBeInTheDocument();
  });
});
