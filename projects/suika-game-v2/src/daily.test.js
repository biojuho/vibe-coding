import { describe, it, expect, beforeEach } from 'vitest';
import {
    emptyStats,
    daysBetween,
    computeUpdatedStats,
    hasPlayedToday,
    buildResultCard,
    loadDailyStats,
    saveDailyStats,
    recordDailyResult,
    DAILY_STATS_KEY,
} from './daily.js';

describe('daysBetween', () => {
    it('returns 0 for the same day', () => {
        expect(daysBetween('2026-05-21', '2026-05-21')).toBe(0);
    });

    it('returns 1 for consecutive days', () => {
        expect(daysBetween('2026-05-21', '2026-05-22')).toBe(1);
    });

    it('handles month and year boundaries', () => {
        expect(daysBetween('2026-01-31', '2026-02-01')).toBe(1);
        expect(daysBetween('2026-12-31', '2027-01-01')).toBe(1);
    });

    it('is negative when the second day is earlier', () => {
        expect(daysBetween('2026-05-22', '2026-05-21')).toBe(-1);
    });
});

describe('computeUpdatedStats', () => {
    const result = (over = {}) => ({
        day: '2026-05-21',
        challenge: 141,
        score: 1000,
        topLevel: 5,
        ...over,
    });

    it('starts a streak of 1 on the first ever play', () => {
        const next = computeUpdatedStats(emptyStats(), result());
        expect(next.currentStreak).toBe(1);
        expect(next.maxStreak).toBe(1);
        expect(next.gamesPlayed).toBe(1);
        expect(next.bestDailyScore).toBe(1000);
    });

    it('increments the streak on a consecutive day', () => {
        let s = computeUpdatedStats(emptyStats(), result());
        s = computeUpdatedStats(
            s,
            result({ day: '2026-05-22', challenge: 142 }),
        );
        expect(s.currentStreak).toBe(2);
        expect(s.maxStreak).toBe(2);
        expect(s.gamesPlayed).toBe(2);
    });

    it('resets the streak to 1 after a missed day', () => {
        let s = computeUpdatedStats(emptyStats(), result());
        s = computeUpdatedStats(s, result({ day: '2026-05-22' }));
        s = computeUpdatedStats(
            s,
            result({ day: '2026-05-25', challenge: 145 }),
        );
        expect(s.currentStreak).toBe(1);
        expect(s.maxStreak).toBe(2); // historical max is retained
    });

    it('does not advance the streak when replaying the same day', () => {
        let s = computeUpdatedStats(emptyStats(), result({ score: 800 }));
        s = computeUpdatedStats(s, result({ score: 1500 }));
        expect(s.currentStreak).toBe(1);
        expect(s.gamesPlayed).toBe(1); // replay is not a new game
        expect(s.today.score).toBe(1500); // keeps the better score
        expect(s.bestDailyScore).toBe(1500);
    });

    it('keeps the better score when a same-day replay is worse', () => {
        let s = computeUpdatedStats(emptyStats(), result({ score: 1500 }));
        s = computeUpdatedStats(s, result({ score: 600 }));
        expect(s.today.score).toBe(1500);
    });

    it('does not mutate the previous stats object', () => {
        const prev = emptyStats();
        const snapshot = JSON.stringify(prev);
        computeUpdatedStats(prev, result());
        expect(JSON.stringify(prev)).toBe(snapshot);
    });
});

describe('hasPlayedToday', () => {
    it('is false for fresh stats', () => {
        expect(hasPlayedToday(emptyStats(), '2026-05-21')).toBe(false);
    });

    it('is true once today is recorded', () => {
        const s = computeUpdatedStats(emptyStats(), {
            day: '2026-05-21',
            challenge: 141,
            score: 100,
            topLevel: 2,
        });
        expect(hasPlayedToday(s, '2026-05-21')).toBe(true);
        expect(hasPlayedToday(s, '2026-05-22')).toBe(false);
    });
});

describe('buildResultCard', () => {
    it('includes the challenge number, score and hashtag', () => {
        const card = buildResultCard({
            challenge: 141,
            score: 3420,
            topLevel: 7,
            streak: 5,
        });
        expect(card).toContain('#141');
        expect(card).toContain('3,420');
        expect(card).toContain('#SuikaDaily');
        expect(card).toContain('🔥 5일 연속');
    });

    it('omits the streak line when there is no streak', () => {
        const card = buildResultCard({
            challenge: 1,
            score: 10,
            topLevel: 0,
            streak: 0,
        });
        expect(card).not.toContain('🔥');
    });

    it('renders an 11-slot progress bar', () => {
        const card = buildResultCard({
            challenge: 1,
            score: 10,
            topLevel: 4,
            streak: 0,
        });
        const barLine = card.split('\n').find((l) => l.includes('🟩'));
        const slots = [...barLine].filter(
            (ch) => ch === '🟩' || ch === '⬜',
        );
        expect(slots).toHaveLength(11);
    });

    it('clamps an out-of-range topLevel without throwing', () => {
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

describe('localStorage persistence', () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it('returns empty stats when nothing is stored', () => {
        expect(loadDailyStats()).toEqual(emptyStats());
    });

    it('round-trips through save and load', () => {
        const stats = computeUpdatedStats(emptyStats(), {
            day: '2026-05-21',
            challenge: 141,
            score: 999,
            topLevel: 6,
        });
        saveDailyStats(stats);
        expect(loadDailyStats()).toEqual(stats);
    });

    it('recovers from corrupt stored JSON', () => {
        localStorage.setItem(DAILY_STATS_KEY, '{not valid json');
        expect(loadDailyStats()).toEqual(emptyStats());
    });

    it('recordDailyResult persists and returns updated stats', () => {
        const out = recordDailyResult({
            day: '2026-05-21',
            challenge: 141,
            score: 500,
            topLevel: 3,
        });
        expect(out.currentStreak).toBe(1);
        expect(loadDailyStats().today.score).toBe(500);
    });
});
