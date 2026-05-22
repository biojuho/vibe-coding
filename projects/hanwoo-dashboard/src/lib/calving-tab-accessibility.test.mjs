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

test("calving tab form fields expose explicit labels and invalid states", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	assert.match(
		source,
		/<span className="section-header-icon" aria-hidden="true">🐮<\/span>/,
	);
	assert.match(source, /<label htmlFor="calving-date"/);
	assert.match(source, /id="calving-date"\s+type="date"/);
	assert.match(source, /aria-invalid=\{Boolean\(errors\.calvingDate\)\}/);
	assert.match(source, /<label htmlFor="calf-gender"/);
	assert.match(source, /id="calf-gender"\s+\{\.\.\.register\('calfGender'\)\}/);
	assert.match(source, /aria-invalid=\{Boolean\(errors\.calfGender\)\}/);
});

test("calving tab validation messages are announced with their controls", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	assert.match(
		source,
		/aria-describedby=\{\s*errors\.calvingDate\s*\?\s*["']calving-date-error["']\s*:\s*undefined\s*\}/,
	);
	assert.match(source, /<div id="calving-date-error" role="alert"/);
	assert.match(
		source,
		/aria-describedby=\{\s*errors\.calfGender\s*\?\s*["']calf-gender-error["']\s*:\s*undefined\s*\}/,
	);
	assert.match(source, /<div id="calf-gender-error" role="alert"/);
	assert.match(
		source,
		/aria-describedby=\{\s*errors\.calfTagNumber\s*\?\s*["']calf-tag-number-error["']\s*:\s*undefined\s*\}/,
	);
	assert.match(source, /<div id="calf-tag-number-error" role="alert"/);
});

test("calving form waits for async saves before re-enabling actions", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	assert.match(source, /const saveInFlightRef = useRef\(false\)/);
	assert.match(source, /const \[isSaving, setIsSaving\] = useState\(false\)/);
	assert.match(source, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
	assert.match(source, /saveInFlightRef\.current = true;/);
	assert.match(source, /setIsSaving\(true\);/);
	assert.match(source, /await onRecordCalving\(\{/);
	assert.match(
		source,
		/finally \{\s*saveInFlightRef\.current = false;\s+setIsSaving\(false\);/,
	);
	assert.match(
		source,
		/const submitButtonLabel = isSaving\s*\?\s*['"]분만 기록 저장 중['"]\s*:\s*['"]분만 완료 및 송아지 등록['"];/,
	);
	assert.match(
		source,
		/type="submit"\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}\s+aria-label=\{submitButtonLabel\}\s+title=\{submitButtonLabel\}/,
	);
	assert.match(
		source,
		/type="button"\s+onClick=\{closeCalvingForm\}\s+disabled=\{isSaving\}/,
	);
	assert.match(source, /aria-busy=\{isSaving\}/);
	assert.match(
		source,
		/aria-label=\{isSaving\s*\?\s*['"]분만 기록 저장 중에는 취소할 수 없습니다['"]\s*:\s*['"]분만 기록 취소['"]\}/,
	);
	assert.match(
		source,
		/title=\{isSaving\s*\?\s*['"]분만 기록 저장 중에는 취소할 수 없습니다['"]\s*:\s*['"]분만 기록 취소['"]\}/,
	);
});

test("calving tab keeps malformed pregnancy dates stable in the list", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	assert.match(source, /function getPregnancyDateTime\(value\) \{/);
	assert.match(
		source,
		/return Number\.isNaN\(date\.getTime\(\)\) \? Number\.POSITIVE_INFINITY : date\.getTime\(\);/,
	);
	assert.match(
		source,
		/sort\(\(first, second\) => getPregnancyDateTime\(first\.pregnancyDate\) - getPregnancyDateTime\(second\.pregnancyDate\)\)/,
	);
	assert.doesNotMatch(
		source,
		/new Date\(first\.pregnancyDate\) - new Date\(second\.pregnancyDate\)/,
	);
});

test("calving tab normalizes malformed cattle and building payloads before rendering", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	assert.match(source, /import \{\s*useMemo,\s*useRef,\s*useState\s*\} from ['"]react['"];/);
	assert.match(source, /function normalizeCalvingCattle\(cattle\) \{/);
	assert.match(source, /return Array\.isArray\(cattle\)/);
	assert.match(source, /row\s*&&\s*typeof\s*row\s*===\s*['"]object['"]\s*&&\s*row\.id\s*!=\s*null/);
	assert.match(source, /function normalizeCalvingBuildings\(buildings\) \{/);
	assert.match(source, /return Array\.isArray\(buildings\)/);
	assert.match(source, /building\s*&&\s*typeof\s*building\s*===\s*['"]object['"]/);
	assert.match(
		source,
		/const safeCattle = useMemo\(\s*\(\s*\)\s*=>\s*normalizeCalvingCattle\(cattle\),\s*\[cattle\],?\s*\);/,
	);
	assert.match(
		source,
		/const safeBuildings = useMemo\(\s*\(\s*\)\s*=>\s*normalizeCalvingBuildings\(buildings\),\s*\[buildings\],?\s*\);/,
	);
	assert.match(source, /const pregnantCows = useMemo\(/);
	assert.match(
		source,
		/safeCattle\s+\.filter\(\s*\(\s*row\s*\)\s*=>\s*row\.status\s*===\s*['"]임신우['"]\s*\)/,
	);
	assert.match(
		source,
		/const cow = safeCattle\.find\(\(row\) => row\.id === selectedCowId\);/,
	);
	assert.match(
		source,
		/const buildingName = safeBuildings\.find\(\(row\) => row\.id === cow\.buildingId\)\?\.name;/,
	);
	assert.doesNotMatch(source, /const pregnantCows = cattle\s+\.filter/);
	assert.doesNotMatch(source, /const cow = cattle\.find/);
	assert.doesNotMatch(
		source,
		/buildings\.find\(\(row\) => row\.id === cow\.buildingId\)/,
	);
});
