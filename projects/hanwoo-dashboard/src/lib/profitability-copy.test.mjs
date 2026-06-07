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

test("profitability service surfaces Korean operator-facing error copy", () => {
	const source = readSource("lib/dashboard/profitability-service.js");

	// These known business-state messages can flow through to
	// ProfitabilityWidget, which renders `{error}` as visible UI text.
	assert.match(source, /수익성 시뮬레이션에 사용할 시세 정보가 없습니다/);
	assert.match(source, /시세 정보를 해석하지 못했습니다/);
	assert.doesNotMatch(source, /수익성 시뮬레이션에 사용할 시세 데이터가 없습니다/);
	assert.doesNotMatch(source, /시세 데이터를 해석하지 못했습니다/);
	assert.match(source, /Degraded profitability estimate/);
	assert.match(
		source,
		/수익성 예측을 불러오지 못했습니다\. 잠시 후 다시 시도해 주세요\./,
	);
	assert.match(source, /OPERATOR_FACING_ERROR_MESSAGES\.has/);

	assert.doesNotMatch(source, /No market price data available/);
	assert.doesNotMatch(source, /Price data parsing failed/);
	assert.doesNotMatch(source, /getProfitabilityEstimates Error/);
	assert.doesNotMatch(source, /error:\s*err\.message/);
});

