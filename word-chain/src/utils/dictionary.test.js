import { describe, it, expect } from 'vitest';
import { koreanWords, getRandomWord } from './dictionary.js';

// ---------------------------------------------------------------------------
// koreanWords structure
// ---------------------------------------------------------------------------

describe('koreanWords', () => {
    it('is a non-empty object', () => {
        expect(typeof koreanWords).toBe('object');
        expect(Object.keys(koreanWords).length).toBeGreaterThan(0);
    });

    it('every key is a single Korean character', () => {
        for (const key of Object.keys(koreanWords)) {
            expect(key).toHaveLength(1);
        }
    });

    it('every value is a non-empty array of strings', () => {
        for (const [key, words] of Object.entries(koreanWords)) {
            expect(Array.isArray(words), `${key} should be an array`).toBe(true);
            expect(words.length, `${key} should have words`).toBeGreaterThan(0);
            for (const word of words) {
                expect(typeof word).toBe('string');
                expect(word.length).toBeGreaterThan(0);
            }
        }
    });

    it('every word starts with its bucket key character', () => {
        for (const [key, words] of Object.entries(koreanWords)) {
            for (const word of words) {
                expect(word[0]).toBe(key);
            }
        }
    });

    it('every word has at least 2 characters', () => {
        for (const words of Object.values(koreanWords)) {
            for (const word of words) {
                expect(word.length).toBeGreaterThanOrEqual(2);
            }
        }
    });
});

// ---------------------------------------------------------------------------
// getRandomWord
// ---------------------------------------------------------------------------

describe('getRandomWord', () => {
    it('returns null for a character with no entries', () => {
        expect(getRandomWord('Z')).toBeNull();
        expect(getRandomWord('')).toBeNull();
        expect(getRandomWord('없')).toBeNull();
    });

    it('returns a word from the correct bucket', () => {
        for (const char of Object.keys(koreanWords)) {
            const word = getRandomWord(char);
            expect(word).not.toBeNull();
            expect(word[0]).toBe(char);
        }
    });

    it('returns a string for known characters', () => {
        const word = getRandomWord('가');
        expect(typeof word).toBe('string');
        expect(word.length).toBeGreaterThan(0);
    });

    it('returns only words from the matching list', () => {
        const char = '나';
        const word = getRandomWord(char);
        expect(koreanWords[char]).toContain(word);
    });

    it('returns different words across multiple calls (probabilistic)', () => {
        // With 13+ words in '가' bucket, repeated calls should not always be identical
        const results = new Set();
        for (let i = 0; i < 50; i++) {
            results.add(getRandomWord('가'));
        }
        // At least 2 distinct words should appear in 50 draws (bucket has 13 words)
        expect(results.size).toBeGreaterThan(1);
    });
});
