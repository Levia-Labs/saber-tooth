// Icons come from the inline sprite in index.html; names map to <symbol id="i-NAME">.
const NS = "http://www.w3.org/2000/svg";

export function icon(name, extra = "") {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", extra ? `ic ${extra}` : "ic");
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(NS, "use");
  use.setAttribute("href", `#i-${name}`);
  svg.append(use);
  return svg;
}
