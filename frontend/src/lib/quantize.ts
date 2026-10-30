// Toast widths snap up to a multiple of a step so stacked toasts differ only in whole steps.
export const TOAST_STEP_PX = 50;

/** The smallest multiple of `step` that is at least `width`. */
export function quantize(width: number, step: number): number {
  if (!(width > 0) || !(step > 0)) return 0;
  const r = Math.ceil(width / step) * step;
  return r < width ? r + step : r; // guards float rounding of width / step
}
