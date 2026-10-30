"""Handlers a spawned worker process rebuilds by name; importable from the child."""

import os
import time


def _pid(args, progress):
    return {"pid": os.getpid()}


def _spin(args, progress):
    """Report progress and wait until cancelled, checking each pass."""
    progress("spinning")
    while True:
        progress.check()
        time.sleep(0.02)


def _boom(args, progress):
    raise ValueError("kaput")


def _die(args, progress):
    os._exit(3)


def _steps(args, progress):
    for n in range(3):
        progress(f"step {n}")
    return {"steps": 3, "map_id": args.get("map_id")}


def _hold(args, progress):
    """Take a while so two overlapping jobs are observable."""
    start = time.time()
    time.sleep(args.get("seconds", 0.6))
    return {"pid": os.getpid(), "start": start}


def handlers():
    return {
        "pid": _pid,
        "spin": _spin,
        "boom": _boom,
        "die": _die,
        "steps": _steps,
        "hold": _hold,
    }
