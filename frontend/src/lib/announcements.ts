// Pure state for the announcement banners: reduce by key, cap, expiry.
import type { IconName } from "../components/icons";
import type { AlertSpec, AlertVariant } from "./alerts";

export type AnnounceVariant = "progress" | AlertVariant;

export interface AnnounceInput {
  /** Banners with the same key replace each other; defaults to the title. */
  key?: string;
  variant: AnnounceVariant;
  title: string;
  message?: string;
  /** A link shown under the message, for example "Open map". */
  link?: BannerLink;
  /** Buttons shown under the message; pressing one runs it and closes the toast. */
  actions?: BannerAction[];
  /** Folded-away extras: raw error text, ids, per-map results. */
  details?: string[];
  /** Info and success stay until dismissed instead of fading after a few seconds. */
  sticky?: boolean;
  /** Runs when the toast's close button is pressed. */
  onDismiss?: () => void;
  /** Makes the toast one row whose body runs this on click; the close button only closes. */
  onOpen?: () => void;
  /** Fix rounds "x/y", shown in the one-row layout only when known. */
  rounds?: string;
}

export interface BannerAction {
  label: string;
  onClick: () => void;
  /** Icon shown before the label. */
  icon?: IconName;
  disabled?: boolean;
  /** Keep the toast open after the press; its owner replaces it with the next state. */
  keepOpen?: boolean;
}

export interface BannerLink {
  to: string;
  label: string;
}

export interface Banner {
  key: string;
  variant: AnnounceVariant;
  title: string;
  message?: string;
  link?: BannerLink;
  actions?: BannerAction[];
  details?: string[];
  onDismiss?: () => void;
  onOpen?: () => void;
  rounds?: string;
  /** Epoch ms at which the banner goes away, or null when it stays until dismissed. */
  expiresAt: number | null;
}

export const MAX_BANNERS = 4;
export const AUTO_DISMISS_MS = 5000;

/** Success and info fade on their own; progress ends by replacement; warning and danger stay. */
export function ttl(variant: AnnounceVariant): number | null {
  return variant === "success" || variant === "info" ? AUTO_DISMISS_MS : null;
}

/** Upper-cases the first letter, so job statuses read as banner messages. */
export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Adds or replaces (in place) the banner for the input's key; drops the oldest beyond the cap. */
export function addBanner(list: Banner[], input: AnnounceInput, now: number): Banner[] {
  const key = input.key ?? input.title;
  const ms = input.sticky ? null : ttl(input.variant);
  const banner: Banner = {
    key,
    variant: input.variant,
    title: input.title,
    expiresAt: ms === null ? null : now + ms,
  };
  if (input.message !== undefined) banner.message = input.message;
  if (input.link !== undefined) banner.link = input.link;
  if (input.actions !== undefined) banner.actions = input.actions;
  if (input.details !== undefined) banner.details = input.details;
  if (input.onDismiss !== undefined) banner.onDismiss = input.onDismiss;
  if (input.onOpen !== undefined) banner.onOpen = input.onOpen;
  if (input.rounds !== undefined) banner.rounds = input.rounds;
  const at = list.findIndex((b) => b.key === key);
  const next = at === -1 ? [...list, banner] : list.map((b, i) => (i === at ? banner : b));
  return trim(next, key);
}

/** Whether a toast can only be closed by the user: danger, or anything without an expiry. */
function lingers(b: Banner): boolean {
  return b.variant === "danger" || (b.variant !== "progress" && b.expiresAt === null);
}

/** Over the cap, drops the oldest toast that fades or is progress, then non-danger, then any; never the new one. */
function trim(list: Banner[], newest: string): Banner[] {
  const out = [...list];
  const tiers: ((b: Banner) => boolean)[] = [
    (b) => !lingers(b),
    (b) => b.variant !== "danger",
    () => true,
  ];
  while (out.length > MAX_BANNERS) {
    for (const test of tiers) {
      const at = out.findIndex((b) => b.key !== newest && test(b));
      if (at !== -1) {
        out.splice(at, 1);
        break;
      }
    }
  }
  return out;
}

/** Turns an alert spec into a toast; its action button appears only when the page supplies the handler. */
export function specToInput(
  key: string,
  spec: AlertSpec,
  handlers: { onRetry?: (() => void) | undefined; onReview?: (() => void) | undefined } = {},
): AnnounceInput {
  const input: AnnounceInput = {
    key,
    variant: spec.variant,
    title: spec.title,
    message: spec.message,
  };
  if (spec.details) input.details = spec.details;
  const handler = spec.action
    ? handlers[spec.action.kind === "retry" ? "onRetry" : "onReview"]
    : undefined;
  if (spec.action && handler) input.actions = [{ label: spec.action.label, onClick: handler }];
  return input;
}

export function dismissBanner(list: Banner[], key: string): Banner[] {
  return list.filter((b) => b.key !== key);
}

/** Removes banners whose expiry has passed. */
export function expireBanners(list: Banner[], now: number): Banner[] {
  const kept = list.filter((b) => b.expiresAt === null || b.expiresAt > now);
  return kept.length === list.length ? list : kept;
}

/** Earliest pending expiry, or null when nothing will expire. */
export function nextExpiry(list: Banner[]): number | null {
  const times = list.flatMap((b) => (b.expiresAt === null ? [] : [b.expiresAt]));
  return times.length === 0 ? null : Math.min(...times);
}

/** The keyed result toast for a finished batch: success, warning when some failed, danger when all did. */
export function batchSummary(
  key: string,
  t: { installed: number; skipped: number; failed: number },
  reasons: string[],
): AnnounceInput {
  const variant: AnnounceVariant =
    t.failed === 0 ? "success" : t.installed + t.skipped === 0 ? "danger" : "warning";
  const counts = `Installed ${t.installed}, skipped ${t.skipped}, failed ${t.failed}.`;
  return {
    key,
    variant,
    title: key,
    message: reasons.length ? `${counts} ${reasons.join("; ")}` : counts,
  };
}
