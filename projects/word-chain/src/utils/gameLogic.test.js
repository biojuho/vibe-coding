import { describe, expect, it } from "vitest";
import { koreanWords } from "./dictionary.js";
import { pickAiWord, validateMove } from "./gameLogic.js";

describe("validateMove", () => {
	it("rejects an empty word", () => {
		const r = validateMove("   ", null, []);
		expect(r.ok).toBe(false);
		expect(r.reason).toContain("입력");
	});

	it("rejects a single-character word", () => {
		const r = validateMove("가", null, []);
		expect(r.ok).toBe(false);
		expect(r.reason).toContain("두 글자");
	});

	it("accepts any valid word as the opening move", () => {
		const r = validateMove("사과", null, []);
		expect(r.ok).toBe(true);
		expect(r.word).toBe("사과");
	});

	it("trims surrounding whitespace", () => {
		const r = validateMove("  바나나  ", null, []);
		expect(r.ok).toBe(true);
		expect(r.word).toBe("바나나");
	});

	it("requires the word to start with the last word's final char", () => {
		const bad = validateMove("바나나", "사과", []);
		expect(bad.ok).toBe(false);
		expect(bad.reason).toContain("'과'");

		const good = validateMove("과자", "사과", []);
		expect(good.ok).toBe(true);
	});

	it("rejects an already-used word", () => {
		const r = validateMove("사과", null, ["사과", "과자"]);
		expect(r.ok).toBe(false);
		expect(r.reason).toContain("이미 사용");
	});

	it("accepts a Set of used words", () => {
		const r = validateMove("사과", null, new Set(["포도"]));
		expect(r.ok).toBe(true);
	});
});

describe("pickAiWord", () => {
	it("returns a dictionary word for a known starting char", () => {
		const w = pickAiWord("가", [], () => 0);
		expect(koreanWords["가"]).toContain(w);
	});

	it("continues after the common opening word 사과", () => {
		const w = pickAiWord("과", ["사과"], () => 0);
		expect(w).toBe("과자");
		expect(koreanWords["과"]).toContain(w);
	});

	it("returns null for a char the dictionary cannot continue", () => {
		expect(pickAiWord("뷁", [], () => 0)).toBeNull();
	});

	it("never returns an already-used word", () => {
		const all = koreanWords["가"];
		// use every '가' word except the last one
		const used = all.slice(0, -1);
		const w = pickAiWord("가", used, () => 0);
		expect(w).toBe(all[all.length - 1]);
	});

	it("returns null (gives up) when every candidate is used", () => {
		const w = pickAiWord("가", koreanWords["가"], () => 0);
		expect(w).toBeNull();
	});

	it("is deterministic given a fixed random source", () => {
		const a = pickAiWord("나", [], () => 0.5);
		const b = pickAiWord("나", [], () => 0.5);
		expect(a).toBe(b);
	});

	it("picks within bounds across the random range", () => {
		for (const r of [0, 0.25, 0.5, 0.75, 0.999]) {
			const w = pickAiWord("바", [], () => r);
			expect(koreanWords["바"]).toContain(w);
		}
	});
});