test("profitability service normalizes dates and numeric inputs before estimating", () => {
	const source = readSource("lib/dashboard/profitability-service.js");

	assert.match(source, /import \{ toFiniteNumber \} from ["']\.\.\/utils["'];/);
	assert.match(source, /function toValidDate\(value\) \{/);
	assert.match(source, /const start = toValidDate\(d1\);/);
	assert.match(source, /const end = toValidDate\(d2\);/);
	assert.match(source, /if \(!start \|\| !end\) \{\s+return null;\s+\}/);
	assert.match(
		source,
		/if \(ageMonths === null \|\| ageMonths < 24\) return null;/,
	);
	assert.match(
		source,
		/const purchasePrice\s*=\s*toFiniteNumber\(cattle\.purchasePrice, null\);/,
	);
	assert.match(
		source,
		/const baseCost\s*=\s*purchasePrice === null \? DEFAULT_CALF_COST : purchasePrice;/,
	);
	assert.match(
		source,
		/const currentWeight\s*=\s*toFiniteNumber\(cattle\.weight\);/,
	);
	assert.match(
		source,
		/const currentRevenue\s*=\s*currentWeight\s*\*\s*currentKgPrice;/,
	);
	assert.match(
		source,
		/const futureWeight\s*=\s*currentWeight\s*\+\s*MONTHLY_WEIGHT_GAIN;/,
	);
	assert.match(source, /weight: currentWeight,/);
	assert.doesNotMatch(
		source,
		/fetchedAt: latestSnapshot\.fetchedAt\.toISOString\(\)/,
	);
	assert.doesNotMatch(
		source,
		/issueDate: latestSnapshot\.issueDate\.toISOString\(\)/,
	);
	assert.doesNotMatch(
		source,
		/const ageMonths = diffMonths\(cattle\.birthDate, now\);\s+\/\/ Limit[\s\S]*?if \(ageMonths < 24\) return null;/,
	);
	assert.doesNotMatch(
		source,
		/const baseCost = cattle\.purchasePrice \|\| DEFAULT_CALF_COST;/,
	);
	assert.doesNotMatch(
		source,
		/toFiniteNumber\(cattle\.purchasePrice\)\s*\|\|\s*DEFAULT_CALF_COST/,
	);
	assert.doesNotMatch(
		source,
		/const currentRevenue = cattle\.weight \* currentKgPrice;/,
	);
	assert.doesNotMatch(
		source,
		/const futureWeight = cattle\.weight \+ MONTHLY_WEIGHT_GAIN;/,
	);
});

test("profitability service normalizes DB row collections before calculations", () => {
	const source = readSource("lib/dashboard/profitability-service.js");

	assert.match(source, /function isProfitabilityServiceRow\(value\) \{/);
	assert.match(
		source,
		/return value !== null && typeof value === ["']object["'] && !Array\.isArray\(value\);/,
	);
	assert.match(source, /function normalizeProfitabilityServiceRows\(rows\) \{/);
	assert.match(
		source,
		/return Array\.isArray\(rows\)\s*\?\s*rows\.filter\(\(row\) => isProfitabilityServiceRow\(row\)\)\s*:\s*\[\];/,
	);
	assert.match(
		source,
		/const activeCattle = normalizeProfitabilityServiceRows\(\s*await prisma\.cattle\.findMany\(\{/,
	);
	assert.match(
		source,
		/const \[recentFeedExpenses, recentSales\] = await Promise\.all\(\[\s*prisma\.expenseRecord/,
	);
	assert.match(source, /\.then\(normalizeProfitabilityServiceRows\)/);
	assert.match(source, /const soldCattle = soldCattleIds\.length/);
	assert.match(
		source,
		/normalizeProfitabilityServiceRows\([\s\S]*?await prisma\.cattle\.findMany\([\s\S]*?\.catch\(\(\) => \[\]\)/,
	);
	assert.match(
		source,
		/const soldCattleById = new Map\(soldCattle\.map\(\(cow\) => \[cow\.id, cow\]\)\);/,
	);
});

test("profitability widget renders the error message verbatim", () => {
	const source = readSource("components/widgets/ProfitabilityWidget.js");

	// The widget must pass the (now Korean) error string straight through
	// without re-introducing an English fallback.
	assert.match(source, /if \(error\) \{/);
	assert.match(source, /<PremiumCardContent role="alert">/);
	assert.match(source, /\{error\}/);
});

test("profitability widget announces loading state", () => {
	const source = readSource("components/widgets/ProfitabilityWidget.js");

	assert.match(source, /if \(isLoading\) \{/);
	assert.match(source, /role="status"/);
	assert.match(source, /aria-live="polite"/);
	assert.match(source, /aria-atomic="true"/);
	assert.match(source, /aria-busy="true"/);
	assert.match(source, /className="sr-only"/);
	assert.match(source, /출하 수익성 예측을 불러오는 중입니다\./);
});

test("profitability widget normalizes recommendation values before rendering", () => {
	const source = readSource("components/widgets/ProfitabilityWidget.js");

	assert.match(source, /import \{ toFiniteNumber \} from ["']@\/lib\/utils["'];/);
	assert.match(source, /visibleData\.map\(\(rawItem\) =>/);
	assert.match(
		source,
		/currentProfit: toFiniteNumber\(rawItem\.currentProfit\)/,
	);
	assert.match(source, /marginalGain: toFiniteNumber\(rawItem\.marginalGain\)/);
	assert.match(source, /ageMonths: toFiniteNumber\(rawItem\.ageMonths\)/);
	assert.match(source, /weight: toFiniteNumber\(rawItem\.weight\)/);
	assert.match(
		source,
		/String\(rawItem\.tagNumber \?\? ["']["']\)\.slice\(-4\) \|\| ["']이력번호 미등록["']/,
	);
	assert.match(source, /String\(rawItem\.name \?\? ["']["']\) \|\| ["']개체명 미등록["']/);
	assert.doesNotMatch(source, /["']----["']/);
	assert.doesNotMatch(source, /String\(rawItem\.name \?\? ["']-["']\)/);
	assert.doesNotMatch(source, /item\.tagNumber\.slice\(-4\)/);
});

test("profitability widget uses action-ready shipment badge copy", () => {
	const source = readSource("components/widgets/ProfitabilityWidget.js");

	assert.match(source, /출하 일정 확인 필요/);
	assert.doesNotMatch(source, /즉시 출하 권장/);
});

test("profitability widget uses candidate-analysis copy for empty and header states", () => {
	const source = readSource("components/widgets/ProfitabilityWidget.js");

	assert.match(source, /title="출하 후보 개체"/);
	assert.match(source, /현재 출하 일정을 확인할 후보가 없거나 수익성 분석에 필요한/);
	assert.match(source, /기록이 부족합니다/);
	assert.match(source, /title="출하 수익성 분석"/);
	assert.match(source, /description="출하 타이밍과 예상 마진을 분석합니다\."/);
	assert.doesNotMatch(source, /출하 추천 개체/);
	assert.doesNotMatch(source, /출하 수익성 추천/);
	assert.doesNotMatch(source, /최적의 출하 타이밍/);
	assert.doesNotMatch(source, /수익성 분석 데이터가/);
});

test("profitability widget normalizes recommendation collection payloads before rendering", () => {
	const source = readSource("components/widgets/ProfitabilityWidget.js");

	assert.match(source, /function normalizeProfitabilityItems\(data\) \{/);
	assert.match(source, /return Array\.isArray\(data\)/);
	assert.match(
		source,
		/\.filter\([\s\S]*?\(item\) => item && typeof item === ["']object["'] && !Array\.isArray\(item\)[\s\S]*?\)/,
	);
	assert.match(source, /id: item\.id \?\? `profitability-item-\$\{index\}`/);
	assert.match(
		source,
		/const visibleData = normalizeProfitabilityItems\(data\);/,
	);
	assert.match(source, /visibleData\.length === 0/);
	assert.match(source, /visibleData\.map\(\(rawItem\) =>/);
	assert.doesNotMatch(source, /!data \|\| data\.length === 0/);
	assert.doesNotMatch(source, /data\.map\(\(rawItem\) =>/);
});

test("profitability widget normalizes malformed top-level props before rendering", () => {
	const source = readSource("components/widgets/ProfitabilityWidget.js");

	assert.match(source, /function normalizeProfitabilityWidgetOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === "object" && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export function ProfitabilityWidget\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ data, isLoading, error, meta = null \} =\s*normalizeProfitabilityWidgetOptions\(options\);/,
	);
	assert.match(
		source,
		/const visibleData = normalizeProfitabilityItems\(data\);/,
	);
	assert.doesNotMatch(
		source,
		/export function ProfitabilityWidget\(\{ data, isLoading, error, meta = null \}\)/,
	);
});

test("profitability widget is mounted on the dashboard, not orphaned", () => {
	// T-366: the widget is registered in WIDGET_REGISTRY with defaultOn:true,
	// so it must actually be wired into the render path and fed SSR data.
	const dashboard = readSource("components/DashboardClient.js");
	const widgetSettings = readSource("lib/hooks/useWidgetSettings.js");
	assert.match(dashboard, /import \{ ProfitabilityWidget \}/);
	assert.match(
		dashboard,
		/import\s*\{\s*[\s\S]*?useWidgetSettings[\s\S]*?\}\s*from\s*['"]@\/lib\/hooks\/useWidgetSettings['"];?/,
	);
	assert.doesNotMatch(dashboard, /const WIDGET_REGISTRY = \[/);
	assert.match(
		widgetSettings,
		/\{\s*id:\s*['"]profitability['"],\s*label:\s*['"]출하 수익성 예측['"],\s*icon:\s*['"]📈['"],\s*defaultOn:\s*true\s*,?\s*\}/,
	);
	assert.match(dashboard, /widgetSettings\.visible\.profitability/);
	assert.match(dashboard, /<ProfitabilityWidget/);

	const page = readSource("app/page.js");
	assert.match(page, /getProfitabilityData/);
	assert.match(page, /initialProfitability=\{initialData\.profitability\}/);
});

test("premium card header renders profitability widget title props as visible content", () => {
	const source = readSource("components/ui/premium-card.js");
	const headerSource = source.slice(
		source.indexOf("const PremiumCardHeader"),
		source.indexOf("PremiumCardHeader.displayName"),
	);

	assert.match(
		headerSource,
		/const \{ className, title, icon, description, children, \.\.\.props \} =\s+normalizePremiumCardOptions\(options\);/,
	);
	assert.match(headerSource, /<h3[\s\S]*\{title\}[\s\S]*<\/h3>/);
	assert.match(headerSource, /<p[\s\S]*\{description\}[\s\S]*<\/p>/);
	assert.match(
		headerSource,
		/<span aria-hidden="true"[\s\S]*\{icon\}[\s\S]*<\/span>/,
	);
	assert.match(headerSource, /\{children\}/);
	assert.doesNotMatch(headerSource, /\{\.\.\.props\}\s*\/>/);
});
