/* global document, FormData */
import { api, el, guard, jobOutcome, runJob, setNav, setStatus } from "./util.js";
import { proposalCard } from "./cards.js";

const main = document.getElementById("main");

export function showNew() {
  setNav("new");
  const url = el("input", {
    type: "url",
    id: "gen-url",
    placeholder: "https://www.youtube.com/watch?v=...",
    "aria-label": "YouTube URL",
  });
  const file = el("input", {
    type: "file",
    id: "gen-file",
    accept: "audio/*",
    "aria-label": "Audio file",
  });
  const out = el("div");
  const go = el(
    "button",
    {
      type: "button",
      class: "primary",
      onclick: guard(async () => {
        let body;
        if (file.files.length) {
          body = new FormData();
          body.append("file", file.files[0]);
        } else if (url.value.trim()) body = { url: url.value.trim() };
        else {
          setStatus("Provide a URL or an audio file.");
          return;
        }
        out.replaceChildren();
        const job = await runJob("Generate", await api.generate(body));
        const mapId = job.result && job.result.map_id;
        if (mapId === undefined) {
          out.replaceChildren(jobOutcome(job));
          return;
        }
        await showCreate(mapId, out);
      }),
    },
    "Generate",
  );
  main.replaceChildren(
    el("h2", {}, "New map"),
    el(
      "div",
      { class: "toolbar" },
      el("label", {}, "URL ", url),
      el("label", {}, "or file ", file),
      go,
    ),
    out,
  );
}

const FIRST_16_BARS = 64;

async function showCreate(mapId, out) {
  const proposals = (await api.proposals(mapId)).filter((p) => p.rule === "create-map");
  const reload = () => showCreate(mapId, out);
  const counts = el(
    "ul",
    {},
    ...proposals.map((p) => el("li", {}, `${p.difficulty}: ${(p.after || []).length} notes`)),
  );
  const head = el("h3", {}, "Proposed map (first 16 bars of Expert)");
  const firstBars = (notes) => notes.filter((n) => n.beat < FIRST_16_BARS);
  const cards = proposals.map((p) =>
    p.difficulty === "Expert"
      ? proposalCard(p, reload, firstBars)
      : proposalCard(p, reload, () => []),
  );
  const shown = cards.filter((_, i) => proposals[i].difficulty === "Expert");
  const approvedAny = proposals.some((p) => p.status === "approved");
  const write = el(
    "button",
    {
      type: "button",
      class: "primary",
      disabled: !approvedAny,
      onclick: guard(async () => {
        const job = await runJob("Write map", await api.apply(mapId));
        out.append(jobOutcome(job));
      }),
    },
    "Write map folder",
  );
  out.replaceChildren(head, counts, ...shown, write);
}
