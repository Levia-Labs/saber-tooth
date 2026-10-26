import { isRetryable } from "./retry.js";
export const statusEl = document.getElementById("status");
export const POLL_MS = 1000;

export function el(tag, props = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value === true) node.setAttribute(key, "");
    else if (value !== false && value != null) node.setAttribute(key, value);
  }
  for (const kid of kids.flat()) {
    node.append(kid instanceof Node ? kid : document.createTextNode(String(kid ?? "")));
  }
  return node;
}

export function setStatus(text) {
  statusEl.textContent = text;
}

export async function request(method, path, body) {
  const init = { method, headers: {} };
  if (body instanceof FormData) init.body = body;
  else if (body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const res = await fetch(path, init);
  let data;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = data && (data.detail || data.error);
    const err = new Error(typeof detail === "string" ? detail : `HTTP ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  maps: () => request("GET", "/api/maps"),
  scan: (id) => request("POST", `/api/maps/${encodeURIComponent(id)}/scan`),
  proposals: (id) => request("GET", `/api/maps/${encodeURIComponent(id)}/proposals`),
  approve: (id) => request("POST", `/api/proposals/${encodeURIComponent(id)}/approve`),
  reject: (id) => request("POST", `/api/proposals/${encodeURIComponent(id)}/reject`),
  approveAll: (id) => request("POST", `/api/maps/${encodeURIComponent(id)}/approve-all`),
  apply: (id) => request("POST", `/api/maps/${encodeURIComponent(id)}/apply`),
  generate: (body) => request("POST", "/api/generate", body),
  learn: () => request("POST", "/api/lightshow/learn"),
  job: (id) => request("GET", `/api/jobs/${encodeURIComponent(id)}`),
};

const MAX_JOB_MS = 30 * 60 * 1000;
const MAX_FETCH_FAILS = 3;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** Poll a job until done or failed; backs off to 3 s, gives up after 30 min. */
export async function runJob(label, started) {
  const jobId = started && started.job;
  if (jobId === undefined || jobId === null) return started;
  setStatus(`${label}: queued`);
  const deadline = Date.now() + MAX_JOB_MS;
  let delay = POLL_MS;
  let fails = 0;
  while (Date.now() < deadline) {
    let job;
    try {
      job = await api.job(jobId);
      fails = 0;
    } catch (err) {
      fails += 1;
      if (!isRetryable(err) || fails >= MAX_FETCH_FAILS) {
        setStatus(`${label}: lost contact with the server`);
        throw err;
      }
      setStatus(`${label}: retrying (${fails}/${MAX_FETCH_FAILS})`);
      await sleep(delay);
      continue;
    }
    if (job.status === "done") {
      setStatus(`${label}: done`);
      return job;
    }
    if (job.status === "failed") {
      setStatus(`${label}: failed`);
      throw new Error(job.error || `${label} failed`);
    }
    setStatus(`${label}: ${job.status || "running"}`);
    await sleep(delay);
    delay = Math.min(delay * 1.5, 3000);
  }
  setStatus(`${label}: timed out after 30 minutes`);
  throw new Error(`${label} timed out`);
}

export function guard(fn) {
  return async (...args) => {
    try {
      await fn(...args);
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  };
}

let running = 0;

function lockJobs(on) {
  for (const b of document.querySelectorAll("[data-job]")) {
    if (on) {
      b.dataset.prev = b.disabled ? "1" : "";
      b.disabled = true;
    } else {
      b.disabled = b.dataset.prev === "1";
    }
  }
}

/** Like guard, but disables every job button while fn runs and refuses re-entry. */
export function jobGuard(fn) {
  return async (...args) => {
    if (running) return;
    running += 1;
    lockJobs(true);
    try {
      await fn(...args);
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    } finally {
      running -= 1;
      lockJobs(false);
    }
  };
}

/** Button that starts a job; created disabled when another job is running. */
export function jobButton(props, label) {
  const btn = el("button", { ...props, "data-job": "1" }, label);
  if (running) {
    btn.dataset.prev = props.disabled ? "1" : "";
    btn.disabled = true;
  }
  return btn;
}

export function jobOutcome(job) {
  const result = (job && job.result) || {};
  const box = el("div", { class: "result" });
  if (result.conflict) box.append(el("p", { class: "err" }, `Conflict: ${result.conflict}`));
  else if (result.folder) box.append(el("p", { class: "ok" }, `Written to: ${result.folder}`));
  else box.append(el("p", { class: "ok" }, "Job finished."));
  return box;
}

export function setNav(view) {
  for (const tab of document.querySelectorAll(".tab")) {
    if (tab.dataset.view === view) tab.setAttribute("aria-current", "page");
    else tab.removeAttribute("aria-current");
  }
}
