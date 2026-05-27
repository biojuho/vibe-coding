function isRecord(value) {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function parseCattleHistoryMetadata(metadata) {
	if (metadata === null || metadata === undefined || metadata === "") {
		return {
			metadata: null,
			metadataParseError: false,
			metadataRaw: metadata ?? null,
		};
	}

	if (typeof metadata === "object") {
		return {
			metadata,
			metadataParseError: false,
			metadataRaw: null,
		};
	}

	if (typeof metadata !== "string") {
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
	if (!Array.isArray(rows)) {
		return [];
	}

	return rows.filter(isRecord).map((row) => {
		const parsed = parseCattleHistoryMetadata(row?.metadata);

		return {
			...row,
			metadata: parsed.metadata,
			metadataParseError: parsed.metadataParseError,
			metadataRaw: parsed.metadataRaw,
		};
	});
}

function toPositiveWeightOrNull(value) {
	if (value === null || value === undefined || value === "") {
		return null;
	}

	const weight = Number(value);
	return Number.isFinite(weight) && weight > 0 ? weight : null;
}

export function extractWeightHistoryPoints(history = []) {
	if (!Array.isArray(history)) {
		return [];
	}

	return history
		.filter(
			(entry) => entry?.eventType === "weight" && isRecord(entry.metadata),
		)
		.map((entry) => {
			const nextWeight = toPositiveWeightOrNull(
				entry.metadata.newWeight ??
					entry.metadata.weight ??
					entry.metadata.to ??
					entry.metadata.after ??
					entry.metadata.currentWeight,
			);

			if (nextWeight === null) {
				return null;
			}

			return {
				eventDate: entry.eventDate,
				weight: nextWeight,
			};
		})
		.filter(Boolean);
}
