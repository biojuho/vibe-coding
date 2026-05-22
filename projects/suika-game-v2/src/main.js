import {
	BEST_SCORE_KEY,
	BOMB_EMOJI,
	BOMB_PROBABILITY_PERCENT,
	DIFFICULTY_KEY,
	DIFFICULTY_PRESETS,
	EXIT_MODAL_KEY,
	FRUITS,
} from "./config.js";
import {
	buildResultCard,
	getStatsSummary,
	hasPlayedToday,
	loadDailyStats,
	recordDailyResult,
} from "./daily.js";
import {
	createNewFruit,
	dropCurrentFruitContext,
	engine,
	getTopFruitY,
	initPhysics,
	moveCurrentFruitTo,
	nudgeCurrentFruit,
	Render,
	Runner,
	removeActiveFruits,
	render,
	runner,
} from "./physics.js";
import {
	dailyChallengeNumber,
	dailySeedString,
	gameRandom,
	seedGameplayRng,
} from "./prng.js";
import {
	handleResize,
	renderCustomGraphics,
	setParticles,
} from "./renderer.js";
import { drawShareCard } from "./sharecard.js";
import {
	applyRescueWeights,
	getSpawnWeightsForScore,
	pickWeightedLevel,
} from "./spawn.js";
import {
	getElement,
	getStoredValue,
	removeStoredValue,
	setOverlayHidden,
	setPauseButtonLabel,
	setStoredValue,
	setText,
	updateBestScoreDisplay,
	updateComboDisplay,
	updateDifficultyButtons,
	updateModeDisplay,
	updateScoreDisplay,
} from "./ui.js";

// --- Global State ---
export let currentFruit = null;
export let nextFruitLevel = 0;
export let isDropping = false;
export let score = 0;
export let gameState = "START"; // 'START' | 'PLAYING' | 'PAUSED' | 'GAMEOVER'
export let bestScore = 0;
export let inputBound = false;
export let uiEventsBound = false;
export let renderStarted = false;
export let pendingFruitSpawn = false;
export let shakeIntensity = 0;
export let comboCount = 0;
export let lastMergeAt = 0;
export let difficultyMode = "normal";
export let dropsSinceMerge = 0;

// --- Daily-challenge state ---
export let gameMode = "daily"; // 'daily' | 'free'
export let maxFruitLevel = 0; // highest fruit reached this round
export let dailyChallenge = dailyChallengeNumber();
export let lastResultCard = ""; // shareable text for the last round
let dailyStats = loadDailyStats(); // streak/score history (localStorage)

// Setters for external modules
export function setScore(val) {
	score = val;
}
export function setComboCount(val) {
	comboCount = val;
}
export function setLastMergeAt(val) {
	lastMergeAt = val;
}
export function setDropsSinceMerge(val) {
	dropsSinceMerge = val;
}
export function setGameState(val) {
	gameState = val;
}
export function setCurrentFruit(val) {
	currentFruit = val;
}
export function setNextFruitLevel(val) {
	nextFruitLevel = val;
}
export function setIsDropping(val) {
	isDropping = val;
}
export function setPendingFruitSpawn(val) {
	pendingFruitSpawn = val;
}

/** Record the highest fruit level reached, for the share card. */
export function reportFruitLevel(level) {
	if (level > maxFruitLevel) maxFruitLevel = level;
}

export function getActiveDifficultyConfig() {
	return DIFFICULTY_PRESETS[difficultyMode] || DIFFICULTY_PRESETS.normal;
}

export function triggerHaptic(pattern) {
	if (!navigator.vibrate) return;
	navigator.vibrate(pattern);
}

export function triggerShake(intensity, internal = false) {
	if (!internal) {
		shakeIntensity = intensity;
	} else {
		shakeIntensity = intensity;
	}
}

export {
	getElement,
	setOverlayHidden,
	setPauseButtonLabel,
	updateComboDisplay,
	updateScoreDisplay,
};

export function syncBestScore() {
	if (score <= bestScore) return;
	bestScore = score;
	setStoredValue(BEST_SCORE_KEY, bestScore.toString());
	updateBestScoreDisplay();
}

function resetRoundState() {
	score = 0;
	comboCount = 0;
	lastMergeAt = 0;
	dropsSinceMerge = 0;
	maxFruitLevel = 0;
	setParticles([]);
	shakeIntensity = 0;
	currentFruit = null;
	isDropping = false;
	pendingFruitSpawn = false;
	updateScoreDisplay();
	updateComboDisplay();
	setOverlayHidden("game-over", true);
	setOverlayHidden("exit-modal", true);
	setOverlayHidden("pause-screen", true);
	removeStoredValue(EXIT_MODAL_KEY);
}

