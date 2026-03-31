import { 
    DIFFICULTY_PRESETS, FRUITS, BEST_SCORE_KEY, 
    EXIT_MODAL_KEY, DIFFICULTY_KEY, BOMB_PROBABILITY_PERCENT, BOMB_EMOJI 
} from './config.js';

import {
    initPhysics, engine, runner, render, pickWeightedLevel, 
    removeActiveFruits, createNewFruit, getTopFruitY,
    dropCurrentFruitContext, moveCurrentFruitTo, nudgeCurrentFruit
} from './physics.js';

import {
    renderCustomGraphics, handleResize, setParticles
} from './renderer.js';

import {
    getElement, setText, updateScoreDisplay, updateBestScoreDisplay,
    updateComboDisplay, updateDifficultyButtons, updateModeDisplay,
    setPauseButtonLabel, setOverlayHidden, getStoredValue,
    setStoredValue, removeStoredValue
} from './ui.js';

// --- Global State ---
export let currentFruit = null;
export let nextFruitLevel = 0;
export let isDropping = false;
export let score = 0;
export let gameState = 'START'; // 'START' | 'PLAYING' | 'PAUSED' | 'GAMEOVER'
export let bestScore = 0;
export let inputBound = false;
export let uiEventsBound = false;
export let renderStarted = false;
export let pendingFruitSpawn = false;
export let shakeIntensity = 0;
export let comboCount = 0;
export let lastMergeAt = 0;
export let difficultyMode = 'normal';
export let dropsSinceMerge = 0;

// Setters for external modules
export function setScore(val) { score = val; }
export function setComboCount(val) { comboCount = val; }
export function setLastMergeAt(val) { lastMergeAt = val; }
export function setDropsSinceMerge(val) { dropsSinceMerge = val; }
export function setGameState(val) { gameState = val; }
export function setCurrentFruit(val) { currentFruit = val; }
export function setNextFruitLevel(val) { nextFruitLevel = val; }
export function setIsDropping(val) { isDropping = val; }
export function setPendingFruitSpawn(val) { pendingFruitSpawn = val; }

export function getActiveDifficultyConfig() {
    return DIFFICULTY_PRESETS[difficultyMode] || DIFFICULTY_PRESETS.normal;
}

export function triggerHaptic(pattern) {
    if (!navigator.vibrate) return;
    navigator.vibrate(pattern);
}

export function triggerShake(intensity, internal = false) { 
    if(!internal) {
        shakeIntensity = intensity; 
    } else {
        shakeIntensity = intensity;
    }
}

export { updateScoreDisplay, updateComboDisplay, getElement, setOverlayHidden, setPauseButtonLabel };

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
    setParticles([]);
    shakeIntensity = 0;
    currentFruit = null;
    isDropping = false;
    pendingFruitSpawn = false;
    updateScoreDisplay();
    updateComboDisplay();
    setOverlayHidden('game-over', true);
    setOverlayHidden('exit-modal', true);
    setOverlayHidden('pause-screen', true);
    removeStoredValue(EXIT_MODAL_KEY);
}

function getSpawnWeightsForScore(currentScore) {
    const profiles = getActiveDifficultyConfig().spawnProfiles;
    let selectedProfile = profiles[0];
    for (const profile of profiles) {
        if (currentScore >= profile.minScore) {
            selectedProfile = profile;
        }
    }
    return [...selectedProfile.weights];
}

function applyRescueWeights(weights) {
    const difficulty = getActiveDifficultyConfig();
    const rescueAfterDrops = difficulty.rescueAfterDrops;
    if (dropsSinceMerge < rescueAfterDrops) return weights;

    const rescued = [...weights];
    rescued[0] += 18;
    rescued[1] += 10;
    if (rescued.length > 4) {
        rescued[4] = Math.max(0, rescued[4] - 8);
    }

    const topFruitY = getTopFruitY();
    if (topFruitY < 250) {
        rescued[0] += 12;
        rescued[1] += 8;
        rescued[2] += 4;
        if (rescued.length > 4) {
            rescued[4] = Math.max(0, rescued[4] - 6);
        }
    }

    if (topFruitY < 215) {
        rescued[0] += 18;
        rescued[1] += 12;
        if (rescued.length > 3) {
            rescued[3] = Math.max(0, rescued[3] - 8);
        }
        if (rescued.length > 4) {
            rescued[4] = Math.max(0, rescued[4] - 10);
        }
    }

    return rescued;
}

let nextIsBomb = false;

export function setNextObject() {
    const difficulty = getActiveDifficultyConfig();
    nextIsBomb = false;
    
    if (Math.random() * 100 < BOMB_PROBABILITY_PERCENT) {
        nextFruitLevel = 0;
        nextIsBomb = true;
    } else if (dropsSinceMerge >= difficulty.guaranteedRescueAfter) {
        nextFruitLevel = 0;
    } else {
        const baseWeights = getSpawnWeightsForScore(score);
        const adjustedWeights = applyRescueWeights(baseWeights);
        nextFruitLevel = pickWeightedLevel(adjustedWeights);
    }
    const nextDisplay = getElement('next-fruit-display');
    if (nextDisplay) {
        if (nextIsBomb) {
            nextDisplay.innerText = BOMB_EMOJI;
            nextDisplay.style.color = 'red';
        } else {
            nextDisplay.innerText = FRUITS[nextFruitLevel].label;
            nextDisplay.style.color = '';
        }

        nextDisplay.style.transform = 'scale(0.5)';
        setTimeout(() => nextDisplay.style.transform = 'scale(1)', 150);
    }
}

