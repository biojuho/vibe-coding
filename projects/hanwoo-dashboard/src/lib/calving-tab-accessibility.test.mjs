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

test("calving empty state opens the cattle registration path", () => {
	const source = readSource("components/tabs/CalvingTab.js");
	const dashboardSource = readSource("components/DashboardClient.js");

	assert.match(source, /import EmptyState from ["']@\/components\/ui\/empty-state["'];/);
	assert.match(source, /import \{ ClipboardPlus \} from ["']lucide-react["'];/);
	assert.match(source, /onOpenCattleRegistration/);
	assert.match(
		source,
		/const handleOpenCattleRegistration =\s+typeof onOpenCattleRegistration === ["']function["']\s+\?\s+onOpenCattleRegistration\s+:\s+null;/,
	);
	assert.match(source, /<EmptyState[\s\S]*?icon=\{ClipboardPlus\}/);
	assert.match(source, /title="현재 임신우가 없습니다"/);
	assert.match(source, /actionLabel="임신우 등록하기"/);
	assert.match(source, /onAction=\{handleOpenCattleRegistration\}/);
	assert.doesNotMatch(source, /현재 임신우가 없습니다\.[\s\S]*?<\/div>/);
	assert.match(
		dashboardSource,
		/<CalvingTab[\s\S]*?onOpenCattleRegistration=\{\(\) =>[\s\S]*?handleQuickAction\(\{[\s\S]*?id: ["']add-cattle["'][\s\S]*?\}\)[\s\S]*?\}/,
	);
});

test("calving tab form fields expose explicit labels and invalid states", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	assert.match(
		source,
		/<span\s+className="section-header-icon"\s+aria-hidden="true">[\s\S]*?🐮[\s\S]*?<\/span>/,
	);
	assert.match(source, /<label[\s\S]*?htmlFor="calving-date"/);
	assert.match(source, /id="calving-date"[\s\S]*?type="date"/);
	assert.match(source, /aria-invalid=\{Boolean\(errors\.calvingDate\)\}/);
	assert.match(source, /<label[\s\S]*?htmlFor="calf-gender"/);
	assert.match(source, /id="calf-gender"[\s\S]*?\{\s*\.\.\.register\s*\(\s*["']calfGender["']\s*\)\s*\}/);
	assert.match(source, /aria-invalid=\{Boolean\(errors\.calfGender\)\}/);
});

test("calving tab validation messages are announced with their controls", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	assert.match(
		source,
		/aria-describedby=\{\s*errors\.calvingDate\s*\?\s*["']calving-date-error["']\s*:\s*undefined\s*\}/,
	);
	assert.match(source, /<div[\s\S]*?id="calving-date-error"[\s\S]*?role="alert"/);
	assert.match(
		source,
		/aria-describedby=\{\s*errors\.calfGender\s*\?\s*["']calf-gender-error["']\s*:\s*undefined\s*\}/,
	);
	assert.match(source, /<div[\s\S]*?id="calf-gender-error"[\s\S]*?role="alert"/);
	assert.match(
		source,
		/aria-describedby=\{\s*errors\.calfTagNumber\s*\?\s*["']calf-tag-number-error["']\s*:\s*undefined\s*\}/,
	);
	assert.match(source, /<div[\s\S]*?id="calf-tag-number-error"[\s\S]*?role="alert"/);
});

test("calving form waits for async saves before re-enabling actions", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	assert.match(source, /const saveInFlightRef = useRef\(false\)/);
	assert.match(source, /const isMountedRef = useRef\(false\)/);
	assert.match(source, /const \[isSaving, setIsSaving\] = useState\(false\)/);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+isMountedRef\.current = true;[\s\S]*?return \(\) => \{\s+isMountedRef\.current = false;\s+saveInFlightRef\.current = false;/,
	);
	assert.match(source, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
	assert.match(source, /saveInFlightRef\.current = true;/);
	assert.match(source, /setIsSaving\(true\);/);
	assert.match(source, /await handleRecordCalving\(\{/);
	assert.doesNotMatch(source, /await onRecordCalving\(\{/);
	assert.match(
		source,
		/if \(!recorded \|\| !isMountedRef\.current\) \{\s+return;\s+\}/,
	);
	assert.doesNotMatch(source, /if \(!recorded\) \{\s+return;\s+\}/);
	assert.match(
		source,
		/finally \{\s*saveInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setIsSaving\(false\);/,
	);
	assert.doesNotMatch(
		source,
		/finally \{\s*saveInFlightRef\.current = false;\s+setIsSaving\(false\);/,
	);
	assert.match(
		source,
		/const submitButtonLabel = isSaving\s*\?\s*['"]분만 기록 저장 중['"]\s*:\s*['"]분만 완료 및 송아지 등록['"];/,
	);
	assert.match(
		source,
		/const submitButtonText = isSaving\s*\?\s*['"]분만 기록 저장 중\.\.\.['"]\s*:\s*['"]분만 완료 및 송아지 등록['"];/,
	);
	assert.match(
		source,
		/const cancelButtonLabel = isSaving\s*\?\s*['"]분만 기록 저장 중에는 취소할 수 없습니다['"]\s*:\s*['"]분만 기록 취소['"];/,
	);
	assert.match(
		source,
		/const cancelButtonText = isSaving\s*\?\s*['"]분만 기록 저장 중\.\.\.['"]\s*:\s*['"]분만 기록 취소['"];/,
	);
	assert.match(
		source,
		/type="submit"\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}\s+aria-label=\{submitButtonLabel\}\s+title=\{submitButtonLabel\}/,
	);
	assert.match(source, /\{submitButtonText\}/);
	assert.doesNotMatch(
		source,
		/\{isSaving\s*\?\s*["']분만 기록 저장 중\.\.\.["']\s*:\s*["']분만 완료 및 송아지 등록["']\s*\}/,
	);
	assert.match(
		source,
		/type="button"\s+onClick=\{closeCalvingForm\}\s+disabled=\{isSaving\}/,
	);
	assert.match(source, /aria-busy=\{isSaving\}/);
	assert.match(source, /aria-label=\{cancelButtonLabel\}/);
	assert.match(source, /title=\{cancelButtonLabel\}/);
	assert.match(source, /\{cancelButtonText\}/);
	assert.doesNotMatch(
		source,
		/const cancelButtonText = isSaving\s*\?\s*['"]분만 기록 저장 중\.\.\.['"]\s*:\s*['"]취소['"];/,
	);
	assert.match(
		source,
		/onClick=\{\(\) => openCalvingForm\(cow\.id\)\}[\s\S]*?aria-label=\{`\$\{cow\.name\} 분만 처리 열기`\}[\s\S]*?title=\{`\$\{cow\.name\} 분만 처리 열기`\}/,
	);
});

test("calving tab keeps malformed pregnancy dates stable in the list", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	assert.match(source, /function getPregnancyDateTime\(value\) \{/);
	assert.match(
		source,
		/return Number\.isNaN\(\s*date\.getTime\(\)\s*\)\s*\?\s*Number\.POSITIVE_INFINITY\s*:\s*date\.getTime\(\)\s*;?/,
	);
	assert.match(source, /\.sort\(\s*\(\s*first\s*,\s*second\s*\)\s*=>/);
	assert.match(source, /getPregnancyDateTime\(\s*first\.pregnancyDate\s*\)/);
	assert.match(source, /getPregnancyDateTime\(\s*second\.pregnancyDate\s*\)/);
	assert.doesNotMatch(
		source,
		/new Date\(first\.pregnancyDate\) - new Date\(second\.pregnancyDate\)/,
	);
});

test("calving tab alert badges use operator-readable countdown labels", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	assert.match(source, /임박 \{daysLeft\}일 남음/);
	assert.doesNotMatch(source, /임박 D-\{daysLeft\}/);
});

test("calving tab normalizes malformed cattle and building payloads before rendering", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	assert.match(source, /import \{\s*useEffect,\s*useMemo,\s*useRef,\s*useState\s*\} from ['"]react['"];/);
	assert.match(source, /function normalizeCalvingTabOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export default function CalvingTab\(options = \{\}\) \{/);
	assert.match(source, /normalizeCalvingTabOptions\(options\);/);
	assert.match(
		source,
		/const handleRecordCalving =\s+typeof onRecordCalving === ["']function["'] \? onRecordCalving : async \(\) => false;/,
	);
	assert.match(source, /function normalizeCalvingCattle\(cattle\) \{/);
	assert.match(source, /return Array\.isArray\(cattle\)/);
	assert.match(
		source,
		/row\s*&&\s*typeof\s*row\s*===\s*['"]object['"]\s*&&\s*!Array\.isArray\(row\)\s*&&\s*row\.id\s*!=\s*null/,
	);
	assert.match(source, /function normalizeCalvingBuildings\(buildings\) \{/);
	assert.match(source, /return Array\.isArray\(buildings\)/);
	assert.match(
		source,
		/building\s*&&\s*typeof\s*building\s*===\s*['"]object['"]\s*&&\s*!Array\.isArray\(building\)/,
	);
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
		/const cow = safeCattle\s*\.\s*find\(\s*\(\s*row\s*\)\s*=>\s*row\s*\.\s*id\s*===\s*selectedCowId\s*\)\s*;?/,
	);
	assert.match(
		source,
		/const buildingName = safeBuildings\s*\.\s*find\(\s*\(\s*row\s*\)\s*=>\s*row\s*\.\s*id\s*===\s*cow\s*\.\s*buildingId\s*,?\s*\)\s*\??\.\s*name\s*;?/,
	);
	assert.doesNotMatch(source, /export default function CalvingTab\(\{\s+cattle,/);
	assert.doesNotMatch(source, /const pregnantCows = cattle\s+\.filter/);
	assert.doesNotMatch(source, /const cow = cattle\.find/);
	assert.doesNotMatch(
		source,
		/buildings\.find\(\(row\) => row\.id === cow\.buildingId\)/,
	);
});

test("CalvingTab form-trigger button declares aria-expanded so screen readers announce inline form state", () => {
	const source = readSource("components/tabs/CalvingTab.js");

	// The "분만 처리 시작" button toggles an inline form; aria-expanded lets
	// screen readers announce whether the form is open (WCAG 4.1.2 State)
	assert.match(source, /aria-expanded=\{isSelected\}/);
});
