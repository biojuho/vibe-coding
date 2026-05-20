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

test('profitability service surfaces Korean operator-facing error copy', () => {
  const source = readSource('lib/dashboard/profitability-service.js');

  // These thrown messages flow through `error: err.message` into
  // ProfitabilityWidget, which renders `{error}` as visible UI text.
  assert.match(source, /수익성 시뮬레이션에 사용할 시세 데이터가 없습니다/);
  assert.match(source, /시세 데이터를 해석하지 못했습니다/);
  assert.match(source, /수익성 추정 오류/);

  assert.doesNotMatch(source, /No market price data available/);
  assert.doesNotMatch(source, /Price data parsing failed/);
  assert.doesNotMatch(source, /getProfitabilityEstimates Error/);
});

test('profitability widget renders the error message verbatim', () => {
  const source = readSource('components/widgets/ProfitabilityWidget.js');

  // The widget must pass the (now Korean) error string straight through
  // without re-introducing an English fallback.
  assert.match(source, /\{error\}/);
});

test('profitability widget is mounted on the dashboard, not orphaned', () => {
  // T-366: the widget is registered in WIDGET_REGISTRY with defaultOn:true,
  // so it must actually be wired into the render path and fed SSR data.
  const dashboard = readSource('components/DashboardClient.js');
  assert.match(dashboard, /import \{ ProfitabilityWidget \}/);
  assert.match(dashboard, /\{ id: 'profitability', label: '출하 수익성 예측', icon: '📈', defaultOn: true \}/);
  assert.match(dashboard, /widgetSettings\.visible\.profitability/);
  assert.match(dashboard, /<ProfitabilityWidget/);

  const page = readSource('app/page.js');
  assert.match(page, /getProfitabilityData/);
  assert.match(page, /initialProfitability=\{profitability\}/);
});
