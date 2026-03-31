import Matter from 'matter-js';
import {
    BOMB_EMOJI, BOMB_RADIUS, FRUITS, BOMB_PROBABILITY_PERCENT, 
    GAME_HEIGHT, GAME_WIDTH, DROP_DELAY_MS
} from './config.js';

import {
    score, comboCount, lastMergeAt, dropsSinceMerge, 
    gameState, bestScore, currentFruit, nextFruitLevel,
    isDropping, pendingFruitSpawn, shakeIntensity,
    setScore, setComboCount, setLastMergeAt, setDropsSinceMerge,
    setGameState, setCurrentFruit, setNextFruitLevel,
    setIsDropping, setPendingFruitSpawn,
    updateScoreDisplay, updateComboDisplay,
    syncBestScore, setOverlayHidden, setPauseButtonLabel,
    getActiveDifficultyConfig, triggerHaptic, triggerShake, getElement
} from './main.js';

import { createParticles, explodeBombEffects } from './renderer.js';

export const Engine = Matter.Engine,
    Render = Matter.Render,
    Runner = Matter.Runner,
    Bodies = Matter.Bodies,
    Composite = Matter.Composite,
    Events = Matter.Events,
    World = Matter.World,
    Query = Matter.Query;

export let engine;
export let runner;
export let render;

// Used by renderer to access engine easily
export function getEngine() { return engine; }
export function getRender() { return render; }

export function initPhysics(container, renderCustomGraphics) {
    engine = Engine.create();
    engine.positionIterations = 8;
    engine.velocityIterations = 8;

    render = Render.create({
        element: container,
        engine: engine,
        options: {
            width: GAME_WIDTH,
            height: GAME_HEIGHT,
            wireframes: false,
            background: 'transparent',
            pixelRatio: window.devicePixelRatio
        }
    });

    const WALL_THICKNESS = 60;
    const wallOptions = { isStatic: true, render: { fillStyle: '#bcaaa4', visible: false } };
    const groundOptions = { isStatic: true, render: { fillStyle: '#8d6e63', visible: false } };

    World.add(engine.world, [
        Bodies.rectangle(-WALL_THICKNESS / 2, GAME_HEIGHT / 2, WALL_THICKNESS, GAME_HEIGHT * 2, wallOptions), // Left
        Bodies.rectangle(GAME_WIDTH + WALL_THICKNESS / 2, GAME_HEIGHT / 2, WALL_THICKNESS, GAME_HEIGHT * 2, wallOptions), // Right
        Bodies.rectangle(GAME_WIDTH / 2, GAME_HEIGHT + WALL_THICKNESS / 2 - 60, GAME_WIDTH + 200, WALL_THICKNESS, groundOptions) // Bottom
    ]);

    runner = Runner.create();

    Events.on(render, 'afterRender', renderCustomGraphics);
    Events.on(engine, 'collisionStart', handleCollision);
    Events.on(engine, 'beforeUpdate', () => {
        if (gameState === 'PLAYING') {
            checkGameOver();
            decayComboIfNeeded();
        }
        updateShake();
    });
}

function applyMergeScore(baseScore, mergedFruitCount) {
    const difficulty = getActiveDifficultyConfig();
    const now = Date.now();
    let currentCombo = comboCount;
    if (now - lastMergeAt <= difficulty.comboWindowMs) {
        currentCombo += 1;
    } else {
        currentCombo = 1;
    }
    
    setComboCount(currentCombo);
    setLastMergeAt(now);
    setDropsSinceMerge(0);

    const comboMultiplier = 1 + Math.min(currentCombo - 1, difficulty.comboCap) * difficulty.comboStep;
    const clusterMultiplier = 1 + Math.max(0, mergedFruitCount - 3) * difficulty.clusterStep;
    const scoreGain = Math.round(
        baseScore * (mergedFruitCount - 1) * comboMultiplier * clusterMultiplier
    );

    updateComboDisplay();
    return scoreGain;
}

