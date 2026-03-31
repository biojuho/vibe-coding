import { getActiveDifficultyConfig, score, bestScore, comboCount, difficultyMode } from './main.js';

export function getElement(id) {
    return document.getElementById(id);
}

export function setText(id, value) {
    const element = getElement(id);
    if (element) element.innerText = value;
}

export function updateScoreDisplay() {
    setText('score', score.toString());
    setText('final-score', score.toString());
}

export function updateBestScoreDisplay() {
    setText('best-score', bestScore.toString());
}

export function updateComboDisplay() {
    const comboElement = getElement('combo-text');
    if (!comboElement) return;

    if (comboCount < 2) {
        comboElement.classList.add('hidden');
        return;
    }

    const difficulty = getActiveDifficultyConfig();
    const comboMultiplier = 1 + Math.min(comboCount - 1, difficulty.comboCap) * difficulty.comboStep;
    comboElement.innerText = `Combo x${comboCount} (${comboMultiplier.toFixed(1)}x)`;
    comboElement.classList.remove('hidden');
    comboElement.style.transform = 'scale(0.8)';
    requestAnimationFrame(() => {
        comboElement.style.transform = 'scale(1)';
    });
}

export function updateDifficultyButtons() {
    const buttons = document.querySelectorAll('.difficulty-btn');
    buttons.forEach((button) => {
        const mode = button.getAttribute('data-difficulty');
        button.classList.toggle('active', mode === difficultyMode);
    });
}

export function updateModeDisplay() {
    setText('mode-text', getActiveDifficultyConfig().label);
}

export function setPauseButtonLabel(gameState) {
    const pauseButton = getElement('pause-btn');
    if (!pauseButton) return;
    pauseButton.innerText = gameState === 'PAUSED' ? 'Resume' : 'Pause';
}

export function setOverlayHidden(id, hidden) {
    const overlay = getElement(id);
    if (!overlay) return;
    overlay.classList.toggle('hidden', hidden);
}

export function getStoredValue(key) {
    try {
        return localStorage.getItem(key);
    } catch (_error) {
        return null;
    }
}

export function setStoredValue(key, value) {
    try {
        localStorage.setItem(key, value);
    } catch (_error) {
        // no-op
    }
}

export function removeStoredValue(key) {
    try {
        localStorage.removeItem(key);
    } catch (_error) {
        // no-op
    }
}