let nextIsBomb = false;

export function setNextObject() {
	const difficulty = getActiveDifficultyConfig();
	nextIsBomb = false;

	if (gameRandom() * 100 < BOMB_PROBABILITY_PERCENT) {
		nextFruitLevel = 0;
		nextIsBomb = true;
	} else if (dropsSinceMerge >= difficulty.guaranteedRescueAfter) {
		nextFruitLevel = 0;
	} else {
		const baseWeights = getSpawnWeightsForScore(
			score,
			difficulty.spawnProfiles,
		);
		const adjustedWeights = applyRescueWeights(baseWeights, {
			dropsSinceMerge,
			rescueAfterDrops: difficulty.rescueAfterDrops,
			topFruitY: getTopFruitY(),
		});
		nextFruitLevel = pickWeightedLevel(adjustedWeights, gameRandom);
	}
	const nextDisplay = getElement("next-fruit-display");
	if (nextDisplay) {
		if (nextIsBomb) {
			nextDisplay.innerText = BOMB_EMOJI;
			nextDisplay.style.color = "red";
		} else {
			nextDisplay.innerText = FRUITS[nextFruitLevel].label;
			nextDisplay.style.color = "";
		}

		nextDisplay.style.transform = "scale(0.5)";
		setTimeout(() => (nextDisplay.style.transform = "scale(1)"), 150);
	}
}

function startGame() {
	resetRoundState();
	removeActiveFruits();

	// Seed the gameplay RNG. Daily mode uses the UTC calendar date, so every
	// player worldwide faces the identical fruit/bomb sequence; free play
	// uses a fresh unpredictable seed each round.
	if (gameMode === "daily") {
		dailyChallenge = dailyChallengeNumber();
		seedGameplayRng(dailySeedString());
	} else {
		seedGameplayRng(`free-${Date.now()}-${Math.random()}`);
	}

	gameState = "PLAYING";
	setOverlayHidden("start-screen", true);

	if (!renderStarted) {
		Render.run(render);
		renderStarted = true;
	}

	Runner.stop(runner);
	Runner.run(runner, engine);
	setPauseButtonLabel(gameState);

	setNextObject();
	createNewFruit(nextIsBomb);
}

function restartGame() {
	startGame();
}

/**
 * Called by physics.js the moment the round ends. Records the daily result,
 * refreshes the streak HUD and builds the shareable result card.
 */
export function notifyGameOver() {
	if (gameMode === "daily") {
		const day = dailySeedString();
		dailyStats = recordDailyResult({
			day,
			challenge: dailyChallenge,
			score,
			topLevel: maxFruitLevel,
		});
		lastResultCard = buildResultCard({
			challenge: dailyChallenge,
			score,
			topLevel: maxFruitLevel,
			streak: dailyStats.currentStreak,
			mode: "Daily",
		});
	} else {
		lastResultCard = buildResultCard({
			challenge: dailyChallenge,
			score,
			topLevel: maxFruitLevel,
			streak: 0,
			mode: "Free",
		});
	}
	renderGameOverSummary();
}

/** Populate the game-over overlay with the result card + streak. */
function renderGameOverSummary() {
	setText("result-card", lastResultCard);
	if (gameMode === "daily") {
		setText(
			"daily-streak-result",
			`🔥 ${dailyStats.currentStreak}일 연속  ·  최고 ${dailyStats.maxStreak}일`,
		);
	} else {
		setText("daily-streak-result", "프리 플레이 — 기록은 저장되지 않습니다");
	}
	getElement("restart-btn")?.focus(); // keyboard focus on the primary action
}

/** Populate and show the Daily Stats overlay. */
function openStats() {
	const summary = getStatsSummary(dailyStats);
	setText("stat-streak", String(summary.currentStreak));
	setText("stat-maxstreak", String(summary.maxStreak));
	setText("stat-games", String(summary.gamesPlayed));
	setText("stat-best", summary.bestDailyScore.toLocaleString("en-US"));

	const list = getElement("stats-recent-list");
	if (list) {
		list.replaceChildren();
		if (summary.recent.length === 0) {
			const li = document.createElement("li");
			li.className = "stats-empty";
			li.textContent = "아직 기록이 없어요. 첫 챌린지에 도전하세요!";
			list.appendChild(li);
		} else {
			for (const r of summary.recent) {
				const fruit =
					FRUITS[Math.min(r.topLevel, FRUITS.length - 1)] || FRUITS[0];
				const li = document.createElement("li");
				const chal = document.createElement("span");
				chal.className = "recent-chal";
				chal.textContent = `#${r.challenge}`;
				const emoji = document.createElement("span");
				emoji.className = "recent-fruit";
				emoji.textContent = fruit.label;
				const sc = document.createElement("span");
				sc.className = "recent-score";
				sc.textContent = `${r.score.toLocaleString("en-US")}점`;
				li.append(chal, emoji, sc);
				list.appendChild(li);
			}
		}
	}
	setOverlayHidden("stats-screen", false);
	getElement("stats-close-btn")?.focus(); // land keyboard focus in the dialog
}

