# API

The service listens on `127.0.0.1:${SABER_PORT:-8100}`. There is no authentication; access is limited to localhost.

## Routes

1. `GET /api/maps`: the library, with finding counts per map.
2. `POST /api/maps/{id}/scan`: run the checks on a map and create proposals.
3. `GET /api/maps/{id}/proposals`: proposals for a map, with before and after excerpts.
4. `POST /api/proposals/{id}/approve`: approve one proposal.
5. `POST /api/proposals/{id}/reject`: reject one proposal.
6. `POST /api/maps/{id}/approve-all`: explicit bulk approval of every pending proposal for one map.
7. `POST /api/maps/{id}/apply`: write the approved proposals into the sibling folder `<original name> [saber-tooth]`.
8. `POST /api/generate`: body `{"url": "<youtube url>"}` or a multipart audio file. Starts a job that ends in a `create-map` proposal.
9. `POST /api/lightshow/learn`: rebuild the lightshow template index.
10. `GET /api/jobs/{id}`: job status and error message.

## Proposal states

1. `pending`: created by scan, waiting for a decision.
2. `approved`: accepted, not yet written.
3. `rejected`: declined, never written.
4. `applied`: written into the sibling folder.

## Upstream: beat-analyser

saber-tooth calls these beat-analyser routes server to server on the internal network.

1. `POST /upload`: multipart `file`.
2. `POST /download_yt`: JSON `{"url": "..."}`.
3. `GET /folders`: list project folders.
4. `GET /download/<name>`: download a project.

Project output is read from the shared volume instead; see [ADR 0005](adr/0005-beat-analyser-via-shared-volume.md).
