### Task 8: Docs, build and full gate

**Files:**

- Modify: `README.md` (features list: Jobs tab), `docs/dockerhub.md` (features list: one line for the Jobs tab and the durable queue)
- Modify: `src/saber_tooth/web/` (rebuilt bundle via `task st:web:build`, if the repo commits the built bundle; check `git ls-files src/saber_tooth/web | head -3`)

- [ ] **Step 1: Docs**

README features gain: "Jobs tab: what the server is running, what waits (with cancel) and what finished in the last day; queued jobs survive a restart." The same sentence goes in the features list of `docs/dockerhub.md`. Keep the Docker Hub page under its current length limit (`task st:hub:check` prints the character count; the full description limit is 25000).

- [ ] **Step 2: Build and gate**

Run: `task st:web:build`, then `task st:gate`
Expected: every gate PASS. Fix red gates in their owning file; never lower a baseline.

- [ ] **Step 3: Live check**

Run: `task st:up`, then `task st:smoke`, then `curl -s http://127.0.0.1:8100/api/jobs` (expect JSON with `running`, `queued`, `recent`).
Expected: smoke PASS.

- [ ] **Step 4: Commit**

Main thread commits: `task st:commit -- -m "docs: Jobs tab and durable queue in README and Docker Hub page; rebuilt web bundle" <files>`
