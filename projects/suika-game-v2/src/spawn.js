// spawn.js
//
// Pure spawn-selection logic: which fruit level the player is handed next.
// Extracted from main.js/physics.js so the gameplay-critical rescue
// weighting (which prevents unwinnable "dead" rounds) is unit testable and
// has no hidden dependency on physics or game state.
//
// All functions here are pure: callers pass in the current state explicitly.

/**
 * Pick a fruit level index from a weight table.
 * @param {number[]} weights - non-negative weight per level.
 * @param {() => number} randomFn - returns a float in [0, 1).
 * @returns {number} chosen index (0 if weights are empty/all-zero).
 */
export function pickWeightedLevel(weights, randomFn) {
	const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
	if (totalWeight <= 0) return 0;

	let randomValue = randomFn() * totalWeight;
	for (let index = 0; index < weights.length; index++) {
		randomValue -= weights[index];
		if (randomValue <= 0) return index;
	}
	return 0;
}

/**
 * Select the spawn-weight profile for the current score. Profiles are
 * ordered by ascending `minScore`; the highest one the score clears wins.
 * @param {number} score
 * @param {{minScore:number, weights:number[]}[]} profiles
 * @returns {number[]} a fresh copy of the chosen profile's weights.
 */
export function getSpawnWeightsForScore(score, profiles) {
	let selected = profiles[0];
	for (const profile of profiles) {
		if (score >= profile.minScore) selected = profile;
	}
	return [...selected.weights];
}

/**
 * Bias the weights toward small fruit when the player is struggling, so a
 * round is never mathematically unwinnable. The longer it has been since a
 * merge, and the closer the stack is to the top, the stronger the rescue.
 *
 * @param {number[]} weights - base weights (not mutated).
 * @param {{dropsSinceMerge:number, rescueAfterDrops:number,
 *          topFruitY:number}} ctx
 * @returns {number[]} adjusted weights (always a fresh array).
 */
export function applyRescueWeights(weights, ctx) {
	const { dropsSinceMerge, rescueAfterDrops, topFruitY } = ctx;
	const rescued = [...weights];

	// Not struggling yet - return the base weights untouched.
	if (dropsSinceMerge < rescueAfterDrops) return rescued;

	// Tier 1: it has simply been too long since a merge.
	rescued[0] += 18;
	rescued[1] += 10;
	if (rescued.length > 4) rescued[4] = Math.max(0, rescued[4] - 8);

	// Tier 2: the stack is getting tall.
	if (topFruitY < 250) {
		rescued[0] += 12;
		rescued[1] += 8;
		rescued[2] += 4;
		if (rescued.length > 4) rescued[4] = Math.max(0, rescued[4] - 6);
	}

	// Tier 3: the stack is dangerously close to the top.
	if (topFruitY < 215) {
		rescued[0] += 18;
		rescued[1] += 12;
		if (rescued.length > 3) rescued[3] = Math.max(0, rescued[3] - 8);
		if (rescued.length > 4) rescued[4] = Math.max(0, rescued[4] - 10);
	}

	return rescued;
}
