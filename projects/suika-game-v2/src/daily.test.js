import { beforeEach, describe, expect, it } from "vitest";
import {
	buildResultCard,
	computeUpdatedStats,
	DAILY_STATS_KEY,
	daysBetween,
	emptyStats,
	getStatsSummary,
	HISTORY_CAP,
	hasPlayedToday,
	loadDailyStats,
	recordDailyResult,
	saveDailyStats,
} from "./daily.js";

describe("daysBetween", () => {
	it("returns 0 for the same day", () => {
		expect(daysBetween("2026-05-21", "2026-05-21")).toBe(0);
	});

	it("returns 1 for consecutive days", () => {
		expect(daysBetween("2026-05-21", "2026-05-22")).toBe(1);
	});

	it("handles month and year boundaries", () => {
		expect(daysBetween("2026-01-31", "2026-02-01")).toBe(1);
		expect(daysBetween("2026-12-31", "2027-01-01")).toBe(1);
	});

	it("is negative when the second day is earlier", () => {
		expect(daysBetween("2026-05-22", "2026-05-21")).toBe(-1);
	});
});

describe("computeUpdatedStats", () => {
	const result = (over = {}) => ({
		day: "2026-05-21",
		challenge: 141,
		score: 1000,
		topLevel: 5,
		...over,
	});

	it("starts a streak of 1 on the first ever play", () => {
		const next = computeUpdatedStats(emptyStats(), result());
		expect(next.currentStreak).toBe(1);
		expect(next.maxStreak).toBe(1);
		expect(next.gamesPlayed).toBe(1);
		expect(next.bestDailyScore).toBe(1000);
	});

	it("increments the streak on a consecutive day", () => {
		let s = computeUpdatedStats(emptyStats(), result());
		s = computeUpdatedStats(s, result({ day: "2026-05-22", challenge: 142 }));
		expect(s.currentStreak).toBe(2);
		expect(s.maxStreak).toBe(2);
		expect(s.gamesPlayed).toBe(2);
	});

	it("resets the streak to 1 after a missed day", () => {
		let s = computeUpdatedStats(emptyStats(), result());
		s = computeUpdatedStats(s, result({ day: "2026-05-22" }));
		s = computeUpdatedStats(s, result({ day: "2026-05-25", challenge: 145 }));
		expect(s.currentStreak).toBe(1);
		expect(s.maxStreak).toBe(2); // historical max is retained
	});

	it("does not advance the streak when replaying the same day", () => {
		let s = computeUpdatedStats(emptyStats(), result({ score: 800 }));
		s = computeUpdatedStats(s, result({ score: 1500 }));
		expect(s.currentStreak).toBe(1);
		expect(s.gamesPlayed).toBe(1); // replay is not a new game
		expect(s.today.score).toBe(1500); // keeps the better score
		expect(s.bestDailyScore).toBe(1500);
	});

	it("keeps the better score when a same-day replay is worse", () => {
		let s = computeUpdatedStats(emptyStats(), result({ score: 1500 }));
		s = computeUpdatedStats(s, result({ score: 600 }));
		expect(s.today.score).toBe(1500);
	});

	it("does not mutate the previous stats object", () => {
		const prev = emptyStats();
		const snapshot = JSON.stringify(prev);
		computeUpdatedStats(prev, result());
		expect(JSON.stringify(prev)).toBe(snapshot);
	});
});

describe("hasPlayedToday", () => {
	it("is false for fresh stats", () => {
		expect(hasPlayedToday(emptyStats(), "2026-05-21")).toBe(false);
	});

	it("is true once today is recorded", () => {
		const s = computeUpdatedStats(emptyStats(), {
			day: "2026-05-21",
			challenge: 141,
			score: 100,
			topLevel: 2,
		});
		expect(hasPlayedToday(s, "2026-05-21")).toBe(true);
		expect(hasPlayedToday(s, "2026-05-22")).toBe(false);
	});
});

describe("buildResultCard", () => {
	it("includes the challenge number, score and hashtag", () => {
		const card = buildResultCard({
			challenge: 141,
			score: 3420,
			topLevel: 7,
			streak: 5,
		});
		expect(card).toContain("#141");
		expect(card).toContain("3,420");
		expect(card).toContain("#SuikaDaily");
		expect(card).toContain("🔥 5일 연속");
	});

	it("omits the streak line when there is no streak", () => {
		const card = buildResultCard({
			challenge: 1,
			score: 10,
			topLevel: 0,
			streak: 0,
		});
		expect(card).not.toContain("🔥");
	});

	it("renders an 11-slot progress bar", () => {
		const card = buildResultCard({
			challenge: 1,
			score: 10,
			topLevel: 4,
			streak: 0,
		});
		const barLine = card.split("\n").find((l) => l.includes("🟩"));
		const slots = [...barLine].filter((ch) => ch === "🟩" || ch === "⬜");
		expect(slots).toHaveLength(11);
	});

	it("clamps an out-of-range topLevel without throwing", () => {
		expect(() =>
			buildResultCard({
				challenge: 1,
				score: 10,
				topLevel: 999,
				streak: 0,
			}),
		).not.toThrow();
	});
});

