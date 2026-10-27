// Library page: search, status filter, sortable table, infinite scroll over GET /api/maps.
import { api, el, setStatus } from "./util.js";
import { icon } from "./icons.js";
import { rememberLibrary } from "./router.js";
import { mapRow } from "./librows.js";
import { SORTS, STATUSES, apiQuery, encodeState, nextSort, parseState } from "./urlstate.js";

const PAGE = 40;
const SEARCH_DEBOUNCE_MS = 250;
const COLUMNS = [
  ["cover", "Image", null],
  ["title", "Title", "title"],
  ["env", "Environment", "environment"],
  ["status", "Status", "status"],
  ["actions", "Actions", null],
];
let observer = null;

export function showLibrary() {
  if (observer) observer.disconnect();
  let state = parseState(location.search);
  rememberLibrary(encodeState(state));
  let items = [];
  let total = 0;
  let loading = false;
  let failed = false;
  let gen = 0;
  let abort = null;

  const search = el("input", {
    type: "search",
    id: "lib-q",
    value: state.q,
    placeholder: "Search title, mapper, environment",
    "aria-label": "Search maps",
    autocomplete: "off",
  });
  const segments = STATUSES.map(([key, label]) =>
    el(
      "button",
      {
        type: "button",
        class: "seg",
        "data-status": key,
        onclick: () => change({ status: key }, true),
      },
      label,
    ),
  );
  const sortSelect = el(
    "select",
    { "aria-label": "Sort by", onchange: () => change({ sort: sortSelect.value }, true) },
    SORTS.map(([key, label]) => el("option", { value: key }, label)),
  );
  const orderBtn = el("button", {
    type: "button",
    class: "btn icon order",
    onclick: () => change({ order: state.order === "asc" ? "desc" : "asc" }, true),
  });
  const heads = COLUMNS.map(([cls, label, key]) => {
    const th = el("th", { scope: "col", class: `c-${cls}` });
    if (!key) {
      th.append(label);
      return [th, null];
    }
    const btn = el(
      "button",
      { type: "button", class: "thbtn", onclick: () => change(nextSort(state, key), true) },
      label,
    );
    th.append(btn);
    return [th, key];
  });
  const body = el("tbody");
  const count = el("p", { class: "count muted", "aria-live": "polite" });
  const empty = el("p", { class: "empty", hidden: true }, "No maps match these filters.");
  const more = el(
    "button",
    { type: "button", class: "btn", hidden: true, onclick: () => loadPage(false) },
    "Load more",
  );
  const sentinel = el("div", { class: "sentinel" });

  function syncControls() {
    if (search.value !== state.q) search.value = state.q;
    for (const seg of segments)
      seg.setAttribute("aria-pressed", String(seg.dataset.status === state.status));
    sortSelect.value = state.sort;
    orderBtn.replaceChildren(
      icon(state.order === "asc" ? "sort-asc" : "sort-desc"),
      el(
        "span",
        { class: "sr" },
        state.order === "asc"
          ? "Ascending, switch to descending"
          : "Descending, switch to ascending",
      ),
    );
    for (const [th, key] of heads) {
      if (!key) continue;
      const active = key === state.sort;
      th.setAttribute(
        "aria-sort",
        active ? (state.order === "asc" ? "ascending" : "descending") : "none",
      );
      const btn = th.querySelector("button");
      btn.querySelector("svg")?.remove();
      if (active) btn.append(icon(state.order === "asc" ? "sort-asc" : "sort-desc"));
    }
  }

  function syncFooter() {
    const shown = items.length;
    count.textContent = failed
      ? ""
      : loading && !shown
        ? "Loading maps..."
        : `${shown} of ${total} maps`;
    more.hidden = failed ? false : shown >= total || (loading && !shown);
    more.textContent = failed ? "Retry" : "Load more";
    more.disabled = loading && shown > 0;
    empty.hidden = loading || failed || total > 0;
  }

  async function loadPage(reset) {
    if (reset) {
      if (abort) abort.abort();
      items = [];
      total = 0;
      body.replaceChildren();
    } else if (loading) return;
    const mine = ++gen;
    abort = new AbortController();
    loading = true;
    failed = false;
    syncFooter();
    try {
      const page = await api.mapsPage(apiQuery(state, items.length, PAGE), abort.signal);
      if (mine !== gen) return;
      items.push(...page.items);
      total = page.total;
      body.append(...page.items.map(mapRow));
    } catch (err) {
      if (mine !== gen || err.name === "AbortError") return;
      failed = true;
      setStatus(`Error: ${err.message}`);
    }
    loading = false;
    syncFooter();
    if (observer && sentinel.isConnected) {
      observer.unobserve(sentinel);
      observer.observe(sentinel);
    }
  }

  function change(patch, push) {
    state = { ...state, ...patch };
    const search_ = encodeState(state);
    history[push ? "pushState" : "replaceState"](null, "", `${location.pathname}${search_}`);
    rememberLibrary(search_);
    syncControls();
    loadPage(true);
  }

  let timer = 0;
  search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (search.value.trim() !== state.q.trim()) change({ q: search.value }, false);
    }, SEARCH_DEBOUNCE_MS);
  });

  if (typeof IntersectionObserver === "function") {
    observer = new IntersectionObserver(
      (entries) => {
        if (!sentinel.isConnected) observer.disconnect();
        else if (entries.some((e) => e.isIntersecting) && !failed && items.length < total)
          loadPage(false);
      },
      { rootMargin: "400px 0px" },
    );
    observer.observe(sentinel);
  }

  const main = document.getElementById("main");
  main.replaceChildren(
    el("h2", {}, "Library"),
    el(
      "div",
      { class: "toolbar" },
      el(
        "label",
        { class: "searchbox" },
        el("span", { class: "sr" }, "Search maps"),
        icon("search"),
        search,
      ),
      el("div", { class: "segs", role: "group", "aria-label": "Filter by status" }, segments),
      el(
        "div",
        { class: "sortbox" },
        el("label", {}, el("span", { class: "sr" }, "Sort by"), sortSelect),
        orderBtn,
      ),
    ),
    count,
    el(
      "table",
      { class: "maps" },
      el(
        "thead",
        {},
        el(
          "tr",
          {},
          heads.map(([th]) => th),
        ),
      ),
      body,
    ),
    empty,
    el("div", { class: "more" }, more),
    sentinel,
  );
  syncControls();
  loadPage(true);
  return "";
}
