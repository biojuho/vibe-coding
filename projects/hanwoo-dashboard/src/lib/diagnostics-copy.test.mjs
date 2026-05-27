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

test("admin diagnostics page uses Korean operations copy for visible states", () => {
	const source = readSource("components/admin/DiagnosticsPageClient.js");
	const systemActions = readSource("lib/actions/system.js");

	assert.match(source, /운영 진단/);
	assert.match(source, /시스템 상태 점검/);
	assert.match(source, /데이터베이스 상태/);
	assert.match(source, /레코드를 불러오는 중입니다/);
	assert.match(source, /대시보드로 돌아가기/);
	assert.match(
		source,
		/const DASHBOARD_NAVIGATION_ERROR_MESSAGE =\s+["']대시보드로 이동하지 못했습니다\. 잠시 후 다시 시도해 주세요\.["'];/,
	);
	assert.match(
		source,
		/const handleDashboardReturn = \(\) => \{\s+try \{\s+router\.push\(["']\/["']\);/,
	);
	assert.match(
		source,
		/console\.error\(["']Failed to navigate from diagnostics to dashboard:/,
	);
	assert.match(
		source,
		/title: ["']대시보드로 이동하지 못했습니다\.["'][\s\S]*?description: DASHBOARD_NAVIGATION_ERROR_MESSAGE/,
	);
	assert.match(
		source,
		/type=\"button\"\s+onClick=\{handleDashboardReturn\}\s+aria-label=\"운영 대시보드로 돌아가기\"\s+title=\"운영 대시보드로 돌아가기\"/,
	);
	assert.match(
		source,
		/<ArrowLeft className=\"h-4 w-4\" aria-hidden=\"true\" \/>/,
	);
	assert.match(source, /원본 데이터를 불러오지 못했습니다/);
	assert.match(
		source,
		/진단 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요/,
	);
	assert.match(source, /aria-label="검사할 원본 데이터 선택"/);
	assert.match(source, /title="검사할 원본 데이터 선택"/);
	assert.match(source, /MODEL_OPTIONS/);
	assert.match(systemActions, /status: ["']정상["']/);
	assert.match(systemActions, /status: ["']연결 실패["']/);
	assert.match(source, /status: ["']DB 상태 확인 불가["']/);
	assert.match(source, /latency: ["']DB 응답 시간 확인 불가["']/);
	assert.match(source, /nodeVersion: ["']Node 버전 확인 불가["']/);
	assert.match(systemActions, /latency: ["']DB 응답 시간 확인 불가["']/);
	assert.doesNotMatch(source, /System Diagnostics/);
	assert.doesNotMatch(source, /Database Status/);
	assert.doesNotMatch(source, /Loading records/);
	assert.doesNotMatch(source, /Please try again in a moment/);
	assert.doesNotMatch(source, /description: error\.message/);
	assert.doesNotMatch(systemActions, /status: ["']Online["']/);
	assert.doesNotMatch(systemActions, /status: ["']Offline["']/);
	assert.doesNotMatch(systemActions, /latency: ["']N\/A["']/);
	assert.doesNotMatch(systemActions, /latency: ["']확인 불가["']/);
});

test("admin diagnostics loading states are announced", () => {
	const source = readSource("components/admin/DiagnosticsPageClient.js");

	assert.match(source, /if \(loading\) \{/);
	assert.match(
		source,
		/className="clay-page-card p-8 text-center"[\s\S]*?role="status"[\s\S]*?aria-live="polite"[\s\S]*?aria-atomic="true"[\s\S]*?aria-busy="true"/,
	);
	assert.match(source, /\{dataLoading \? \(/);
	assert.match(
		source,
		/className="clay-inset rounded-\[24px\][^"]*"[\s\S]*?role="status"[\s\S]*?aria-live="polite"[\s\S]*?aria-atomic="true"[\s\S]*?aria-busy="true"/,
	);
});

test("admin diagnostics numeric metrics are normalized before rendering", () => {
	const source = readSource("components/admin/DiagnosticsPageClient.js");

	assert.match(source, /import \{ toFiniteNumber \} from ["']@\/lib\/utils["'];/);
	assert.match(
		source,
		/Object\s*\.\s*entries\(\s*stats\s*\.\s*database\s*\.\s*recordCounts\s*\)\s*\.\s*map\(\s*\(\s*\[\s*key\s*,\s*value\s*\]\s*\)\s*=>\s*\[\s*key\s*,\s*toFiniteNumber\(\s*value\s*\)\s*,?\s*\]\s*\)/,
	);
	assert.match(
		source,
		/const uptimeMinutes\s*=\s*Math\s*\.\s*floor\(\s*toFiniteNumber\(\s*stats\s*\?\.\s*uptime\s*\)\s*\/\s*60\s*,?\s*\);?/,
	);
	assert.match(
		source,
		/const heapUsedMb\s*=\s*Math\s*\.\s*round\(\s*toFiniteNumber\(\s*stats\s*\?\.\s*memory\s*\?\.\s*heapUsed\s*\)\s*\/\s*1024\s*\/\s*1024\s*,?\s*\);?/,
	);
	assert.match(
		source,
		/const heapTotalMb\s*=\s*Math\s*\.\s*round\(\s*toFiniteNumber\(\s*stats\s*\?\.\s*memory\s*\?\.\s*heapTotal\s*\)\s*\/\s*1024\s*\/\s*1024\s*,?\s*\);?/,
	);
	assert.match(source, /value=\{`\$\{heapUsedMb\} MB`\}/);
	assert.match(source, /sub=\{`전체 \$\{heapTotalMb\} MB`\}/);
	assert.doesNotMatch(source, /Math\.floor\(stats\.uptime \/ 60\)/);
	assert.doesNotMatch(
		source,
		/Math\.round\(stats\.memory\.heapUsed \/ 1024 \/ 1024\)/,
	);
	assert.doesNotMatch(
		source,
		/Math\.round\(stats\.memory\.heapTotal \/ 1024 \/ 1024\)/,
	);
});
