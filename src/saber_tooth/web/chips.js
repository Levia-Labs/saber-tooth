// Status chips, difficulty pips and cover images for map rows and the map page.
import { icon } from "./icons.js";

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

/** Chip text for a map item: counts for error and warn, fixed words otherwise. */
export function statusLabel(item) {
  switch (item.status) {
    case "error":
      return plural(item.errors, "error");
    case "warn":
      return plural(item.warnings, "warning");
    case "ok":
      return "All good";
    case "unreadable":
      return "Unreadable";
    default:
      return "Not scanned";
  }
}

const ICONS = {
  error: "error",
  warn: "warning",
  ok: "ok",
  unscanned: "unscanned",
  unreadable: "unreadable",
};

export function statusKind(status) {
  return Object.hasOwn(ICONS, status) ? status : "unscanned";
}

const SHORT = { Easy: "E", Normal: "N", Hard: "H", Expert: "Ex", ExpertPlus: "Ex+" };

/** Short pip text for a difficulty name. */
export function pipLabel(name) {
  return SHORT[name] || String(name).slice(0, 2);
}

export function statusChip(item) {
  const kind = statusKind(item.status);
  const chip = document.createElement("span");
  chip.className = `chip chip-${kind}`;
  const text = document.createElement("span");
  text.textContent = statusLabel(item);
  chip.append(icon(ICONS[kind]), text);
  return chip;
}

export function pips(names) {
  const box = document.createElement("span");
  box.className = "pips";
  if (!names || !names.length) return box;
  box.setAttribute("aria-label", `Difficulties: ${names.join(", ")}`);
  for (const name of names) {
    const pip = document.createElement("span");
    pip.className = "pip";
    pip.setAttribute("aria-hidden", "true");
    pip.textContent = pipLabel(name);
    box.append(pip);
  }
  return box;
}

function placeholder() {
  const box = document.createElement("span");
  box.className = "cover cover-empty";
  box.append(icon("logo"));
  return box;
}

/** Cover image from the item's cover_url, falling back to the tinted logo mark. */
export function cover(item, big = false) {
  if (!item.cover_url) {
    const empty = placeholder();
    if (big) empty.classList.add("cover-big");
    return empty;
  }
  const img = document.createElement("img");
  img.className = big ? "cover cover-big" : "cover";
  img.alt = "";
  img.loading = "lazy";
  img.decoding = "async";
  img.src = item.cover_url;
  img.addEventListener("error", () => {
    const empty = placeholder();
    if (big) empty.classList.add("cover-big");
    img.replaceWith(empty);
  });
  return img;
}
