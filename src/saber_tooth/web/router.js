// History API router. Pure matching plus a small navigation controller; no DOM imports.
export function matchRoute(pathname) {
  const path = String(pathname || "/").replace(/\/+$/, "") || "/";
  if (path === "/") return { name: "library" };
  if (path === "/new") return { name: "new" };
  const found = /^\/maps\/([^/]+)$/.exec(path);
  if (found) {
    try {
      return { name: "map", id: decodeURIComponent(found[1]) };
    } catch {
      return { name: "notfound" };
    }
  }
  return { name: "notfound" };
}

export function mapHref(id) {
  return `/maps/${encodeURIComponent(id)}`;
}

/** True when a click on a link should be handled by the router instead of the browser. */
export function isPlainClick(event, link, origin) {
  if (event.defaultPrevented || event.button !== 0) return false;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
  if (link.target && link.target !== "_self") return false;
  if (link.download) return false;
  const url = new URL(link.href, origin);
  return url.origin === origin && matchRoute(url.pathname).name !== "notfound";
}

let token = 0;
let render = null;
let librarySearch = "";

/** A render is current while no later navigation has started. */
export function isCurrent(t) {
  return t === token;
}

/** Remember the library query so the map page's back link restores it. */
export function rememberLibrary(search) {
  librarySearch = search || "";
}

export function libraryHref() {
  return `/${librarySearch}`;
}

async function run() {
  token += 1;
  const mine = token;
  const title = await render(matchRoute(location.pathname), mine);
  if (mine !== token) return;
  document.title = title ? `${title} - saber-tooth` : "saber-tooth";
  const heading = document.querySelector("main h2");
  if (heading) {
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
  }
}

export function navigate(url, replace = false) {
  history[replace ? "replaceState" : "pushState"](null, "", url);
  if (!replace) scrollTo(0, 0);
  return run();
}

/** Install the router. renderRoute(route, token) draws the page and returns its title. */
export function start(renderRoute) {
  render = renderRoute;
  window.addEventListener("popstate", run);
  document.addEventListener("click", (event) => {
    const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
    if (!link || !isPlainClick(event, link, location.origin)) return;
    event.preventDefault();
    const url = new URL(link.href);
    navigate(url.pathname + url.search);
  });
  return run();
}
