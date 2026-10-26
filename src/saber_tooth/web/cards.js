/* global requestAnimationFrame */
import { drawTimeline } from "./timeline.js";
import { api, el, guard } from "./util.js";

export function proposalCard(p, onChange, notesFilter) {
  const keep = notesFilter || ((notes) => notes);
  const before = keep(p.before || []);
  const after = keep(p.after || []);
  const canvas = el("canvas", {
    role: "img",
    "aria-label": `Before and after note grids for ${p.summary}`,
  });
  const approve = el(
    "button",
    {
      type: "button",
      class: "approve",
      disabled: p.status === "approved",
      onclick: guard(async () => {
        await api.approve(p.id);
        await onChange();
      }),
    },
    "Approve",
  );
  const reject = el(
    "button",
    {
      type: "button",
      class: "reject",
      disabled: p.status === "rejected",
      onclick: guard(async () => {
        await api.reject(p.id);
        await onChange();
      }),
    },
    "Reject",
  );
  const card = el(
    "article",
    { class: `card sev-${p.severity} st-${p.status}` },
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
    canvas,
  );
  requestAnimationFrame(() => drawTimeline(canvas, before, after));
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
