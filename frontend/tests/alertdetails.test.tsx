import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Alert } from "../src/components/Alert";

const css = readFileSync(resolve(__dirname, "../src/styles/alerts.css"), "utf-8").replace(
  /\/\*[\s\S]*?\*\//g,
  "",
);
const rule = (selector: string) =>
  new RegExp(`(?:^|\n)${selector.replace(/[.]/g, "\\.")}\\s*\\{([^}]*)\\}`).exec(css)?.[1] ?? "";

test("the details body is height-capped, scrolls and keeps whitespace", () => {
  const body = rule(".alert-details-body");
  expect(body).toMatch(/max-height:\s*min\(40vh,\s*18rem\)/);
  expect(body).toMatch(/overflow-y:\s*auto/);
  expect(body).toMatch(/scrollbar-width:\s*thin/);
  const pre = rule(".alert-details-body pre");
  expect(pre).toMatch(/white-space:\s*pre-wrap/);
  expect(pre).toMatch(/monospace/);
});

test("the toast stack never exceeds the viewport", () => {
  expect(rule(".toast-stack")).toMatch(/max-height:\s*calc\(100dvh/);
});

test("expanded details render in a labelled keyboard-scrollable region", () => {
  render(<Alert variant="danger" title="Failed" details={["Traceback line"]} />);
  const region = screen.getByLabelText("Error details");
  expect(region.tabIndex).toBe(0);
  expect(region.textContent).toContain("Traceback line");
});

test("Details and the action share one row container, Details first", () => {
  render(
    <Alert
      variant="danger"
      title="Failed"
      details={["x"]}
      actions={<a href="/m">Open fixed map</a>}
    />,
  );
  const row = screen.getByText("Details").closest(".alert-foot") as HTMLElement;
  expect(row).not.toBeNull();
  const link = screen.getByText("Open fixed map");
  expect(row.contains(link)).toBe(true);
  const summary = screen.getByText("Details");
  expect(summary.compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(rule(".alert-foot")).toMatch(/flex-wrap:\s*wrap/);
  expect(rule(".alert-foot .alert-actions")).toMatch(/margin-left:\s*auto/);
});

test("toasts have a 650px floor and go full width on a narrow viewport, no mobile breakpoint", () => {
  expect(rule(".toast-stack .toast")).toMatch(
    /min-width:\s*min\(calc\(650px \* var\(--ui-scale, 1\)\),\s*100%\)/,
  );
  expect(css).not.toMatch(/max-width:\s*719\.98px/);
  const narrow = /@media \(max-width:\s*(\d+)px\)\s*\{\s*\.toast-stack \.toast\s*\{([^}]*)\}/.exec(
    css,
  );
  expect(narrow).not.toBeNull();
  expect(Number(narrow![1])).toBe(650 + 32);
  expect(narrow![2]).toMatch(/min-width:\s*100%/);
  expect(rule(".toast-stack")).toMatch(/width:\s*min\(100% - 2rem,/);
});
