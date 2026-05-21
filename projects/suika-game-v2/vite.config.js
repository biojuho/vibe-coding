import { defineConfig } from 'vite';

// Relative base so the built game can be hosted from any sub-path
// (GitHub Pages, itch.io, a CDN folder, ...).
export default defineConfig({
    base: './',
    test: {
        environment: 'jsdom',
        include: ['src/**/*.test.js'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'html'],
            // Only the deterministic logic modules carry meaningful coverage.
            // main/physics/renderer are DOM- and canvas-bound integration code.
            include: ['src/prng.js', 'src/daily.js'],
        },
    },
});
