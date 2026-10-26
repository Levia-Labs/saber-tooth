# saber-tooth v1 Implementation Plan (index)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Docker service (FastAPI API + plain HTML frontend) that generates Beat Saber maps from beat-analyser output, finds and fixes impossible and empty sections, adds missing difficulties and applies learned vanilla lightshows, writing only new map folders after per-change approval.

**Architecture:** One Python package `saber_tooth` with pure cores (`model`, `timing`, `mapio`, `profiles`, `swings`, `checks`, `generator`, `fixer`, `lightshow`) and thin shells (`store`, `analyser`, `jobs`, `api`, `web`, `cli`). Cores never touch the network or the real `CustomLevels`; shells are tested with temp dirs and `httpx.MockTransport`. Compose runs saber-tooth next to the `levialabs/beat-analyser` image with a shared uploads volume.

**Tech Stack:** Python 3.12, uv, FastAPI, uvicorn, httpx, Pillow, pytest, hypothesis, ruff, SQLite (stdlib), ffmpeg (container), vanilla JS, Taskfile, Crepidoma.

**Spec:** `docs/superpowers/specs/2026-10-26-saber-tooth-design.md`

## Global Constraints

1. Vanilla only: never emit Chroma, Noodle Extensions, Vivify, Heck keys, `_requirements` or `_suggestions` entries. Source maps keep theirs untouched only in the copied original files we do not rewrite.
2. Output: difficulty files `version: "3.3.0"`, Info `_version: "2.1.0"`. Standard characteristic only.
3. Every saber-tooth output map has all five Standard difficulties: Easy, Normal, Hard, Expert, ExpertPlus.
4. Never write inside an existing map folder. New folders only, created via `.partial` folder then rename.
5. Fixed-map folder name: `<original folder name> [saber-tooth]`, then `[saber-tooth 2]`, `[saber-tooth 3]` on repeats. Info `_songName` gets suffix ` [saber-tooth]`.
6. Generated-map folder name: `st-<slug> (<Title> - saber-tooth)` with characters `<>:"/\|?*` removed.
7. Quality bar: generated difficulties have zero findings (errors and warnings). Applied fixes leave zero errors and add no new finding.
8. Source files at most 300 lines. Python text I/O passes `encoding="utf-8"`. LF line endings. No em dashes.
9. Tests never read the real `CustomLevels` or call real services.
10. Service binds `127.0.0.1` only; port `${SABER_PORT:-8100}`.

## Review Focus

1. Map folder using lowercase `info.dat` and `ExpertPlusStandard.dat` / `Hard.beatmap.dat` names must load (Task 3 test `test_discovers_mixed_case_names`).
2. Map with BPM changes (v2 `_customData._BPMChanges`, v3 `bpmEvents`) must time notes in seconds correctly so speed rules do not misfire (Task 2 test `test_timing_with_bpm_change`, Task 3 test `test_v2_bpm_changes_loaded`).
3. Applying fixes to the same map twice must create `[saber-tooth 2]`, never overwrite (Task 15 test `test_apply_twice_creates_numbered_folder`).
4. Two approved proposals that together create a new finding must abort apply, write nothing and name the proposals (Task 15 test `test_conflicting_proposals_abort`).
5. Song title with `:`/`?`/`/` must yield a valid folder name (Task 9 test `test_folder_name_sanitized`).

## Execution lanes

Tasks 1-3 run sequentially. Then three parallel lanes on disjoint paths: Lane A (Tasks 4-7), Lane B (Tasks 11-12, needs only Tasks 2-3 and Task 6's `onset_density`, so it starts after Task 6 lands), Lane C (Tasks 13-14). Then Task 8, then Tasks 9 and 10 in parallel, then 15, then 16 and 17 in parallel, then 18.

`write_map` copies audio and cover only when present in `copy_from`; fixtures carry no audio.

## Task files

1. [Task 1: Crepidoma adoption and repo scaffold](task-01.md)
2. [Task 2: Core model and timing](task-02.md)
3. [Task 3: Map IO (read v2/v3/v4, write v3 + Info v2.1) and safe filesystem](task-03.md)
4. [Task 4 (Lane A): Difficulty profiles and swing model](task-04.md)
5. [Task 5 (Lane A): Check rules](task-05.md)
6. [Task 6 (Lane A): Analysis model and empty-gap rule](task-06.md)
7. [Task 7 (Lane A): CLI check, inspect, survey](task-07.md)
8. [Task 8: Tempo map and generator](task-08.md)
9. [Task 9: Map assembly for new songs](task-09.md)
10. [Task 10: Fixer (proposals from findings)](task-10.md)
11. [Task 11 (Lane B): Lightshow learner](task-11.md)
12. [Task 12 (Lane B): Lightshow applier](task-12.md)
13. [Task 13 (Lane C): Store and job worker](task-13.md)
14. [Task 14 (Lane C): beat-analyser client and audio encoding](task-14.md)
15. [Task 15: Service layer (scan, generate, apply)](task-15.md)
16. [Task 16: HTTP API and CLI gen-url](task-16.md)
17. [Task 17: Frontend](task-17.md)
18. [Task 18: Docker, compose, final docs](task-18.md)