/** Hide the Daily Stats overlay. */
function closeStats() {
	setOverlayHidden("stats-screen", true);
	getElement("stats-btn")?.focus(); // return focus to the trigger
}

/**
 * Share the result: a rendered PNG card via the Web Share API when possible,
 * otherwise the spoiler-free text card copied to the clipboard.
 */
async function shareResult() {
	const shareText = `${lastResultCard}\n${window.location.href}`;
	const copyFallback = async () => {
		try {
			await navigator.clipboard.writeText(shareText);
			alert("결과 카드가 클립보드에 복사되었습니다!");
		} catch (_error) {
			// Clipboard blocked - nothing more we can do gracefully.
		}
	};

	try {
		const blob = await drawShareCard({
			challenge: dailyChallenge,
			score,
			topLevel: maxFruitLevel,
			streak: gameMode === "daily" ? dailyStats.currentStreak : 0,
			mode: gameMode === "daily" ? "Daily" : "Free",
		});
		const file = new File([blob], `suika-daily-${dailyChallenge}.png`, {
			type: "image/png",
		});

		if (navigator.canShare && navigator.canShare({ files: [file] })) {
			await navigator.share({
				title: "Suika Daily",
				text: shareText,
				files: [file],
			});
			return;
		}
		if (navigator.share) {
			await navigator.share({ title: "Suika Daily", text: shareText });
			return;
		}
		await copyFallback();
	} catch (error) {
		if (error && error.name === "AbortError") return; // user cancelled
		await copyFallback();
	}
}

/** Switch between the Daily challenge and Free play modes. */
function setGameMode(mode) {
	if (mode !== "daily" && mode !== "free") return;
	if (gameState === "PLAYING") return; // don't swap mid-round
	gameMode = mode;
	updateGameModeUI();
}

/** Reflect the active game mode + daily streak on the start screen. */
function updateGameModeUI() {
	const buttons = document.querySelectorAll(".mode-btn");
	buttons.forEach((button) => {
		const mode = button.getAttribute("data-mode");
		button.classList.toggle("active", mode === gameMode);
	});

	setText("daily-challenge-label", `Daily #${dailyChallenge}`);

	if (gameMode === "daily") {
		const played = hasPlayedToday(dailyStats, dailySeedString());
		const streakText =
			dailyStats.currentStreak > 0
				? `🔥 ${dailyStats.currentStreak}일 연속 도전 중`
				: "오늘부터 연속 기록을 쌓아보세요";
		const playedText = played
			? `오늘 기록: ${dailyStats.today.score.toLocaleString("en-US")}점 (다시 도전 가능)`
			: "";
		setText(
			"start-streak",
			[streakText, playedText].filter(Boolean).join("  ·  "),
		);
	} else {
		setText("start-streak", "프리 플레이 — 매 판 새로운 무작위 시드");
	}
}

function togglePause() {
	if (gameState === "PLAYING") {
		gameState = "PAUSED";
		triggerHaptic(10);
		Runner.stop(runner);
		setOverlayHidden("pause-screen", false);
		setPauseButtonLabel(gameState);
		return;
	}

	if (gameState !== "PAUSED") return;

	gameState = "PLAYING";
	triggerHaptic(6);
	setOverlayHidden("pause-screen", true);
	Runner.run(runner, engine);
	setPauseButtonLabel(gameState);

	if (pendingFruitSpawn && !currentFruit) {
		createNewFruit(nextIsBomb);
	}
}

function setDifficultyMode(mode) {
	if (!DIFFICULTY_PRESETS[mode]) return;
	difficultyMode = mode;
	setStoredValue(DIFFICULTY_KEY, mode);
	updateDifficultyButtons();
	updateModeDisplay();
	updateComboDisplay();
	setNextObject();
}

function loadDifficultyMode() {
	const stored = getStoredValue(DIFFICULTY_KEY);
	if (stored && DIFFICULTY_PRESETS[stored]) {
		difficultyMode = stored;
	} else {
		difficultyMode = "normal";
	}
	updateDifficultyButtons();
	updateModeDisplay();
}

