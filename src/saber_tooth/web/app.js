/* global document, confirm */
import { api, el, guard, jobOutcome, runJob, setNav } from "./util.js";
import { groupBy, proposalCard } from "./cards.js";
import { showNew } from "./newmap.js";

const main = document.getElementById("main");

// ---- Library ----
async function showLibrary() {
  setNav("library");
  main.replaceChildren(el("p", { class: "muted" }, "Loading maps..."));
  const maps = await api.maps();
  const filter = el("input", {
    type: "search",
    placeholder: "Filter maps",
    "aria-label": "Filter maps",
  });
  const body = el("tbody");
  const render = () => {
    const q = filter.value.trim().toLowerCase();
    body.replaceChildren(
      ...maps
        .filter((m) =>
          `${m.title} ${m.mapper} ${m.folder} ${m.environment}`.toLowerCase().includes(q),
        )
        .map(mapRow),
    );
  };
  filter.addEventListener("input", render);
  const learn = el(
    "button",
    {
      type: "button",
      onclick: guard(async () => {
        await runJob("Learn lightshows", await api.learn());
      }),
    },
    "Learn lightshows",
  );
  const head = el(
    "tr",
    {},
    ...["Title", "Mapper", "Environment", "Errors", "Warnings", ""].map((h) =>
      el("th", { scope: "col" }, h),
    ),
  );
  main.replaceChildren(
    el("h2", {}, "Library"),
    el("div", { class: "toolbar" }, filter, learn),
    el("table", {}, el("thead", {}, head), body),
  );
  render();
}

function mapRow(m) {
  const title = m.parse_error ? `${m.title || m.folder} (unparseable)` : m.title || m.folder;
  const scan = el(
    "button",
    {
      type: "button",
      "aria-label": `Scan ${m.title || m.folder}`,
      onclick: guard(async () => {
        await runJob("Scan", await api.scan(m.id));
        await showMap(m.id, m.title || m.folder);
      }),
    },
    "Scan",
  );
  const open = el(
    "button",
    {
      type: "button",
      "aria-label": `Review ${m.title || m.folder}`,
      onclick: guard(() => showMap(m.id, m.title || m.folder)),
    },
    "Review",
  );
  return el(
    "tr",
    {},
    el("td", {}, title),
    el("td", {}, m.mapper),
    el("td", {}, m.environment),
    el("td", { class: `num ${m.errors ? "err" : ""}` }, m.errors),
    el("td", { class: `num ${m.warnings ? "warn" : ""}` }, m.warnings),
    el("td", {}, el("div", { class: "row" }, scan, open)),
  );
}

// ---- Proposals ----

async function showMap(id, name) {
  setNav("");
  const proposals = await api.proposals(id);
  const reload = () => showMap(id, name);
  const approvedCount = proposals.filter((p) => p.status === "approved").length;
  const result = el("div");
  const applyBtn = el(
    "button",
    {
      type: "button",
      class: "primary",
      disabled: approvedCount === 0,
      onclick: guard(async () => {
        result.replaceChildren();
        applyBtn.disabled = true;
        try {
          const job = await runJob("Apply", await api.apply(id));
          result.replaceChildren(jobOutcome(job));
        } catch (err) {
          result.replaceChildren(
            el(
              "div",
              { class: "result" },
              el("p", { class: "err" }, `Conflict or failure: ${err.message}`),
            ),
          );
          throw err;
        } finally {
          applyBtn.disabled = false;
        }
      }),
    },
    "Apply approved",
  );
  const all = el(
    "button",
    {
      type: "button",
      disabled: proposals.length === 0,
      onclick: guard(async () => {
        if (!confirm(`Approve every pending proposal for "${name}"?`)) return;
        await api.approveAll(id);
        await reload();
      }),
    },
    "Approve all for this map",
  );
  const back = el("button", { type: "button", onclick: guard(showLibrary) }, "Back to library");
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
  main.replaceChildren(
    el("h2", {}, name),
    el("div", { class: "toolbar" }, back, all, applyBtn),
    result,
    ...sections,
  );
}

// ---- New map ----
for (const tab of document.querySelectorAll(".tab")) {
  tab.addEventListener(
    "click",
    guard(() => (tab.dataset.view === "new" ? showNew() : showLibrary())),
  );
}
guard(showLibrary)();
