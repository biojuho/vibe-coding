// Minimal in-memory sliding-window rate limiter. This dashboard is single
// instance / local-first (no Redis), so an in-process map keyed by client IP is
// sufficient and intentionally best-effort. The clock is injectable so the
// behaviour is deterministically testable.

export interface RateLimitResult {
	allowed: boolean;
	remaining: number;
	retryAfterSec: number;
}

interface Bucket {
	hits: number[];
}

export class SlidingWindowRateLimiter {
	private readonly limit: number;
	private readonly windowMs: number;
	private readonly now: () => number;
	private readonly buckets = new Map<string, Bucket>();

	constructor(options: {
		limit: number;
		windowMs: number;
		now?: () => number;
	}) {
		this.limit = options.limit;
		this.windowMs = options.windowMs;
		this.now = options.now ?? Date.now;
	}

	// Records an attempt for `key` and reports whether it is within the window
	// budget. Old timestamps outside the window are evicted lazily on access.
	check(key: string): RateLimitResult {
		const current = this.now();
		const cutoff = current - this.windowMs;
		const bucket = this.buckets.get(key) ?? { hits: [] };

		bucket.hits = bucket.hits.filter((ts) => ts > cutoff);

		if (bucket.hits.length >= this.limit) {
			const oldest = bucket.hits[0];
			const retryAfterMs = oldest + this.windowMs - current;
			this.buckets.set(key, bucket);
			return {
				allowed: false,
				remaining: 0,
				retryAfterSec: Math.max(1, Math.ceil(retryAfterMs / 1000)),
			};
		}

		bucket.hits.push(current);
		this.buckets.set(key, bucket);
		return {
			allowed: true,
			remaining: this.limit - bucket.hits.length,
			retryAfterSec: 0,
		};
	}

	// Clears the recorded attempts for a key — call on a successful login so a
	// legitimate user is not penalised for earlier typos.
	reset(key: string) {
		this.buckets.delete(key);
	}
}

// Derives a best-effort client identifier from proxy headers, falling back to a
// shared bucket when no IP can be determined.
export function clientIpFromHeaders(headers: Headers): string {
	const forwarded = headers.get("x-forwarded-for");
	if (forwarded) {
		const first = forwarded.split(",")[0]?.trim();
		if (first) {
			return first;
		}
	}

	return headers.get("x-real-ip")?.trim() || "unknown";
}
