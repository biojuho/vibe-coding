import { describe, expect, it } from "vitest";
import {
	createRng,
	dailyChallengeNumber,
	dailySeedString,
	gameRandom,
	getActiveSeedLabel,
	mulberry32,
	seedGameplayRng,
	xmur3,
} from "./prng.js";

// The expected values below are the *actual* outputs of the algorithms.
// If they ever change, the daily challenge is no longer reproducible -
// that would silently break fairness, so these tests are the contract.

describe("xmur3", () => {
	it("is deterministic for a given string", () => {
		expect(xmur3("abc")()).toBe(1792905582);
		expect(xmur3("abc")()).toBe(xmur3("abc")());
	});

	it("produces different hashes for different strings", () => {
		expect(xmur3("abc")()).not.toBe(xmur3("abd")());
	});

	it("always returns 32-bit unsigned integers", () => {
		const next = xmur3("seed");
		for (let i = 0; i < 50; i++) {
			const v = next();
			expect(Number.isInteger(v)).toBe(true);
			expect(v).toBeGreaterThanOrEqual(0);
			expect(v).toBeLessThanOrEqual(0xffffffff);
		}
	});
});

describe("mulberry32", () => {
	it("reproduces a known sequence for a fixed seed", () => {
		const rng = mulberry32(12345);
		expect(rng()).toBeCloseTo(0.9797282678, 9);
		expect(rng()).toBeCloseTo(0.3067522645, 9);
		expect(rng()).toBeCloseTo(0.4842054215, 9);
	});

	it("only ever returns floats in [0, 1)", () => {
		const rng = mulberry32(1);
		for (let i = 0; i < 1000; i++) {
			const v = rng();
			expect(v).toBeGreaterThanOrEqual(0);
			expect(v).toBeLessThan(1);
		}
	});
});

describe("createRng", () => {
	it("reproduces a known sequence for a string seed", () => {
		const rng = createRng("suika-test");
		const seq = [rng.next(), rng.next(), rng.next(), rng.next(), rng.next()];
		expect(seq.map((v) => +v.toFixed(10))).toEqual([
			0.5813032535, 0.0593393347, 0.6709457692, 0.5453270772, 0.0959595039,
		]);
	});

	it("two generators with the same seed are identical", () => {
		const a = createRng("replay");
		const b = createRng("replay");
		for (let i = 0; i < 100; i++) {
			expect(a.next()).toBe(b.next());
		}
	});

	it("numeric and string seeds both work", () => {
		expect(createRng(42).next()).toBe(createRng(42).next());
		expect(typeof createRng("x").next()).toBe("number");
	});

	it("int() yields inclusive integers within range", () => {
		const rng = createRng("x");
		const out = [];
		for (let i = 0; i < 8; i++) out.push(rng.int(0, 4));
		expect(out).toEqual([2, 2, 1, 3, 4, 1, 3, 0]);
		for (const v of out) {
			expect(v).toBeGreaterThanOrEqual(0);
			expect(v).toBeLessThanOrEqual(4);
		}
	});
});

describe("gameplay singleton stream", () => {
	it("reseeding reproduces the same sequence", () => {
		seedGameplayRng("2026-05-21");
		const first = [gameRandom(), gameRandom(), gameRandom()];
		seedGameplayRng("2026-05-21");
		const second = [gameRandom(), gameRandom(), gameRandom()];
		expect(second).toEqual(first);
	});

	it("matches the recorded daily-seed sequence", () => {
		seedGameplayRng("2026-05-21");
		const seq = [gameRandom(), gameRandom(), gameRandom()];
		expect(seq.map((v) => +v.toFixed(10))).toEqual([
			0.9516146453, 0.8753749637, 0.3527338661,
		]);
	});

	it("different seeds diverge", () => {
		seedGameplayRng("day-a");
		const a = gameRandom();
		seedGameplayRng("day-b");
		const b = gameRandom();
		expect(a).not.toBe(b);
	});

	it("exposes the active seed label", () => {
		seedGameplayRng("label-check");
		expect(getActiveSeedLabel()).toBe("label-check");
	});
});

describe("daily challenge identity", () => {
	it("formats UTC calendar days, ignoring time-of-day", () => {
		expect(dailySeedString(new Date(Date.UTC(2026, 4, 21, 3, 0, 0)))).toBe(
			"2026-05-21",
		);
		expect(dailySeedString(new Date(Date.UTC(2026, 4, 21, 23, 59, 0)))).toBe(
			"2026-05-21",
		);
	});

	it("zero-pads months and days", () => {
		expect(dailySeedString(new Date(Date.UTC(2026, 0, 3)))).toBe("2026-01-03");
	});

	it("numbers the epoch day as challenge #1", () => {
		expect(dailyChallengeNumber(new Date(Date.UTC(2026, 0, 1)))).toBe(1);
	});

	it("increments by one per calendar day", () => {
		expect(dailyChallengeNumber(new Date(Date.UTC(2026, 0, 2)))).toBe(2);
		expect(dailyChallengeNumber(new Date(Date.UTC(2026, 4, 21)))).toBe(141);
	});
});
