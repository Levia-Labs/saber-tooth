### Task 12 (Lane B): Lightshow applier

**Files:**

- Create: `lightshow/apply.py`, `lightshow/energy.py`
- Test: `tests/test_lightshow_apply.py`

**Interfaces:**

- Consumes: Task 11, Task 6 `onset_density`.
- Produces: `bar_energy(beatmap: Beatmap, timing: Timing, analysis: Analysis | None) -> list[float]`; `choose_environment(t: Templates, seed: int) -> str`; `build_lightshow(beatmap: Beatmap, timing: Timing, t: Templates, analysis: Analysis | None, seed: int, environment: str | None = None) -> ApplyLightshowPayload` where the payload is `(environment, color_scheme, events_per_difficulty)` matching Task 10's `ApplyLightshow` fields.

Atmosphere rules:

1. Energy per bar from analysis onsets, else from note density of the densest difficulty.
2. Sections: 4-bar mean energy; a change of at least 0.25 between consecutive 4-bar blocks starts a new section.
3. Each section picks one donor `source` (consistent style inside a section) with units near the section's energy; inside the section each bar takes the unit from that donor with the closest energy, cycling through a 4-bar motif so phrasing repeats.
4. Section starts with energy > 0.7 get a colour boost on; sections below 0.4 get boost off and only units with energy < 0.5.
5. Final 2 bars fade: only units with energy < 0.3, then all lights off at the last note plus 2 beats.
6. Environment: `environment` argument, else top-3 environments by unit count chosen with `random.Random(seed)`. Colour scheme: a scheme learned from a donor of that environment, else `None`.
7. All events lie within `[0, last_note_beat + 4]` and are sorted; same lightshow for every difficulty.

- [ ] **Step 1: Write failing tests**: events sorted and within song bounds; high-energy section contains a boost-on; environment is a learned one; quiet bars only use low-energy units; deterministic for equal seed.
- [ ] **Steps 2-4:** fail, implement, pass. **Step 5:** Commit `feat: apply energy-driven vanilla lightshows`.
