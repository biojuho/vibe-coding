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

test('pen and cattle cards expose keyboard activation semantics', () => {
  const source = readSource('components/ui/cards.js');

  assert.match(source, /function runOnKeyboardActivation\(event, callback\)/);
  assert.match(source, /event\.key !== 'Enter' && event\.key !== ' '/);
  assert.match(source, /const penAlertLabel = hasAlert \? ', 발정 알림 있음' : '';/);
  assert.match(source, /<div className="pen-alert-badge" aria-hidden="true">❤️<\/div>/);
  assert.match(source, /onKeyDown=\{\(event\) => runOnKeyboardActivation\(event, \(\) => onSelect\(buildingId, penNumber\)\)\}/);
  assert.match(source, /aria-label=\{`\$\{penNumber\}번 칸 상세 보기, \$\{cattle\.length\}두 배치됨\$\{penAlertLabel\}`\}/);
  assert.match(source, /onKeyDown=\{\(event\) => runOnKeyboardActivation\(event, \(\) => onClick\(cow\)\)\}/);
  assert.match(source, /const cattleAlertSummary = \[/);
  assert.match(source, /hasEstrusAlert \? \(estrusD===0 \? '오늘 발정 알림' : `발정 \$\{estrusD\}일 전 알림`\) : null/);
  assert.match(source, /hasCalvingAlert \? `분만 \$\{calvingDays\}일 전 알림` : null/);
  assert.match(source, /aria-label=\{cattleAccessibleLabel\}/);
  assert.match(source, /<div className="cattle-chevron" aria-hidden="true">›<\/div>/);
  assert.match(source, /role="button"/);
  assert.match(source, /tabIndex=\{0\}/);
});
