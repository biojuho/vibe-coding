import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import test from 'node:test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function readSource(relativePath) {
  return readFileSync(path.join(__dirname, '..', relativePath), 'utf8');
}

test('offline sync thrown errors use stable Korean retry copy', () => {
  const source = readSource('lib/syncManager.js');

  assert.match(source, /OFFLINE_SYNC_RETRY_ERROR_MESSAGE = '오프라인 요청을 동기화하지 못했습니다\. 잠시 후 다시 시도해 주세요\.';/);
  assert.match(source, /const errorMessage = OFFLINE_SYNC_RETRY_ERROR_MESSAGE;/);
  assert.doesNotMatch(source, /error instanceof Error && error\.message/);
  assert.doesNotMatch(source, /threw an unknown error/);
});