function handleCollision(event) {
    const pairs = event.pairs;
    const processed = new Set();
    pairs.forEach(pair => {
        const bodyA = pair.bodyA;
        const bodyB = pair.bodyB;

        // 1. Bomb Explosion Logic
        if (bodyA.plugin?.isBomb || bodyB.plugin?.isBomb) {
            const bombBody = bodyA.plugin?.isBomb ? bodyA : bodyB;
            const otherBody = bodyA.plugin?.isBomb ? bodyB : bodyA;
            
            if (bombBody.toBeRemoved) return;
            
            if (otherBody.label === 'fruit' || otherBody.isStatic) {
                bombBody.toBeRemoved = true;
                explodeBomb(bombBody.position.x, bombBody.position.y);
            }
            return;
        }

        if (processed.has(bodyA.id) || processed.has(bodyB.id)) return;

        if (bodyA.label === 'fruit' && bodyB.label === 'fruit' &&
            bodyA.plugin.level === bodyB.plugin.level) {

            if (bodyA.toBeRemoved || bodyB.toBeRemoved) return;
            const level = bodyA.plugin.level;
            if (level === FRUITS.length - 1) return;

            const cluster = getCluster(bodyA, level);
            if (cluster.length >= 3) {
                let sumX = 0, sumY = 0;
                cluster.forEach(b => {
                    sumX += b.position.x; sumY += b.position.y;
                    b.toBeRemoved = true; processed.add(b.id);
                });
                const midX = sumX / cluster.length;
                const midY = sumY / cluster.length;

                cluster.forEach((body) => World.remove(engine.world, body));
                const nextLevel = level + 1;
                const nextData = FRUITS[nextLevel];

                const newBody = Bodies.circle(midX, midY, nextData.radius, {
                    label: 'fruit', render: { visible: false },
                    plugin: { level: nextLevel }, restitution: 0.3
                });
                newBody.immunityUntil = Date.now() + 1000;
                World.add(engine.world, newBody);

                let currentScore = score;
                currentScore += applyMergeScore(nextData.score, cluster.length);
                setScore(currentScore);

                updateScoreDisplay();
                createParticles(midX, midY, nextData.color);
                triggerHaptic(nextLevel >= 4 ? [20, 30, 20] : 14);
                if (nextLevel >= 4) triggerShake(Math.min((nextLevel - 3) * 5, 20));
            }
        }
    });
}

const BOMB_EXPLOSION_RADIUS = 120;
function explodeBomb(x, y) {
    triggerShake(40); // Huge shake
    triggerHaptic([50, 50, 50, 50, 50]);
    
    explodeBombEffects(x, y);
    
    const bombs = Composite.allBodies(engine.world).filter(b => b.plugin?.isBomb);
    bombs.forEach(b => World.remove(engine.world, b));

    const explosionBounds = {
        min: { x: x - BOMB_EXPLOSION_RADIUS, y: y - BOMB_EXPLOSION_RADIUS },
        max: { x: x + BOMB_EXPLOSION_RADIUS, y: y + BOMB_EXPLOSION_RADIUS }
    };
    
    const bodiesInRange = Query.region(Composite.allBodies(engine.world), explosionBounds);
    
    let destroyedCount = 0;
    bodiesInRange.forEach(body => {
        if (body.label === 'fruit' && !body.isStatic) {
            const dx = body.position.x - x;
            const dy = body.position.y - y;
            const dist = Math.sqrt(dx*dx + dy*dy);
            
            if (dist <= BOMB_EXPLOSION_RADIUS) {
                World.remove(engine.world, body);
                destroyedCount++;
                if(Math.random() > 0.5) createParticles(body.position.x, body.position.y, "#333333");
            }
        }
    });
    
    if (destroyedCount > 0) {
        let currentScore = score;
        currentScore += destroyedCount * 5; 
        setScore(currentScore);
        updateScoreDisplay();
    }
}

function getCluster(startBody, level) {
    const cluster = new Set();
    const queue = [startBody];
    cluster.add(startBody);
    const allBodies = Composite.allBodies(engine.world);

    while (queue.length > 0) {
        const current = queue.shift();
        const collisions = Query.collides(current, allBodies);
        collisions.forEach(c => {
            const other = c.bodyA === current ? c.bodyB : c.bodyA;
            if (other.label === 'fruit' && other.plugin.level === level && !other.plugin.isBomb &&
                !other.toBeRemoved && !cluster.has(other)) {
                cluster.add(other);
                queue.push(other);
            }
        });
    }
    return Array.from(cluster);
}

function decayComboIfNeeded() {
    if (comboCount === 0) return;
    if (Date.now() - lastMergeAt <= getActiveDifficultyConfig().comboWindowMs) return;
    setComboCount(0);
    updateComboDisplay();
}

function updateShake() {
    if (shakeIntensity > 0) {
        let newIntensity = shakeIntensity * 0.9;
        if (newIntensity < 0.5) newIntensity = 0;
        triggerShake(newIntensity, true); // true indicates a simple internal set, not the initial trigger
    }
}

