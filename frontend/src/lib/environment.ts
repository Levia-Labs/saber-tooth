// Display names for environments; filter values and API calls keep the raw names.

/** "BigMirrorEnvironment" -> "Big Mirror", "KDAEnvironment" -> "KDA", "Origins" -> "Origins". */
export function formatEnvironment(name: string): string {
  const stripped = name.replace(/Environment$/, "");
  const base = stripped.trim() === "" ? name : stripped;
  return base
    .replace(/_+/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim();
}
