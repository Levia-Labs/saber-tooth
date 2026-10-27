// Map page at /maps/<id>: header, actions, findings and proposals with before/after timelines.
import { api, el, guard, jobGuard, jobOutcome, runJob } from "./util.js";
import { groupBy, proposalCard } from "./cards.js";
import { cover, pips, statusChip } from "./chips.js";
import { icon } from "./icons.js";
import { isCurrent, libraryHref } from "./router.js";
import { actionButton } from "./ui.js";
import { TIPS } from "./tips.js";
import { mapName } from "./librows.js";

const main = document.getElementById("main");

function backLink() {
  return el("a", { class: "back", href: libraryHref() }, icon("back"), "Library");
}

function notFound(id) {
  main.replaceChildren(
    backLink(),
    el("h2", {}, "Map not found"),
    el("p", { class: "muted" }, `No map with id ${id}. It may have been removed from the folder.`),
  );
  return "Map not found";
}

function proposalSections(proposals, reload) {
  const sections = [];
  for (const [difficulty, byDiff] of groupBy(proposals, "difficulty")) {
    sections.push(el("h3", {}, difficulty));
    for (const [rule, byRule] of groupBy(byDiff, "rule")) {
      sections.push(el("p", { class: "muted" }, `${rule} (${byRule.length})`));
      sections.push(...byRule.map((p) => proposalCard(p, reload)));
    }
  }
  if (!proposals.length)
    sections.push(el("p", { class: "muted" }, "No proposals. Scan the map first."));
  return sections;
}

/** Render the map page; returns the document title. */
export async function showMap(id, token, outcome) {
  let map;
  let proposals;
  try {
    [map, proposals] = await Promise.all([api.map(id), api.proposals(id)]);
  } catch (err) {
    if (err.status === 404) return notFound(id);
    throw err;
  }
  if (!isCurrent(token)) return null;
  const name = mapName(map);
  const reload = () => showMap(id, token);
  const approved = proposals.filter((p) => p.status === "approved").length;

  const scan = actionButton({
    name: "scan",
    label: "Scan",
    text: true,
    tip: TIPS.scan,
    job: true,
    onclick: jobGuard(async () => {
      await runJob("Scan", await api.scan(id));
      if (isCurrent(token)) await showMap(id, token);
    }),
  });
  const all = actionButton({
    name: "approve",
    label: "Approve all",
    text: true,
    tip: TIPS.approveAll,
    disabled: proposals.length === 0,
    onclick: guard(async () => {
      if (!confirm(`Approve every pending proposal for "${name}"?`)) return;
      await api.approveAll(id);
      await reload();
    }),
  });
  const apply = actionButton({
    name: "apply",
    label: "Apply approved",
    text: true,
    tip: TIPS.apply.replace("<map>", name),
    job: true,
    class: "primary",
    disabled: approved === 0,
    onclick: jobGuard(async () => {
      let box;
      try {
        box = jobOutcome(await runJob("Apply", await api.apply(id)));
      } catch (err) {
        box = el(
          "div",
          { class: "result" },
          el("p", { class: "err" }, `Conflict or failure: ${err.message}`),
        );
      }
      if (isCurrent(token)) await showMap(id, token, box);
    }),
  });
  main.replaceChildren(
    backLink(),
    el(
      "section",
      { class: "maphead" },
      cover(map, true),
      el(
        "div",
        { class: "mapmeta" },
        el("h2", {}, name),
        el(
          "p",
          { class: "sub" },
          map.mapper || "Unknown mapper",
          map.environment ? ` - ${map.environment}` : "",
        ),
        el("div", { class: "metarow" }, statusChip(map), pips(map.difficulties)),
      ),
      el("div", { class: "toolbar" }, scan, all, apply),
    ),
    el("div", {}, outcome || ""),
    ...proposalSections(proposals, reload),
  );
  return name;
}
