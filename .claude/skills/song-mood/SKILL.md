---
name: song-mood
description: Map a song's metadata and researched mood to one catalogue environment and a seven-colour palette, then generate the map with that style. Use when asked to style a generated map to its song.
---

# song-mood

1. Metadata: `task st:songmeta -- <audio-or-map>` prints JSON with title, artist, duration and bpm. A null field is unknown; do not guess it.
2. Research: WebSearch `"<artist> <title>" genre mood meaning`, then WebFetch up to three pages (reviews, lyrics commentary, genre pages). Note genre, emotions, imagery and energy. Record each URL used.
3. Catalogue: `task st:environments` prints one line per environment: `name | moods | valence energy intensity | setting | genres | palette`. Pick the environment whose moods and scores sit closest to the song, with genre and setting as tiebreakers. Name the runner-up.
4. Palette: choose seven colours as `#rrggbb` for the roles saber_left, saber_right, env_left, env_right, env_left_boost, env_right_boost, obstacle.
   1. Start from the chosen environment's default palette and shift hue and saturation toward the mood: warm and saturated for joy or anger, cool and muted for sadness or calm, near-neutral with one accent for tension.
   2. Keep saber_left and saber_right far apart in hue; boost colours are lighter variants of the environment colours; obstacle is dark or low-contrast against both sabers.
5. Generate: `task st:gen -- <youtube-url> --environment <Name> --color <role>=<hex> ... --wait`. Roles omitted keep the environment's default. `--wait` prints the job id and then the result JSON with the output folder.
6. Receipt, at most 10 lines: environment, palette, one-line mood match, source URLs, output folder, job id.

Vanilla only: no Chroma, Noodle or Vivify. The generator writes the environment and colour scheme into the vanilla info.dat.
