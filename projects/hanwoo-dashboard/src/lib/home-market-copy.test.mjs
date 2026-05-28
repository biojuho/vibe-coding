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

test("home dashboard fallback and panel labels use Korean product copy", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /Joolife 한우 농장/);
	assert.match(source, /오늘 요약/);
	assert.match(source, /빠른 기록/);
	assert.match(source, /운영 준비/);
	assert.doesNotMatch(source, /Joolife Dashboard/);
	assert.doesNotMatch(source, /Today Brief/);
	assert.doesNotMatch(source, /Quick Record/);
	assert.doesNotMatch(source, /Farm Setup/);
	assert.match(source, /대시보드 정보를 불러오지 못했습니다/);
	assert.match(
		source,
		/대시보드 정보를 불러오는 데 시간이 오래 걸리고 있습니다/,
	);
	assert.doesNotMatch(source, /대시보드 데이터를 불러오지 못했습니다/);
	assert.doesNotMatch(
		source,
		/대시보드 데이터를 불러오는 데 시간이 오래 걸리고 있습니다/,
	);
	assert.match(source, /모든 권리 보유/);
	assert.match(source, /운영 문의: joolife@joolife\.io\.kr/);
	assert.doesNotMatch(source, /000-00-00000/);
	assert.doesNotMatch(source, /사업자등록번호: 000/);
	assert.doesNotMatch(source, /Failed to load/);
	assert.doesNotMatch(source, /Loading .* timed out/);
	assert.doesNotMatch(source, /All rights reserved/);
});