function checkGameOver() {
    if (gameState === 'GAMEOVER') return;
    const fruits = Composite.allBodies(engine.world).filter(b => b.label === 'fruit' && !b.isStatic);
    for (let fruit of fruits) {
        if (fruit.immunityUntil && Date.now() < fruit.immunityUntil) continue;
        if (fruit.position.y < 200) {
            if (Math.abs(fruit.velocity.y) < 0.2 && Math.abs(fruit.velocity.x) < 0.2) {
                setGameState('GAMEOVER');
                syncBestScore();
                updateScoreDisplay();
                setOverlayHidden('game-over', false);
                setOverlayHidden('pause-screen', true);
                setPauseButtonLabel();
                triggerHaptic([30, 40, 30]);
                Runner.stop(runner);
                break;
            }
        }
    }
}

export function pickWeightedLevel(weights) {
    const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
    if (totalWeight <= 0) return 0;

    let randomValue = Math.random() * totalWeight;
    for (let index = 0; index < weights.length; index++) {
        randomValue -= weights[index];
        if (randomValue <= 0) {
            return index;
        }
    }
    return 0;
}

export function removeActiveFruits() {
    const activeBodies = Composite.allBodies(engine.world).filter(
        (body) => body.label === 'fruit' || body.label === 'current_fruit'
    );
    activeBodies.forEach((body) => World.remove(engine.world, body));
}

export function createNewFruit(nextIsBomb) {
    if (gameState !== 'PLAYING') return;
    const level = nextFruitLevel;
    const fruitData = FRUITS[level];
    
    // Will be defined in main.js, imported here
    import('./main.js').then(module => {
        module.setNextObject();
    });

    let newFruit;
    if (nextIsBomb) {
        newFruit = Bodies.circle(GAME_WIDTH / 2, 80, BOMB_RADIUS, {
            label: "current_fruit", isStatic: true,
            render: { visible: false }, plugin: { isBomb: true }
        });
    } else {
        newFruit = Bodies.circle(GAME_WIDTH / 2, 80, fruitData.radius, {
            label: "current_fruit", isStatic: true,
            render: { visible: false }, plugin: { level: level, isBomb: false }
        });
    }
    newFruit.immunityUntil = Date.now() + 2000;
    World.add(engine.world, newFruit);
    
    setCurrentFruit(newFruit);
    setIsDropping(false);
    setPendingFruitSpawn(false);
}

export function dropCurrentFruitContext() {
    if (isDropping || gameState !== 'PLAYING' || !currentFruit) return;
    setIsDropping(true);
    setPendingFruitSpawn(true);
    setDropsSinceMerge(dropsSinceMerge + 1);
    
    triggerHaptic(8);
    currentFruit.label = 'fruit';
    Matter.Body.setStatic(currentFruit, false);
    currentFruit.immunityUntil = Date.now() + 2000;
    Matter.Body.setAngularVelocity(currentFruit, (Math.random() - 0.5) * 0.1);
    
    const dropDelay = getActiveDifficultyConfig().dropDelayMs;
    setTimeout(() => {
        if (gameState === 'PLAYING') {
            createNewFruit();
        }
    }, dropDelay);

    setCurrentFruit(null);
}

export function nudgeCurrentFruit(deltaX) {
    if (!currentFruit) return;
    const nextX = currentFruit.position.x + deltaX;
    const clampedX = Math.max(
        currentFruit.circleRadius + 10,
        Math.min(nextX, GAME_WIDTH - currentFruit.circleRadius - 10)
    );
    Matter.Body.setPosition(currentFruit, { x: clampedX, y: 80 });
}

export function moveCurrentFruitTo(pointerX, containerRect) {
    if (!currentFruit) return;
    const scaleX = GAME_WIDTH / containerRect.width;
    let x = (pointerX - containerRect.left) * scaleX;
    x = Math.max(
        currentFruit.circleRadius + 10,
        Math.min(x, GAME_WIDTH - currentFruit.circleRadius - 10)
    );
    Matter.Body.setPosition(currentFruit, { x, y: 80 });
}

export function getTopFruitY() {
    const fruits = Composite.allBodies(engine.world).filter(
        (body) => body.label === 'fruit' && !body.isStatic
    );
    if (fruits.length === 0) return GAME_HEIGHT;
    return Math.min(...fruits.map((fruit) => fruit.position.y));
}