describe("localStorage persistence", () => {
	beforeEach(() => {
		localStorage.clear();
	});

	it("returns empty stats when nothing is stored", () => {
		expect(loadDailyStats()).toEqual(emptyStats());
	});

	it("round-trips through save and load", () => {
		const stats = computeUpdatedStats(emptyStats(), {
			day: "2026-05-21",
			challenge: 141,
			score: 999,
			topLevel: 6,
		});
		saveDailyStats(stats);
		expect(loadDailyStats()).toEqual(stats);
	});

	it("recovers from corrupt stored JSON", () => {
		localStorage.setItem(DAILY_STATS_KEY, "{not valid json");
		expect(loadDailyStats()).toEqual(emptyStats());
	});

	it("recordDailyResult persists and returns updated stats", () => {
		const out = recordDailyResult({
			day: "2026-05-21",
			challenge: 141,
			score: 500,
			topLevel: 3,
		});
		expect(out.currentStreak).toBe(1);
		expect(loadDailyStats().today.score).toBe(500);
	});
});

describe("history accumulation", () => {
	const play = (stats, day, challenge, score, topLevel = 3) =>
		computeUpdatedStats(stats, { day, challenge, score, topLevel });

	it("appends one entry per distinct day", () => {
		let s = play(emptyStats(), "2026-05-21", 141, 100);
		s = play(s, "2026-05-22", 142, 200);
		s = play(s, "2026-05-23", 143, 300);
		expect(s.history).toHaveLength(3);
		expect(s.history.map((h) => h.challenge)).toEqual([141, 142, 143]);
	});

	it("updates the same day in place rather than appending", () => {
		let s = play(emptyStats(), "2026-05-21", 141, 100);
		s = play(s, "2026-05-21", 141, 900);
		expect(s.history).toHaveLength(1);
		expect(s.history[0].score).toBe(900);
	});

	it("keeps the better score on a same-day replay", () => {
		let s = play(emptyStats(), "2026-05-21", 141, 900);
		s = play(s, "2026-05-21", 141, 200);
		expect(s.history[0].score).toBe(900);
	});

	it("caps history at HISTORY_CAP entries, keeping the most recent", () => {
		let s = emptyStats();
		for (let i = 0; i < HISTORY_CAP + 15; i++) {
			s = play(s, `day-${i}`, i, i * 10); // synthetic distinct days
		}
		expect(s.history.length).toBe(HISTORY_CAP);
		expect(s.history[s.history.length - 1].challenge).toBe(HISTORY_CAP + 14);
	});

	it("history last entry mirrors today", () => {
		const s = play(emptyStats(), "2026-05-21", 141, 555, 6);
		expect(s.history[s.history.length - 1]).toEqual(s.today);
	});
});

describe("getStatsSummary", () => {
	it("returns zeroed summary for empty stats", () => {
		const sum = getStatsSummary(emptyStats());
		expect(sum).toEqual({
			currentStreak: 0,
			maxStreak: 0,
			gamesPlayed: 0,
			bestDailyScore: 0,
			recent: [],
		});
	});

	it("reports streak, games and best score", () => {
		let s = computeUpdatedStats(emptyStats(), {
			day: "2026-05-21",
			challenge: 141,
			score: 1200,
			topLevel: 5,
		});
		s = computeUpdatedStats(s, {
			day: "2026-05-22",
			challenge: 142,
			score: 800,
			topLevel: 4,
		});
		const sum = getStatsSummary(s);
		expect(sum.currentStreak).toBe(2);
		expect(sum.gamesPlayed).toBe(2);
		expect(sum.bestDailyScore).toBe(1200);
	});

	it("lists recent results newest-first, capped at 7", () => {
		let s = emptyStats();
		for (let i = 0; i < 10; i++) {
			s = computeUpdatedStats(s, {
				day: `day-${i}`,
				challenge: i,
				score: i * 100,
				topLevel: 2,
			});
		}
		const sum = getStatsSummary(s);
		expect(sum.recent).toHaveLength(7);
		expect(sum.recent[0].challenge).toBe(9); // newest first
		expect(sum.recent[6].challenge).toBe(3);
	});
});
