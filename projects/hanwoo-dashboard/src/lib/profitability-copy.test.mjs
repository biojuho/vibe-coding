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

  // These known business-state messages can flow through to
  // ProfitabilityWidget, which renders `{error}` as visible UI text.
  assert.match(source, /수익성 시뮬레이션에 사용할 시세 데이터가 없습니다/);
  assert.match(source, /시세 데이터를 해석하지 못했습니다/);
  assert.match(source, /수익성 추정 오류/);
  assert.match(source, /수익성 예측을 불러오지 못했습니다\. 잠시 후 다시 시도해 주세요\./);
  assert.match(source, /OPERATOR_FACING_ERROR_MESSAGES\.has/);

  assert.doesNotMatch(source, /No market price data available/);
  assert.doesNotMatch(source, /Price data parsing failed/);
  assert.doesNotMatch(source, /getProfitabilityEstimates Error/);
  assert.doesNotMatch(source, /error:\s*err\.message/);
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
  const widgetSettings = readSource('lib/hooks/useWidgetSettings.js');
  assert.match(dashboard, /import \{ ProfitabilityWidget \}/);
  assert.match(dashboard, /import \{ WIDGET_REGISTRY, useWidgetSettings \} from '@\/lib\/hooks\/useWidgetSettings';/);
  assert.doesNotMatch(dashboard, /const WIDGET_REGISTRY = \[/);
  assert.match(widgetSettings, /\{ id: 'profitability', label: '출하 수익성 예측', icon: '📈', defaultOn: true \}/);
  assert.match(dashboard, /widgetSettings\.visible\.profitability/);
  assert.match(dashboard, /<ProfitabilityWidget/);

  const page = readSource('app/page.js');
  assert.match(page, /getProfitabilityData/);
  assert.match(page, /initialProfitability=\{profitability\}/);
});

test('premium card header renders profitability widget title props as visible content', () => {
  const source = readSource('components/ui/premium-card.js');
  const headerSource = source.slice(
    source.indexOf('const PremiumCardHeader'),
    source.indexOf('PremiumCardHeader.displayName'),
  );

  assert.match(headerSource, /\(\{ className, title, icon, description, children, \.\.\.props \}/);
  assert.match(headerSource, /<h3[\s\S]*\{title\}[\s\S]*<\/h3>/);
  assert.match(headerSource, /<p[\s\S]*\{description\}[\s\S]*<\/p>/);
  assert.match(headerSource, /<span aria-hidden="true"[\s\S]*\{icon\}[\s\S]*<\/span>/);
  assert.match(headerSource, /\{children\}/);
  assert.doesNotMatch(headerSource, /\{\.\.\.props\}\s*\/>/);
});
