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

test('settings tab switch controls expose Korean accessible names and checked state', () => {
  const source = readSource('components/tabs/SettingsTab.js');

  assert.match(source, /role="switch"/);
  assert.match(source, /aria-checked=\{isDark\}/);
  assert.match(source, /aria-label=\{isDark \? '다크모드 끄기' : '다크모드 켜기'\}/);
  assert.match(source, /title=\{isDark \? '다크모드 끄기' : '다크모드 켜기'\}/);
  assert.match(source, /aria-checked=\{isOn\}/);
  assert.match(source, /aria-label=\{`\$\{widget\.label\} 위젯 \$\{isOn \? '숨기기' : '보이기'\}`\}/);
  assert.match(source, /title=\{`\$\{widget\.label\} 위젯 \$\{isOn \? '숨기기' : '보이기'\}`\}/);
  assert.match(source, /aria-hidden="true"/);
  assert.doesNotMatch(source, /aria-label="Theme"/);
  assert.doesNotMatch(source, /aria-label="Widget"/);
});
