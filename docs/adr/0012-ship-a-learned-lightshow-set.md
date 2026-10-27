# 0012 Ship a learned lightshow set

## Context

Lighting templates were learned only when the user pressed Learn, so a fresh install proposed no lighting and the default-environment fixer had nothing to offer. Most users would press Learn first.

## Decision

1. A learned set ships in the package as `src/saber_tooth/lightshow/data/templates.json.gz` (about 1.2 MB gzipped, 52 MB parsed): 20 environments, 10330 one-bar units.
2. The service uses `/data/lightshow.json` when the Learn button has written it, else the bundled file. Learn stays available and replaces the bundled set with the styles of the user's own maps.
3. The set is parsed once per process and parsed again only when the file modification time or size changes.
4. `task st:learn-bundle -- <levels_dir>` regenerates the file reproducibly (gzip mtime 0).
5. `.gitignore` re-includes the data folder, `.gitattributes` marks `*.gz` binary, and the pre-commit large-file limit is raised to 2048 KB for this one path only.

## Consequences

1. Scan, generate and apply light maps out of the box.
2. The set is derived from the lighting of 98 community maps installed on the author's machine. Those maps carry their authors' rights. Publishing this file in a public repository needs a licensing check first (permission or licence terms of the source maps, or a derivation that keeps no recognisable per-map lighting). Until then the repository must stay private.
3. The parsed set holds about 50 MB in memory per process.
4. A change in the learner changes the bundle only when `task st:learn-bundle` is run again.
