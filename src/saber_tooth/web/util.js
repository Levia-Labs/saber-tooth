/* global document, Node, FormData, fetch, setTimeout */
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
    throw new Error(typeof detail === "string" ? detail : `HTTP ${res.status}`);
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

/** Poll a job until done or failed; resolves with the final job object. */
export async function runJob(label, started) {
  const jobId = started && started.job;
  if (jobId === undefined || jobId === null) return started;
  setStatus(`${label}: queued`);
  for (;;) {
    const job = await api.job(jobId);
    if (job.status === "done") {
      setStatus(`${label}: done`);
      return job;
    }
    if (job.status === "failed") {
      setStatus(`${label}: failed`);
      throw new Error(job.error || `${label} failed`);
    }
    setStatus(`${label}: ${job.status || "running"}`);
    await new Promise((resolve) => setTimeout(resolve, POLL_MS));
  }
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