function loadBestScore() {
	const saved = Number(getStoredValue(BEST_SCORE_KEY));
	bestScore = Number.isFinite(saved) && saved > 0 ? saved : 0;
	updateBestScoreDisplay();
}

function setupInput(container) {
	if (inputBound) return;
	inputBound = true;

	const move = (event) => {
		if (isDropping || gameState !== "PLAYING" || !currentFruit) return;
		const pointX = event.touches ? event.touches[0].clientX : event.clientX;
		moveCurrentFruitTo(pointX, container.getBoundingClientRect());
	};

	container.addEventListener("touchstart", move, { passive: true });
	container.addEventListener("mousemove", move);
	container.addEventListener("touchmove", move, { passive: true });
	container.addEventListener("mouseup", dropCurrentFruitContext);
	container.addEventListener("touchend", dropCurrentFruitContext);
	container.addEventListener("touchcancel", () => {
		if (gameState === "PLAYING") {
			isDropping = false;
		}
	});

	window.addEventListener("keydown", (event) => {
		if (event.key.toLowerCase() === "p") {
			togglePause();
			return;
		}

		if (event.key.toLowerCase() === "r" && gameState === "GAMEOVER") {
			restartGame();
			return;
		}

		if (gameState !== "PLAYING" || !currentFruit) return;

		if (event.key === "ArrowLeft") {
			event.preventDefault();
			nudgeCurrentFruit(-24);
			return;
		}

		if (event.key === "ArrowRight") {
			event.preventDefault();
			nudgeCurrentFruit(24);
			return;
		}

		if (event.key === " " || event.key === "Enter") {
			event.preventDefault();
			dropCurrentFruitContext();
		}
	});
}

function setupUIEvents() {
	if (uiEventsBound) return;
	uiEventsBound = true;

	const startButton = getElement("start-btn");
	if (startButton) {
		startButton.addEventListener("click", startGame);
	}

	const shareButton = getElement("share-btn");
	if (shareButton) {
		shareButton.addEventListener("click", shareResult);
	}

	const restartButton = getElement("restart-btn");
	if (restartButton) {
		restartButton.addEventListener("click", restartGame);
	}

	const pauseButton = getElement("pause-btn");
	if (pauseButton) {
		pauseButton.addEventListener("click", togglePause);
	}

	const difficultyButtons = document.querySelectorAll(".difficulty-btn");
	difficultyButtons.forEach((btn) => {
		btn.addEventListener("click", (e) => {
			const mode = e.target.getAttribute("data-difficulty");
			if (mode) setDifficultyMode(mode);
		});
	});

	const modeButtons = document.querySelectorAll(".mode-btn");
	modeButtons.forEach((btn) => {
		btn.addEventListener("click", (e) => {
			const mode = e.target.getAttribute("data-mode");
			if (mode) setGameMode(mode);
		});
	});

	const statsButton = getElement("stats-btn");
	if (statsButton) {
		statsButton.addEventListener("click", openStats);
	}

	const statsCloseButton = getElement("stats-close-btn");
	if (statsCloseButton) {
		statsCloseButton.addEventListener("click", closeStats);
	}

	const leaveBtn = getElement("leave-btn");
	if (leaveBtn) {
		leaveBtn.addEventListener("click", () => {
			setOverlayHidden("exit-modal", true);
		});
	}

	const stayBtn = getElement("stay-btn");
	if (stayBtn) {
		stayBtn.addEventListener("click", () => {
			setOverlayHidden("exit-modal", true);
			if (gameState === "PAUSED") {
				togglePause();
			}
		});
	}

	document.addEventListener("mouseleave", (e) => {
		if (
			e.clientY <= 0 ||
			e.clientX <= 0 ||
			e.clientX >= window.innerWidth ||
			e.clientY >= window.innerHeight
		) {
			if (gameState === "PLAYING" && !getStoredValue(EXIT_MODAL_KEY)) {
				togglePause();
				setOverlayHidden("exit-modal", false);
				setStoredValue(EXIT_MODAL_KEY, "true");
			}
		}
	});
}

function initGame() {
	const container = getElement("game-container");
	if (!container) return;

	initPhysics(container, renderCustomGraphics);

	setupInput(container);
	handleResize();
	window.addEventListener("resize", handleResize);

	setupUIEvents();
	loadDifficultyMode();
	loadBestScore();
	updateScoreDisplay();
	updateGameModeUI();
	setPauseButtonLabel(gameState);
	setNextObject();
}

// Start everything when DOM is ready
if (document.readyState === "loading") {
	document.addEventListener("DOMContentLoaded", initGame);
} else {
	initGame();
}
