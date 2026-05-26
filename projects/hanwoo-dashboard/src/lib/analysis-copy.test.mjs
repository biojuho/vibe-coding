import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

test("analysis and financial widgets use Korean operator copy", () => {
	const analysisSource = readSource("components/tabs/AnalysisTab.js");
	const financialWidgetSource = readSource(
		"components/widgets/FinancialChartWidget.js",
	);

	assert.match(
		financialWidgetSource,
		/import \{ BarChart3 \} from ["']lucide-react["'];/,
	);
	assert.match(
		financialWidgetSource,
		/<BarChart3[\s\S]*?size=\{22\}[\s\S]*?aria-hidden="true"/,
	);
	assert.match(
		analysisSource,
		/className="inline-flex h-9 w-9 items-center justify-center rounded-full"\s+aria-hidden="true"/,
	);
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
	assert.doesNotMatch(
		analysisSource,
		/Financial Analysis|Monthly Flow|Cost Mix|Top Sales/,
	);
	assert.doesNotMatch(
		financialWidgetSource,
		/Farm Financial Overview|Recent 6-month|Unit: KRW|Revenue|Expense|Profit/,
	);
	assert.doesNotMatch(
		financialWidgetSource,
		/fontSize: ["']22px["'], lineHeight: 1 \}\}>\?<\/span>/,
	);
});

test("analysis tab normalizes numeric inputs before financial and feed aggregation", () => {
	const analysisSource = readSource("components/tabs/AnalysisTab.js");

	assert.match(
		analysisSource,
		/import \{ formatMoney, toFiniteNumber \} from ["']@\/lib\/utils["'];/,
	);
	assert.match(analysisSource, /function toMonthKey\(value\) \{/);
	assert.match(analysisSource, /function normalizeAnalysisItems\(items\) \{/);
	assert.match(
		analysisSource,
		/return Array\.isArray\(\s*items\s*\)\s*\?\s*items\s*\.\s*filter\(\s*\(\s*item\s*\)\s*=>\s*item\s*&&\s*typeof\s*item\s*===\s*["']object["']\s*\)\s*:\s*\[\s*\]\s*;?/,
	);
	assert.match(
		analysisSource,
		/const safeSaleRecords = useMemo[\s\S]*?normalizeAnalysisItems\(\s*saleRecords\s*\)[\s\S]*?\[\s*saleRecords\s*\]/,
	);
	assert.match(
		analysisSource,
		/const safeFeedHistory = useMemo[\s\S]*?normalizeAnalysisItems\(\s*feedHistory\s*\)[\s\S]*?\[\s*feedHistory\s*\]/,
	);
	assert.match(
		analysisSource,
		/const safeCattleList = useMemo[\s\S]*?normalizeAnalysisItems\(\s*cattleList\s*\)[\s\S]*?\[\s*cattleList\s*\]/,
	);
	assert.match(
		analysisSource,
		/const safeExpenseRecords = useMemo[\s\S]*?normalizeAnalysisItems\(\s*expenseRecords\s*\)[\s\S]*?\[\s*expenseRecords\s*\]/,
	);
	assert.match(
		analysisSource,
		/const hasExpenseData = safeExpenseRecords\.length > 0;/,
	);
	assert.match(
		analysisSource,
		/const dateKey = value\.trim\(\)\.slice\(0, 10\);/,
	);
	assert.match(
		analysisSource,
		/strictDate\.toISOString\(\)\.slice\(0, 10\) !== dateKey/,
	);
	assert.match(analysisSource, /safeSaleRecords\.forEach\(\(record\) => \{/);
	assert.match(analysisSource, /const key = toMonthKey\(record\.saleDate\);/);
	assert.match(
		analysisSource,
		/safeExpenseRecords\.forEach\(\(expense\) => \{/,
	);
	assert.match(analysisSource, /const key = toMonthKey\(expense\.date\);/);
	assert.match(
		analysisSource,
		/data\[key\]\.revenue \+= toFiniteNumber\(record\.price\);/,
	);
	assert.match(
		analysisSource,
		/data\[key\]\.cost \+= toFiniteNumber\(expense\.amount\);/,
	);
	assert.match(
		analysisSource,
		/\(totals\[category\] \|\| 0\) \+ toFiniteNumber\(expense\.amount\)/,
	);
	assert.match(analysisSource, /\[\s*\.\.\.\s*safeSaleRecords\s*\]\s*\.\s*sort/);
	assert.match(
		analysisSource,
		/toFiniteNumber\(second\.price\) - toFiniteNumber\(first\.price\)/,
	);
	assert.match(analysisSource, /safeFeedHistory\.reduce/);
	assert.match(
		analysisSource,
		/sum\s*\+\s*toFiniteNumber\(\s*row\.roughage\s*\)\s*\+\s*toFiniteNumber\(\s*row\.concentrate\s*\)/,
	);
	assert.match(analysisSource, /safeCattleList\.length/);
	assert.doesNotMatch(analysisSource, /saleRecords\.forEach/);
	assert.doesNotMatch(analysisSource, /expenseRecords\.forEach/);
	assert.doesNotMatch(analysisSource, /\[\.\.\.saleRecords\]\.sort/);
	assert.doesNotMatch(analysisSource, /feedHistory\.reduce/);
	assert.doesNotMatch(analysisSource, /cattleList\.length/);
	assert.doesNotMatch(
		analysisSource,
		/const date = new Date\(record\.saleDate\);/,
	);
	assert.doesNotMatch(
		analysisSource,
		/const date = new Date\(expense\.date\);/,
	);
	assert.doesNotMatch(
		analysisSource,
		/sum \+ row\.roughage \+ row\.concentrate/,
	);
	assert.doesNotMatch(analysisSource, /data\[key\]\.revenue \+= record\.price/);
	assert.doesNotMatch(analysisSource, /data\[key\]\.cost \+= expense\.amount/);
});

test("financial chart widget normalizes numeric inputs before chart aggregation", () => {
	const source = readSource("components/widgets/FinancialChartWidget.js");
	const summarySource = readSource("lib/dashboard/summary-service.js");

	assert.match(
		source,
		/import \{ formatMoney, toFiniteNumber \} from ["']@\/lib\/utils["'];/,
	);
	assert.match(source, /function toMonthKey\(value\) \{/);
	assert.match(source, /function normalizeFinancialChartItems\(items\) \{/);
	assert.match(
		source,
		/return Array\.isArray\(\s*items\s*\)\s*\?\s*items\s*\.\s*filter\(\s*\(\s*item\s*\)\s*=>\s*item\s*&&\s*typeof\s*item\s*===\s*["']object["']\s*\)\s*:\s*\[\s*\]\s*;?/,
	);
	assert.match(
		source,
		/const safeSaleRecords = normalizeFinancialChartItems\(saleRecords\);/,
	);
	assert.match(
		source,
		/const safeCostRecords = normalizeFinancialChartItems\(expenseRecords\);/,
	);
	assert.match(
		source,
		/const safeSeriesData = normalizeFinancialChartItems\(seriesData\);/,
	);
	assert.match(
		source,
		/const date\s*=\s*value\s*instanceof\s*Date\s*\?\s*new\s+Date\s*\(\s*value\s*\.\s*getTime\s*\(\s*\)\s*\)\s*:\s*new\s+Date\s*\(\s*value\s*\);?/,
	);
	assert.match(source, /const dateKey = value\.trim\(\)\.slice\(0, 10\);/);
	assert.match(
		source,
		/strictDate\.toISOString\(\)\.slice\(0, 10\) !== dateKey/,
	);
	assert.match(source, /safeSaleRecords\.forEach\(\(record\) => \{/);
	assert.match(source, /const key = toMonthKey\(record\.saleDate\);/);
	assert.match(source, /safeCostRecords\.forEach\(\(record\) => \{/);
	assert.match(source, /const key = toMonthKey\(record\.date\);/);
	assert.match(source, /if \(!key\) return;/);
	assert.match(
		source,
		/salesByMonth\[key\]\s*=\s*\(salesByMonth\[key\]\s*\|\|\s*0\s*\)\s*\+\s*toFiniteNumber\(record\.price\)\s*;?/,
	);
	assert.match(
		source,
		/expensesByMonth\[key\]\s*=\s*\(\s*expensesByMonth\[key\]\s*\|\|\s*0\s*\)\s*\+\s*toFiniteNumber\(\s*record\.amount\s*\)\s*;?/,
	);
	assert.match(source, /safeSeriesData\.length > 0/);
	assert.match(source, /safeSeriesData\.map\(\(row\) => \(\{/);
	assert.match(source, /\[REVENUE_KEY\]: toFiniteNumber\(row\.revenue\),/);
	assert.match(
		source,
		/\[EXPENSE_KEY\]: Math\.floor\(toFiniteNumber\(row\.expense\)\),/,
	);
	assert.match(source, /\[PROFIT_KEY\]: toFiniteNumber\(row\.profit\),/);
	assert.doesNotMatch(source, /saleRecords\.forEach/);
	assert.doesNotMatch(source, /expenseRecords\.forEach/);
	assert.doesNotMatch(source, /seriesData\.map/);
	assert.doesNotMatch(source, /const date = new Date\(value\);/);
	assert.doesNotMatch(
		source,
		/const key = `\$\{date\.getFullYear\(\)\}-\$\{String\(date\.getMonth\(\) \+ 1\)\.padStart\(2, ["']0["']\)\}`;/,
	);
	assert.doesNotMatch(source, /record\.price \|\| 0/);
	assert.doesNotMatch(source, /record\.amount \|\| 0/);
	assert.doesNotMatch(source, /row\.revenue \|\| 0/);
	assert.doesNotMatch(source, /row\.expense \|\| 0/);
	assert.doesNotMatch(source, /row\.profit \|\| 0/);

	assert.match(
		summarySource,
		/import \{ toFiniteNumber \} from ["']\.\.\/utils["'];/,
	);
	assert.match(
		summarySource,
		/const date\s*=\s*value\s*instanceof\s*Date\s*\?\s*new\s+Date\s*\(\s*value\s*\.\s*getTime\s*\(\s*\)\s*\)\s*:\s*new\s+Date\s*\(\s*value\s*\);?/,
	);
	assert.match(
		summarySource,
		/const dateKey = value\.trim\(\)\.slice\(0, 10\);/,
	);
	assert.match(
		summarySource,
		/strictDate\.toISOString\(\)\.slice\(0, 10\) !== dateKey/,
	);
	assert.match(
		summarySource,
		/const monthKey = toMonthKey\(record\.saleDate\);/,
	);
	assert.match(summarySource, /const monthKey = toMonthKey\(record\.date\);/);
	assert.match(summarySource, /if \(!monthKey\) continue;/);
	assert.match(
		summarySource,
		/salesByMonth\.set\(\s*monthKey\s*,\s*\(\s*salesByMonth\.get\(\s*monthKey\s*\)\s*\?\?\s*0\s*\)\s*\+\s*toFiniteNumber\(\s*record\.price\s*\)\s*,?\s*\);?/,
	);
	assert.match(
		summarySource,
		/expensesByMonth\.set\(\s*monthKey\s*,\s*\(\s*expensesByMonth\.get\(\s*monthKey\s*\)\s*\?\?\s*0\s*\)\s*\+\s*toFiniteNumber\(\s*record\.amount\s*\)\s*,?\s*\);?/,
	);
	assert.match(
		summarySource,
		/const monthlySalesTotal = toFiniteNumber\(salesThisMonth\._sum\.price\);/,
	);
	assert.match(
		summarySource,
		/const monthlyExpenseTotal = toFiniteNumber\(expensesThisMonth\._sum\.amount\);/,
	);
	assert.doesNotMatch(
		summarySource,
		/toMonthKey\(new Date\(record\.saleDate\)\)/,
	);
	assert.doesNotMatch(summarySource, /toMonthKey\(new Date\(record\.date\)\)/);
	assert.doesNotMatch(
		summarySource,
		/const date = value instanceof Date \? value : new Date\(value\);/,
	);
	assert.doesNotMatch(summarySource, /record\.price \?\? 0/);
	assert.doesNotMatch(summarySource, /record\.amount \?\? 0/);
	assert.doesNotMatch(summarySource, /salesThisMonth\._sum\.price \?\? 0/);
	assert.doesNotMatch(summarySource, /expensesThisMonth\._sum\.amount \?\? 0/);
});
