function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function parseCattleHistoryMetadata(metadata) {
  if (metadata === null || metadata === undefined || metadata === '') {
    return {
      metadata: null,
      metadataParseError: false,
      metadataRaw: metadata ?? null,
    };
  }

  if (typeof metadata === 'object') {
    return {
      metadata,
      metadataParseError: false,
      metadataRaw: null,
    };
  }

  if (typeof metadata !== 'string') {
    return {
      metadata: null,
      metadataParseError: true,
      metadataRaw: String(metadata),
    };
  }

  try {
    return {
      metadata: JSON.parse(metadata),
      metadataParseError: false,
      metadataRaw: null,
    };
  } catch {
    return {
      metadata: null,
      metadataParseError: true,
      metadataRaw: metadata,
    };
  }
}

export function normalizeCattleHistoryRows(rows = []) {
  return rows.map((row) => {
    const parsed = parseCattleHistoryMetadata(row?.metadata);

    return {
      ...row,
      metadata: parsed.metadata,
      metadataParseError: parsed.metadataParseError,
      metadataRaw: parsed.metadataRaw,
    };
  });
}

export function extractWeightHistoryPoints(history = []) {
  return history
    .filter((entry) => entry?.eventType === 'weight' && isRecord(entry.metadata))
    .map((entry) => {
      const nextWeight = Number(
        entry.metadata.newWeight ??
          entry.metadata.weight ??
          entry.metadata.to ??
          entry.metadata.after ??
          entry.metadata.currentWeight,
      );

      if (!Number.isFinite(nextWeight)) {
        return null;
      }

      return {
        eventDate: entry.eventDate,
        weight: nextWeight,
      };
    })
    .filter(Boolean);
}
