// One library row: cover, title, environment, status chip and action buttons.
import { api, el, jobGuard, runJob } from "./util.js";
import { cover, pips, statusChip } from "./chips.js";
import { mapHref } from "./router.js";
import { actionButton } from "./ui.js";
import { TIPS } from "./tips.js";

export function mapName(m) {
  return m.title || m.folder;
}

/** Row element for a map item; a finished scan swaps the row for a fresh one. */
export function mapRow(m) {
  const name = mapName(m);
  const href = mapHref(m.id);
  const titleLink = el("a", { class: "title-link", href }, name);
  const sub = el(
    "div",
    { class: "sub" },
    m.parse_error ? "Unreadable Info file" : m.mapper || "Unknown mapper",
  );
  const review = actionButton({
    name: "review",
    label: `Review ${name}`,
    tip: TIPS.review,
    href,
    class: "icon",
  });
  const pending = m.pending || 0;
  if (pending > 0) {
    review.setAttribute("aria-label", `Review ${name}, ${pending} fixes waiting for review`);
    review.append(el("span", { class: "badge-count", "aria-hidden": "true" }, pending));
  }
  const refresh = async () => {
    const fresh = await api.map(m.id);
    if (row.isConnected) row.replaceWith(mapRow(fresh));
  };
  const apply = actionButton({
    name: "apply",
    label: `Apply approved fixes for ${name}`,
    tip: TIPS.apply.replace("<map>", name),
    job: true,
    class: "icon",
    onclick: jobGuard(async () => {
      await runJob("Apply", await api.apply(m.id));
      await refresh();
    }),
  });
  const scan = actionButton({
    name: "scan",
    label: `Scan ${name}`,
    tip: TIPS.scan,
    job: true,
    class: "icon",
    onclick: jobGuard(async () => {
      await runJob("Scan", await api.scan(m.id));
      await refresh();
    }),
  });
  const row = el(
    "tr",
    { "data-map": m.id },
    el("td", { class: "c-cover" }, cover(m)),
    el("td", { class: "c-title" }, titleLink, sub, pips(m.difficulties)),
    el("td", { class: "c-env" }, m.environment || ""),
    el("td", { class: "c-status" }, statusChip(m)),
    el(
      "td",
      { class: "c-actions" },
      el("div", { class: "row" }, review, scan, ...((m.approved || 0) > 0 ? [apply] : [])),
    ),
  );
  return row;
}
