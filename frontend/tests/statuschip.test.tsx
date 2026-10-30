import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import { StatusChip } from "../src/components/Chips";
import { TipProvider } from "../src/components/Tip";
import { STATUS_META, STATUS_ORDER, statusHref, statusLinkLabel } from "../src/lib/status";
import type { StatusKey } from "../src/api/types";

const base = { errors: 0, warnings: 0 };
const show = (status: StatusKey, extra = {}, link = true) =>
  render(
    <MemoryRouter>
      <TipProvider>
        <StatusChip
          item={{ status, ...base, ...extra }}
          to={link ? statusHref("m1", { status, ...base, ...extra }) : undefined}
        />
      </TipProvider>
    </MemoryRouter>,
  );

describe("crop status", () => {
  test("has the scissors icon, a label and a place in the filter", () => {
    expect(STATUS_META.crop).toEqual({ label: "Qualified for crop", icon: "scissors" });
    expect(STATUS_ORDER).toContain("crop");
    expect(STATUS_ORDER.indexOf("crop")).toBe(STATUS_ORDER.indexOf("ok") - 1);
  });

  test("uses the info blue token", () => {
    const css = readFileSync(resolve(__dirname, "../src/styles/chips.css"), "utf8");
    expect(css).toMatch(/\.chip-crop\s*\{[^}]*--tone:\s*var\(--blue\)/);
  });

  test("chip names itself and carries the icon", () => {
    const { container } = show("crop", {}, false);
    const el = screen.getByRole("img", { name: "Qualified for crop" });
    expect(el).toHaveClass("chip-crop");
    expect(container.querySelector("svg")).not.toBeNull();
  });
});

describe("status chip navigation", () => {
  test.each([
    ["error", { errors: 3 }, "/maps/m1?tab=status&from=library", "Open status: 3 errors"],
    ["warn", { warnings: 1 }, "/maps/m1?tab=status&from=library", "Open status: 1 warning"],
    ["crop", {}, "/maps/m1?tab=crop&from=library", "Open crop"],
    ["ok", {}, "/maps/m1?from=library", "Open map: All good"],
    ["unscanned", {}, "/maps/m1?from=library", "Open map: Not scanned"],
  ] as const)("%s links to %s", (status, extra, href, name) => {
    const item = { status, ...base, ...extra };
    expect(statusHref("m1", item)).toBe(href);
    expect(statusLinkLabel(item)).toBe(name);
    show(status, extra);
    expect(screen.getByRole("link", { name })).toHaveAttribute("href", href);
  });

  test("without a target the chip is not a link", () => {
    show("crop", {}, false);
    expect(screen.queryByRole("link")).toBeNull();
  });
});
