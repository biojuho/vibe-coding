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
	assert.match(systemActions, /latency: ["']확인 불가["']/);
	assert.doesNotMatch(source, /System Diagnostics/);
	assert.doesNotMatch(source, /Database Status/);
	assert.doesNotMatch(source, /Loading records/);
	assert.doesNotMatch(source, /Please try again in a moment/);
	assert.doesNotMatch(source, /description: error\.message/);
	assert.doesNotMatch(systemActions, /status: ["']Online["']/);
	assert.doesNotMatch(systemActions, /status: ["']Offline["']/);
	assert.doesNotMatch(systemActions, /latency: ["']N\/A["']/);
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
