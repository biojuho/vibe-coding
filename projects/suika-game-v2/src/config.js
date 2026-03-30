// config.js
export const BOMB_EMOJI = '💣';
export const BOMB_PROBABILITY_PERCENT = 3;
export const BOMB_EXPLOSION_RADIUS = 120;
export const BOMB_RADIUS = 28;
export const GAME_WIDTH = 480;
export const GAME_HEIGHT = 800;
export const WALL_THICKNESS = 60;
export const DROP_DELAY_MS = 800;
export const BEST_SCORE_KEY = 'suika_v2_best_score';
export const EXIT_MODAL_KEY = 'suika_v2_exit_modal_shown';
export const DIFFICULTY_KEY = 'suika_v2_difficulty';
export const COMBO_WINDOW_MS = 2200;

export const SPAWN_PROFILES = [
    { minScore: 0, weights: [45, 35, 15, 5, 0] },
    { minScore: 700, weights: [35, 34, 20, 10, 1] },
    { minScore: 1800, weights: [25, 31, 24, 16, 4] },
    { minScore: 3200, weights: [18, 28, 28, 20, 6] }
];

export const DIFFICULTY_PRESETS = {
    casual: {
        label: 'Casual',
        dropDelayMs: DROP_DELAY_MS + 180,
        comboWindowMs: COMBO_WINDOW_MS + 1000,
        comboStep: 0.16,
        comboCap: 4,
        clusterStep: 0.12,
        rescueAfterDrops: 3,
        guaranteedRescueAfter: 6,
        spawnProfiles: [
            { minScore: 0, weights: [56, 31, 10, 3, 0] },
            { minScore: 900, weights: [47, 31, 15, 6, 1] },
            { minScore: 2200, weights: [38, 29, 20, 10, 3] },
            { minScore: 4200, weights: [30, 26, 23, 15, 6] }
        ]
    },
    normal: {
        label: 'Normal',
        dropDelayMs: DROP_DELAY_MS,
        comboWindowMs: COMBO_WINDOW_MS,
        comboStep: 0.2,
        comboCap: 5,
        clusterStep: 0.15,
        rescueAfterDrops: 5,
        guaranteedRescueAfter: 8,
        spawnProfiles: SPAWN_PROFILES
    },
    hard: {
        label: 'Hard',
        dropDelayMs: DROP_DELAY_MS - 160,
        comboWindowMs: COMBO_WINDOW_MS - 900,
        comboStep: 0.3,
        comboCap: 7,
        clusterStep: 0.22,
        rescueAfterDrops: 9,
        guaranteedRescueAfter: 12,
        spawnProfiles: [
            { minScore: 0, weights: [34, 33, 21, 10, 2] },
            { minScore: 900, weights: [26, 30, 25, 15, 4] },
            { minScore: 2200, weights: [19, 26, 28, 20, 7] },
            { minScore: 4200, weights: [13, 21, 29, 25, 12] }
        ]
    }
};

export const FRUITS = [
    { radius: 15, label: "🍒", color: "#FF1744", score: 10 },
    { radius: 25, label: "🍓", color: "#F50057", score: 20 },
    { radius: 35, label: "🍇", color: "#AA00FF", score: 30 },
    { radius: 45, label: "🍊", color: "#FF9100", score: 40 },
    { radius: 60, label: "🫐", color: "#FF3D00", score: 50 },
    { radius: 75, label: "🍎", color: "#D50000", score: 60 },
    { radius: 90, label: "🍏", color: "#AEEA00", score: 70 },
    { radius: 105, label: "🍑", color: "#FFAB91", score: 80 },
    { radius: 120, label: "🍍", color: "#FFD600", score: 90 },
    { radius: 135, label: "🍈", color: "#00E676", score: 100 },
    { radius: 155, label: "🍉", color: "#00C853", score: 110 }
];
