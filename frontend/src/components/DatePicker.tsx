import * as Popover from "@radix-ui/react-popover";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import {
  addDays,
  addMonths,
  clampDate,
  firstWeekday,
  inRange,
  monthWeeks,
  parseIso,
  sameDay,
  toIso,
} from "../lib/calendar";
import { Icon } from "./icons";

interface Props {
  id: string;
  /** Visible label text, also the accessible name of the trigger and the dialog. */
  label: string;
  /** ISO `YYYY-MM-DD`, or "" for no date. */
  value: string;
  onChange: (value: string) => void;
  min?: string;
  max?: string;
  locale?: string;
}

/** Date after a navigation key, or null when the key is not one. */
function target(key: string, shift: boolean, d: Date, weekStart: number): Date | null {
  const col = (d.getDay() - weekStart + 7) % 7;
  switch (key) {
    case "ArrowLeft":
      return addDays(d, -1);
    case "ArrowRight":
      return addDays(d, 1);
    case "ArrowUp":
      return addDays(d, -7);
    case "ArrowDown":
      return addDays(d, 7);
    case "Home":
      return addDays(d, -col);
    case "End":
      return addDays(d, 6 - col);
    case "PageUp":
      return addMonths(d, shift ? -12 : -1);
    case "PageDown":
      return addMonths(d, shift ? 12 : 1);
    default:
      return null;
  }
}

/** Dependency-free calendar popover: ARIA grid, keyboard navigation, min/max, today and clear. */
export function DatePicker({ id, label, value, onChange, min, max, locale }: Props) {
  const selected = parseIso(value);
  const today = new Date();
  const [open, setOpen] = useState(false);
  const [focus, setFocus] = useState<Date>(selected ?? clampDate(today, min, max));
  const grid = useRef<HTMLDivElement>(null);
  const moved = useRef(false);
  const weekStart = useMemo(() => firstWeekday(locale), [locale]);
  const fmt = (o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat(locale, o);
  const weeks = monthWeeks(focus, weekStart);
  const names = weeks[0]!.map((d) => ({
    long: fmt({ weekday: "long" }).format(d),
    short: fmt({ weekday: "short" }).format(d),
  }));
  const minYear = (min ? parseIso(min) : null)?.getFullYear() ?? today.getFullYear() - 30;
  const maxYear = (max ? parseIso(max) : null)?.getFullYear() ?? today.getFullYear() + 5;
  const years = Array.from({ length: maxYear - minYear + 1 }, (_, i) => minYear + i);
  const go = (d: Date) => {
    moved.current = true;
    setFocus(clampDate(d, min, max));
  };
  const pick = (d: Date | null) => {
    onChange(d ? toIso(d) : "");
    setOpen(false);
  };

  useEffect(() => {
    if (!open || !moved.current) return;
    moved.current = false;
    grid.current?.querySelector<HTMLElement>('button[tabindex="0"]')?.focus();
  }, [open, focus]);

  const onKey = (e: KeyboardEvent) => {
    const next = target(e.key, e.shiftKey, focus, weekStart);
    if (!next) return;
    e.preventDefault();
    go(next);
  };
  const text = selected ? fmt({ dateStyle: "medium" }).format(selected) : "Pick a date";
  const minDate = min ? parseIso(min) : null;
  const maxDate = max ? parseIso(max) : null;
  const todayOk = inRange(today, min, max);

  return (
    <Popover.Root
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (o) setFocus(selected ?? clampDate(new Date(), min, max));
      }}
    >
      <Popover.Trigger
        id={id}
        className="date-trigger"
        aria-label={`${label}: ${selected ? text : "no date"}`}
      >
        <Icon name="calendar" />
        <span className={selected ? "" : "muted"}>{text}</span>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="popover date-pop"
          align="start"
          sideOffset={6}
          collisionPadding={8}
          aria-label={`${label} calendar`}
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            moved.current = true;
            setFocus((f) => new Date(f));
          }}
        >
          <div className="date-head">
            <button
              type="button"
              className="btn icon plain"
              aria-label="Previous month"
              onClick={() => go(addMonths(focus, -1))}
              disabled={
                !!minDate &&
                addDays(new Date(focus.getFullYear(), focus.getMonth(), 1), -1) < minDate
              }
            >
              <Icon name="chevron-left" />
            </button>
            <select
              aria-label="Month"
              value={focus.getMonth()}
              onChange={(e) => go(new Date(focus.getFullYear(), Number(e.target.value), 1))}
            >
              {Array.from({ length: 12 }, (_, m) => (
                <option key={m} value={m}>
                  {fmt({ month: "long" }).format(new Date(2000, m, 1))}
                </option>
              ))}
            </select>
            <select
              aria-label="Year"
              value={focus.getFullYear()}
              onChange={(e) =>
                go(new Date(Number(e.target.value), focus.getMonth(), focus.getDate()))
              }
            >
              {years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn icon plain"
              aria-label="Next month"
              onClick={() => go(addMonths(focus, 1))}
              disabled={
                !!maxDate && new Date(focus.getFullYear(), focus.getMonth() + 1, 1) > maxDate
              }
            >
              <Icon name="chevron-right" />
            </button>
          </div>
          <div
            ref={grid}
            role="grid"
            aria-label={fmt({ month: "long", year: "numeric" }).format(focus)}
            className="date-grid"
          >
            <div role="row" className="date-row">
              {names.map((n) => (
                <span key={n.long} role="columnheader" aria-label={n.long} className="date-dow">
                  {n.short}
                </span>
              ))}
            </div>
            {weeks.map((week) => (
              <div role="row" className="date-row" key={toIso(week[0]!)}>
                {week.map((d) => {
                  const outside = d.getMonth() !== focus.getMonth();
                  const ok = inRange(d, min, max);
                  const isSel = !!selected && sameDay(d, selected);
                  return (
                    <span
                      role="gridcell"
                      key={toIso(d)}
                      aria-selected={isSel}
                      aria-disabled={!ok || undefined}
                    >
                      <button
                        type="button"
                        className={`date-day${outside ? " outside" : ""}${
                          sameDay(d, today) ? " today" : ""
                        }`}
                        tabIndex={sameDay(d, focus) ? 0 : -1}
                        disabled={!ok}
                        aria-label={fmt({ dateStyle: "full" }).format(d)}
                        aria-current={sameDay(d, today) ? "date" : undefined}
                        onKeyDown={onKey}
                        onClick={() => pick(d)}
                      >
                        {d.getDate()}
                      </button>
                    </span>
                  );
                })}
              </div>
            ))}
          </div>
          <div className="date-foot">
            <button
              type="button"
              className="btn plain"
              disabled={!todayOk}
              onClick={() => pick(today)}
            >
              Today
            </button>
            <button
              type="button"
              className="btn plain"
              disabled={!selected}
              onClick={() => pick(null)}
            >
              Clear
            </button>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
