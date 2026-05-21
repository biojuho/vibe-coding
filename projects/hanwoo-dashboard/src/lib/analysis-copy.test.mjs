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
  assert.match(analysisSource, /className="inline-flex h-9 w-9 items-center justify-center rounded-full"\s+aria-hidden="true"/);
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

test('analysis tab normalizes numeric inputs before financial and feed aggregation', () => {
  const analysisSource = readSource('components/tabs/AnalysisTab.js');

  assert.match(analysisSource, /import \{ formatMoney, toFiniteNumber \} from '@\/lib\/utils';/);
  assert.match(analysisSource, /function toMonthKey\(value\) \{/);
  assert.match(analysisSource, /const dateKey = value\.trim\(\)\.slice\(0, 10\);/);
  assert.match(analysisSource, /strictDate\.toISOString\(\)\.slice\(0, 10\) !== dateKey/);
  assert.match(analysisSource, /const key = toMonthKey\(record\.saleDate\);/);
  assert.match(analysisSource, /const key = toMonthKey\(expense\.date\);/);
  assert.match(analysisSource, /data\[key\]\.revenue \+= toFiniteNumber\(record\.price\);/);
  assert.match(analysisSource, /data\[key\]\.cost \+= toFiniteNumber\(expense\.amount\);/);
  assert.match(analysisSource, /\(totals\[category\] \|\| 0\) \+ toFiniteNumber\(expense\.amount\)/);
  assert.match(analysisSource, /toFiniteNumber\(second\.price\) - toFiniteNumber\(first\.price\)/);
  assert.match(analysisSource, /sum \+ toFiniteNumber\(row\.roughage\) \+ toFiniteNumber\(row\.concentrate\)/);
  assert.doesNotMatch(analysisSource, /const date = new Date\(record\.saleDate\);/);
  assert.doesNotMatch(analysisSource, /const date = new Date\(expense\.date\);/);
  assert.doesNotMatch(analysisSource, /sum \+ row\.roughage \+ row\.concentrate/);
  assert.doesNotMatch(analysisSource, /data\[key\]\.revenue \+= record\.price/);
  assert.doesNotMatch(analysisSource, /data\[key\]\.cost \+= expense\.amount/);
});

test('financial chart widget normalizes numeric inputs before chart aggregation', () => {
  const source = readSource('components/widgets/FinancialChartWidget.js');
  const summarySource = readSource('lib/dashboard/summary-service.js');

  assert.match(source, /import \{ formatMoney, toFiniteNumber \} from '@\/lib\/utils';/);
  assert.match(source, /function toMonthKey\(value\) \{/);
  assert.match(source, /Number\.isNaN\(date\.getTime\(\)\)/);
  assert.match(source, /const key = toMonthKey\(record\.saleDate\);/);
  assert.match(source, /const key = toMonthKey\(record\.date\);/);
  assert.match(source, /if \(!key\) return;/);
  assert.match(source, /salesByMonth\[key\] = \(salesByMonth\[key\] \|\| 0\) \+ toFiniteNumber\(record\.price\);/);
  assert.match(source, /expensesByMonth\[key\] = \(expensesByMonth\[key\] \|\| 0\) \+ toFiniteNumber\(record\.amount\);/);
  assert.match(source, /\[REVENUE_KEY\]: toFiniteNumber\(row\.revenue\),/);
  assert.match(source, /\[EXPENSE_KEY\]: Math\.floor\(toFiniteNumber\(row\.expense\)\),/);
  assert.match(source, /\[PROFIT_KEY\]: toFiniteNumber\(row\.profit\),/);
  assert.doesNotMatch(source, /const key = `\$\{date\.getFullYear\(\)\}-\$\{String\(date\.getMonth\(\) \+ 1\)\.padStart\(2, '0'\)\}`;/);
  assert.doesNotMatch(source, /record\.price \|\| 0/);
  assert.doesNotMatch(source, /record\.amount \|\| 0/);
  assert.doesNotMatch(source, /row\.revenue \|\| 0/);
  assert.doesNotMatch(source, /row\.expense \|\| 0/);
  assert.doesNotMatch(source, /row\.profit \|\| 0/);

  assert.match(summarySource, /import \{ toFiniteNumber \} from '\.\.\/utils';/);
  assert.match(summarySource, /const date = value instanceof Date \? new Date\(value\.getTime\(\)\) : new Date\(value\);/);
  assert.match(summarySource, /const dateKey = value\.trim\(\)\.slice\(0, 10\);/);
  assert.match(summarySource, /strictDate\.toISOString\(\)\.slice\(0, 10\) !== dateKey/);
  assert.match(summarySource, /const monthKey = toMonthKey\(record\.saleDate\);/);
  assert.match(summarySource, /const monthKey = toMonthKey\(record\.date\);/);
  assert.match(summarySource, /if \(!monthKey\) continue;/);
  assert.match(summarySource, /salesByMonth\.set\(monthKey, \(salesByMonth\.get\(monthKey\) \?\? 0\) \+ toFiniteNumber\(record\.price\)\);/);
  assert.match(summarySource, /expensesByMonth\.set\(monthKey, \(expensesByMonth\.get\(monthKey\) \?\? 0\) \+ toFiniteNumber\(record\.amount\)\);/);
  assert.match(summarySource, /const monthlySalesTotal = toFiniteNumber\(salesThisMonth\._sum\.price\);/);
  assert.match(summarySource, /const monthlyExpenseTotal = toFiniteNumber\(expensesThisMonth\._sum\.amount\);/);
  assert.doesNotMatch(summarySource, /toMonthKey\(new Date\(record\.saleDate\)\)/);
  assert.doesNotMatch(summarySource, /toMonthKey\(new Date\(record\.date\)\)/);
  assert.doesNotMatch(summarySource, /const date = value instanceof Date \? value : new Date\(value\);/);
  assert.doesNotMatch(summarySource, /record\.price \?\? 0/);
  assert.doesNotMatch(summarySource, /record\.amount \?\? 0/);
  assert.doesNotMatch(summarySource, /salesThisMonth\._sum\.price \?\? 0/);
  assert.doesNotMatch(summarySource, /expensesThisMonth\._sum\.amount \?\? 0/);
});
