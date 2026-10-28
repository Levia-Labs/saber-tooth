# Task 14: NpsChart SVG component (part c)

Continues [task-14b.md](task-14b.md).

- [ ] **Step 4: Run to pass**

Run: `npx --prefix frontend vitest run --root frontend tests/cropchart.test.tsx`
Expected: 6 passed.

- [ ] **Step 5: Gates**

Run: `npm --prefix frontend run typecheck`
Expected: no errors.
Run: `npm --prefix frontend run lint`
Expected: no warnings. If `jsx-a11y` rejects pointer handlers on the `role="group"` svg, change that role to `application`; no other change is needed.
Run: `npx --prefix frontend prettier --config .crepidoma/configs/.prettierrc --check frontend/src/components/NpsChart.tsx frontend/src/styles/crop.css frontend/tests/cropchart.test.tsx`
Expected: all files pass; else `--write` on those files only.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: NPS chart with section bands and draggable window edges"` (subagents never commit).

---
