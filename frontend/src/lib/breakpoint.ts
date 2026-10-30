/**
 * The one mobile breakpoint. Below 1300 px the app is in mobile view: the bottom navigation bar,
 * icon-only buttons and tabs, card rows in the lists, the filter sheet, full-width toasts.
 *
 * Every CSS rule of that view uses MOBILE_QUERY verbatim (`@media (max-width: 1299.98px)`), and
 * the desktop-only rules use DESKTOP_QUERY; tests/breakpoint.test.ts keeps the stylesheets in
 * step with this file. Media queries cannot read a variable, so the text is the shared value.
 *
 * VR never enters the mobile view: it keeps the desktop table rows at any size, only bigger. The
 * table tiers (MID_QUERY, COMPACT_QUERY) are what adapts its columns by effective width. Both the
 * stylesheets and `matchMedia` are rewritten by src/vr/scale.ts (see `mediaFor`):
 *
 *   - outside VR the tier queries become MOBILE_QUERY (the tiers are part of the mobile view);
 *   - in VR MOBILE_QUERY never matches, the tiers scale by the UI scale, and DESKTOP_QUERY starts
 *     at 1100 px (the side sheet of the wide and mid tiers).
 */
export const MOBILE_MAX_PX = 1299.98;
export const MOBILE_QUERY = `(max-width: ${MOBILE_MAX_PX}px)`;
export const DESKTOP_QUERY = "(min-width: 1300px)";
/** The table tiers: the old 1279 and 1099 px tiers, spelled apart from the content tiers. */
export const MID_QUERY = "(max-width: 1279.98px)";
export const COMPACT_QUERY = "(max-width: 1099.98px)";
/** DESKTOP_QUERY in VR. */
export const VR_DESKTOP_QUERY = "(min-width: 1100px)";
/** Genuinely tiny phones: the toolbar folds into a kebab menu. */
export const TINY_QUERY = "(max-width: 479px)";

/** The query to evaluate for `query` outside or inside VR; any other query passes through. */
export function mediaFor(query: string, vr: boolean): string {
  const q = query.trim();
  if (vr) {
    if (q === MOBILE_QUERY) return "not all";
    if (q === DESKTOP_QUERY) return VR_DESKTOP_QUERY;
    return query;
  }
  return q === MID_QUERY || q === COMPACT_QUERY ? MOBILE_QUERY : query;
}
