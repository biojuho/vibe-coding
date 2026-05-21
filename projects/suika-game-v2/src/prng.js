// prng.js
//
// Deterministic, seedable pseudo-random number generator.
//
// Why this exists:
//   A normal Suika clone uses Math.random() everywhere, so no two playthroughs
//   are ever comparable. "Suika Daily" instead derives a single seed from the
//   calendar date, so every player on Earth gets the *identical* fruit/bomb
//   sequence on a given day - a fair, Wordle-style daily challenge.
//
// Determinism contract:
//   Given the same seed, gameRandom() always yields the same sequence.
//   This is what makes the daily challenge fair AND makes the logic unit
//   testable (see prng.test.js).
//
// Algorithm: mulberry32 - a tiny, fast, well-distributed 32-bit generator.
// String seeds are folded into a 32-bit integer with the xmur3 hash.

/**
 * xmur3 string hash -> seed function producing 32-bit integers.
 * @param {string} str - arbitrary seed string.
 * @returns {() => number} a function returning successive 32-bit hash values.
 */
export function xmur3(str) {
    let h = 1779033703 ^ str.length;
    for (let i = 0; i < str.length; i++) {
        h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
        h = (h << 13) | (h >>> 19);
    }
    return function () {
        h = Math.imul(h ^ (h >>> 16), 2246822507);
        h = Math.imul(h ^ (h >>> 13), 3266489909);
        h ^= h >>> 16;
        return h >>> 0;
    };
}

/**
 * mulberry32 PRNG.
 * @param {number} seed - 32-bit unsigned integer seed.
 * @returns {() => number} function returning floats in [0, 1).
 */
export function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
        a |= 0;
        a = (a + 0x6d2b79f5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

/**
 * Build a self-contained random generator from any string or number seed.
 * Useful when callers want an isolated stream (e.g. tests, replays).
 * @param {string|number} seed
 * @returns {{ next: () => number, int: (min:number,max:number)=>number }}
 */
export function createRng(seed) {
    const intSeed =
        typeof seed === 'number' ? seed >>> 0 : xmur3(String(seed))();
    const next = mulberry32(intSeed);
    return {
        next,
        /** Inclusive integer in [min, max]. */
        int(min, max) {
            return min + Math.floor(next() * (max - min + 1));
        },
    };
}

// --- Gameplay singleton --------------------------------------------------
//
// physics.js pulls its gameplay randomness from this single shared stream so
// that one seed deterministically reproduces an entire round. Cosmetic-only
// randomness (particles, screen shake) deliberately keeps using Math.random()
// - it must never consume from this stream or determinism would break.

let gameplayRng = mulberry32((Math.random() * 0xffffffff) >>> 0);
let activeSeedLabel = 'unseeded';

/**
 * Reset the shared gameplay stream to a known seed.
 * @param {string|number} seed - seed string (e.g. a daily date) or integer.
 * @returns {string} the human-readable seed label now in effect.
 */
export function seedGameplayRng(seed) {
    const intSeed =
        typeof seed === 'number' ? seed >>> 0 : xmur3(String(seed))();
    gameplayRng = mulberry32(intSeed);
    activeSeedLabel = String(seed);
    return activeSeedLabel;
}

/**
 * Next gameplay random float in [0, 1). Drop-in replacement for Math.random().
 * @returns {number}
 */
export function gameRandom() {
    return gameplayRng();
}

/** @returns {string} the seed label currently driving gameplay. */
export function getActiveSeedLabel() {
    return activeSeedLabel;
}

// --- Daily challenge identity -------------------------------------------

// Day 1 of the challenge. The challenge number is the day offset from here,
// mirroring how Wordle-style games number their puzzles.
const EPOCH_UTC = Date.UTC(2026, 0, 1); // 2026-01-01
const MS_PER_DAY = 86400000;

/**
 * UTC calendar-day string for a given moment, e.g. "2026-05-21".
 * UTC is used so every timezone shares the same daily puzzle.
 * @param {Date} [date] - defaults to now.
 * @returns {string}
 */
export function dailySeedString(date = new Date()) {
    const y = date.getUTCFullYear();
    const m = String(date.getUTCMonth() + 1).padStart(2, '0');
    const d = String(date.getUTCDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

/**
 * Sequential challenge number for a given day (#1 on the epoch date).
 * @param {Date} [date] - defaults to now.
 * @returns {number}
 */
export function dailyChallengeNumber(date = new Date()) {
    const dayStart = Date.UTC(
        date.getUTCFullYear(),
        date.getUTCMonth(),
        date.getUTCDate(),
    );
    return Math.floor((dayStart - EPOCH_UTC) / MS_PER_DAY) + 1;
}