test("dashboard cattle mutation catch paths use safe Korean fallback copy", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(
		source,
		/요청 처리 중 오류가 발생했습니다\. 잠시 후 다시 시도해 주세요\./,
	);
	assert.match(source, /description: "잠시 후 다시 시도해 주세요\."/);
	assert.doesNotMatch(source, /시도해주세요/);
	assert.match(source, /개체를 보관 처리할까요\?/);
	assert.match(source, /보관 기록으로 남습니다/);
	assert.match(source, /confirmLabel: "개체 보관 처리"/);
	assert.match(source, /cancelLabel: "개체 보관 취소"/);
	assert.doesNotMatch(
		source,
		/confirmLabel: "보관 처리"[\s\S]*?cancelLabel: "취소"/,
	);
	assert.match(source, /개체를 보관 처리했습니다/);
	assert.match(source, /개체 보관 처리에 실패했습니다/);
	assert.match(source, /console\.error\(["']Failed to add cattle:["'], error\);/);
	assert.match(source, /console\.error\(["']Failed to update cattle:["'], error\);/);
	assert.doesNotMatch(source, /showError\(errorTitle, error\.message\)/);
	assert.doesNotMatch(source, /개체를 삭제할까요/);
	assert.doesNotMatch(source, /개체를 삭제했습니다/);
	assert.doesNotMatch(source, /개체 삭제에 실패했습니다/);
});

test("dashboard drag-and-drop cattle moves wait for confirmation and update before accepting another move", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const movingCattleIdRef = useRef\(null\)/);
	assert.match(source, /if \(movingCattleIdRef\.current\) return false;/);
	assert.match(source, /movingCattleIdRef\.current = cattleId;/);
	assert.match(source, /const shouldMove = await confirm\(\{/);
	assert.match(source, /return handleUpdateCattle\(updated, \{/);
	assert.match(source, /finally \{\s+movingCattleIdRef\.current = null;/);
	assert.match(source, /개체를 이동할까요\?/);
	assert.match(source, /confirmLabel: "개체 이동"/);
	assert.match(source, /cancelLabel: "개체 이동 취소"/);
	assert.doesNotMatch(
		source,
		/confirmLabel: "이동"[\s\S]*?cancelLabel: "취소"/,
	);
	assert.match(source, /개체를 이동했습니다/);
});

test("calving flow requires an operator-entered calf tag number", () => {
	const dashboardSource = readSource("components/DashboardClient.js");
	const calvingTabSource = readSource("components/tabs/CalvingTab.js");
	const formSchemaSource = readSource("lib/formSchemas.js");

	assert.match(calvingTabSource, /송아지 이력번호/);
	assert.match(calvingTabSource, /register\(["']calfTagNumber["']\)/);
	assert.match(calvingTabSource, /calfTagNumber: values\.calfTagNumber/);
	assert.match(
		formSchemaSource,
		/const DATE_INPUT_PATTERN = \/\^\\d\{4\}-\\d\{2\}-\\d\{2\}\$\/;/,
	);
	assert.match(
		formSchemaSource,
		/const PLAIN_NUMBER_INPUT_PATTERN = \/\^-\?\(\?:\\d\+\|\\d\+\\\.\\d\+\|\\\.\\d\+\)\$\/;/,
	);
	assert.match(formSchemaSource, /const toPlainNumber = \(value\) =>/);
	assert.match(
		formSchemaSource,
		/PLAIN_NUMBER_INPUT_PATTERN\.test\(normalized\)/,
	);
	assert.match(formSchemaSource, /const isDateInputString = \(value\) =>/);
	assert.match(
		formSchemaSource,
		/parsed\.toISOString\(\)\.slice\(0, 10\) === value/,
	);
	assert.match(formSchemaSource, /\.refine\(isDateInputString,/);
	assert.doesNotMatch(formSchemaSource, /z\.coerce\.number/);
	assert.doesNotMatch(formSchemaSource, /new Date\(value\)\.getTime\(\)/);
	assert.match(
		formSchemaSource,
		/calfTagNumber: requiredText\(["']송아지 이력번호를 입력해 주세요\.["'], 30\)/,
	);
	assert.doesNotMatch(dashboardSource, /KR0000/);
	assert.doesNotMatch(dashboardSource, /Math\.random\(\) \* 900000/);
});

test("dashboard full-list loading failures show retry feedback instead of silent placeholders", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /FULL_CATTLE_LOAD_ERROR_MESSAGE/);
	assert.match(source, /FULL_SALES_LOAD_ERROR_MESSAGE/);
	assert.match(source, /function normalizeFullListLoadOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === "object" && !Array\.isArray\(options\)/,
	);
	assert.match(
		source,
		/const ensureAllCattleLoaded = useCallback\(\s+async \(options = \{\}\) => \{\s+const \{ silent = false \} = normalizeFullListLoadOptions\(options\);/,
	);
	assert.match(
		source,
		/const ensureAllSalesLoaded = useCallback\(\s+async \(options = \{\}\) => \{\s+const \{ silent = false \} = normalizeFullListLoadOptions\(options\);/,
	);
	assert.match(
		source,
		/setAllCattleLoadError\(FULL_CATTLE_LOAD_ERROR_MESSAGE\)/,
	);
	assert.match(source, /setAllSalesLoadError\(FULL_SALES_LOAD_ERROR_MESSAGE\)/);
	assert.match(source, /const preloadForTab = useCallback/);
	assert.match(source, /preloadForTab\(nextTab\)/);
	assert.match(source, /preloadForTab\(action\.targetTab\)/);
	assert.match(source, /onNavigate=\{handleTabChange\}/);
	assert.match(
		source,
		/ensureAllCattleLoaded\(\{ silent: true \}\)\.catch\(\(\) => \{\}\)/,
	);
	assert.match(
		source,
		/ensureAllSalesLoaded\(\{ silent: true \}\)\.catch\(\(\) => \{\}\)/,
	);
	assert.match(source, /다시 불러오기/);
	assert.doesNotMatch(
		source,
		/void ensureAllCattleLoaded\(\{ silent: true \}\);/,
	);
	assert.doesNotMatch(
		source,
		/void ensureAllSalesLoaded\(\{ silent: true \}\);/,
	);
	assert.doesNotMatch(source, /async \(\{ silent = false \} = \{\}\) =>/);
});

test("dashboard full-list preload completions ignore stale unmounted state", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+dashboardMountedRef\.current = true;\s+return \(\) => \{\s+dashboardMountedRef\.current = false;/,
	);
	assert.match(
		source,
		/const normalizedItems = normalizeDashboardCattleList\(items\);\s+if \(dashboardMountedRef\.current\) \{\s+setAllCattleRegistry\(normalizedItems\);/,
	);
	assert.match(
		source,
		/if \(dashboardMountedRef\.current\) \{\s+setAllCattleLoadError\(FULL_CATTLE_LOAD_ERROR_MESSAGE\);/,
	);
	assert.match(
		source,
		/if \(dashboardMountedRef\.current\) \{\s+setIsAllCattleLoading\(false\);/,
	);
	assert.match(
		source,
		/if \(dashboardMountedRef\.current\) \{\s+setAllSalesLedger\(items\);/,
	);
	assert.match(
		source,
		/if \(dashboardMountedRef\.current\) \{\s+setAllSalesLoadError\(FULL_SALES_LOAD_ERROR_MESSAGE\);/,
	);
	assert.match(
		source,
		/if \(dashboardMountedRef\.current\) \{\s+setIsAllSalesLoading\(false\);/,
	);
	assert.match(source, /fullCattleLoadRef\.current = null;/);
	assert.match(source, /fullSalesLoadRef\.current = null;/);
	assert.doesNotMatch(
		source,
		/\.then\(\(items\) => \{\s+const normalizedItems = normalizeDashboardCattleList\(items\);\s+setAllCattleRegistry\(normalizedItems\);/,
	);
	assert.doesNotMatch(
		source,
		/\.then\(\(items\) => \{\s+setAllSalesLedger\(items\);/,
	);
});

test("dashboard summary and notification refresh completions ignore stale unmounted state", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/if \(\s+dashboardMountedRef\.current &&\s+summaryRefreshRequestRef\.current === requestId\s+\) \{\s+setSummary\(json\.data\);/,
	);
	assert.match(
		source,
		/const nextNotifications = await getNotifications\(\);\s+if \(dashboardMountedRef\.current\) \{\s+setNotifications\(normalizeDashboardNotifications\(nextNotifications\)\);/,
	);
	assert.doesNotMatch(
		source,
		/if \(summaryRefreshRequestRef\.current === requestId\) \{\s+setSummary\(json\.data\);/,
	);
	assert.doesNotMatch(
		source,
		/const nextNotifications = await getNotifications\(\);\s+setNotifications\(normalizeDashboardNotifications\(nextNotifications\)\);/,
	);
});

test("dashboard cattle archive completions ignore stale unmounted state", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/const result = await deleteCattle\(id\);\s+if \(result\.success\) \{\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+removeCattleRecord\(id\);/,
	);
	assert.match(
		source,
		/if \(dashboardMountedRef\.current\) \{\s+showError\("개체 보관 처리에 실패했습니다\.", result\.message\);\s+\}/,
	);
	assert.match(
		source,
		/catch \{\s+if \(dashboardMountedRef\.current\) \{\s+showError\("개체 보관 처리 중 오류가 발생했습니다\."\);\s+\}\s+return false;/,
	);
	assert.match(
		source,
		/finally \{\s+if \(dashboardMountedRef\.current\) \{\s+setDeletingCattleId\(null\);\s+\}/,
	);
	assert.doesNotMatch(
		source,
		/if \(result\.success\) \{\s+removeCattleRecord\(id\);/,
	);
	assert.doesNotMatch(
		source,
		/finally \{\s+setDeletingCattleId\(null\);/,
	);
});

test("dashboard cattle create and update completions ignore stale unmounted state", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/const result = await createCattle\(newCattle\);\s+if \(result\.success\) \{\s+const savedCattle = result\.data \|\| newCattle;\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+prependCattleRecord\(savedCattle\);/,
	);
	assert.match(
		source,
		/const result = await updateCattle\(updated\.id, updated\);\s+if \(result\.success\) \{\s+const savedCattle = result\.data \|\| updated;\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+replaceCattleRecord\(savedCattle\);/,
	);
	assert.match(
		source,
		/if \(dashboardMountedRef\.current\) \{\s+showError\(errorTitle, result\.message\);\s+\}\s+return false;\s+\} catch \(error\) \{\s+console\.error\(["']Failed to add cattle:["'], error\);\s+if \(dashboardMountedRef\.current\) \{\s+showError\(errorTitle, unexpectedActionErrorDescription\);/,
	);
	assert.match(
		source,
		/if \(dashboardMountedRef\.current\) \{\s+showError\(errorTitle, result\.message\);\s+\}\s+return false;\s+\} catch \(error\) \{\s+console\.error\(["']Failed to update cattle:["'], error\);\s+if \(dashboardMountedRef\.current\) \{\s+showError\(errorTitle, unexpectedActionErrorDescription\);/,
	);
	assert.doesNotMatch(
		source,
		/const savedCattle = result\.data \|\| newCattle;\s+prependCattleRecord\(savedCattle\);/,
	);
	assert.doesNotMatch(
		source,
		/const savedCattle = result\.data \|\| updated;\s+replaceCattleRecord\(savedCattle\);/,
	);
});

test("dashboard building mutation completions ignore stale unmounted state", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/if \(!res\.success\) \{\s+if \(dashboardMountedRef\.current\) \{\s+showError\("축사 정보를 추가하지 못했습니다\.", res\.message\);\s+\}\s+return false;\s+\}\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+setBuildings\(\(prev\) => sortByName\(\[res\.data, \.\.\.prev\]\)\);/,
	);
	assert.match(
		source,
		/if \(!res\.success\) \{\s+if \(dashboardMountedRef\.current\) \{\s+showError\("축사를 삭제하지 못했습니다\.", res\.message\);\s+\}\s+return false;\s+\}\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+setBuildings\(\(prev\) => prev\.filter\(\(building\) => building\.id !== id\)\);/,
	);
	assert.doesNotMatch(
		source,
		/if \(!res\.success\) \{\s+showError\("축사 정보를 추가하지 못했습니다\.", res\.message\);/,
	);
	assert.doesNotMatch(
		source,
		/if \(!res\.success\) \{\s+showError\("축사를 삭제하지 못했습니다\.", res\.message\);/,
	);
	assert.doesNotMatch(
		source,
		/if \(!res\.success\) \{\s+showError\("축사 정보를 추가하지 못했습니다\.", res\.message\);\s+return false;\s+\}\s+setBuildings\(\(prev\) => sortByName\(\[res\.data, \.\.\.prev\]\)\);/,
	);
	assert.doesNotMatch(
		source,
		/if \(!res\.success\) \{\s+showError\("축사를 삭제하지 못했습니다\.", res\.message\);\s+return false;\s+\}\s+setBuildings\(\(prev\) => prev\.filter\(\(building\) => building\.id !== id\)\);/,
	);
});

test("dashboard inventory mutation completions ignore stale unmounted state", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/const handleAddItem = async \(data\) => \{\s+const res = await addInventoryItem\(data\);\s+if \(!res\.success\) \{\s+if \(dashboardMountedRef\.current\) \{\s+showError\("[^"]+", res\.message\);\s+\}\s+return false;\s+\}\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+setInventoryList\(\(prev\) => sortInventoryItems\(\[res\.data, \.\.\.prev\]\)\);/,
	);
	assert.match(
		source,
		/const handleUpdateQuantity = async \(id, qty\) => \{\s+const res = await updateInventoryQuantity\(id, qty\);\s+if \(!res\.success\) \{\s+if \(dashboardMountedRef\.current\) \{\s+showError\("[^"]+", res\.message\);\s+\}\s+return false;\s+\}\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+setInventoryList\(\(prev\) =>/,
	);
	assert.doesNotMatch(
		source,
		/const handleAddItem = async \(data\) => \{\s+const res = await addInventoryItem\(data\);\s+if \(!res\.success\) \{\s+showError\("[^"]+", res\.message\);/,
	);
	assert.doesNotMatch(
		source,
		/const handleUpdateQuantity = async \(id, qty\) => \{\s+const res = await updateInventoryQuantity\(id, qty\);\s+if \(!res\.success\) \{\s+showError\("[^"]+", res\.message\);/,
	);
});

test("dashboard schedule mutation completions ignore stale unmounted state", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/const handleCreateEvent = async \(data\) => \{\s+const res = await createScheduleEvent\(data\);\s+if \(!res\.success\) \{\s+if \(dashboardMountedRef\.current\) \{\s+showError\("[^"]+", res\.message\);\s+\}\s+return false;\s+\}\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+setScheduleEvents\(\(prev\) => sortByDateAsc\(\[res\.data, \.\.\.prev\], "date"\)\);/,
	);
	assert.match(
		source,
		/const handleToggleEvent = async \(id, isCompleted\) => \{\s+const res = await toggleEventCompletion\(id, isCompleted\);\s+if \(!res\.success\) \{\s+if \(dashboardMountedRef\.current\) \{\s+showError\("[^"]+", res\.message\);\s+\}\s+return false;\s+\}\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+setScheduleEvents\(\(prev\) =>/,
	);
	assert.doesNotMatch(
		source,
		/const handleCreateEvent = async \(data\) => \{\s+const res = await createScheduleEvent\(data\);\s+if \(!res\.success\) \{\s+showError\("[^"]+", res\.message\);/,
	);
	assert.doesNotMatch(
		source,
		/const handleToggleEvent = async \(id, isCompleted\) => \{\s+const res = await toggleEventCompletion\(id, isCompleted\);\s+if \(!res\.success\) \{\s+showError\("[^"]+", res\.message\);/,
	);
});

test("dashboard sales and feed mutation completions ignore stale unmounted state", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/const res = await createSalesRecord\(data\);\s+if \(!res\.success\) \{\s+if \(dashboardMountedRef\.current\) \{\s+showError\("[^"]+", res\.message\);\s+\}\s+return false;\s+\}\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+prependSaleRecord\(res\.data\);/,
	);
	assert.match(
		source,
		/const res = await recordFeed\(data\);\s+if \(!res\.success\) \{\s+if \(dashboardMountedRef\.current\) \{\s+showError\("[^"]+", res\.message\);\s+\}\s+return false;\s+\}\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+setFeedHistory\(\(prev\) =>/,
	);
	assert.doesNotMatch(
		source,
		/const res = await createSalesRecord\(data\);\s+if \(!res\.success\) \{\s+showError\("[^"]+", res\.message\);/,
	);
	assert.doesNotMatch(
		source,
		/const res = await recordFeed\(data\);\s+if \(!res\.success\) \{\s+showError\("[^"]+", res\.message\);/,
	);
});

test("dashboard drag move confirmation ignores stale unmounted state", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/const shouldMove = await confirm\(\{[\s\S]+?\}\);\s+if \(!dashboardMountedRef\.current\) \{\s+return false;\s+\}\s+if \(!shouldMove\) \{\s+return false;\s+\}\s+const updated = \{/,
	);
	assert.doesNotMatch(
		source,
		/const shouldMove = await confirm\(\{[\s\S]+?\}\);\s+if \(!shouldMove\) \{\s+return false;\s+\}\s+const updated = \{/,
	);
});

test("dashboard calving mutation completions ignore stale unmounted state", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/if \(!res\.success\) \{\s+if \(dashboardMountedRef\.current\) \{\s+showError\("[^"]+", res\.message\);\s+\}\s+return false;\s+\}\s+const savedMother = res\.data\?\.mother \|\| updatedMother;\s+const savedCalf = res\.data\?\.calf \|\| calfDraft;\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+upsertCalvingRecords\(savedMother, savedCalf\);/,
	);
	assert.doesNotMatch(
		source,
		/if \(!res\.success\) \{\s+showError\("[^"]+", res\.message\);\s+return false;\s+\}\s+const savedMother = res\.data\?\.mother \|\| updatedMother;/,
	);
	assert.doesNotMatch(
		source,
		/const savedCalf = res\.data\?\.calf \|\| calfDraft;\s+upsertCalvingRecords\(savedMother, savedCalf\);/,
	);
});

test("dashboard farm settings mutation completions ignore stale unmounted state", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/const handleUpdateFarmSettings = async \(data\) => \{\s+const res = await updateFarmSettings\(data\);\s+if \(!res\.success\) \{\s+if \(dashboardMountedRef\.current\) \{\s+showError\("[^"]+", res\.message\);\s+\}\s+return false;\s+\}\s+if \(!dashboardMountedRef\.current\) \{\s+return true;\s+\}\s+setFarmSettings\(res\.data\);/,
	);
	assert.doesNotMatch(
		source,
		/const handleUpdateFarmSettings = async \(data\) => \{\s+const res = await updateFarmSettings\(data\);\s+if \(!res\.success\) \{\s+showError\("[^"]+", res\.message\);/,
	);
	assert.doesNotMatch(
		source,
		/if \(!res\.success\) \{\s+showError\("[^"]+", res\.message\);\s+return false;\s+\}\s+setFarmSettings\(res\.data\);/,
	);
});

test("dashboard offline sync refresh failures are announced separately", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(
		source,
		/const OFFLINE_SYNC_REFRESH_ERROR_MESSAGE\s*=\s*["']동기화 결과를 보려면 화면을 새로고침해 주세요\.["'];?/,
	);
	assert.match(
		source,
		/try \{\s+router\.refresh\(\);\s+\} catch \(refreshError\) \{\s+console\.error\(["']Offline queue refresh failed:/,
	);
	assert.match(
		source,
		/title: ["']동기화 후 화면 새로고침에 실패했습니다\.["'][\s\S]*?description: OFFLINE_SYNC_REFRESH_ERROR_MESSAGE/,
	);
	assert.doesNotMatch(
		source,
		/if \(synced > 0\) \{\s+router\.refresh\(\);\s+\}/,
	);
});

test("home building navigation uses semantic buttons", () => {
	const source = readSource("components/DashboardClient.js");
	const css = readSource("app/globals.css");

	assert.match(source, /<button\s+type="button"\s+className="empty-state-cta/);
	assert.match(source, /onClick=\{\(\) => handleTabChange\(["']settings["']\)\}/);
	assert.match(source, /첫 번째 축사를 추가해 주세요/);
	assert.doesNotMatch(source, /첫 번째 축사를 추가해보세요/);
	assert.match(
		source,
		/onClick=\{\(\) => handleTabChange\(["']settings["']\)\}[\s\S]*?aria-label="설정에서 첫 번째 축사를 추가해 주세요"[\s\S]*?title="설정에서 첫 번째 축사를 추가해 주세요"/,
	);
	assert.doesNotMatch(source, /설정에서 첫 번째 축사 추가하기/);
	assert.match(
		source,
		/type="button"\s+onClick=\{\(\) => handleSelectBuilding\(building\.id\)\}/,
	);
	assert.match(
		source,
		/const buildingCardLabel = `\$\{building\.name\} 축사 상세 보기, 총 \$\{building\.penCount\}칸, \$\{buildingHeadcount\}두 배치됨`;/,
	);
	assert.match(source, /aria-label=\{buildingCardLabel\}/);
	assert.match(source, /title=\{buildingCardLabel\}/);
	assert.match(
		source,
		/className="clay-surface rounded-\[28px\][^"]*group\/building w-full text-left"/,
	);
	assert.match(css, /\.empty-state-cta \{\s+background:[\s\S]*?font: inherit;/);
	assert.doesNotMatch(
		source,
		/<div className="empty-state-cta[^"]*"[^>]*onClick/,
	);
	assert.doesNotMatch(source, /<Card key=\{building\.id\} onClick/);
});

test("setup progress track exposes semantic progress state", () => {
	const source = readSource("components/DashboardClient.js");
	const setupProgressTrackLabel = '"운영 준비도 진행률"';

	assert.match(
		source,
		/const setupProgressLabel = `[^`]*\$\{progressPercent\}% \(\$\{progressCompleted\}\/\$\{progressTotal\}\)`;/,
	);
	assert.ok(
		source.includes(
			`const setupProgressTrackLabel = ${setupProgressTrackLabel}`,
		),
	);
	assert.match(source, /function SetupProgressPanel[\s\S]*const setupProgressLabel/);
	assert.match(source, /function SetupProgressPanel\(options = \{\}\) \{/);
	assert.match(
		source,
		/const progressItems = normalizeDashboardHelperItems\(safeProgress\.items\);/,
	);
	assert.match(
		source,
		/const progressPercent = Math\.min\([\s\S]*?100,[\s\S]*?Math\.max\(0, toFiniteNumber\(safeProgress\.percent\)\),[\s\S]*?\);/,
	);
	assert.match(source, /if \(!progressItems\.length \|\| progressPercent === 100\) \{/);
	assert.doesNotMatch(
		source,
		/function TodayFocusPanel[\s\S]*setupProgressLabel[\s\S]*function SetupProgressPanel/,
	);
	assert.match(source, /className="setup-progress-score"/);
	assert.match(source, /aria-label=\{setupProgressLabel\}/);
	assert.match(source, /title=\{setupProgressLabel\}/);
	assert.match(source, /className="setup-progress-track"/);
	assert.match(source, /role="progressbar"/);
	assert.match(source, /aria-label=\{setupProgressTrackLabel\}/);
	assert.match(source, /aria-valuemin=\{0\}/);
	assert.match(source, /aria-valuemax=\{100\}/);
	assert.match(source, /aria-valuenow=\{progressPercent\}/);
	assert.match(source, /aria-valuetext=\{setupProgressLabel\}/);
	assert.match(source, /title=\{setupProgressLabel\}/);
	assert.match(source, /style=\{\{ width: `\$\{progressPercent\}%` \}\}/);
	assert.doesNotMatch(
		source,
		/<div\s+className="setup-progress-track"\s+aria-hidden="true"/,
	);
});

test("setup progress items expose completion state in their accessible names", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(
		source,
		/const setupItemLabel = `\$\{item\.title\} \$\{item\.done \?/,
	);
	assert.match(source, /aria-label=\{setupItemLabel\}/);
	assert.match(source, /title=\{setupItemLabel\}/);
	assert.match(source, /className=\{`setup-progress-item \$\{item\.done/);
	assert.match(source, /<span className="setup-progress-icon" aria-hidden="true">/);
	assert.match(source, /progressItems\.map\(\(item\) => \{/);
});

test("home dashboard icon-only actions expose Korean accessible labels", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /aria-label="알림 센터 열기"/);
	assert.match(source, /title="알림 센터 열기"/);
	assert.match(source, /aria-label="개체 등록 열기"/);
	assert.match(source, /title="개체 등록 열기"/);
	assert.match(source, /aria-label="현장 스마트 모드 활성화"/);
	assert.match(source, /title="현장 스마트 모드 활성화"/);
	assert.match(source, /aria-label="축사 목록으로 돌아가기"/);
	assert.match(source, /aria-label="칸 목록으로 돌아가기"/);
	assert.match(source, /<Bell className="h-5 w-5" aria-hidden="true" \/>/);
	assert.match(source, /<Plus className="h-5 w-5" aria-hidden="true" \/>/);
	assert.match(source, /<ArrowLeft className="h-5 w-5" aria-hidden="true" \/>/);
	assert.match(
		source,
		/<span className="section-header-icon" aria-hidden="true">\s*🏠\s*<\/span>/,
	);
	assert.match(
		source,
		/<span className="cta-icon" aria-hidden="true">\s*🏠\s*<\/span>/,
	);
	assert.match(
		source,
		/shadow-\[0_0_10px_hsl\(var\(--destructive\)\)\]"\s+aria-hidden="true"/,
	);
	assert.match(
		source,
		/<div className="text-3xl mb-2" aria-hidden="true">\s*🐄\s*<\/div>/,
	);
	assert.match(source, /function PenCattleList\(options = \{\}\) \{/);
	assert.match(
		source,
		/const visibleCattle = normalizeDashboardHelperItems\(cattleList\);/,
	);
	assert.match(
		source,
		/const handleSelect = typeof onSelect === ["']function["'] \? onSelect : \(\) => \{\};/,
	);
	assert.match(source, /const penCattle = visibleCattle\.filter\(/);
	assert.match(source, /onClick=\{handleSelect\}/);
	assert.match(source, /이 칸은 비어 있습니다/);
	assert.doesNotMatch(source, /이 칸은 비어있습니다/);
	assert.doesNotMatch(source, /aria-label="Notifications"/);
	assert.doesNotMatch(source, /aria-label="Add cattle"/);
	assert.doesNotMatch(source, /aria-label="Back"/);
});

test("home footer links expose explicit navigation labels", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(
		source,
		/href="\/terms"[\s\S]*?aria-label="Joolife 이용약관 보기"[\s\S]*?title="Joolife 이용약관 보기"/,
	);
	assert.match(
		source,
		/href="\/privacy"[\s\S]*?aria-label="Joolife 개인정보처리방침 보기"[\s\S]*?title="Joolife 개인정보처리방침 보기"/,
	);
	assert.match(
		source,
		/href="\/subscription"[\s\S]*?aria-label="Joolife 프리미엄 구독 화면 열기"[\s\S]*?title="Joolife 프리미엄 구독 화면 열기"/,
	);
});

test("today focus action buttons expose consolidated task labels", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /function normalizeDashboardHelperOptions\(options\) \{/);
	assert.match(source, /function normalizeDashboardHelperItems\(items\) \{/);
	assert.match(
		source,
		/items\.filter\([\s\S]*?\(item\) => item && typeof item === ["']object["'] && !Array\.isArray\(item\)/,
	);
	assert.match(source, /function TodayFocusPanel\(options = \{\}\) \{/);
	assert.match(
		source,
		/const visibleItems = normalizeDashboardHelperItems\(items\);/,
	);
	assert.match(
		source,
		/const handleNavigate = typeof onNavigate === ["']function["'] \? onNavigate : \(\) => \{\};/,
	);
	assert.match(source, /if \(!visibleItems\.length\) \{/);
	assert.match(source, /\{visibleItems\.length\}개/);
	assert.match(source, /visibleItems\.map\(\(item\) => \{/);
	assert.match(
		source,
		/const focusItemLabel = `\$\{item\.title\} - \$\{item\.detail\} \(\$\{item\.meta\}\)`;/,
	);
	assert.match(
		source,
		/onClick=\{\(\) => handleClick\(item\)\}\s+aria-label=\{focusItemLabel\}\s+title=\{focusItemLabel\}/,
	);
	assert.match(source, /className="today-focus-meta">\{item\.meta\}<\/span>/);
});

test("quick action buttons expose consolidated task labels", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /function QuickActionPanel\(options = \{\}\) \{/);
	assert.match(
		source,
		/const visibleActions = normalizeDashboardHelperItems\(actions\);/,
	);
	assert.match(
		source,
		/const handleAction = typeof onAction === ["']function["'] \? onAction : \(\) => \{\};/,
	);
	assert.match(source, /title="이번 달 출하"/);
	assert.doesNotMatch(source, /title="이번달 출하"/);
	assert.match(source, /detail: "판매 기록 바로 입력"/);
	assert.doesNotMatch(source, /detail: "매출 바로 입력"/);
	assert.match(
		source,
		/const quickActionLabel = `\$\{action\.label\} - \$\{action\.detail\}`;/,
	);
	assert.match(
		source,
		/onClick=\{\(\) => handleAction\(action\)\}\s+aria-label=\{quickActionLabel\}\s+title=\{quickActionLabel\}/,
	);
	assert.match(
		source,
		/<span className="quick-action-icon" aria-hidden="true">[\s\S]*?<Icon size=\{18\} strokeWidth=\{2\.2\} \/>/,
	);
});

test("notification center trigger exposes its dialog relationship", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /const NOTIFICATION_MODAL_ID = "notification-center-dialog";/);
	assert.match(source, /aria-haspopup="dialog"/);
	assert.match(source, /aria-expanded=\{showNotifications\}/);
	assert.match(source, /aria-controls=\{NOTIFICATION_MODAL_ID\}/);
	assert.match(source, /<NotificationModal\s+id=\{NOTIFICATION_MODAL_ID\}/);
});

test("market price widget uses Korean product copy for visible states", () => {
	const source = readSource("components/widgets/MarketPriceWidget.js");

	assert.match(
		source,
		/function toValidUpdatedAt\(value, fallback = new Date\(\)\) \{/,
	);
	assert.match(
		source,
		/return Number\.isNaN\(date\.getTime\(\)\) \? fallback : date;/,
	);
	assert.match(source, /function normalizePriceSnapshot\(data\) \{/);
	assert.match(source, /bull: data\.bull \?\? \{\}/);
	assert.match(source, /cow: data\.cow \?\? \{\}/);
	assert.match(source, /function normalizeMarketPriceWidgetOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === "object" && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export default function MarketPriceWidget\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ initialData = null \} = normalizeMarketPriceWidgetOptions\(options\);/,
	);
	assert.match(
		source,
		/useState\(\s*\(\s*\)\s*=>\s*normalizePriceSnapshot\(\s*initialData\s*\),?\s*\)/,
	);
	assert.match(source, /setPrices\(normalizePriceSnapshot\(data\)\)/);
	assert.match(
		source,
		/initialData \? toValidUpdatedAt\(initialData\.fetchedAt\) : null/,
	);
	assert.match(
		source,
		/setLastUpdated\(toValidUpdatedAt\(data\?\.fetchedAt\)\)/,
	);
	assert.doesNotMatch(
		source,
		/export default function MarketPriceWidget\(\{ initialData = null \}\)/,
	);
	assert.match(source, /function normalizePricePanelOptions\(options\) \{/);
	assert.match(source, /function normalizePricePanelRows\(rows\) \{/);
	assert.match(
		source,
		/return Array\.isArray\(rows\) \? rows\.filter\(\(row\) => Array\.isArray\(row\)\) : \[\];/,
	);
	assert.match(source, /function PricePanel\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ title, rows \} = normalizePricePanelOptions\(options\);/,
	);
	assert.match(source, /const visibleRows = normalizePricePanelRows\(rows\);/);
	assert.match(source, /visibleRows\.map\(\(\[grade, value\], index\) =>/);
	assert.match(source, /index === visibleRows\.length - 1/);
	assert.doesNotMatch(source, /function PricePanel\(\{ title, rows \}\)/);
	assert.doesNotMatch(source, /rows\.map\(\(\[grade, value\], index\) =>/);

	assert.match(source, /한우 시세를 불러오는 중입니다/);
	assert.match(source, /지금은 한우 시세 정보를 확인할 수 없습니다/);
	assert.doesNotMatch(source, /지금은 한우 시세 데이터를 확인할 수 없습니다/);
	assert.match(source, /시세 흐름/);
	assert.match(source, /한우 도매 시세/);
	assert.match(source, /가중평균 거래가/);
	assert.match(source, /실시간 KAPE/);
	assert.match(source, /저장된 KAPE/);
	assert.match(source, /이전 저장값/);
	assert.match(source, /수소 kg당 시세/);
	assert.match(source, /암소 kg당 시세/);
	assert.match(source, /kg당 \{formatMoney\(value\)\}/);
	assert.doesNotMatch(source, /수소 \/ kg/);
	assert.doesNotMatch(source, /암소 \/ kg/);
	assert.doesNotMatch(source, /\{formatMoney\(value\)\} \/ kg/);
	assert.match(source, /마지막 갱신/);
	assert.match(source, /데이터 출처: KAPE/);
	assert.doesNotMatch(source, /<span>갱신 \{lastUpdated\.toLocaleTimeString\(\)\}<\/span>/);
	assert.doesNotMatch(source, /<span>출처: KAPE<\/span>/);
	assert.match(
		source,
		/role="status"\s+aria-live="polite"\s+aria-atomic="true"\s+aria-busy="true"/,
	);
	assert.match(
		source,
		/if \(!prices \|\| prices\.available === false\)[\s\S]*?role="status"[\s\S]*?aria-live="polite"[\s\S]*?aria-atomic="true"[\s\S]*?지금은 한우 시세 정보를 확인할 수 없습니다/,
	);
	assert.match(source, /disabled=\{loading\}\s+aria-busy=\{loading\}/);
	assert.match(source, /const isMountedRef = useRef\(false\);/);
	assert.match(
		source,
		/if \(!isMountedRef\.current\) \{\s+return Promise\.resolve\(null\);\s+\}\s+const requestId = requestSequenceRef\.current \+ 1;/,
	);
	assert.match(
		source,
		/if \(!isMountedRef\.current \|\| requestSequenceRef\.current !== requestId\) \{\s+return data;\s+\}/,
	);
	assert.match(
		source,
		/if \(isMountedRef\.current && requestSequenceRef\.current === requestId\) \{\s+setLoading\(false\);/,
	);
	assert.match(source, /let refreshTimer = null;/);
	assert.match(source, /let interval = null;/);
	assert.match(source, /let fallbackPollTimer = null;/);
	assert.match(source, /const MARKET_PRICE_POLL_INTERVAL_MS = 1000 \* 60 \* 60;/);
	assert.match(source, /const scheduleFallbackPolling = \(\) => \{/);
	assert.match(
		source,
		/try \{\s+refreshTimer = window\.setTimeout\(\(\) => \{\s+void fetchPrices\(\);\s+\}, 0\);\s+\} catch \(error\) \{/,
	);
	assert.match(
		source,
		/console\.error\(["']Failed to schedule market price refresh:/,
	);
	assert.match(source, /void Promise\.resolve\(\)\.then\(\(\) => fetchPrices\(\)\);/);
	assert.match(
		source,
		/try \{\s+interval = window\.setInterval\(/,
	);
	assert.match(source, /MARKET_PRICE_POLL_INTERVAL_MS/);
	assert.match(
		source,
		/console\.error\(["']Failed to schedule market price polling:/,
	);
	assert.match(source, /scheduleFallbackPolling\(\);/);
	assert.match(
		source,
		/fallbackPollTimer = window\.setTimeout\(\(\) => \{\s+void fetchPrices\(\);\s+if \(isMountedRef\.current\) \{\s+scheduleFallbackPolling\(\);/,
	);
	assert.match(
		source,
		/console\.error\(["']Failed to schedule market price fallback polling:/,
	);
	assert.match(
		source,
		/try \{\s+window\.clearTimeout\(refreshTimer\);\s+\} catch \{\}/,
	);
	assert.match(
		source,
		/try \{\s+window\.clearInterval\(interval\);\s+\} catch \{\}/,
	);
	assert.match(
		source,
		/try \{\s+window\.clearTimeout\(fallbackPollTimer\);\s+\} catch \{\}/,
	);
	assert.match(
		source,
		/aria-label=\{\s*loading \? ["']한우 시세 갱신 중["'] : ["']한우 시세 새로고침["']\s*\}/,
	);
	assert.match(
		source,
		/title=\{loading \? ["']한우 시세 갱신 중["'] : ["']한우 시세 새로고침["']\}/,
	);
	assert.doesNotMatch(source, /loading \? ["']시세 갱신 중["']/);
	assert.match(source, /<RefreshCwIcon\s+aria-hidden="true"/);
	assert.doesNotMatch(source, /Loading market prices/);
	assert.doesNotMatch(source, /Market price data is unavailable/);
	assert.doesNotMatch(source, /Market Pulse/);
	assert.doesNotMatch(source, /Hanwoo Market Prices/);
	assert.doesNotMatch(source, /weighted average transaction price/);
	assert.doesNotMatch(source, /Live KAPE|Cached KAPE|Stale Cache|Unavailable/);
	assert.doesNotMatch(source, /Bull \/ kg|Cow \/ kg/);
	assert.doesNotMatch(source, />Updated /);
	assert.doesNotMatch(source, />Source: KAPE/);
	assert.doesNotMatch(source, /aria-label="Refresh"/);
	assert.doesNotMatch(source, /new Date\(initialData\.fetchedAt\)/);
	assert.doesNotMatch(
		source,
		/setLastUpdated\(data\?\.fetchedAt \? new Date\(data\.fetchedAt\) : new Date\(\)\)/,
	);
	assert.doesNotMatch(source, /[吏媛異諛湲]/);
	assert.doesNotMatch(source, /\?[가-힣]/);
});

test("schedule calendar navigation exposes Korean accessible labels", () => {
	const source = readSource("components/tabs/ScheduleTab.js");

	assert.match(source, /aria-label="이전 달 보기"/);
	assert.match(source, /title="이전 달 보기"/);
	assert.match(source, /aria-label="다음 달 보기"/);
	assert.match(source, /title="다음 달 보기"/);
	assert.match(
		source,
		/<ChevronLeft\s+className="text-\[color:var\(--color-text-secondary\)\]"\s+aria-hidden="true"\s+\/>/,
	);
	assert.match(
		source,
		/<ChevronRight\s+className="text-\[color:var\(--color-text-secondary\)\]"\s+aria-hidden="true"\s+\/>/,
	);
	assert.match(source, /<PlusCircle size=\{14\} aria-hidden="true" \/>/);
	assert.doesNotMatch(source, /aria-label="Previous month"/);
	assert.doesNotMatch(source, /aria-label="Next month"/);
});

test("schedule calendar date cells are semantic buttons", () => {
	const source = readSource("components/tabs/ScheduleTab.js");

	assert.match(
		source,
		/<button\s+type="button"\s+key=\{dateStr\}\s+onClick=\{\(\) => openFormForDate\(dateStr\)\}/,
	);
	assert.match(source, /aria-label=\{`\$\{dateStr\} 일정 등록 열기`\}/);
	assert.match(source, /title=\{`\$\{dateStr\} 일정 등록 열기`\}/);
	assert.match(source, /textAlign: ["']left["']/);
	assert.doesNotMatch(
		source,
		/<div\s+key=\{dateStr\}\s+onClick=\{\(\) => openFormForDate\(dateStr\)\}/,
	);
});

test("upcoming schedule toggle identifies the target event", () => {
	const source = readSource("components/tabs/ScheduleTab.js");

	assert.match(
		source,
		/const eventCompletionLabel = isSavingEvent\s*\?\s*`\$\{event\.title\} 일정 완료 상태 변경 중`\s*:\s*`\$\{event\.title\} 일정 완료 상태 변경`;/,
	);
	assert.match(source, /aria-label=\{eventCompletionLabel\}/);
	assert.match(source, /title=\{eventCompletionLabel\}/);
	assert.match(source, /const eventCompletionText = isSavingEvent/);
	assert.match(source, /\{eventCompletionText\}/);
});

test("weather widget uses Korean product copy for unavailable state", () => {
	const source = readSource("components/widgets/widgets.js");
	const dashboardSource = readSource("components/DashboardClient.js");
	const hookSource = readSource("lib/hooks/useWeather.js");
	const utilsSource = readSource("lib/utils.js");

	assert.match(
		source,
		/toFiniteNumber[\s\S]*?from\s+["']@\/lib\/utils["']/i,
	);
	assert.match(source, /const temp = toFiniteNumber\(weather\.temp\);/);
	assert.match(source, /const humidity = toFiniteNumber\(weather\.humidity\);/);
	assert.match(
		source,
		/const apparentTemp = toFiniteNumber\(weather\.apparentTemp, temp\);/,
	);
	assert.match(
		source,
		/const windSpeed = toFiniteNumber\(weather\.windSpeed\);/,
	);
	assert.match(
		source,
		/const tempMax = toFiniteNumber\(weather\.tempMax, temp\);/,
	);
	assert.match(
		source,
		/const tempMin = toFiniteNumber\(weather\.tempMin, temp\);/,
	);
	assert.match(
		source,
		/const precipitation = toFiniteNumber\(weather\.precipitation\);/,
	);
	assert.match(source, /const thi\s*=\s*calcTHI\(\s*temp\s*,\s*humidity\s*\);?/);
	assert.match(source, /function normalizeWeatherForecast\(forecast\) \{/);
	assert.match(
		source,
		/return Array\.isArray\(forecast\)\s*\?\s*forecast\s*\.\s*filter\(\s*\(?day\)?\s*=>\s*day\s*&&\s*typeof\s+day\s*===\s*["']object["']\s*&&\s*!Array\.isArray\(day\)\s*,?\s*\)\s*:\s*\[\s*\];?/,
	);
	assert.match(source, /function normalizeWeatherWidgetOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === "object" && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export function WeatherWidget\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ weather \} = normalizeWeatherWidgetOptions\(options\);/,
	);
	assert.match(
		source,
		/const safeForecast = normalizeWeatherForecast\(weather\.forecast\);/,
	);
	assert.doesNotMatch(source, /export function WeatherWidget\(\{ weather \}\)/);

	assert.match(source, /날씨 확인 불가/);
	assert.match(source, /지금은 날씨 정보를 확인할 수 없습니다/);
	assert.doesNotMatch(source, /지금은 날씨 데이터를 확인할 수 없습니다/);
	assert.match(
		source,
		/className="weather-card animate-fadeInUp"\s+role="status"\s+aria-live="polite"\s+aria-atomic="true"/,
	);
	assert.match(source, /["']서울["']/);
	assert.match(dashboardSource, /["']서울["']/);
	assert.match(hookSource, /["']서울["']/);
	assert.doesNotMatch(source, /Weather Unavailable/);
	assert.doesNotMatch(source, /Weather data is temporarily unavailable/);
	assert.match(
		source,
		/<div\s+[\s\S]*?className="weather-icon-bg"[\s\S]*?aria-hidden="true"[\s\S]*?>\s*\{icon\}\s*<\/div>/,
	);
	assert.match(
		source,
		/<div\s+[\s\S]*?aria-hidden="true"[\s\S]*?style=\{\{\s*fontSize:\s*["']18px["']\s*,\s*marginBottom:\s*["']3px["']\s*,\s*lineHeight:\s*1\s*,?\s*\}\}\s*>\s*\{item\.i\}\s*<\/div>/,
	);
	assert.match(
		source,
		/<span aria-hidden="true">📍<\/span> \{weather\.locationName\}/,
	);
	assert.match(source, /<span aria-hidden="true">\{icon\}<\/span> \{desc\}/);
	assert.match(
		source,
		/<span aria-hidden="true">🐂<\/span> 온열지수: \{thiLevel\.label\}/,
	);
	assert.match(source, /<span aria-hidden="true">📅<\/span> 3일 예보/);
	assert.match(
		source,
		/formatForecastDateLabel\(\s*day\.date\s*,\s*\{\s*weekday\s*:\s*["']short["']\s*,\s*month\s*:\s*["']short["']\s*,\s*day\s*:\s*["']numeric["']\s*,?\s*\}\s*\)/,
	);
	assert.match(source, /safeForecast\.length > 0/);
	assert.match(
		source,
		/gridTemplateColumns:\s*`repeat\(\s*\$\{safeForecast\.length\}\s*,\s*1fr\s*\)`/,
	);
	assert.match(source, /safeForecast\.map\(\(day, idx\) => \{/);
	assert.match(
		source,
		/const weatherDescription = getWeatherDesc\(day\.weatherCode\);/,
	);
	assert.match(
		source,
		/<div\s+[\s\S]*?role="img"[\s\S]*?aria-label=\{weatherDescription\}[\s\S]*?title=\{weatherDescription\}[\s\S]*?style=\{\{\s*fontSize:\s*["']24px["']\s*,\s*marginBottom:\s*["']4px["']\s*,?\s*\}\}\s*>\s*\{getWeatherIcon\(day\.weatherCode\)\}\s*<\/div>/,
	);
	assert.match(
		source,
		/<span aria-hidden="true">🌧<\/span> 강수 \{day\.precipProb\}%/,
	);
	assert.match(source, /<span aria-hidden="true">🐄<\/span> 가축 기상 경고/);
	assert.match(
		source,
		/<span aria-hidden="true">\{a\.icon\}<\/span> \{a\.msg\}/,
	);
	assert.doesNotMatch(
		source,
		/Math\.round\(weather\.(?:temp|apparentTemp|tempMax|tempMin)\)/,
	);
	assert.doesNotMatch(
		source,
		/\$\{weather\.(?:humidity|windSpeed|precipitation)\}/,
	);
	assert.match(source, /Math\.round\(toFiniteNumber\(day\.tempMax\)\)/);
	assert.match(source, /Math\.round\(toFiniteNumber\(day\.tempMin\)\)/);
	assert.match(source, /getLivestockWeatherAlerts\(safeForecast\)/);
	assert.match(utilsSource, /환기 상태를 확인해 주세요/);
	assert.match(utilsSource, /급수량을 확보하고 송풍을 강화해 주세요/);
	assert.match(utilsSource, /즉시 냉방과 살수 조치를 진행해 주세요/);
	assert.match(utilsSource, /환기와 급수 상태를 강화해 주세요/);
	assert.match(utilsSource, /냉방과 살수 조치를 진행해 주세요/);
	assert.match(utilsSource, /보온 설비를 점검해 주세요/);
	assert.match(utilsSource, /보온 상태를 확인해 주세요/);
	assert.match(utilsSource, /축사 누수와 바닥 상태를 점검해 주세요/);
	assert.doesNotMatch(utilsSource, /환기 상태를 확인하세요/);
	assert.doesNotMatch(utilsSource, /급수량 확보와 송풍 강화가 필요한 수준입니다/);
	assert.doesNotMatch(utilsSource, /즉시 냉방과 살수 조치가 필요한 고위험 상태입니다/);
	assert.doesNotMatch(utilsSource, /환기와 급수 상태를 강화하세요/);
	assert.doesNotMatch(utilsSource, /냉방과 살수 조치가 필요합니다/);
	assert.doesNotMatch(utilsSource, /보온 설비 점검이 필요합니다/);
	assert.doesNotMatch(utilsSource, /보온 상태를 확인하세요/);
	assert.doesNotMatch(utilsSource, /축사 누수와 바닥 상태를 점검하세요/);
	assert.doesNotMatch(source, /weather\.forecast\.map/);
	assert.doesNotMatch(source, /weather\.forecast \|\| \[\]/);
	assert.match(dashboardSource, /WEATHER_STALE_MESSAGE/);
	assert.match(hookSource, /WEATHER_STALE_MESSAGE/);
	assert.match(dashboardSource, /WEATHER_TIMEOUT_MESSAGE/);
	assert.match(hookSource, /WEATHER_TIMEOUT_MESSAGE/);
	assert.doesNotMatch(
		dashboardSource,
		/Showing the last available weather snapshot/,
	);
	assert.doesNotMatch(
		hookSource,
		/Showing the last available weather snapshot/,
	);
	assert.doesNotMatch(dashboardSource, /Weather lookup timed out after 5000ms/);
	assert.doesNotMatch(hookSource, /Weather lookup timed out after 5000ms/);
	assert.doesNotMatch(source, /["']Seoul["']/);
	assert.doesNotMatch(
		source,
		/new Date\(day\.date\)\.toLocaleDateString\(["']ko-KR["']/,
	);
	assert.doesNotMatch(dashboardSource, /["']Seoul["']/);
	assert.doesNotMatch(hookSource, /locationName.*["']Seoul["']/);
});

test("weather geolocation lookup falls back safely when browser location APIs fail", () => {
	const dashboardSource = readSource("components/DashboardClient.js");
	const hookSource = readSource("lib/hooks/useWeather.js");

	assert.match(
		hookSource,
		/const FALLBACK_WEATHER_COORDS = \{ latitude: 35\.446, longitude: 127\.344 \};/,
	);
	assert.match(dashboardSource, /const fetchFallbackWeather = \(\) => \{/);
	assert.match(hookSource, /const fetchFallbackWeather = \(\) => \{/);
	assert.match(
		dashboardSource,
		/const fetchFallbackWeather = \(\) => \{\s+if \(cancelled\) \{\s+return;\s+\}\s+fetchWeather\(35\.446, 127\.344\);/,
	);
	assert.match(
		hookSource,
		/const fetchFallbackWeather = \(\) => \{\s+if \(cancelled\) \{\s+return;\s+\}\s+fetchWeather\(\s+FALLBACK_WEATHER_COORDS\.latitude,\s+FALLBACK_WEATHER_COORDS\.longitude,\s+\);/,
	);
	assert.match(dashboardSource, /const fetchWeatherFromCoords = \(latitudeValue, longitudeValue\) => \{/);
	assert.match(hookSource, /const fetchWeatherFromCoords = \(latitudeValue, longitudeValue\) => \{/);
	assert.match(
		dashboardSource,
		/const fetchWeatherFromCoords = \(latitudeValue, longitudeValue\) => \{\s+if \(cancelled\) \{\s+return false;\s+\}/,
	);
	assert.match(
		hookSource,
		/const fetchWeatherFromCoords = \(latitudeValue, longitudeValue\) => \{\s+if \(cancelled\) \{\s+return false;\s+\}/,
	);
	assert.match(
		dashboardSource,
		/const latitude = Number\(latitudeValue\);\s+const longitude = Number\(longitudeValue\);/,
	);
	assert.match(
		hookSource,
		/const latitude = Number\(latitudeValue\);\s+const longitude = Number\(longitudeValue\);/,
	);
	assert.match(
		dashboardSource,
		/const isValidWeatherCoordinate =\s+Number\.isFinite\(latitude\) &&\s+Number\.isFinite\(longitude\) &&\s+latitude >= -90 &&\s+latitude <= 90 &&\s+longitude >= -180 &&\s+longitude <= 180;/,
	);
	assert.match(
		hookSource,
		/const isValidWeatherCoordinate =\s+Number\.isFinite\(latitude\) &&\s+Number\.isFinite\(longitude\) &&\s+latitude >= -90 &&\s+latitude <= 90 &&\s+longitude >= -180 &&\s+longitude <= 180;/,
	);
	assert.match(
		dashboardSource,
		/if \(isValidWeatherCoordinate\) \{\s+fetchWeather\(latitude, longitude\);\s+return true;\s+\}\s+return false;/,
	);
	assert.match(
		hookSource,
		/if \(isValidWeatherCoordinate\) \{\s+fetchWeather\(latitude, longitude\);\s+return true;\s+\}\s+return false;/,
	);
	assert.match(dashboardSource, /const fetchWeatherFromPosition = \(position\) => \{/);
	assert.match(hookSource, /const fetchWeatherFromPosition = \(position\) => \{/);
	assert.match(
		dashboardSource,
		/const fetchWeatherFromPosition = \(position\) => \{\s+if \(cancelled\) \{\s+return;\s+\}/,
	);
	assert.match(
		hookSource,
		/const fetchWeatherFromPosition = \(position\) => \{\s+if \(cancelled\) \{\s+return;\s+\}/,
	);
	assert.match(
		dashboardSource,
		/fetchWeatherFromCoords\(position\?\.coords\?\.latitude, position\?\.coords\?\.longitude\)/,
	);
	assert.match(
		hookSource,
		/fetchWeatherFromCoords\(position\?\.coords\?\.latitude, position\?\.coords\?\.longitude\)/,
	);
	assert.match(
		dashboardSource,
		/if \(\s+farmSettings\.latitude !== null &&\s+farmSettings\.latitude !== undefined &&\s+farmSettings\.longitude !== null &&\s+farmSettings\.longitude !== undefined\s+\) \{\s+if \(!fetchWeatherFromCoords\(farmSettings\.latitude, farmSettings\.longitude\)\) \{\s+fetchFallbackWeather\(\);\s+\}/,
	);
	assert.match(
		hookSource,
		/if \(\s+farmSettings\?\.latitude !== null &&\s+farmSettings\?\.latitude !== undefined &&\s+farmSettings\?\.longitude !== null &&\s+farmSettings\?\.longitude !== undefined\s+\) \{\s+if \(!fetchWeatherFromCoords\(farmSettings\.latitude, farmSettings\.longitude\)\) \{\s+fetchFallbackWeather\(\);\s+\}/,
	);
	assert.match(
		dashboardSource,
		/typeof navigator !== "undefined" && "geolocation" in navigator/,
	);
	assert.match(
		hookSource,
		/typeof navigator !== "undefined" && "geolocation" in navigator/,
	);
	assert.match(
		dashboardSource,
		/try \{\s*navigator\.geolocation\.getCurrentPosition\(\s*fetchWeatherFromPosition,\s*fetchFallbackWeather,\s*\);[\s\S]*?\} catch \{\s*fetchFallbackWeather\(\);[\s\S]*?\}/,
	);
	assert.match(
		hookSource,
		/try \{\s*navigator\.geolocation\.getCurrentPosition\(\s*fetchWeatherFromPosition,\s*fetchFallbackWeather,\s*\);[\s\S]*?\} catch \{\s*fetchFallbackWeather\(\);[\s\S]*?\}/,
	);
	assert.doesNotMatch(dashboardSource, /else if \("geolocation" in navigator\)/);
	assert.doesNotMatch(hookSource, /\(\) => fetchWeather\(35\.446, 127\.344\)/);
	assert.doesNotMatch(dashboardSource, /if \(farmSettings\.latitude && farmSettings\.longitude\)/);
	assert.doesNotMatch(hookSource, /if \(farmSettings\?\.latitude && farmSettings\?\.longitude\)/);
	assert.doesNotMatch(
		dashboardSource,
		/fetchWeather\(position\.coords\.latitude, position\.coords\.longitude\)/,
	);
	assert.doesNotMatch(
		hookSource,
		/fetchWeather\(position\.coords\.latitude, position\.coords\.longitude\)/,
	);
	assert.doesNotMatch(
		dashboardSource,
		/fetchWeather\(farmSettings\.latitude, farmSettings\.longitude\);/,
	);
	assert.doesNotMatch(
		hookSource,
		/fetchWeather\(farmSettings\.latitude, farmSettings\.longitude\);/,
	);
	assert.doesNotMatch(
		dashboardSource,
		/if \(Number\.isFinite\(latitude\) && Number\.isFinite\(longitude\)\) \{\s+fetchWeather\(latitude, longitude\);/,
	);
	assert.doesNotMatch(
		hookSource,
		/if \(Number\.isFinite\(latitude\) && Number\.isFinite\(longitude\)\) \{\s+fetchWeather\(latitude, longitude\);/,
	);
});

test("tab navigation buttons expose Korean action labels and selected state", () => {
	const source = readSource("components/widgets/widgets.js");

	assert.match(source, /function normalizeTabBarOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === "object" && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export function TabBar\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ activeTab, onTabChange \} = normalizeTabBarOptions\(options\);/,
	);
	assert.match(
		source,
		/const handleTabChange =\s*typeof onTabChange === "function" \? onTabChange : \(\) => \{\};/,
	);

	assert.match(source, /<nav className="tab-bar" aria-label="대시보드 메뉴">/);
	assert.match(
		source,
		/const tabActionLabel = `\$\{t\.label\} 탭 열기\$\{isActive \? ", 현재 선택됨" : ""\}`;/,
	);
	assert.match(source, /onClick=\{\(\) => handleTabChange\(t\.id\)\}/);
	assert.match(source, /aria-current=\{isActive \? "page" : undefined\}/);
	assert.match(source, /aria-label=\{tabActionLabel\}/);
	assert.match(source, /title=\{tabActionLabel\}/);
	assert.doesNotMatch(source, /export function TabBar\(\{ activeTab, onTabChange \}\)/);
	assert.doesNotMatch(source, /onClick=\{\(\) => onTabChange\(t\.id\)\}/);
});

test("sales tab missing cattle fallback copy stays Korean", () => {
	const source = readSource("components/tabs/SalesTab.js");

	assert.match(source, /개체명 미등록/);
	assert.match(source, /이력번호 미등록/);
	assert.doesNotMatch(source, /Unknown/);
	assert.doesNotMatch(source, /000-0000-0000/);
});

test("sales tab normalizes numeric inputs before sales and profit aggregation", () => {
	const source = readSource("components/tabs/SalesTab.js");

	assert.match(source, /출하 및 판매 분석/);
	assert.match(source, /총 누적 판매액/);
	assert.match(source, /판매액, 등급, 수익 분석 차트/);
	assert.doesNotMatch(source, /출하 및 매출 분석/);
	assert.doesNotMatch(source, /총 누적 매출/);
	assert.doesNotMatch(source, /매출, 등급, 수익 분석 차트/);
	assert.match(source, /연결된 비용 기록 없음/);
	assert.match(source, /비용 기록 없어 수익 추정 불가/);
	assert.doesNotMatch(source, /관련 비용 없음/);
	assert.doesNotMatch(source, /비용 미등록/);
	assert.doesNotMatch(source, />수익 추정 불가</);
	assert.match(
		source,
		/import \{ formatMoney, toFiniteNumber \} from ["']@\/lib\/utils["'];/,
	);
	assert.match(source, /const salePrice = toFiniteNumber\(record\.price\);/);
	assert.match(
		source,
		/const purchaseCost = toFiniteNumber\(cow\.purchasePrice\);/,
	);
	assert.match(source, /sum \+ toFiniteNumber\(expense\.amount\)/);
	assert.match(source, /price: salePrice,/);
	assert.match(
		source,
		/profit: hasExpenseData \? salePrice - totalCost : null,/,
	);
	assert.match(source, /sum \+ toFiniteNumber\(record\.price\)/);
	assert.match(source, /sum \+ toFiniteNumber\(record\.profit\)/);
	assert.doesNotMatch(
		source,
		/const purchaseCost = cow\.purchasePrice \|\| 0;/,
	);
	assert.doesNotMatch(source, /sum \+ expense\.amount/);
	assert.doesNotMatch(
		source,
		/profit: hasExpenseData \? record\.price - totalCost : null,/,
	);
});

test("sales profit chart exposes an accessible chart summary", () => {
	const source = readSource("components/tabs/SalesTab.js");

	assert.match(
		source,
		/const salesProfitChartLabel =\s*["']최근 5건 수익 분석 차트\. 판매금액과 수익을 출하 개체별로 비교합니다\.["'];?/,
	);
	assert.match(
		source,
		/role="img"\s+aria-label=\{salesProfitChartLabel\}\s+title=\{salesProfitChartLabel\}[\s\S]*?<ResponsiveContainer width="100%" height="100%">/,
	);
});

test("sales tab normalizes collection payloads before rendering and aggregation", () => {
	const source = readSource("components/tabs/SalesTab.js");

	assert.match(source, /function normalizeSalesTabOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export default function SalesTab\(options = \{\}\) \{/);
	assert.match(source, /normalizeSalesTabOptions\(options\);/);
	assert.match(
		source,
		/const handleCreateSale =\s+typeof onCreateSale === ["']function["'] \? onCreateSale : async \(\) => false;/,
	);
	assert.match(source, /function normalizeSalesItems\(items\) \{/);
	assert.match(
		source,
		/const safeSaleRecords = useMemo\(\s*\(\s*\)\s*=>\s*normalizeSalesItems\(\s*saleRecords\s*\),\s*\[\s*saleRecords\s*\],?\s*\);?/,
	);
	assert.match(
		source,
		/const safeCattleList = useMemo\(\s*\(\s*\)\s*=>\s*normalizeSalesItems\(\s*cattleList\s*\),\s*\[\s*cattleList\s*\],?\s*\);?/,
	);
	assert.match(
		source,
		/const safeExpenseRecords = useMemo\(\s*\(\s*\)\s*=>\s*normalizeSalesItems\(\s*expenseRecords\s*\),\s*\[\s*expenseRecords\s*\],?\s*\);?/,
	);
	assert.match(source, /\[\.\.\.safeSaleRecords\]/);
	assert.match(
		source,
		/safeCattleList\s*\.\s*find\(\s*\(?item\)?\s*=>\s*item\s*\.\s*id\s*===\s*record\s*\.\s*cattleId\s*,?\s*\)/,
	);
	assert.match(
		source,
		/safeExpenseRecords\s*\.\s*filter\(\s*\(?expense\)?\s*=>\s*expense\s*\.\s*cattleId\s*===\s*record\s*\.\s*cattleId\s*,?\s*\)/,
	);
	assert.match(source, /safeCattleList\s*\.\s*map\(\s*\(?cow\)?\s*=>\s*\(/);
	assert.match(source, /disabled=\{!safeCattleList\.length \|\| isSaving\}/);
	assert.match(source, /actionLabel=\{\s+safeCattleList\.length/);
	assert.match(source, /"판매 기록 등록"/);
	assert.match(source, /"개체를 먼저 등록해 주세요"/);
	assert.doesNotMatch(source, /"개체 등록 필요"/);
	assert.doesNotMatch(source, /"매출 기록"/);
	assert.doesNotMatch(source, /export default function SalesTab\(\{\s+saleRecords,/);
	assert.doesNotMatch(source, /\[\.\.\.saleRecords\]/);
	assert.doesNotMatch(
		source,
		/expenseRecords\.filter\(\(expense\) => expense\.cattleId === record\.cattleId\)/,
	);
	assert.doesNotMatch(source, /cattleList\?\.map/);
	assert.doesNotMatch(source, /cattleList\?\.length/);
});

test("dashboard fallback average weight normalizes cattle weights", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(
		source,
		/import \{ formatMoney, toFiniteNumber \} from ["']@\/lib\/utils["'];/,
	);
	assert.match(source, /sum \+ toFiniteNumber\(cow\.weight\)/);
	assert.doesNotMatch(source, /sum \+ \(cow\.weight \|\| 0\)/);
});

test("dashboard client normalizes malformed top-level props before setup", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /function normalizeDashboardClientOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export default function DashboardClient\(options = \{\}\) \{/);
	assert.match(source, /\} = normalizeDashboardClientOptions\(options\);/);
	assert.doesNotMatch(
		source,
		/export default function DashboardClient\(\{\s+initialCattlePage,/,
	);
});

test("dashboard normalizes malformed building payloads before home rendering", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /function normalizeDashboardBuildings\(buildings\) \{/);
	assert.match(source, /if \(!Array\.isArray\(buildings\)\) return \[\]/);
	assert.match(
		source,
		/\.filter\(\s*\(\s*building\s*\)\s*=>[\s\S]*?building\s*&&[\s\S]*?typeof\s*building\s*===\s*['"]object['"][\s\S]*?!Array\.isArray\(building\)[\s\S]*?building\.id\s*!=\s*null,?\s*\)/,
	);
	assert.match(
		source,
		/useState\(\s*\(\s*\)\s*=>\s*normalizeDashboardBuildings\(\s*initialBuildings\s*\),?\s*\)/,
	);
	assert.match(
		source,
		/const safeBuildings = useMemo\(\s*\(\s*\)\s*=>\s*normalizeDashboardBuildings\(buildings\),\s*\[buildings\],?\s*\);/,
	);
	assert.match(source, /buildings: safeBuildings/);
	assert.match(source, /\{safeBuildings\.length === 0 \? \(/);
	assert.match(source, /\{safeBuildings\.map\(\(building\) => \{/);
	assert.match(source, /<FeedTab[\s\S]*?buildings=\{safeBuildings\}/);
	assert.match(source, /<SettingsTab[\s\S]*?buildings=\{safeBuildings\}/);
	assert.doesNotMatch(source, /useState\(initialBuildings\)/);
	assert.doesNotMatch(source, /buildings\.map\(\(building/);
	assert.doesNotMatch(source, /buildings\.find\(\(building/);
	assert.doesNotMatch(source, /buildings\.length === 0/);
});

test("dashboard normalizes cattle collection before home rendering and full export", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /function normalizeDashboardItems\(items\) \{/);
	assert.match(
		source,
		/items\.filter\([\s\S]*?\(item\) =>[\s\S]*?item &&[\s\S]*?typeof item === ["']object["'][\s\S]*?!Array\.isArray\(item\)[\s\S]*?item\.id != null/,
	);
	assert.match(
		source,
		/function normalizeDashboardCattleList\(cattleItems\) \{/,
	);
	assert.match(
		source,
		/normalizeDashboardItems\(cattleItems\)\s*\.\s*map\(\s*\(?cow\)?\s*=>\s*\(\{/,
	);
	assert.match(
		source,
		/name:\s*typeof cow\.name === ["']string["']\s*&&\s*cow\.name\.trim\(\)\.length > 0/,
	);
	assert.match(
		source,
		/items\.push\(\.\.\.normalizeDashboardItems\(json\.data\.items\)\);/,
	);
	assert.match(
		source,
		/const normalizedItems = normalizeDashboardCattleList\(items\);/,
	);
	assert.match(source, /setAllCattleRegistry\(normalizedItems\);/);
	assert.match(source, /return normalizedItems;/);
	assert.match(
		source,
		/const cattleList = useMemo\(\s+\(\) => normalizeDashboardCattleList\(allCattleRegistry \?\? pagedCattleItems\),\s+\[allCattleRegistry, pagedCattleItems\],\s+\);/,
	);
	assert.doesNotMatch(
		source,
		/const cattleList = allCattleRegistry \?\? pagedCattleItems;/,
	);
	assert.doesNotMatch(
		source,
		/items\.push\(\.\.\.\(json\.data\.items \|\| \[\]\)\);/,
	);
});

test("dashboard normalizes notification payloads before home rendering", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(
		source,
		/function normalizeDashboardNotifications\(notifications\) \{/,
	);
	assert.match(source, /Array\.isArray\(notifications\)/);
	assert.match(
		source,
		/\.filter\(\s*\(?notification\)?\s*=>[\s\S]*?notification\s*&&[\s\S]*?typeof\s+notification\s*===\s*["']object["'][\s\S]*?!Array\.isArray\(notification\)\s*,?\s*\)/,
	);
	assert.match(
		source,
		/useState\(\s*\(\s*\)\s*=>\s*normalizeDashboardNotifications\(\s*initialNotifications\s*\),?\s*\)/,
	);
	assert.match(
		source,
		/setNotifications\(normalizeDashboardNotifications\(nextNotifications\)\)/,
	);
	assert.match(
		source,
		/\{notifications\s*\.\s*some\(\s*\(?notification\)?\s*=>\s*notification\s*\.\s*level\s*===\s*["']critical["']\s*,?\s*\)\s*&&\s*\(/,
	);
	assert.match(
		source,
		/<NotificationModal\s+id=\{NOTIFICATION_MODAL_ID\}\s+notifications=\{notifications\}/,
	);
	assert.match(source, /<NotificationWidget\s+notifications=\{notifications\}/);
	assert.match(source, /<EstrusAlertBanner\s+notifications=\{notifications\}/);
	assert.match(source, /<CalvingAlertBanner\s+notifications=\{notifications\}/);
	assert.doesNotMatch(source, /useState\(initialNotifications \|\| \[\]\)/);
});

test("dashboard fallback monthly sales count filters by current year and valid sale dates", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /function toValidCalendarDate\(value\) \{/);
	assert.match(source, /const dateKey = value\.trim\(\)\.slice\(0, 10\);/);
	assert.match(
		source,
		/strictDate\.toISOString\(\)\.slice\(0, 10\) !== dateKey/,
	);
	assert.match(source, /const today = new Date\(\);/);
	assert.match(source, /const currentMonth = today\.getMonth\(\);/);
	assert.match(source, /const currentYear = today\.getFullYear\(\);/);
	assert.match(
		source,
		/const saleDate = toValidCalendarDate\(record\.saleDate\);/,
	);
	assert.match(source, /saleDate\.getMonth\(\) === currentMonth/);
	assert.match(source, /saleDate\.getFullYear\(\) === currentYear/);
	assert.doesNotMatch(source, /const saleDate = new Date\(record\.saleDate\);/);
	assert.doesNotMatch(
		source,
		/return saleRecords\.filter\(\(record\) => new Date\(record\.saleDate\)\.getMonth\(\) === currentMonth\)\.length;/,
	);
});

test("sales form fields expose explicit labels and invalid state", () => {
	const source = readSource("components/tabs/SalesTab.js");

	assert.match(
		source,
		/<PremiumLabel htmlFor="sale-date">\s*출하일자\s*<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="sale-date"[\s\S]*?aria-invalid=\{Boolean\(errors\.saleDate\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="sale-price">\s*판매 가격 \(원\)\s*<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="sale-price"[\s\S]*?aria-invalid=\{Boolean\(errors\.price\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="sale-cattle">\s*출하 개체\s*<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="sale-cattle"[\s\S]*?aria-invalid=\{Boolean\(errors\.cattleId\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="sale-grade">\s*등급\s*<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="sale-grade"[\s\S]*?aria-invalid=\{Boolean\(errors\.grade\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="sale-purchaser">\s*구매처\s*<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="sale-purchaser"[\s\S]*?aria-invalid=\{Boolean\(errors\.purchaser\)\}/,
	);
});

test("sales form validation messages are announced by their controls", () => {
	const source = readSource("components/tabs/SalesTab.js");
	const fields = [
		["saleDate", "sale-date-error"],
		["price", "sale-price-error"],
		["cattleId", "sale-cattle-error"],
		["grade", "sale-grade-error"],
		["purchaser", "sale-purchaser-error"],
	];

	for (const [errorPath, errorId] of fields) {
		assert.match(
			source,
			new RegExp(
				`aria-describedby=\\{\\s*errors\\.${errorPath}\\s*\\?\\s*"${errorId}"\\s*:\\s*undefined\\s*\\}`,
			),
		);
		assert.match(
			source,
			new RegExp(`<div\\s+[\\s\\S]*?id="${errorId}"[\\s\\S]*?role="alert"`),
		);
	}
});

test("sales form waits for async saves before re-enabling actions", () => {
	const source = readSource("components/tabs/SalesTab.js");

	assert.match(source, /const \[isSaving, setIsSaving\] = useState\(false\)/);
	assert.match(source, /const isMountedRef = useRef\(false\)/);
	assert.match(source, /const saveInFlightRef = useRef\(false\)/);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+isMountedRef\.current = true;[\s\S]*?return \(\) => \{\s+isMountedRef\.current = false;\s+saveInFlightRef\.current = false;/,
	);
	assert.match(
		source,
		/if \(saveInFlightRef\.current \|\| isSaving\) \{\s+return;\s+\}/,
	);
	assert.match(source, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
	assert.match(source, /saveInFlightRef\.current = true;/);
	assert.match(source, /setIsSaving\(true\);/);
	assert.match(source, /await handleCreateSale\(values\)/);
	assert.doesNotMatch(source, /await onCreateSale\(values\)/);
	assert.match(
		source,
		/if \(!saved \|\| !isMountedRef\.current\) \{\s+return;\s+\}/,
	);
	assert.match(
		source,
		/finally \{\s+saveInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setIsSaving\(false\);/,
	);
	assert.doesNotMatch(
		source,
		/finally \{\s+saveInFlightRef\.current = false;\s+setIsSaving\(false\);/,
	);
	assert.match(source, /const addFormButtonLabel = isSaving/);
	assert.match(source, /판매 기록 저장 중에는 등록 창을 닫을 수 없습니다/);
	assert.match(source, /판매 기록 등록 취소/);
	assert.match(source, /판매 기록 등록 창 열기/);
	assert.match(source, /새 판매 기록 등록/);
	assert.doesNotMatch(source, /새 매출 기록 등록/);
	assert.match(source, /const addFormButtonText = isSaving/);
	assert.match(source, /판매 기록 저장 중\.\.\./);
	assert.match(source, /판매 기록 등록 취소/);
	assert.match(source, /: "판매 기록 등록";/);
	assert.doesNotMatch(
		source,
		/const addFormButtonText = isSaving[\s\S]*?\? "판매 기록 저장 중\.\.\."[\s\S]*?: isAdding[\s\S]*?\? "취소"[\s\S]*?: "\+매출 등록";/,
	);
	assert.doesNotMatch(
		source,
		/const addFormButtonText = isSaving[\s\S]*?: isAdding[\s\S]*?\? "취소"/,
	);
	assert.doesNotMatch(source, /"\+매출 등록"/);
	assert.match(
		source,
		/onClick=\{toggleAddForm\}\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}\s+aria-label=\{addFormButtonLabel\}\s+title=\{addFormButtonLabel\}/,
	);
	assert.match(source, /\{addFormButtonText\}/);
	assert.match(
		source,
		/const submitButtonLabel = isSaving\s*\?\s*["']판매 기록 등록 중["']\s*:\s*["']판매 기록 등록["'];?/,
	);
	assert.match(
		source,
		/const submitButtonText = isSaving\s*\?\s*["']판매 기록 등록 중\.\.\.["']\s*:\s*["']판매 기록 등록["'];?/,
	);
	assert.doesNotMatch(source, /판매 기록 등록하기/);
	assert.match(
		source,
		/disabled=\{!safeCattleList\.length \|\| isSaving\}\s+aria-busy=\{isSaving\}/,
	);
	assert.match(
		source,
		/aria-label=\{submitButtonLabel\}\s+title=\{submitButtonLabel\}/,
	);
});

test("inventory form fields expose explicit labels and invalid state", () => {
	const source = readSource("components/tabs/InventoryTab.js");

	assert.match(
		source,
		/<PremiumLabel htmlFor="inventory-name">자재명<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="inventory-name"[\s\S]*?aria-invalid=\{Boolean\(errors\.name\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="inventory-category">\s*분류\s*<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="inventory-category"[\s\S]*?aria-invalid=\{Boolean\(errors\.category\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="inventory-quantity">\s*수량\s*<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="inventory-quantity"[\s\S]*?aria-invalid=\{Boolean\(errors\.quantity\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="inventory-unit">\s*단위\s*<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="inventory-unit"[\s\S]*?aria-invalid=\{Boolean\(errors\.unit\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="inventory-threshold">\s*경고 기준값\s*<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="inventory-threshold"[\s\S]*?aria-invalid=\{Boolean\(errors\.threshold\)\}/,
	);
});

test("inventory form validation messages are announced by their controls", () => {
	const source = readSource("components/tabs/InventoryTab.js");
	const fields = [
		["name", "inventory-name-error"],
		["category", "inventory-category-error"],
		["quantity", "inventory-quantity-error"],
		["unit", "inventory-unit-error"],
		["threshold", "inventory-threshold-error"],
	];

	for (const [errorPath, errorId] of fields) {
		assert.match(
			source,
			new RegExp(
				`aria-describedby=\\{\\s*errors\\.${errorPath}\\s*\\?\\s*"${errorId}"\\s*:\\s*undefined\\s*\\}`,
			),
		);
		assert.match(
			source,
			new RegExp(`<div\\s+[\\s\\S]*?id="${errorId}"[\\s\\S]*?role="alert"`),
		);
	}
});

test("inventory form waits for async saves before re-enabling actions", () => {
	const source = readSource("components/tabs/InventoryTab.js");

	assert.match(source, /const \[isSaving, setIsSaving\] = useState\(false\)/);
	assert.match(source, /const isMountedRef = useRef\(false\)/);
	assert.match(source, /const saveInFlightRef = useRef\(false\)/);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+isMountedRef\.current = true;[\s\S]*?return \(\) => \{\s+isMountedRef\.current = false;\s+saveInFlightRef\.current = false;\s+quantityInFlightRef\.current = false;/,
	);
	assert.match(
		source,
		/if \(saveInFlightRef\.current \|\| isSaving\) \{\s+return;\s+\}/,
	);
	assert.match(source, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
	assert.match(source, /saveInFlightRef\.current = true;/);
	assert.match(source, /setIsSaving\(true\);/);
	assert.match(source, /await handleAddItem\(values\)/);
	assert.match(
		source,
		/if \(!saved \|\| !isMountedRef\.current\) \{\s+return;\s+\}/,
	);
	assert.match(
		source,
		/finally \{\s+saveInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setIsSaving\(false\);/,
	);
	assert.doesNotMatch(
		source,
		/finally \{\s+saveInFlightRef\.current = false;\s+setIsSaving\(false\);/,
	);
	assert.match(source, /onClick=\{toggleAddForm\}\s+disabled=\{isSaving\}/);
	assert.match(
		source,
		/const submitButtonLabel = isSaving\s*\?\s*["']재고 등록 중["']\s*:\s*["']재고 등록["'];?/,
	);
	assert.doesNotMatch(source, /재고 등록하기/);
	assert.match(
		source,
		/type="submit"\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}\s+aria-label=\{submitButtonLabel\}\s+title=\{submitButtonLabel\}/,
	);
});

test("inventory inline quantity editor exposes item-specific input label", () => {
	const source = readSource("components/tabs/InventoryTab.js");

	assert.match(source, /aria-label=\{`\$\{item\.name\} 재고 수량 입력`\}/);
	assert.match(source, /title=\{`\$\{item\.name\} 재고 수량 입력`\}/);
	assert.match(source, /const itemQuantitySaveLabel = isQuantitySaving/);
	assert.match(source, /재고 수량 저장 중/);
	assert.match(source, /aria-label=\{itemQuantitySaveLabel\}/);
	assert.match(source, /title=\{itemQuantitySaveLabel\}/);
	assert.match(source, /aria-label=\{`\$\{item\.name\} 재고 수량 수정`\}/);
	assert.match(source, /title=\{`\$\{item\.name\} 재고 수량 수정`\}/);
});

test("inventory inline quantity updates wait for async saves before re-enabling controls", () => {
	const source = readSource("components/tabs/InventoryTab.js");

	assert.match(
		source,
		/const PLAIN_NONNEGATIVE_NUMBER_INPUT_PATTERN = \/\^\(\?:\\d\+\|\\d\+\\\.\\d\+\|\\\.\\d\+\)\$\/;/,
	);
	assert.match(source, /function parseInlineQuantityInput\(value\)/);
	assert.match(
		source,
		/const parsedQuantity = parseInlineQuantityInput\(editQty\);/,
	);
	assert.match(source, /if \(!Number\.isFinite\(parsedQuantity\)\) \{/);
	assert.match(
		source,
		/const \[savingQuantityId, setSavingQuantityId\] = useState\(null\)/,
	);
	assert.match(source, /const quantityInFlightRef = useRef\(false\)/);
	assert.match(
		source,
		/if \(quantityInFlightRef\.current \|\| savingQuantityId\) \{\s+return;\s+\}/,
	);
	assert.match(source, /quantityInFlightRef\.current = true;/);
	assert.match(source, /setSavingQuantityId\(id\);/);
	assert.match(source, /await handleUpdateQuantity\(id, parsedQuantity\);/);
	assert.match(
		source,
		/if \(!saved \|\| !isMountedRef\.current\) \{\s+return;\s+\}/,
	);
	assert.match(
		source,
		/finally \{\s+quantityInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setSavingQuantityId\(null\);/,
	);
	assert.doesNotMatch(
		source,
		/finally \{\s+quantityInFlightRef\.current = false;\s+setSavingQuantityId\(null\);/,
	);
	assert.match(source, /const isQuantitySaving = savingQuantityId === item\.id;/);
	assert.match(source, /disabled=\{isQuantitySaving\}/);
	assert.match(source, /aria-busy=\{isQuantitySaving\}/);
	assert.doesNotMatch(source, /Number\(editQty\) < 0/);
});

test("dashboard full-list loading placeholders expose polite busy status", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(
		source,
		/onClick=\{\(\) => \{\s+void ensureAllCattleLoaded\(\{ silent: false \}\)\.catch\(\(\) => \{\}\);\s+\}\}[\s\S]*?aria-label="전체 개체 목록 다시 불러오기"[\s\S]*?title="전체 개체 목록 다시 불러오기"/,
	);
	assert.match(
		source,
		/onClick=\{\(\) => \{\s+void ensureAllSalesLoaded\(\{ silent: false \}\)\.catch\(\(\) => \{\}\);\s+\}\}[\s\S]*?aria-label="판매 기록 다시 불러오기"[\s\S]*?title="판매 기록 다시 불러오기"/,
	);
	assert.match(source, /전체 판매 기록을 불러오지 못했습니다/);
	assert.match(source, /판매 기록을 불러오는 중입니다/);
	assert.match(source, /판매 기록을 준비 중입니다/);
	assert.doesNotMatch(source, /매출 기록 다시 불러오기/);
	assert.match(
		source,
		/needsCompleteCattleData && !Array\.isArray\(allCattleRegistry\)[\s\S]*?<CardContent[\s\S]*?role="status"[\s\S]*?aria-live="polite"[\s\S]*?aria-atomic="true"[\s\S]*?aria-busy=\{isAllCattleLoading\}/,
	);
	assert.match(
		source,
		/activeTab === "analysis" && !Array\.isArray\(allSalesLedger\)[\s\S]*?<CardContent[\s\S]*?role="status"[\s\S]*?aria-live="polite"[\s\S]*?aria-atomic="true"[\s\S]*?aria-busy=\{isAllSalesLoading\}/,
	);
});

test("dashboard API fallback messages stay operator-facing Korean", () => {
	const cattleRoute = readSource("app/api/dashboard/cattle/route.js");
	const salesRoute = readSource("app/api/dashboard/sales/route.js");
	const summaryRoute = readSource("app/api/dashboard/summary/route.js");
	const listQueries = readSource("lib/dashboard/list-queries.js");

	assert.match(cattleRoute, /개체 목록을 불러오지 못했습니다/);
	assert.match(cattleRoute, /개체 목록 조회 조건을 확인해 주세요/);
	assert.match(salesRoute, /판매 기록을 불러오지 못했습니다/);
	assert.match(salesRoute, /판매 기록 조회 조건을 확인해 주세요/);
	assert.match(summaryRoute, /대시보드 요약을 불러오지 못했습니다/);
	assert.match(listQueries, /목록 개수는 1 이상 숫자로 입력해 주세요/);
	assert.match(cattleRoute, /AUTHENTICATION_REQUIRED_MESSAGE/);
	assert.match(salesRoute, /AUTHENTICATION_REQUIRED_MESSAGE/);
	assert.match(summaryRoute, /AUTHENTICATION_REQUIRED_MESSAGE/);
	assert.match(listQueries, /const normalized = String\(value\)\.trim\(\);/);
	assert.match(listQueries, /Number\.parseInt\(normalized, 10\)/);
	assert.match(listQueries, /목록 위치 정보가 올바르지 않습니다/);
	assert.match(listQueries, /시작일은 종료일보다 늦을 수 없습니다/);
	assert.match(listQueries, /\/\^\\d\{4\}-\\d\{2\}-\\d\{2\}\$\/\.test/);
	assert.match(listQueries, /toDateKey\(parsed\) !== normalized/);
	assert.doesNotMatch(listQueries, /Number\.parseInt\(String\(value\), 10\)/);
	assert.doesNotMatch(cattleRoute, /message: error\.message \|\|/);
	assert.doesNotMatch(salesRoute, /message: error\.message \|\|/);
	assert.doesNotMatch(summaryRoute, /message: error\.message \|\|/);
	assert.doesNotMatch(cattleRoute, /message: error\.message/);
	assert.doesNotMatch(salesRoute, /message: error\.message/);
	assert.doesNotMatch(
		cattleRoute,
		/message: error\.message \}, \{ status: 401/,
	);
	assert.doesNotMatch(salesRoute, /message: error\.message \}, \{ status: 401/);
	assert.doesNotMatch(
		summaryRoute,
		/message: error\.message \}, \{ status: 401/,
	);
	assert.doesNotMatch(cattleRoute, /Failed to load cattle list/);
	assert.doesNotMatch(salesRoute, /Failed to load sales list/);
	assert.doesNotMatch(summaryRoute, /Failed to load dashboard summary/);
	assert.doesNotMatch(
		listQueries,
		/must be a positive integer|cursor.*malformed|valid YYYY-MM-DD|before or equal/,
	);
});
