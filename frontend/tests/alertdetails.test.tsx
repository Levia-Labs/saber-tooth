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
  new RegExp(`${selector.replace(/[.]/g, "\\.")}\\s*\\{([^}]*)\\}`).exec(css)?.[1] ?? "";

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
