# 0013 Worker processes for parallel jobs

## Context

Jobs ran on one worker thread. Fix and scan are CPU-bound Python, so extra threads would share the GIL and not run in parallel. The user wants to raise the number of concurrent fixing jobs. The `Service` cannot be sent to another process: it holds a SQLite connection, locks and an HTTP client.

## Decision

1. A dispatcher thread claims queued jobs oldest first while fewer than the `max_concurrent_jobs` setting are running, and runs each on its own thread. The setting is read before every claim, so a change applies to jobs started afterwards; running jobs finish.
2. The setting is 1 to the recommended maximum (default 1). The recommended maximum is `min(cores - 1, available memory / 512 MiB)`, at least 1 and at most 16; cores and memory come from the container cgroup limits when set. 512 MiB is the peak of one fix worker (about 310 MiB measured on the fixture maps, with margin for long songs).
3. With a cap above one, the kinds `scan`, `fix` and `relight` run in a spawned worker process (`multiprocessing`, start method `spawn`), one per job. With a cap of one they run in the API process as before, which keeps the warm analysis cache and avoids the spawn cost.
4. The child receives a `ChildSpec` of plain strings (levels, data, database path, analyser URL and uploads path) and rebuilds its own `Service`, `Store` connection and analyser client. SQLite runs in WAL mode with a 30 s busy timeout so the processes can write one file.
5. The parent stays the only writer of job rows. The child sends progress and one final message (done, cancelled, failed) over a pipe; a parent-side thread writes them. Cancel travels the other way through a multiprocessing `Event` that `progress.check()` reads, so a cancelled child stops at its next checkpoint. A child that exits without a final message fails the job with its exit code.
6. Jobs on the same map never run together: a queued job whose map has a running job is skipped and keeps its place. The existing per-kind dedupe stays.
7. Other kinds (downloads, generate, crop, apply, learn) keep running on a thread in the API process.

## Consequences

1. Fix and scan use several cores when the setting is above one.
2. Each child starts cold: the in-memory analysis cache is empty, so the first analysis of an audio file in a child calls the analyser again.
3. Each child imports the service and numeric libraries, about a second of start-up and 300 MiB or more of memory.
4. A restart still fails running jobs; children are daemon processes and end with the API process.
5. The recommended maximum is measured when asked; a saved value is not lowered if memory shrinks later.
