// Shared button builders: icon plus label, tooltip text, optional job locking.
import { el, jobButton } from "./util.js";
import { icon } from "./icons.js";

/**
 * Button or link with an icon. Label is read by screen readers; it is visible when text is true.
 * props.href makes a real link; props.job makes a job button that locks while a job runs.
 */
export function actionButton({ name, label, tip, text = false, href, job = false, ...rest }) {
  const kids = [icon(name), el("span", { class: text ? "" : "sr" }, label)];
  const base = { ...rest, "data-tip": tip };
  if (href) return el("a", { ...base, href, class: `btn ${rest.class || ""}`.trim() }, kids);
  const props = { type: "button", ...base, class: `btn ${rest.class || ""}`.trim() };
  return job ? jobButton(props, kids) : el("button", props, kids);
}
