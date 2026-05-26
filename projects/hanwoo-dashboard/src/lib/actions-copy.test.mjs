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

test("server action user-facing failures use Korean product copy", () => {
	const cattleActions = readSource("lib/actions/cattle.js");
	const salesActions = readSource("lib/actions/sales.js");
	const buildingActions = readSource("lib/actions/building.js");
	const farmSettingsActions = readSource("lib/actions/farm-settings.js");
	const feedActions = readSource("lib/actions/feed.js");
	const inventoryActions = readSource("lib/actions/inventory.js");
	const scheduleActions = readSource("lib/actions/schedule.js");
	const expenseActions = readSource("lib/actions/expense.js");
	const systemActions = readSource("lib/actions/system.js");

	assert.match(cattleActions, /개체 목록을 불러오지 못했습니다/);
	assert.match(cattleActions, /개체를 등록하지 못했습니다/);
	assert.match(cattleActions, /개체 정보를 수정하지 못했습니다/);
	assert.match(cattleActions, /분만 처리를 완료하지 못했습니다/);
	assert.match(
		cattleActions,
		/이미 등록된 이력번호입니다\. 다른 이력번호를 입력해 주세요\./,
	);
	assert.match(cattleActions, /error\?\.code !== ["']P2002["']/);
	assert.match(cattleActions, /target\.includes\(["']tagNumber["']\)/);
	assert.match(cattleActions, /판매 기록이 있어 보관 처리할 수 없습니다/);
	assert.match(cattleActions, /개체 보관 처리에 실패했습니다/);
	assert.doesNotMatch(cattleActions, /개체 삭제에 실패했습니다/);
	assert.match(salesActions, /판매 기록을 불러오지 못했습니다/);
	assert.match(salesActions, /판매 기록을 등록하지 못했습니다/);
	assert.match(buildingActions, /축사 정보를 추가하지 못했습니다/);
	assert.match(buildingActions, /먼저 소를 이동해 주세요/);
	assert.match(buildingActions, /축사를 삭제하지 못했습니다/);
	assert.match(farmSettingsActions, /농장 정보를 저장하지 못했습니다/);
	assert.match(feedActions, /급여 기록을 저장하지 못했습니다/);
	assert.match(inventoryActions, /재고 항목을 추가하지 못했습니다/);
	assert.match(inventoryActions, /재고 수량을 수정하지 못했습니다/);
	assert.match(scheduleActions, /일정을 등록하지 못했습니다/);
	assert.match(scheduleActions, /일정 상태를 변경하지 못했습니다/);
	assert.match(expenseActions, /비용 기록을 등록하지 못했습니다/);
	assert.match(systemActions, /지원하지 않는 데이터 유형입니다/);
	assert.match(systemActions, /원본 데이터를 불러오지 못했습니다/);
	assert.match(systemActions, /진단 정보를 불러오지 못했습니다/);

	assert.doesNotMatch(cattleActions, /Failed to fetch cattle data/);
	assert.doesNotMatch(cattleActions, /message: error\.message/);
	assert.doesNotMatch(salesActions, /Failed to fetch sales records/);
	assert.doesNotMatch(salesActions, /message: error\.message/);
	assert.doesNotMatch(buildingActions, /message: e\.message/);
	assert.doesNotMatch(buildingActions, /이동해주세요/);
	assert.doesNotMatch(farmSettingsActions, /message: e\.message/);
	assert.doesNotMatch(feedActions, /message: e\.message/);
	assert.doesNotMatch(inventoryActions, /message: error\.message/);
	assert.doesNotMatch(scheduleActions, /message: e\.message/);
	assert.doesNotMatch(expenseActions, /message: error\.message/);
	assert.doesNotMatch(systemActions, /message: error\.message/);
	assert.doesNotMatch(systemActions, /error: error\.message/);
	assert.doesNotMatch(systemActions, /Invalid model name/);
});

test("sales history copy uses validated payload values", () => {
	const salesActions = readSource("lib/actions/sales.js");

	assert.match(salesActions, /payload\.price\.toLocaleString\(\)/);
	assert.match(
		salesActions,
		/const saleGradeLabel = payload\.grade \|\| ["']등급 미등록["'];/,
	);
	assert.match(salesActions, /등급: \$\{saleGradeLabel\}/);
	assert.doesNotMatch(salesActions, /parseInt\(data\.price\)/);
	assert.doesNotMatch(salesActions, /data\.grade \|\| ["']-["']/);
	assert.doesNotMatch(salesActions, /payload\.grade \|\| ["']-["']/);
});
