// Toast widths snap up to a multiple of a step so stacked toasts differ only in whole steps.
export const TOAST_STEP_PX = 50;

/** The smallest multiple of `step` that is at least `width`. */
export function quantize(width: number, step: number): number {
  if (!(width > 0) || !(step > 0)) return 0;
  const r = Math.ceil(width / step) * step;
  return r < width ? r + step : r; // guards float rounding of width / step
}

/** The toast width: content snapped up to a step, never below `floor`, never above `cap`. */
export function quantizeToast(content: number, step: number, floor: number, cap: number): number {
  const snapped = quantize(Math.max(content, floor), step);
  return Math.floor(Math.min(snapped, cap) / step) * step;
}

export const TOAST_FLOOR_PX = 650;
