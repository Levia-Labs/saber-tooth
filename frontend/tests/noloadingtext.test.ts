import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import ts from "typescript";
import { describe, expect, test } from "vitest";

/** Rule: never show "loading x" text; use the animated Spinner or a skeleton with an aria-label. */
const LOADING = /\bloading\b/i;

/** Visible text nodes and string literals rendered as children. Attributes and comments pass. */
export function loadingTextHits(source: string): string[] {
  const file = ts.createSourceFile(
    "x.tsx",
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  const hits: string[] = [];
  const insideAttribute = (node: ts.Node): boolean => {
    for (let n: ts.Node | undefined = node.parent; n; n = n.parent) {
      if (ts.isJsxAttribute(n)) return true;
      if (ts.isJsxElement(n) || ts.isJsxFragment(n)) return false;
    }
    return true;
  };
  const visit = (node: ts.Node): void => {
    if (ts.isJsxText(node) && LOADING.test(node.text)) hits.push(node.text.trim());
    const literal = ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node);
    if (literal && LOADING.test(node.text) && !insideAttribute(node)) hits.push(node.text);
    ts.forEachChild(node, visit);
  };
  visit(file);
  return hits;
}

function sources(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const path = join(dir, e.name);
    if (e.isDirectory()) return sources(path);
    return e.name.endsWith(".tsx") ? [path] : [];
  });
}

describe("loading text matcher", () => {
  test.each([
    "const a = <p>Loading</p>;",
    "const a = <p>Loading playlists.</p>;",
    'const a = <p>{busy ? "Loading matches" : "Done"}</p>;',
    "const a = <p>{`loading x`}</p>;",
    'const a = <span className="sr-only">loading</span>;',
  ])("flags %s", (code) => expect(loadingTextHits(code).length).toBeGreaterThan(0));

  test.each([
    'const a = <Spinner label="Loading matches" />;',
    'const a = <div aria-label="Loading" title={busy ? "Loading" : "Idle"} />;',
    '// Loading comment\nconst a = <img loading="lazy" />;',
    "const a = <p>Downloading</p>;",
    'const a = <p>{busy ? "Done" : "Idle"}</p>;',
  ])("passes %s", (code) => expect(loadingTextHits(code)).toEqual([]));
});

describe("frontend/src", () => {
  test("renders no loading text", () => {
    const root = join(__dirname, "..", "src");
    const bad = sources(root)
      .map((p) => relative(root, p).replaceAll("\\", "/"))
      .filter((rel) => loadingTextHits(readFileSync(join(root, rel), "utf-8")).length > 0);
    expect(bad).toEqual([]);
  });
});
