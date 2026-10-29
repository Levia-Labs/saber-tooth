/* global document */
// Captures product screenshots (PNG and WebP) of a running saber-tooth in headless Chrome or Edge.
// Usage: node scripts/screenshots.mjs [--base URL] [--out DIR] [--width 1440 --height 900] [--path EXE]
//        [--sizes 1280x720,1920x1080] [--only vr-library,vr-jobs]
// --sizes captures every selected shot at each size, named NAME-WxH; --only keeps the named shots.
// Read-only: every request that is not GET or HEAD is aborted, so no job ever starts.
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(fileURLToPath(new URL("../frontend/package.json", import.meta.url)));
const puppeteer = require("puppeteer-core");

const EXE = [
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
];
const PNG_MAX = 1_500_000;
const WEBP_MAX = 600_000;

function parseSize(text) {
  const [width, height] = text.split("x").map(Number);
  if (!(width > 0 && height > 0)) throw new Error(`bad size ${text}, expected WIDTHxHEIGHT`);
  return { width, height };
}

function parse(argv) {
  const out = {
    base: "http://127.0.0.1:8100",
    out: "docs/screenshots",
    width: 1440,
    height: 900,
    exe: "",
    sizes: [],
    only: [],
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--base") out.base = argv[++i];
    else if (a === "--out") out.out = argv[++i];
    else if (a === "--width") out.width = Number(argv[++i]);
    else if (a === "--height") out.height = Number(argv[++i]);
    else if (a === "--path") out.exe = argv[++i];
    else if (a === "--sizes") out.sizes = argv[++i].split(",").map(parseSize);
    else if (a === "--only") out.only = argv[++i].split(",");
    else throw new Error(`unknown argument ${a}`);
  }
  return out;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const getJson = async (url) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.json();
};

/** Rank maps for the Status tab: ok first, then fixed copies, then anything scanned. */
function rank(m) {
  if (m.status === "ok") return 0;
  if (m.fixed_copy_id || m.original_id) return 1;
  return m.status === "unscanned" ? 3 : 2;
}

async function pickMap(base) {
  const items = (await getJson(`${base}/api/maps?limit=50`)).items ?? [];
  const usable = items
    .filter((m) => m.audio_url && !m.parse_error)
    .sort((a, b) => rank(a) - rank(b));
  let crop = null;
  for (const m of usable) {
    try {
      const t = await getJson(`${base}/api/maps/${m.id}/timeline`);
      if (Object.values(t.lengths ?? {}).some((l) => l.enabled && l.suggestions?.length)) {
        crop = m;
        break;
      }
    } catch {
      /* try the next map */
    }
  }
  if (!crop) throw new Error("no map with audio and enabled crop suggestions");
  return { crop, status: usable[0] ?? crop };
}

async function settle(page) {
  // Pages that poll (jobs, VR status) are never idle for long: wait a while, then shoot anyway.
  await page.waitForNetworkIdle({ idleTime: 500, timeout: 8000 }).catch(() => undefined);
  await page.waitForFunction(() => !document.querySelector("[data-skeleton], .sk"), {
    timeout: 30000,
  });
  await sleep(500);
}

async function save(page, dir, name, url) {
  const buf = await page.screenshot({ type: "png" });
  if (buf.length > PNG_MAX) throw new Error(`${name}.png is ${buf.length} bytes, over ${PNG_MAX}`);
  writeFileSync(join(dir, `${name}.png`), buf);
  let q = 85;
  let web = await page.screenshot({ type: "webp", quality: q });
  while (web.length > WEBP_MAX && q > 30) {
    q -= 10;
    web = await page.screenshot({ type: "webp", quality: q });
  }
  writeFileSync(join(dir, `${name}.webp`), web);
  console.log(
    `${name}: png ${Math.round(buf.length / 1024)} KB, webp ${Math.round(web.length / 1024)} KB q${q} ${url}`,
  );
}

async function main() {
  const opt = parse(process.argv.slice(2));
  const base = opt.base.replace(/\/$/, "");
  const exe = opt.exe || EXE.find((p) => existsSync(p));
  if (!exe) throw new Error(`no browser found, pass --path (tried ${EXE.join(", ")})`);
  const { crop, status } = await pickMap(base);
  const desktop = { width: opt.width, height: opt.height };
  const vr = { width: 1920, height: 1080 };
  const shots = [
    ["library", "/", desktop, null],
    ["map-status", `/maps/${status.id}`, desktop, null],
    ["map-crop", `/maps/${crop.id}?tab=crop`, desktop, '[role="slider"][aria-label="Crop start"]'],
    ["beatsaver", "/beatsaver", desktop, null],
    ["new-map", "/new", desktop, null],
    ["about", "/about", desktop, null],
    ["jobs", "/jobs", desktop, null],
    ["playlists", "/beatsaver/playlists", desktop, null],
    ["vr-library", "/vr", vr, null],
    ["vr-map", `/vr/maps/${status.id}`, vr, null],
    ["vr-beatsaver", "/vr/beatsaver", vr, null],
    ["vr-jobs", "/vr/jobs", vr, null],
    ["vr-about", "/about?mode=vr", vr, null],
    ["vr-playlists", "/beatsaver/playlists?mode=vr", vr, null],
  ];
  const picked = shots.filter(([name]) => !opt.only.length || opt.only.includes(name));
  const plan = opt.sizes.length
    ? picked.flatMap(([name, path, , wait]) =>
        opt.sizes.map((s) => [`${name}-${s.width}x${s.height}`, path, s, wait]),
      )
    : picked;
  mkdirSync(opt.out, { recursive: true });
  const profile = mkdtempSync(join(tmpdir(), "st-shots-"));
  const browser = await puppeteer.launch({
    browser: "chrome",
    executablePath: exe,
    headless: true,
    userDataDir: profile,
  });
  const failed = [];
  try {
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on("request", (req) =>
      ["GET", "HEAD"].includes(req.method()) ? req.continue() : req.abort(),
    );
    for (const [name, path, size, wait] of plan) {
      try {
        await page.setViewport(size);
        await page.goto(base + path, { waitUntil: "load", timeout: 30000 });
        if (wait) await page.waitForSelector(wait, { timeout: 30000 });
        await settle(page);
        await save(page, opt.out, name, base + path);
      } catch (e) {
        failed.push(`${name}: ${e.message}`);
        console.error(`FAIL ${name} ${base + path}: ${e.message}`);
      }
    }
  } finally {
    await browser.close();
    rmSync(profile, { recursive: true, force: true });
  }
  process.exit(failed.length ? 1 : 0);
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
