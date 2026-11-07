export type HistoryChange = {
  field: string;
  label?: string;
  kind?: string;
  before: unknown;
  after: unknown;
};

export type HistoryEntry = {
  id: number;
  action: string;
  details: Record<string, unknown> & { changes?: HistoryChange[] };
};

export type VersionDifference = HistoryChange;

/**
 * Compares the card state immediately after `fromId` with its state after
 * `toId`, using only audit details already authorized by the API.
 */
export function compareHistoryVersions(
  entries: HistoryEntry[],
  fromId: number,
  toId: number,
): VersionDifference[] {
  if (fromId >= toId) return [];
  const fromIndex = entries.findIndex((entry) => entry.id === fromId);
  const toIndex = entries.findIndex((entry) => entry.id === toId);
  if (fromIndex < 0 || toIndex <= fromIndex) return [];

  const net = new Map<string, VersionDifference>();
  for (const entry of entries.slice(fromIndex + 1, toIndex + 1)) {
    const changes = [...(entry.details.changes ?? [])];
    if (
      entry.action === "status_changed" &&
      typeof entry.details.origin === "string" &&
      typeof entry.details.destination === "string"
    ) {
      changes.push({
        field: "status",
        label: "Etapa",
        before: entry.details.origin,
        after: entry.details.destination,
      });
    }

    for (const change of changes) {
      const key = `${change.kind ?? "value"}:${change.field}`;
      const existing = net.get(key);
      net.set(key, {
        ...change,
        before: existing ? existing.before : change.before,
      });
    }
  }

  return [...net.values()].filter(
    (change) => JSON.stringify(change.before) !== JSON.stringify(change.after),
  );
}
