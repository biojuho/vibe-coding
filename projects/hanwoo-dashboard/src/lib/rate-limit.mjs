const store = new Map();

function pruneExpired(now) {
	for (const [key, entry] of store) {
		if (entry.resetAt <= now) {
			store.delete(key);
		}
	}
}

export function checkRateLimit(key, { maxRequests = 5, windowMs = 3600000 } = {}) {
	const now = Date.now();

	if (store.size > 5000) {
		pruneExpired(now);
	}

	const entry = store.get(key);

	if (!entry || entry.resetAt <= now) {
		store.set(key, { count: 1, resetAt: now + windowMs });
		return { allowed: true, remaining: maxRequests - 1 };
	}

	if (entry.count >= maxRequests) {
		const retryAfterSeconds = Math.ceil((entry.resetAt - now) / 1000);
		return { allowed: false, remaining: 0, retryAfterSeconds };
	}

	entry.count += 1;
	return { allowed: true, remaining: maxRequests - entry.count };
}
