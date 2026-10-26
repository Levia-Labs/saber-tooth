# 0005 beat-analyser integration through a shared volume

## Context

beat-analyser is a separate Flask container. It downloads YouTube audio or accepts an upload, and stores each project in `/app/uploads/<name>/` with `audio.wav`, `meta.json` (`name`, `key`, `bpm`), `labels.json` and header-less CSVs (`time,label_id`): `beats`, `kick`, `snare`, `hh`, `bass`, `melody`, `chords`. It rejects POSTs with a foreign `Origin` header. Server-to-server calls send no `Origin`.

## Decision

1. saber-tooth calls `POST /upload` and `POST /download_yt` on the internal network. beat-analyser has no published port.
2. The named volume `analyser-uploads` is mounted at `/app/uploads` in beat-analyser and read-only at `/analyser` in saber-tooth.
3. saber-tooth reads the project folder (audio and CSVs) from that volume instead of downloading results over HTTP.
4. `audio.wav` is converted to `song.egg` with ffmpeg.

## Consequences

1. No large transfers over HTTP and no extra parsing of an export format.
2. saber-tooth depends on the folder layout of beat-analyser. A layout change there breaks the reader.
3. saber-tooth cannot modify analyser data because the mount is read-only.
4. A job fails with the upstream message when beat-analyser is unreachable or returns an error.
