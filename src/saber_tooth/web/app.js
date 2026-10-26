import { api, el, guard, jobButton, jobGuard, jobOutcome, runJob, setNav } from "./util.js";
import { groupBy, proposalCard } from "./cards.js";
import { showNew } from "./newmap.js";

const main = document.getElementById("main");
let navToken = 0; // bumped on every view change
let activeMap = null; // id of the map view on screen, else null

// ---- Library ----
async function showLibrary() {
  navToken += 1;
  activeMap = null;
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
  const learn = jobButton(
    {
      type: "button",
      onclick: jobGuard(async () => {
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

/** Update a library row's counts without changing the view; no-op once the row is gone. */
async function refreshCounts(id, errCell, warnCell) {
  const fresh = (await api.maps()).find((m) => m.id === id);
  if (!fresh || !errCell.isConnected) return;
  errCell.textContent = fresh.errors;
  errCell.className = `num ${fresh.errors ? "err" : ""}`;
  warnCell.textContent = fresh.warnings;
  warnCell.className = `num ${fresh.warnings ? "warn" : ""}`;
}

function mapRow(m) {
  const title = m.parse_error ? `${m.title || m.folder} (unparseable)` : m.title || m.folder;
  const errCell = el("td", { class: `num ${m.errors ? "err" : ""}` }, m.errors);
  const warnCell = el("td", { class: `num ${m.warnings ? "warn" : ""}` }, m.warnings);
  const scan = jobButton(
    {
      type: "button",
      "aria-label": `Scan ${m.title || m.folder}`,
      onclick: jobGuard(async () => {
        const token = navToken;
        await runJob("Scan", await api.scan(m.id));
        if (token === navToken || activeMap === m.id) await showMap(m.id, m.title || m.folder);
        else await refreshCounts(m.id, errCell, warnCell);
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
    errCell,
    warnCell,
    el("td", {}, el("div", { class: "row" }, scan, open)),
  );
}

// ---- Proposals ----

async function showMap(id, name, outcome) {
  navToken += 1;
  activeMap = id;
  setNav("");
  const proposals = await api.proposals(id);
  const reload = () => showMap(id, name);
  const approvedCount = proposals.filter((p) => p.status === "approved").length;
  const result = el("div", {}, outcome || "");
  const applyBtn = jobButton(
    {
      type: "button",
      class: "primary",
      disabled: approvedCount === 0,
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
        await showMap(id, name, box);
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
    guard(() => {
      if (tab.dataset.view === "new") {
        navToken += 1;
        activeMap = null;
        return showNew();
      }
      return showLibrary();
    }),
  );
}
guard(showLibrary)();
