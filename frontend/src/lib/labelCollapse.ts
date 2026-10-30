/**
 * Overflow-driven button labels. A row of buttons shows every label while it fits on one line;
 * when it does not, labels collapse to icon-only one button at a time (the last button first, the
 * primary one last) until it fits, and come back when the room does. The label text stays in the
 * DOM as the button's name; `data-collapsed` on the label span is what the stylesheet hides.
 *
 * There is no width rule: the row is measured. Each pass expands every label, then collapses until
 * the row fits, so the result depends on the room alone and not on the state the last pass left.
 * That is also why the resize of the row itself, when its collapse shrinks it, settles in one
 * extra pass. A tolerance of `FIT_SLACK_PX` absorbs sub-pixel rounding.
 */
export const LABEL_SELECTOR = ".label-collapsible";
export const ROW_SELECTOR = "[data-label-row]";
export const FIT_SLACK_PX = 2;

/** True when the row's content overflows its width or wraps to a second line. */
export function overflows(row: HTMLElement): boolean {
  if (row.scrollWidth > row.clientWidth + FIT_SLACK_PX) return true;
  const kids = Array.from(row.children) as HTMLElement[];
  const first = kids[0];
  return first !== undefined && kids.some((k) => Math.abs(k.offsetTop - first.offsetTop) > 4);
}

/** The labels of a row, in the order they collapse: primary buttons last, otherwise last first. */
export function collapseOrder(row: HTMLElement): HTMLElement[] {
  const labels = Array.from(row.querySelectorAll<HTMLElement>(LABEL_SELECTOR)).filter(
    (l) => !l.closest(".keep-label"),
  );
  const primary = (l: HTMLElement) => (l.closest(".btn.primary, [data-label-primary]") ? 1 : 0);
  return labels
    .map((label, at) => ({ label, at }))
    .sort((a, b) => primary(a.label) - primary(b.label) || b.at - a.at)
    .map((x) => x.label);
}

/** Expand every label of the row, then collapse in order until it fits. Returns how many collapsed. */
export function fitRow(row: HTMLElement): number {
  const order = collapseOrder(row);
  for (const l of order) l.removeAttribute("data-collapsed");
  let n = 0;
  while (n < order.length && overflows(row)) {
    order[n]!.setAttribute("data-collapsed", "");
    n++;
  }
  return n;
}

/** The row a label belongs to: the marked ancestor, else the button's parent (past a Tip wrapper). */
export function rowOf(label: HTMLElement): HTMLElement | null {
  const marked = label.closest<HTMLElement>(ROW_SELECTOR);
  if (marked) return marked;
  let el = label.parentElement?.parentElement ?? null;
  while (el?.classList.contains("tip-wrap")) el = el.parentElement;
  return el;
}

/**
 * Keep every row of the document fitted: observes the rows with a ResizeObserver and rescans when
 * the DOM changes (a label added, a count in a label changing). Returns the teardown.
 */
export function installLabelCollapse(root: HTMLElement = document.body): () => void {
  const rows = new Set<HTMLElement>();
  const observer = new ResizeObserver((entries) => {
    for (const e of entries) if (rows.has(e.target as HTMLElement)) fitRow(e.target as HTMLElement);
  });
  let frame = 0;
  const scan = () => {
    frame = 0;
    const found = new Set<HTMLElement>();
    for (const label of Array.from(root.querySelectorAll<HTMLElement>(LABEL_SELECTOR))) {
      const row = rowOf(label);
      if (row) found.add(row);
    }
    for (const row of found) {
      if (!rows.has(row)) {
        rows.add(row);
        observer.observe(row);
      }
      fitRow(row);
    }
    for (const row of Array.from(rows)) {
      if (!found.has(row)) {
        rows.delete(row);
        observer.unobserve(row);
      }
    }
  };
  const later = () => {
    if (!frame) frame = requestAnimationFrame(scan);
  };
  const mutations = new MutationObserver(later);
  mutations.observe(root, { childList: true, subtree: true, characterData: true });
  window.addEventListener("resize", later);
  scan();
  return () => {
    mutations.disconnect();
    observer.disconnect();
    window.removeEventListener("resize", later);
    if (frame) cancelAnimationFrame(frame);
  };
}
