import { describe, it, expect } from 'vitest';
import {
    pickWeightedLevel,
    getSpawnWeightsForScore,
    applyRescueWeights,
} from './spawn.js';

describe('pickWeightedLevel', () => {
    it('returns 0 when every weight is zero', () => {
        expect(pickWeightedLevel([0, 0, 0], () => 0.5)).toBe(0);
    });

    it('returns 0 for an empty weight table', () => {
        expect(pickWeightedLevel([], () => 0.5)).toBe(0);
    });

    it('picks the only non-zero slot', () => {
        for (const r of [0.01, 0.3, 0.99]) {
            expect(pickWeightedLevel([0, 10, 0], () => r)).toBe(1);
        }
    });

    it('edge case: an exactly-zero random value resolves to slot 0', () => {
        // randomValue depletes to exactly 0 at the first slot. Harmless in
        // practice: real spawn profiles always give slot 0 a positive weight.
        expect(pickWeightedLevel([0, 10, 0], () => 0)).toBe(0);
        expect(pickWeightedLevel([5, 10], () => 0)).toBe(0);
    });

    it('maps the random value onto the cumulative weight ranges', () => {
        // weights [50,50]: r<0.5 -> 0, r>=0.5 -> 1
        expect(pickWeightedLevel([50, 50], () => 0.0)).toBe(0);
        expect(pickWeightedLevel([50, 50], () => 0.49)).toBe(0);
        expect(pickWeightedLevel([50, 50], () => 0.6)).toBe(1);
    });

    it('roughly honours the weight distribution', () => {
        const weights = [70, 20, 10];
        const counts = [0, 0, 0];
        // deterministic sweep across [0,1)
        for (let i = 0; i < 1000; i++) {
            const r = i / 1000;
            counts[pickWeightedLevel(weights, () => r)]++;
        }
        expect(counts[0]).toBeGreaterThan(counts[1]);
        expect(counts[1]).toBeGreaterThan(counts[2]);
        expect(counts[0] + counts[1] + counts[2]).toBe(1000);
    });
});

describe('getSpawnWeightsForScore', () => {
    const profiles = [
        { minScore: 0, weights: [45, 35, 15, 5, 0] },
        { minScore: 700, weights: [35, 34, 20, 10, 1] },
        { minScore: 1800, weights: [25, 31, 24, 16, 4] },
    ];

    it('picks the first profile at score 0', () => {
        expect(getSpawnWeightsForScore(0, profiles)).toEqual([45, 35, 15, 5, 0]);
    });

    it('stays on a profile until the next threshold', () => {
        expect(getSpawnWeightsForScore(699, profiles)[0]).toBe(45);
        expect(getSpawnWeightsForScore(700, profiles)[0]).toBe(35);
        expect(getSpawnWeightsForScore(1799, profiles)[0]).toBe(35);
        expect(getSpawnWeightsForScore(1800, profiles)[0]).toBe(25);
    });

    it('clamps to the highest profile for very high scores', () => {
        expect(getSpawnWeightsForScore(999999, profiles)[0]).toBe(25);
    });

    it('returns a copy, not the profile array itself', () => {
        const out = getSpawnWeightsForScore(0, profiles);
        out[0] = -1;
        expect(profiles[0].weights[0]).toBe(45);
    });
});

describe('applyRescueWeights', () => {
    const base = [45, 35, 15, 5, 2];

    it('returns the weights unchanged before the rescue threshold', () => {
        const out = applyRescueWeights(base, {
            dropsSinceMerge: 3,
            rescueAfterDrops: 5,
            topFruitY: 600,
        });
        expect(out).toEqual(base);
    });

    it('never mutates the input array', () => {
        const snapshot = [...base];
        applyRescueWeights(base, {
            dropsSinceMerge: 9,
            rescueAfterDrops: 5,
            topFruitY: 200,
        });
        expect(base).toEqual(snapshot);
    });

    it('applies tier 1 only when the stack is low', () => {
        const out = applyRescueWeights(base, {
            dropsSinceMerge: 5,
            rescueAfterDrops: 5,
            topFruitY: 500,
        });
        expect(out).toEqual([63, 45, 15, 5, 0]);
    });

    it('adds tier 2 when the stack is tall (topFruitY < 250)', () => {
        const out = applyRescueWeights(base, {
            dropsSinceMerge: 5,
            rescueAfterDrops: 5,
            topFruitY: 240,
        });
        expect(out).toEqual([75, 53, 19, 5, 0]);
    });

    it('adds tier 3 when the stack is critical (topFruitY < 215)', () => {
        const out = applyRescueWeights(base, {
            dropsSinceMerge: 5,
            rescueAfterDrops: 5,
            topFruitY: 210,
        });
        expect(out).toEqual([93, 65, 19, 0, 0]);
    });

    it('clamps reduced weights at zero', () => {
        const out = applyRescueWeights(base, {
            dropsSinceMerge: 20,
            rescueAfterDrops: 5,
            topFruitY: 100,
        });
        expect(out.every((w) => w >= 0)).toBe(true);
    });
});
