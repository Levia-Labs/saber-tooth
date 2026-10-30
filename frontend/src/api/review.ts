import type { QueryClient } from "@tanstack/react-query";
import { keys } from "./queries";
import type { Proposal } from "./types";

type Status = Proposal["status"];

/**
 * Writes a decision into the cached proposal list in the same render as the click, runs the
 * request, rolls the list back if it fails, then refetches the proposals and the map together.
 * The banner and the toolbar read the same cached list as the cards, so none of them lags.
 */
export async function decideOptimistically<T>(
  client: QueryClient,
  mapId: string,
  change: (list: Proposal[]) => Proposal[],
  request: () => Promise<T>,
): Promise<T> {
  const key = keys.proposals(mapId);
  await client.cancelQueries({ queryKey: key });
  const previous = client.getQueryData<Proposal[]>(key);
  if (previous) client.setQueryData<Proposal[]>(key, change(previous));
  try {
    const out = await request();
    void client.invalidateQueries({ queryKey: keys.map(mapId) });
    void client.invalidateQueries({ queryKey: ["maps", "library"] });
    await client.invalidateQueries({ queryKey: key });
    return out;
  } catch (err) {
    if (previous) client.setQueryData<Proposal[]>(key, previous);
    void client.invalidateQueries({ queryKey: key });
    throw err;
  }
}

export const setStatus =
  (id: number | string, to: Status) =>
  (list: Proposal[]): Proposal[] =>
    list.map((p) => (String(p.id) === String(id) ? { ...p, status: to } : p));

export const approvePending = (list: Proposal[]): Proposal[] =>
  list.map((p) => (p.status === "pending" ? { ...p, status: "approved" } : p));
