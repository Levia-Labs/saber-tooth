// Pure state for the announcement banners: reduce by key, cap, expiry.
import type { AlertVariant } from "./alerts";

export type AnnounceVariant = "progress" | AlertVariant;

export interface AnnounceInput {
  /** Banners with the same key replace each other; defaults to the title. */
  key?: string;
  variant: AnnounceVariant;
  title: string;
  message?: string;
}

export interface Banner {
  key: string;
  variant: AnnounceVariant;
  title: string;
  message?: string;
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
  const ms = ttl(input.variant);
  const banner: Banner = {
    key,
    variant: input.variant,
    title: input.title,
    expiresAt: ms === null ? null : now + ms,
  };
  if (input.message !== undefined) banner.message = input.message;
  const at = list.findIndex((b) => b.key === key);
  const next = at === -1 ? [...list, banner] : list.map((b, i) => (i === at ? banner : b));
  return next.slice(-MAX_BANNERS);
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
