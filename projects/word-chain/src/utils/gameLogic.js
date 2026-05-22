// gameLogic.js
//
// Pure word-chain (끝말잇기) rules, extracted from GameInterface.jsx so the
// move validation and the AI's word choice can be unit tested without React.
//
// All functions are pure: callers pass in the current game state explicitly.

import { koreanWords } from "./dictionary.js";

/**
 * Validate a player's move.
 *
 * @param {string} word - the word the player entered (will be trimmed).
 * @param {string|null} lastWord - the previous word in the chain, or null
 *        if this is the opening move.
 * @param {Iterable<string>} usedWords - words already played this round.
 * @returns {{ok: boolean, reason?: string, word?: string}}
 *          On success `word` is the cleaned word to commit.
 */
export function validateMove(word, lastWord, usedWords) {
	const cleaned = (word || "").trim();
	const used = usedWords instanceof Set ? usedWords : new Set(usedWords);

	if (cleaned.length === 0) {
		return { ok: false, reason: "단어를 입력하세요" };
	}
	if (cleaned.length < 2) {
		return { ok: false, reason: "두 글자 이상 입력하세요" };
	}
	if (lastWord) {
		const need = lastWord.slice(-1);
		if (cleaned[0] !== need) {
			return { ok: false, reason: `'${need}'(으)로 시작해야 합니다` };
		}
	}
	if (used.has(cleaned)) {
		return { ok: false, reason: "이미 사용된 단어입니다" };
	}
	return { ok: true, word: cleaned };
}

/**
 * Choose the AI's reply word.
 *
 * Unlike the old getRandomWord(), this excludes words already played, so the
 * AI never repeats a word - and correctly "gives up" (returns null) when it
 * has no fresh word for the required starting character.
 *
 * @param {string} lastChar - character the AI's word must start with.
 * @param {Iterable<string>} usedWords - words already played this round.
 * @param {() => number} [randomFn] - random source in [0,1) (injectable).
 * @returns {string|null} a fresh word, or null if the AI cannot continue.
 */
export function pickAiWord(lastChar, usedWords, randomFn = Math.random) {
	const candidates = koreanWords[lastChar];
	if (!candidates || candidates.length === 0) return null;

	const used = usedWords instanceof Set ? usedWords : new Set(usedWords);
	const fresh = candidates.filter((w) => !used.has(w));
	if (fresh.length === 0) return null;

	return fresh[Math.floor(randomFn() * fresh.length)];
}
