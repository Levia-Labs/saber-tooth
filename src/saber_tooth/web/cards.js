import { drawTimeline, isNotesless } from "./timeline.js";
import { api, el, guard } from "./util.js";
import { icon } from "./icons.js";
import { TIPS } from "./tips.js";

const drawn = new Set();
let resizeTimer;

function redrawAll() {
  for (const item of drawn) {
    if (!item.canvas.isConnected) drawn.delete(item);
    else drawTimeline(item.canvas, item.before, item.after, item.opts);
  }
}

window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(redrawAll, 150);
});

/** Move focus to the first enabled button of a proposal card, else the card. */
function restoreFocus(id) {
  const card = document.querySelector(`[data-proposal="${CSS.escape(String(id))}"]`);
  if (!card) return;
  const next = card.querySelector("button:not(:disabled)");
  (next || card).focus();
}

export function proposalCard(p, onChange, notesFilter) {
  const keep = notesFilter || ((notes) => notes);
  const before = keep(p.before || []);
  const after = keep(p.after || []);
  const canvas = el("canvas", {
    role: "img",
    "aria-label": `Before and after note grids for ${p.summary}`,
  });
  const opts = {
    wallsBefore: p.walls_before || [],
    wallsAfter: p.walls_after || [],
    wallsContext: p.walls_context || [],
  };
  const textOnly = isNotesless(before, after, [...opts.wallsBefore, ...opts.wallsAfter]);
  const body = textOnly ? el("p", { class: "muted" }, p.summary) : canvas;
  const approve = el(
    "button",
    {
      type: "button",
      class: "btn approve",
      "data-tip": TIPS.approve,
      disabled: p.status === "approved",
      onclick: guard(async () => {
        await api.approve(p.id);
        await onChange();
        restoreFocus(p.id);
      }),
    },
    [icon("approve"), "Approve"],
  );
  const reject = el(
    "button",
    {
      type: "button",
      class: "btn reject",
      "data-tip": TIPS.reject,
      disabled: p.status === "rejected",
      onclick: guard(async () => {
        await api.reject(p.id);
        await onChange();
        restoreFocus(p.id);
      }),
    },
    [icon("reject"), "Reject"],
  );
  const card = el(
    "article",
    { class: `card sev-${p.severity} st-${p.status}`, "data-proposal": p.id, tabindex: "-1" },
    el(
      "header",
      {},
      el(
        "div",
        {},
        el("strong", {}, p.summary),
        " ",
        el("span", { class: "badge" }, p.severity),
        " ",
        el("span", { class: "badge" }, p.status),
      ),
      el("div", { class: "row" }, approve, reject),
    ),
    body,
  );
  if (textOnly) return card;
  requestAnimationFrame(() => {
    if (!canvas.isConnected) return;
    for (const item of drawn) if (!item.canvas.isConnected) drawn.delete(item);
    drawn.add({ canvas, before, after, opts });
    drawTimeline(canvas, before, after, opts);
  });
  return card;
}

export function groupBy(list, key) {
  const out = new Map();
  for (const item of list) {
    if (!out.has(item[key])) out.set(item[key], []);
    out.get(item[key]).push(item);
  }
  return out;
}
