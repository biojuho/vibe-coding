# Suika Game v2 (Pro Edition)

Physics-based fruit merge game built with Matter.js and HTML5 Canvas.

## What Is Improved

- Stable in-round restart without full page reload
- Pause and resume (`P` key + Pause button)
- Keyboard controls (`ArrowLeft`, `ArrowRight`, `Space`, `Enter`, `R`)
- Best score persistence with `localStorage`
- Combo scoring system with visual combo badge
- Score-based spawn difficulty curve
- Difficulty presets (`Casual`, `Normal`, `Hard`) with persistent selection
- No-merge rescue weighting to avoid dead rounds
- HUD mode indicator + high-risk/high-reward tuning by mode
- Mobile haptic feedback on drop/merge/game over
- Cleaned event binding (removed duplicate UI handler definitions)

## Controls

- Move: Mouse / Touch drag / `ArrowLeft` / `ArrowRight`
- Drop: Mouse up / Touch end / `Space` / `Enter`
- Pause: `P` or Pause button
- Restart after game over: `R` or Try Again

## Run

1. Install dependencies

   ```bash
   npm install
   ```

1. Start game
   - Open `src/index.html` directly in browser, or

   ```bash
   npm start
   ```

## Scripts

- `npm start`: open `src/index.html`
- `npm run gen:ppt`: generate overview PPT

## Structure

- `src/index.html`: game source (render, physics, input, UI)
- `scripts/generate_ppt.js`: PPT generation script
- `docs/`: presentation artifacts