function startGame() {
    resetRoundState();
    removeActiveFruits();

    gameState = 'PLAYING';
    setOverlayHidden('start-screen', true);

    if (!renderStarted) {
        Matter.Render.run(render);
        renderStarted = true;
    }

    Matter.Runner.stop(runner);
    Matter.Runner.run(runner, engine);
    setPauseButtonLabel(gameState);

    setNextObject();
    createNewFruit(nextIsBomb);
}

function restartGame() {
    const adConfirmed = confirm("팝업 [전면 광고 시뮬레이션]\n\n광고가 재생됩니다. (확인을 누르면 게임이 재시작됩니다)");
    if (adConfirmed) {
        startGame();
    }
}

function togglePause() {
    if (gameState === 'PLAYING') {
        gameState = 'PAUSED';
        triggerHaptic(10);
        Matter.Runner.stop(runner);
        setOverlayHidden('pause-screen', false);
        setPauseButtonLabel(gameState);
        return;
    }

    if (gameState !== 'PAUSED') return;

    gameState = 'PLAYING';
    triggerHaptic(6);
    setOverlayHidden('pause-screen', true);
    Matter.Runner.run(runner, engine);
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
        difficultyMode = 'normal';
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
        if (isDropping || gameState !== 'PLAYING' || !currentFruit) return;
        const pointX = event.touches ? event.touches[0].clientX : event.clientX;
        moveCurrentFruitTo(pointX, container.getBoundingClientRect());
    };

    container.addEventListener('touchstart', move, { passive: true });
    container.addEventListener('mousemove', move);
    container.addEventListener('touchmove', move, { passive: true });
    container.addEventListener('mouseup', dropCurrentFruitContext);
    container.addEventListener('touchend', dropCurrentFruitContext);
    container.addEventListener('touchcancel', () => {
        if (gameState === 'PLAYING') {
            isDropping = false;
        }
    });

    window.addEventListener('keydown', (event) => {
        if (event.key.toLowerCase() === 'p') {
            togglePause();
            return;
        }

        if (event.key.toLowerCase() === 'r' && gameState === 'GAMEOVER') {
            restartGame();
            return;
        }

        if (gameState !== 'PLAYING' || !currentFruit) return;

        if (event.key === 'ArrowLeft') {
            event.preventDefault();
            nudgeCurrentFruit(-24);
            return;
        }

        if (event.key === 'ArrowRight') {
            event.preventDefault();
            nudgeCurrentFruit(24);
            return;
        }

        if (event.key === ' ' || event.key === 'Enter') {
            event.preventDefault();
            dropCurrentFruitContext();
        }
    });
}

function setupUIEvents() {
    if (uiEventsBound) return;
    uiEventsBound = true;

    const startButton = getElement('start-btn');
    if (startButton) {
        startButton.addEventListener('click', startGame);
    }

    const shareButton = getElement('share-btn');
    if (shareButton) {
        shareButton.addEventListener('click', async () => {
            const modeLabel = getActiveDifficultyConfig().label;
            const shareData = {
                title: 'Suika Match-3 Challenge',
                text: `I scored ${score} points in ${modeLabel} mode!`,
                url: window.location.href
            };

            try {
                if (navigator.share) {
                    await navigator.share(shareData);
                } else {
                    await navigator.clipboard.writeText(`${shareData.text}\n${shareData.url}`);
                    alert('Score copied to clipboard.');
                }
            } catch (error) {
                console.error('Error sharing:', error);
            }
        });
    }

    const restartButton = getElement('restart-btn');
    if (restartButton) {
        restartButton.addEventListener('click', restartGame);
    }

    const pauseButton = getElement('pause-btn');
    if (pauseButton) {
        pauseButton.addEventListener('click', togglePause);
    }

    const difficultyButtons = document.querySelectorAll('.difficulty-btn');
    difficultyButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const mode = e.target.getAttribute('data-difficulty');
            if (mode) setDifficultyMode(mode);
        });
    });

    const leaveBtn = getElement('leave-btn');
    if (leaveBtn) {
        leaveBtn.addEventListener('click', () => {
            setOverlayHidden('exit-modal', true);
        });
    }

    const stayBtn = getElement('stay-btn');
    if (stayBtn) {
        stayBtn.addEventListener('click', () => {
            setOverlayHidden('exit-modal', true);
            if (gameState === 'PAUSED') {
                togglePause();
            }
        });
    }

    document.addEventListener('mouseleave', (e) => {
        if (e.clientY <= 0 || e.clientX <= 0 || (e.clientX >= window.innerWidth || e.clientY >= window.innerHeight)) {
            if (gameState === 'PLAYING' && !getStoredValue(EXIT_MODAL_KEY)) {
                togglePause();
                setOverlayHidden('exit-modal', false);
                setStoredValue(EXIT_MODAL_KEY, 'true');
            }
        }
    });
}

function initGame() {
    const container = getElement('game-container');
    if (!container) return;

    initPhysics(container, renderCustomGraphics);

    setupInput(container);
    handleResize();
    window.addEventListener('resize', handleResize);

    setupUIEvents();
    loadDifficultyMode();
    loadBestScore();
    updateScoreDisplay();
    setPauseButtonLabel(gameState);
    setNextObject();
}

// Start everything when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGame);
} else {
    initGame();
}
