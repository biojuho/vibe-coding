import Matter from 'matter-js';
import { GAME_WIDTH, GAME_HEIGHT, BOMB_RADIUS, FRUITS, BOMB_EMOJI } from './config.js';
import { gameState, shakeIntensity, getElement } from './main.js';
import { getEngine, getRender } from './physics.js';

export let particles = [];

const loadedImages = {};
function getFruitImage(src) {
    if (!loadedImages[src]) {
        const img = new Image();
        img.src = src;
        loadedImages[src] = img;
    }
    return loadedImages[src];
}

export function renderCustomGraphics() {
    const render = getRender();
    const engine = getEngine();
    if(!render || !engine) return;

    const ctx = render.context;

    if (shakeIntensity > 0) {
        const dx = (Math.random() - 0.5) * shakeIntensity;
        const dy = (Math.random() - 0.5) * shakeIntensity;
        ctx.translate(dx, dy);
    }

    // Draw Guide Line under potential fruit
    const currentFruit = Matter.Composite.allBodies(engine.world).find(b => b.label === 'current_fruit' && b.isStatic);
    import('./main.js').then(({ isDropping }) => {
        if (currentFruit && gameState === 'PLAYING' && !isDropping) {
            drawGuideLine(ctx, currentFruit.position.x, currentFruit.position.y, currentFruit.circleRadius);
        }
    });

    ctx.globalAlpha = 1.0;
    ctx.shadowBlur = 0;
    ctx.filter = "none";

    const bodies = Matter.Composite.allBodies(engine.world);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    bodies.forEach(body => {
        if (body.plugin?.isBomb && !body.toBeRemoved) {
            const size = BOMB_RADIUS * 2.5;

            ctx.save();
            ctx.translate(body.position.x, body.position.y);
            ctx.rotate(body.angle);

            const img = getFruitImage('./assets/bomb.png');
            if (img.complete && img.naturalHeight !== 0) {
                ctx.drawImage(img, -size/2, -size/2, size, size);
            } else {
                ctx.fillStyle = "#000000";
                ctx.font = `${size}px "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif`;
                ctx.fillText(BOMB_EMOJI, 0, 5);
            }
            ctx.restore();
        } else if (body.label === 'fruit' || body.label === 'current_fruit') {
            const level = body.plugin.level;
            const fruitData = FRUITS[level];
            const size = fruitData.radius * 2.3;

            ctx.save();
            ctx.translate(body.position.x, body.position.y);

            ctx.rotate(body.angle);

            const img = getFruitImage(`./assets/${level}.png`);
            if (img.complete && img.naturalHeight !== 0) {
                ctx.drawImage(img, -size/2, -size/2, size, size);
            } else {
                ctx.fillStyle = "#000000";
                ctx.font = `${size}px "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif`;
                ctx.fillText(fruitData.label, 0, 5);
            }

            ctx.restore();
        }
    });

    if (gameState !== 'GAMEOVER') {
        ctx.beginPath();
        ctx.moveTo(0, 200);
        ctx.lineTo(GAME_WIDTH, 200);
        ctx.strokeStyle = 'rgba(255, 69, 58, 0.5)'; // More subtle line
        ctx.lineWidth = 2;
        ctx.setLineDash([10, 10]);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    updateAndDrawParticles(ctx);

    if (shakeIntensity > 0) ctx.setTransform(1, 0, 0, 1, 0, 0);
}

// --- Effects ---
export function createParticles(x, y, color) {
    const particleCount = 20; // More particles!
    const colors = [color, '#ffffff', '#FFD700']; // Fruit color + White + Gold

    for (let i = 0; i < particleCount; i++) {
        const shapeType = Math.random() > 0.6 ? 'circle' : (Math.random() > 0.5 ? 'square' : 'star');
        const pColor = colors[Math.floor(Math.random() * colors.length)];

        particles.push({
            x: x,
            y: y,
            vx: (Math.random() - 0.5) * 12, // Explode faster
            vy: (Math.random() - 0.5) * 12,
            life: 1.0 + Math.random() * 0.5,
            color: pColor,
            size: Math.random() * 6 + 4,
            rotation: Math.random() * Math.PI * 2,
            rotationSpeed: (Math.random() - 0.5) * 0.2,
            shape: shapeType
        });
    }
}

export function explodeBombEffects(x, y) {
    for (let i = 0; i < 3; i++) {
        createParticles(x + (Math.random()-0.5)*50, y + (Math.random()-0.5)*50, "#FF3D00");
        createParticles(x + (Math.random()-0.5)*50, y + (Math.random()-0.5)*50, "#FF0000");
        createParticles(x + (Math.random()-0.5)*50, y + (Math.random()-0.5)*50, "#000000");
    }
}

function updateAndDrawParticles(ctx) {
    for (let i = particles.length - 1; i >= 0; i--) {
        let p = particles[i];

        // Physics
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.3; // Gravity
        p.vx *= 0.95; // Friction
        p.vy *= 0.95;
        p.rotation += p.rotationSpeed;
        p.life -= 0.02;

        // Draw
        ctx.save();
        ctx.globalAlpha = Math.max(0, p.life);
        ctx.fillStyle = p.color;
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rotation);

        if (p.shape === 'square') {
            ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
        } else if (p.shape === 'star') {
            drawStar(ctx, 0, 0, 5, p.size, p.size / 2);
        } else {
            ctx.beginPath();
            ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.restore();

        if (p.life <= 0) particles.splice(i, 1);
    }
}

// Helper for Star shape
function drawStar(ctx, cx, cy, spikes, outerRadius, innerRadius) {
    let rot = Math.PI / 2 * 3;
    let x = cx;
    let y = cy;
    let step = Math.PI / spikes;

    ctx.beginPath();
    ctx.moveTo(cx, cy - outerRadius);
    for (let i = 0; i < spikes; i++) {
        x = cx + Math.cos(rot) * outerRadius;
        y = cy + Math.sin(rot) * outerRadius;
        ctx.lineTo(x, y);
        rot += step;

        x = cx + Math.cos(rot) * innerRadius;
        y = cy + Math.sin(rot) * innerRadius;
        ctx.lineTo(x, y);
        rot += step;
    }
    ctx.lineTo(cx, cy - outerRadius);
    ctx.closePath();
    ctx.fill();
}

function drawGuideLine(ctx, x, y, radius) {
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x, y + radius + 5);
    ctx.lineTo(x, GAME_HEIGHT - 60); // To static floor level
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 4;
    ctx.setLineDash([10, 15]);
    ctx.lineCap = 'round';
    ctx.globalAlpha = 0.5;
    ctx.stroke();

    // Landing dot
    ctx.beginPath();
    ctx.arc(x, GAME_HEIGHT - 70, 6, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.restore();
}

export function handleResize() {
    const container = getElement('game-container');
    if (!container) return;
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    const scaleX = Math.min(1, (windowWidth - 20) / GAME_WIDTH);
    const scaleY = Math.min(1, (windowHeight - 20) / GAME_HEIGHT);
    const scale = Math.min(scaleX, scaleY);
    container.style.transform = `scale(${scale})`;
}

export function setParticles(newParticles) {
    particles = newParticles;
}
