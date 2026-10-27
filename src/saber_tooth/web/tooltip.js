// Accessible tooltips for any element carrying data-tip. Placement math is pure and tested.
const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), Math.max(lo, hi));

/**
 * Position a tooltip of size tip near anchor (viewport coordinates), staying on screen.
 * Prefers above the anchor; flips below when above does not fit. arrowX is relative to left.
 */
export function placeTooltip({ anchor, tip, viewport, gap = 8, margin = 8 }) {
  const above = anchor.top - gap - tip.height;
  const below = anchor.top + anchor.height + gap;
  const fitsAbove = above >= margin;
  const fitsBelow = below + tip.height <= viewport.height - margin;
  const roomAbove = anchor.top;
  const roomBelow = viewport.height - anchor.top - anchor.height;
  const placement = fitsAbove || (!fitsBelow && roomAbove > roomBelow) ? "top" : "bottom";
  const wanted = placement === "top" ? above : below;
  const top = clamp(wanted, margin, viewport.height - tip.height - margin);
  const center = anchor.left + anchor.width / 2;
  const left = clamp(center - tip.width / 2, margin, viewport.width - tip.width - margin);
  const arrowX = clamp(center - left, 12, tip.width - 12);
  return { left, top, placement, arrowX };
}

const HOLD_MS = 400;
const TOUCH_SHOW_MS = 2500;

export function installTooltips() {
  const tip = document.createElement("div");
  tip.id = "tooltip";
  tip.setAttribute("role", "tooltip");
  tip.hidden = true;
  document.body.append(tip);
  let current = null;
  let holdTimer = 0;
  let hideTimer = 0;

  function hide() {
    clearTimeout(holdTimer);
    clearTimeout(hideTimer);
    if (current) current.removeAttribute("aria-describedby");
    current = null;
    tip.hidden = true;
  }

  function show(target) {
    const text = target.dataset.tip;
    if (!text) return;
    if (current) current.removeAttribute("aria-describedby");
    current = target;
    tip.textContent = text;
    tip.hidden = false;
    const r = target.getBoundingClientRect();
    const t = tip.getBoundingClientRect();
    const spot = placeTooltip({
      anchor: { left: r.left, top: r.top, width: r.width, height: r.height },
      tip: { width: t.width, height: t.height },
      viewport: { width: window.innerWidth, height: window.innerHeight },
    });
    tip.style.left = `${spot.left}px`;
    tip.style.top = `${spot.top}px`;
    tip.style.setProperty("--arrow-x", `${spot.arrowX}px`);
    tip.dataset.placement = spot.placement;
    target.setAttribute("aria-describedby", "tooltip");
  }

  const targetOf = (event) =>
    event.target instanceof Element ? event.target.closest("[data-tip]") : null;

  document.addEventListener("mouseover", (event) => {
    const target = targetOf(event);
    if (target && target !== current) show(target);
  });
  document.addEventListener("mouseout", (event) => {
    const into = event.relatedTarget;
    if (current && !(into instanceof Node && current.contains(into))) hide();
  });
  document.addEventListener("focusin", (event) => {
    const target = targetOf(event);
    if (target) show(target);
  });
  document.addEventListener("focusout", hide);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hide();
  });
  document.addEventListener("scroll", hide, true);
  document.addEventListener("pointerdown", (event) => {
    const target = targetOf(event);
    if (event.pointerType !== "touch" || !target) {
      hide();
      return;
    }
    clearTimeout(holdTimer);
    holdTimer = setTimeout(() => show(target), HOLD_MS);
  });
  document.addEventListener("pointerup", (event) => {
    if (event.pointerType !== "touch") return;
    clearTimeout(holdTimer);
    if (current) hideTimer = setTimeout(hide, TOUCH_SHOW_MS);
  });
  document.addEventListener("pointercancel", hide);
}
