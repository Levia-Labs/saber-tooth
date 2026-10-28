# TODO

Add entries with `task todo:add`.

## 2 Flaky backend job-wait in tests/test_api.py _wait (200x50 ms) under load; make the wait event-driven or longer

status: open
class: quality

## 3 Approve all updates the review banner late

status: open
class: bug

After Approve all on a map review, the banner keeps showing 'No fixes approved yet' for about 3 s before Apply approved enables. Seen 2026-10-28 while capturing website screenshots.

## 4 test_round_trip hypothesis deadline flakes

status: open
class: test

Gate run on 2026-10-28 failed once with DeadlineExceeded in test_round_trip (203 ms vs the 200 ms deadline) and passed on rerun. Raise or disable the deadline for that test, or shrink its inputs.
