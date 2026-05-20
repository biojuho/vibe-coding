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

test('AI chat widget handles Korean configuration errors and exposes an accessible launcher', () => {
  const source = readSource('components/widgets/AIChatWidget.js');

  assert.match(source, /AI 비서 설정/);
  assert.match(source, /설정 키/);
  assert.match(source, /aria-label="AI 농장 비서 열기"/);
  assert.match(source, /title="AI 농장 비서"/);
  assert.match(source, /aria-label="AI 농장 비서에게 보낼 질문"/);
  assert.match(source, /title="AI 농장 비서에게 보낼 질문"/);
  assert.match(source, /aria-label=\{isStreaming \? '답변 생성 중' : '질문 보내기'\}/);
  assert.match(source, /title=\{isStreaming \? '답변 생성 중' : '질문 보내기'\}/);
  assert.match(source, /AI 비서 연결이 잠시 불안정합니다/);
  assert.match(source, /<Bot size=\{25\} aria-hidden="true" \/>/);
  assert.doesNotMatch(source, />AI\s*<\/button>/);
  assert.doesNotMatch(source, /aria-label="Send"/);
  assert.doesNotMatch(source, /onError\(error\.message/);
});
