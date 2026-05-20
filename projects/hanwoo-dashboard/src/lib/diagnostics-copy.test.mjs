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

test('admin diagnostics page uses Korean operations copy for visible states', () => {
  const source = readSource('components/admin/DiagnosticsPageClient.js');
  const systemActions = readSource('lib/actions/system.js');

  assert.match(source, /운영 진단/);
  assert.match(source, /시스템 상태 점검/);
  assert.match(source, /데이터베이스 상태/);
  assert.match(source, /레코드를 불러오는 중입니다/);
  assert.match(source, /대시보드로 돌아가기/);
  assert.match(source, /원본 데이터를 불러오지 못했습니다/);
  assert.match(source, /MODEL_OPTIONS/);
  assert.match(systemActions, /status: '정상'/);
  assert.match(systemActions, /status: '연결 실패'/);
  assert.match(systemActions, /latency: '확인 불가'/);
  assert.doesNotMatch(source, /System Diagnostics/);
  assert.doesNotMatch(source, /Database Status/);
  assert.doesNotMatch(source, /Loading records/);
  assert.doesNotMatch(source, /Please try again in a moment/);
  assert.doesNotMatch(systemActions, /status: 'Online'/);
  assert.doesNotMatch(systemActions, /status: 'Offline'/);
  assert.doesNotMatch(systemActions, /latency: 'N\/A'/);
});
