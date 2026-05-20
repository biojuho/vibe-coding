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

test('server action user-facing failures use Korean product copy', () => {
  const cattleActions = readSource('lib/actions/cattle.js');
  const salesActions = readSource('lib/actions/sales.js');
  const buildingActions = readSource('lib/actions/building.js');
  const farmSettingsActions = readSource('lib/actions/farm-settings.js');
  const systemActions = readSource('lib/actions/system.js');

  assert.match(cattleActions, /개체 목록을 불러오지 못했습니다/);
  assert.match(salesActions, /판매 기록을 불러오지 못했습니다/);
  assert.match(buildingActions, /축사 정보를 추가하지 못했습니다/);
  assert.match(buildingActions, /축사를 삭제하지 못했습니다/);
  assert.match(farmSettingsActions, /농장 정보를 저장하지 못했습니다/);
  assert.match(systemActions, /지원하지 않는 데이터 유형입니다/);

  assert.doesNotMatch(cattleActions, /Failed to fetch cattle data/);
  assert.doesNotMatch(salesActions, /Failed to fetch sales records/);
  assert.doesNotMatch(buildingActions, /message: e\.message/);
  assert.doesNotMatch(farmSettingsActions, /message: e\.message/);
  assert.doesNotMatch(systemActions, /Invalid model name/);
});
