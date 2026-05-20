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

test('legal pages expose stable support channels without personal contact details', () => {
  const privacySource = readSource('app/privacy/page.js');
  const termsSource = readSource('app/terms/page.js');
  const combinedSource = `${privacySource}\n${termsSource}`;

  assert.match(privacySource, /담당: Joolife 운영팀/);
  assert.match(privacySource, /이메일: joolife@joolife\.io\.kr/);
  assert.match(privacySource, /문의 채널: 서비스 운영 문의/);
  assert.match(termsSource, /문의 이메일: joolife@joolife\.io\.kr/);
  assert.match(termsSource, /웹사이트: joolife\.io\.kr/);
  assert.doesNotMatch(combinedSource, /010-\d{4}-\d{4}/);
  assert.doesNotMatch(combinedSource, /경기도 안양시/);
  assert.doesNotMatch(combinedSource, /공작부영아파트/);
  assert.doesNotMatch(combinedSource, /대표자: 박주호/);
  assert.doesNotMatch(combinedSource, /성명: 박주호/);
});
