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

test('home dashboard fallback and panel labels use Korean product copy', () => {
  const source = readSource('components/DashboardClient.js');

  assert.match(source, /Joolife 한우 농장/);
  assert.match(source, /오늘 요약/);
  assert.match(source, /빠른 기록/);
  assert.match(source, /운영 준비/);
  assert.doesNotMatch(source, /Joolife Dashboard/);
  assert.doesNotMatch(source, /Today Brief/);
  assert.doesNotMatch(source, /Quick Record/);
  assert.doesNotMatch(source, /Farm Setup/);
});

test('market price widget uses Korean product copy for visible states', () => {
  const source = readSource('components/widgets/MarketPriceWidget.js');

  assert.match(source, /한우 시세를 불러오는 중입니다/);
  assert.match(source, /지금은 한우 시세 데이터를 확인할 수 없습니다/);
  assert.match(source, /시세 흐름/);
  assert.match(source, /한우 도매 시세/);
  assert.match(source, /가중평균 거래가/);
  assert.match(source, /실시간 KAPE/);
  assert.match(source, /저장된 KAPE/);
  assert.match(source, /이전 저장가/);
  assert.match(source, /수소 \/ kg/);
  assert.match(source, /암소 \/ kg/);
  assert.match(source, /갱신/);
  assert.match(source, /출처: KAPE/);
  assert.doesNotMatch(source, /Loading market prices/);
  assert.doesNotMatch(source, /Market price data is unavailable/);
  assert.doesNotMatch(source, /Market Pulse/);
  assert.doesNotMatch(source, /Hanwoo Market Prices/);
  assert.doesNotMatch(source, /weighted average transaction price/);
  assert.doesNotMatch(source, /Live KAPE|Cached KAPE|Stale Cache|Unavailable/);
  assert.doesNotMatch(source, /Bull \/ kg|Cow \/ kg/);
  assert.doesNotMatch(source, />Updated /);
  assert.doesNotMatch(source, />Source: KAPE/);
});
