// Fix rounds, read from the job's progress text "round n of m"; null when the text has none.
const ROUND = /\bround (\d{1,4}) of (\d{1,4})\b/i;

/** "n/m" for a progress text such as "round 2 of 6", or null when the rounds are not known. */
export function roundsText(progress: string | null | undefined): string | null {
  const hit = ROUND.exec(progress ?? "");
  return hit ? `${Number(hit[1])}/${Number(hit[2])}` : null;
}
