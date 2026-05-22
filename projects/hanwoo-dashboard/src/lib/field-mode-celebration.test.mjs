import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, '..');

function readSource(relativePath) {
  return readFileSync(path.join(SRC_ROOT, relativePath), 'utf8');
}

test('audio synthesizer library exports playTriumphantChime', () => {
  const source = readSource('lib/audio.js');

  assert.match(source, /export function playTriumphantChime\s*\(/);
  assert.match(source, /const notes = \[261.63, 329.63, 392.00, 523.25\]/);
  assert.match(source, /notes\.forEach\(/);
  assert.match(source, /osc\.connect\(gain\)/);
  assert.match(source, /gain\.connect\(ctx\.destination\)/);
});

test('FieldModeView imports playTriumphantChime and sets up celebration refs', () => {
  const source = readSource('components/widgets/FieldModeView.js');

  assert.match(source, /playTriumphantChime/);
  assert.match(source, /const \[showCelebration, setShowCelebration\] = useState\(false\)/);
  assert.match(source, /const celebrationCanvasRef = useRef\(null\)/);
});

test('FieldModeView triggers playTriumphantChime and celebration state when checklist becomes 100% completed', () => {
  const source = readSource('components/widgets/FieldModeView.js');

  assert.match(source, /const previouslyCompletedAll = checklist\.length > 0 && checklist\.every/);
  assert.match(source, /const currentlyCompletedAll = updated\.length > 0 && updated\.every/);
  assert.match(source, /if \(!previouslyCompletedAll && currentlyCompletedAll\) \{/);
  assert.match(source, /allCompletedAfterToggle = true;/);
  assert.match(source, /if \(allCompletedAfterToggle\) \{/);
  assert.match(source, /playTriumphantChime\(\)/);
  assert.match(source, /setShowCelebration\(true\)/);
});

test('FieldModeView mounts the celebration canvas with mixBlendMode screen', () => {
  const source = readSource('components/widgets/FieldModeView.js');

  assert.match(source, /\{showCelebration && \(/);
  assert.match(source, /ref=\{celebrationCanvasRef\}/);
  assert.match(source, /style=\{\{\s*mixBlendMode:\s*'screen'\s*\}\}/);
});

test('FieldModeView sets up a beautiful dynamic particle confetti simulation', () => {
  const source = readSource('components/widgets/FieldModeView.js');

  assert.match(source, /useEffect\(\(\) => \{/);
  assert.match(source, /if \(!showCelebration\) return;/);
  assert.match(source, /const particles = \[\];/);
  assert.match(source, /createFirework/);
  assert.match(source, /p\.vy \+= 0\.15/); // gravity
  assert.match(source, /p\.vx \*= 0\.98/); // friction
  assert.match(source, /animationId = requestAnimationFrame\(animate\)/);
});
