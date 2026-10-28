/* global document */
// Drives a running saber-tooth in a headless browser and fails on any console error.
// Usage: node scripts/browser_check.mjs [chrome|firefox] [--base URL] [--path EXE]
// Read-only: every request that is not GET or HEAD is aborted, so no job ever starts.
import { mkdtempSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(fileURLToPath(new URL("../frontend/package.json", import.meta.url)));
const puppeteer = require("puppeteer-core");

const EXE = {
  firefox: ["C:/Program Files/Mozilla Firefox/firefox.exe", "/usr/bin/firefox"],
  chrome: [
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
  ],
};

function args(argv) {
  const out = { browser: "chrome", base: "http://127.0.0.1:8100", exe: "" };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--base") out.base = argv[++i];
    else if (argv[i] === "--path") out.exe = argv[++i];
    else if (argv[i] === "chrome" || argv[i] === "firefox") out.browser = argv[i];
    else throw new Error(`unknown argument ${argv[i]}`);
  }
  return out;
}

async function firstExisting(paths) {
  const { existsSync } = await import("node:fs");
  const found = paths.find((p) => existsSync(p));
  if (!found) throw new Error(`no browser found, pass --path (tried ${paths.join(", ")})`);
  return found;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const opt = args(process.argv.slice(2));
  const base = opt.base.replace(/\/$/, "");
  const first = await (await fetch(`${base}/api/maps?limit=1`)).json();
  const mapId = first.items?.[0]?.id;
  const routes = ["/", "/beatsaver", "/beatsaver/playlists", "/about"];
  if (mapId) routes.splice(1, 0, `/maps/${mapId}`);

  const profile = mkdtempSync(join(tmpdir(), "st-browser-"));
  const browser = await puppeteer.launch({
    browser: opt.browser,
    executablePath: opt.exe || (await firstExisting(EXE[opt.browser])),
    headless: true,
    userDataDir: profile,
  });
  const problems = [];
  try {
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on("request", (req) =>
      ["GET", "HEAD"].includes(req.method()) ? req.continue() : req.abort(),
    );
    page.on("console", (m) => m.type() === "error" && problems.push(`console: ${m.text()}`));
    page.on("pageerror", (e) => problems.push(`pageerror: ${e.stack || e.message}`));
    for (const route of routes) {
      await page.goto(base + route, { waitUntil: "networkidle0" });
      await sleep(1000);
      const text = await page.evaluate(() => document.querySelector("#root")?.innerText ?? "");
      const heading = await page.evaluate(() => !!document.querySelector("main"));
      if (!heading || text.trim().length < 20) problems.push(`${route}: nothing rendered`);
      console.log(`${opt.browser} ${route} ${text.trim().length} chars`);
    }
  } finally {
    await browser.close();
    rmSync(profile, { recursive: true, force: true });
  }
  if (problems.length) {
    console.log(problems.join("\n"));
    console.log(`FAIL ${opt.browser}: ${problems.length} problem(s)`);
    process.exit(1);
  }
  console.log(`PASS ${opt.browser}: ${routes.length} routes, zero console errors`);
}

main().catch((err) => {
  console.error(err.stack || err.message);
  process.exit(2);
});
