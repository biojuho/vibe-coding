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
  assert.match(source, /const launcherRef = useRef\(null\)/);
  assert.match(source, /const shouldRestoreLauncherFocusRef = useRef\(false\)/);
  assert.match(source, /shouldRestoreLauncherFocusRef\.current = true/);
  assert.match(source, /launcherRef\.current\?\.focus\(\)/);
  assert.match(source, /ref=\{launcherRef\}/);
  assert.match(source, /role="dialog"/);
  assert.match(source, /aria-modal="true"/);
  assert.match(source, /aria-label="AI 농장 비서 채팅"/);
  assert.match(source, /const panelRef = useRef\(null\)/);
  assert.match(source, /panelRef\.current\?\.focus\(\)/);
  assert.match(source, /ref=\{panelRef\}/);
  assert.match(source, /tabIndex=\{-1\}/);
  assert.match(source, /role="log"/);
  assert.match(source, /aria-live="polite"/);
  assert.match(source, /aria-relevant="additions text"/);
  assert.match(source, /aria-label="AI 농장 비서 대화 내용"/);
  assert.match(source, /if \(event\.key === 'Escape'\)/);
  assert.match(source, /closeWidget\(\)/);
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
