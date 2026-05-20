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

test('analysis and financial widgets use Korean operator copy', () => {
  const analysisSource = readSource('components/tabs/AnalysisTab.js');
  const financialWidgetSource = readSource('components/widgets/FinancialChartWidget.js');

  assert.match(financialWidgetSource, /import \{ BarChart3 \} from 'lucide-react';/);
  assert.match(financialWidgetSource, /<BarChart3 size=\{22\} aria-hidden="true"/);
  assert.match(analysisSource, /경영 분석/);
  assert.match(analysisSource, /월별 흐름/);
  assert.match(analysisSource, /비용 구성/);
  assert.match(analysisSource, /상위 판매/);
  assert.match(financialWidgetSource, /농장 재무 흐름/);
  assert.match(financialWidgetSource, /최근 6개월 매출, 비용, 이익 추이/);
  assert.match(financialWidgetSource, /단위: 원/);
  assert.match(financialWidgetSource, /name="매출"/);
  assert.match(financialWidgetSource, /name="비용"/);
  assert.match(financialWidgetSource, /name="이익"/);
  assert.doesNotMatch(analysisSource, /Financial Analysis|Monthly Flow|Cost Mix|Top Sales/);
  assert.doesNotMatch(financialWidgetSource, /Farm Financial Overview|Recent 6-month|Unit: KRW|Revenue|Expense|Profit/);
  assert.doesNotMatch(financialWidgetSource, /fontSize: '22px', lineHeight: 1 \}\}>\?<\/span>/);
});
