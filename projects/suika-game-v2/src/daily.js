// daily.js
//
// Daily-challenge progression: streaks, stats and the spoiler-free result
// card that players share. The streak math is kept as a pure function
// (computeUpdatedStats) so it can be unit tested without a DOM/localStorage.

import { FRUITS } from './config.js';

export const DAILY_STATS_KEY = 'suika_v2_daily_stats';

// How many past daily results to retain for the stats screen.
export const HISTORY_CAP = 30;

/** Shape of a freshly-initialised stats record. */
export function emptyStats() {
    return {
        lastPlayedDay: null, // "YYYY-MM-DD" of the most recent daily attempt
        lastChallenge: 0, // challenge number of that attempt
        currentStreak: 0,
        maxStreak: 0,
        gamesPlayed: 0,
        bestDailyScore: 0,
        // most recent finished result, used to render "already played" UI
        today: null, // { day, challenge, score, topLevel }
        // one entry per played day (best score), oldest first, capped
        history: [], // [{ day, challenge, score, topLevel }]
    };
}

/**
 * Whole-day distance between two "YYYY-MM-DD" strings (b - a).
 * @param {string} a
 * @param {string} b
 * @returns {number} integer day delta (positive if b is later).
 */
export function daysBetween(a, b) {
    const [ay, am, ad] = a.split('-').map(Number);
    const [by, bm, bd] = b.split('-').map(Number);
    const ta = Date.UTC(ay, am - 1, ad);
    const tb = Date.UTC(by, bm - 1, bd);
    return Math.round((tb - ta) / 86400000);
}

/**
 * Pure streak/stats transition. Given the previous stats and a finished
 * daily result, return the new stats object (previous object is untouched).
 *
 * Streak rules:
 *   - first ever play .............. streak = 1
 *   - same calendar day replay ..... streak unchanged, score = max(old, new)
 *   - exactly the next day ......... streak + 1
 *   - any larger gap ............... streak resets to 1
 *
 * @param {object} prev - previous stats (see emptyStats()).
 * @param {{day:string, challenge:number, score:number, topLevel:number}} result
 * @returns {object} new stats object.
 */
export function computeUpdatedStats(prev, result) {
    const stats = { ...emptyStats(), ...prev };
    const { day, challenge, score, topLevel } = result;
    const isSameDay = stats.lastPlayedDay === day;

    // Streak transition.
    let streak;
    if (isSameDay) {
        streak = stats.currentStreak; // replay - streak unchanged
    } else if (stats.lastPlayedDay === null) {
        streak = 1;
    } else if (daysBetween(stats.lastPlayedDay, day) === 1) {
        streak = stats.currentStreak + 1;
    } else {
        streak = 1; // gap (or clock moved backwards) breaks the streak
    }

    // `today` keeps the best score for the current day.
    const prevBestToday = isSameDay && stats.today ? stats.today.score : 0;
    const today =
        score >= prevBestToday
            ? { day, challenge, score, topLevel }
            : stats.today;

    // `history` holds one entry per day; its last entry mirrors `today`.
    let history = stats.history.slice();
    const last = history[history.length - 1];
    if (last && last.day === day) {
        history[history.length - 1] = today;
    } else {
        history.push(today);
    }
    history = history.slice(-HISTORY_CAP);

    return {
        lastPlayedDay: day,
        lastChallenge: challenge,
        currentStreak: streak,
        maxStreak: Math.max(stats.maxStreak, streak),
        gamesPlayed: isSameDay ? stats.gamesPlayed : stats.gamesPlayed + 1,
        bestDailyScore: Math.max(stats.bestDailyScore, score),
        today,
        history,
    };
}

/**
 * Reduce a stats record to a display-ready summary for the stats screen.
 * @param {object} stats
 * @returns {{currentStreak:number, maxStreak:number, gamesPlayed:number,
 *            bestDailyScore:number, recent:object[]}}
 */
export function getStatsSummary(stats) {
    const s = { ...emptyStats(), ...stats };
    return {
        currentStreak: s.currentStreak,
        maxStreak: s.maxStreak,
        gamesPlayed: s.gamesPlayed,
        bestDailyScore: s.bestDailyScore,
        recent: s.history.slice().reverse().slice(0, 7), // newest first
    };
}

/**
 * Whether the player has already finished today's daily challenge.
 * @param {object} stats
 * @param {string} day - today's "YYYY-MM-DD".
 * @returns {boolean}
 */
export function hasPlayedToday(stats, day) {
    return Boolean(stats && stats.today && stats.today.day === day);
}

const BAR_SLOTS = 11; // == FRUITS.length; the fruit-evolution ladder

/**
 * Build the spoiler-free, shareable result card text.
 * It reveals the player's outcome but never the puzzle itself.
 *
 * @param {{challenge:number, score:number, topLevel:number,
 *          streak:number, mode?:string}} r
 * @returns {string} multi-line share text.
 */
export function buildResultCard(r) {
    const { challenge, score, topLevel, streak, mode = 'Daily' } = r;
    const top = FRUITS[Math.min(topLevel, FRUITS.length - 1)] || FRUITS[0];
    const filled = Math.min(Math.max(topLevel + 1, 0), BAR_SLOTS);
    const bar = '🟩'.repeat(filled) + '⬜'.repeat(BAR_SLOTS - filled);
    const streakLine = streak > 0 ? `  ·  🔥 ${streak}일 연속` : '';

    return [
        `🍉 Suika ${mode} #${challenge}`,
        `점수 ${score.toLocaleString('en-US')}${streakLine}`,
        `최고 과일 ${top.label}`,
        bar,
        '#SuikaDaily',
    ].join('\n');
}

// --- localStorage persistence (thin, side-effecting wrappers) ------------

/**
 * Load stats from localStorage, falling back to a fresh record.
 * @returns {object}
 */
export function loadDailyStats() {
    try {
        const raw = localStorage.getItem(DAILY_STATS_KEY);
        if (!raw) return emptyStats();
        return { ...emptyStats(), ...JSON.parse(raw) };
    } catch (_error) {
        return emptyStats();
    }
}

/**
 * Persist stats to localStorage.
 * @param {object} stats
 */
export function saveDailyStats(stats) {
    try {
        localStorage.setItem(DAILY_STATS_KEY, JSON.stringify(stats));
    } catch (_error) {
        // Storage unavailable (private mode / quota) - degrade silently.
    }
}

/**
 * Record a finished daily result: load -> compute -> save.
 * @param {{day:string, challenge:number, score:number, topLevel:number}} result
 * @returns {object} the newly saved stats.
 */
export function recordDailyResult(result) {
    const updated = computeUpdatedStats(loadDailyStats(), result);
    saveDailyStats(updated);
    return updated;
}
