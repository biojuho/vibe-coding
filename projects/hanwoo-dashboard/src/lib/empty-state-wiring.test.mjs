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

test("shared empty state component exposes an action button without custom dependencies", () => {
	const source = readSource("components/ui/empty-state.js");

	assert.match(source, /function normalizeEmptyStateOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export default function EmptyState\(options = \{\}\) \{/);
	assert.match(source, /normalizeEmptyStateOptions\(options\);/);
	assert.match(
		source,
		/const handleAction = typeof onAction === ["']function["'] \? onAction : null;/,
	);
	assert.doesNotMatch(source, /export default function EmptyState\(\{\s+icon: Icon,/);
	assert.match(source, /PremiumButton/);
	assert.match(source, /onClick=\{handleAction\}/);
	assert.match(source, /aria-label=\{actionLabel\}/);
	assert.match(source, /title=\{actionLabel\}/);
	assert.match(source, /className="mt-4 min-h-11 rounded-xl px-4"/);
});

test("operational tabs use action-oriented empty states", () => {
	const expectations = [
		{
			file: "components/tabs/FeedTab.js",
			icon: "Home",
			title: "급여 기록 전 축사를 먼저 준비해 주세요",
			action: "축사 추가하러 가기",
			handler: "handleOpenBuildingSetup",
		},
		{
			file: "components/tabs/InventoryTab.js",
			icon: "PackagePlus",
			title: "등록된 재고가 없습니다",
			action: "재고 등록",
			handler: "setIsAdding(true)",
		},
		{
			file: "components/tabs/SalesTab.js",
			icon: "ReceiptText",
			title: "출하 내역이 없습니다",
			action: "판매 기록 등록",
			fallbackAction: "개체를 먼저 등록해 주세요",
			handler: "setIsAdding(true)",
		},
		{
			file: "components/tabs/CalvingTab.js",
			icon: "ClipboardPlus",
			title: "현재 임신우가 없습니다",
			action: "임신우 등록하기",
			handler: "handleOpenCattleRegistration",
		},
		{
			file: "components/tabs/ScheduleTab.js",
			icon: "CalendarPlus",
			title: "예정된 일정이 없습니다",
			action: "일정 추가",
			handler: "setIsAdding(true)",
		},
	];

	for (const item of expectations) {
		const source = readSource(item.file);
		assert.match(source, /EmptyState/);
		assert.match(source, new RegExp(`icon=\\{${item.icon}\\}`));
		assert.match(source, new RegExp(`title="${item.title}"`));
		assert.match(source, new RegExp(item.action));
		if (item.fallbackAction) {
			assert.match(source, new RegExp(item.fallbackAction));
			assert.doesNotMatch(source, /개체 등록 필요/);
		}
		assert.match(source, new RegExp(item.handler.replace(/[()]/g, "\\$&")));
	}
});

test("operational create forms stay open when async submit handlers fail", () => {
	const expectations = [
		{
			file: "components/tabs/SalesTab.js",
			submit: "submitSale",
			handler: "handleCreateSale",
		},
		{
			file: "components/tabs/InventoryTab.js",
			submit: "submitNewItem",
			handler: "handleAddItem",
		},
		{
			file: "components/tabs/ScheduleTab.js",
			submit: "submitSchedule",
			handler: "handleCreateEvent",
		},
		{
			file: "components/tabs/SettingsTab.js",
			submit: "submitBuilding",
			handler: "handleCreateBuilding",
		},
	];

	for (const item of expectations) {
		const source = readSource(item.file);
		assert.match(
			source,
			new RegExp(`const ${item.submit} = async \\(values\\) => \\{`),
		);
		assert.match(
			source,
			new RegExp(`const saved = await ${item.handler}\\(values\\);`),
		);
		assert.match(
			source,
			/if \(!saved(?: \|\| !isMountedRef\.current)?\) \{\s+return;\s+\}/,
		);
	}
});

test("inventory tab normalizes malformed inventory payloads before rendering", () => {
	const source = readSource("components/tabs/InventoryTab.js");

	assert.match(source, /function normalizeInventoryTabOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export default function InventoryTab\(options = \{\}\) \{/);
	assert.match(source, /normalizeInventoryTabOptions\(options\);/);
	assert.match(
		source,
		/const handleAddItem =\s+typeof onAddItem === ["']function["'] \? onAddItem : async \(\) => false;/,
	);
	assert.match(
		source,
		/const handleUpdateQuantity =\s+typeof onUpdateQuantity === ["']function["']\s+\? onUpdateQuantity\s+: async \(\) => false;/,
	);
	assert.match(source, /function normalizeInventoryItems\(inventory\)/);
	assert.match(source, /if \(!Array\.isArray\(inventory\)\) return \[\]/);
	assert.match(
		source,
		/\.filter\([\s\S]*?\(item\) => item && typeof item === ["']object["'] && !Array\.isArray\(item\)/,
	);
	assert.match(
		source,
		/const safeInventory = normalizeInventoryItems\(inventory\);/,
	);
	assert.match(source, /safeInventory\.map\(\(item\) => \{/);
	assert.match(source, /safeInventory\.length === 0/);
	assert.match(source, /id: item\.id \?\? `inventory-\$\{index\}`/);
	assert.match(source, /["']재고명 미등록["']/);
	assert.match(
		source,
		/unit:\s*typeof\s+item\s*\.\s*unit\s*===\s*["']string["']\s*&&\s*item\s*\.\s*unit\s*\.\s*trim\s*\(\s*\)\s*\?\s*item\s*\.\s*unit\s*:\s*["']개["']/,
	);
	assert.match(source, /const saved = await handleAddItem\(values\);/);
	assert.match(
		source,
		/const saved = await handleUpdateQuantity\(id, parsedQuantity\);/,
	);
	assert.doesNotMatch(source, /export default function InventoryTab\(\{\s+inventory,/);
	assert.doesNotMatch(source, /const saved = await onAddItem\(values\);/);
	assert.doesNotMatch(
		source,
		/const saved = await onUpdateQuantity\(id, parsedQuantity\);/,
	);
	assert.doesNotMatch(source, /inventory\.map\(\(item\) => \{/);
	assert.doesNotMatch(source, /inventory\.length === 0/);
});

test("inventory tab keeps missing quantities unavailable instead of zero", () => {
	const source = readSource("components/tabs/InventoryTab.js");

	assert.match(
		source,
		/if \(value === null \|\| value === undefined \|\| value === ""\) \{\s+return fallback;\s+\}/,
	);
	assert.match(source, /quantity: toInventoryNumber\(item\.quantity, null\)/);
	assert.match(source, /const hasQuantity = item\.quantity !== null;/);
	assert.match(
		source,
		/hasQuantity && item\.threshold !== null && item\.quantity <= item\.threshold/,
	);
	assert.match(
		source,
		/setEditQty\(hasQuantity \? String\(item\.quantity\) : ""\)/,
	);
	assert.match(source, /hasQuantity \? item\.quantity : ["']수량 미등록["']/);
	assert.doesNotMatch(source, /quantity: toInventoryNumber\(item\.quantity\),/);
	assert.doesNotMatch(source, /const isLow = item\.threshold && item\.quantity <= item\.threshold/);
});

test("cattle edit form delegates close behavior to the async update handler", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(
		source,
		/<CattleForm\s+[\s\S]*?cattle=\{selectedCow\}[\s\S]*?buildings=\{safeBuildings\}[\s\S]*?onSubmit=\{handleUpdateCattle\}/,
	);
	assert.match(
		source,
		/const result = await updateCattle\(updated\.id, updated\);/,
	);
	assert.match(
		source,
		/if \(result\.success\) \{[\s\S]*?setIsEditing\(false\);/,
	);
	assert.doesNotMatch(
		source,
		/onSubmit=\{\(updated\) => \{ handleUpdateCattle\(updated\); setIsEditing\(false\); \}\}/,
	);
});

test("feed record form preserves input when async save fails", () => {
	const source = readSource("components/tabs/FeedTab.js");

	assert.match(source, /const submitFeedRecord = async \(values\) => \{/);
	assert.match(source, /function normalizeFeedTabOptions\(options\) \{/);
	assert.match(
		source,
		/export default function FeedTab\(options = \{\}\) \{/,
	);
	assert.match(
		source,
		/\} = normalizeFeedTabOptions\(options\);/,
	);
	assert.match(
		source,
		/const handleRecordFeed =\s+typeof onRecordFeed === "function" \? onRecordFeed : async \(\) => false;/,
	);
	assert.match(
		source,
		/const recorded = await handleRecordFeed\(\{\s+\.\.\.values,\s+buildingId: selectedBuilding,\s+\}\);/,
	);
	assert.match(
		source,
		/if \(!recorded \|\| !isMountedRef\.current\) \{\s+return;\s+\}/,
	);
	assert.doesNotMatch(source, /if \(!recorded\) \{\s+return;\s+\}/);
	assert.match(
		source,
		/reset\(\{\s+\.\.\.createFeedRecordValues\(\),\s+date: values\.date,\s+\}\);/,
	);
});

test("feed record form waits for async saves before re-enabling submit", () => {
	const source = readSource("components/tabs/FeedTab.js");

	assert.match(source, /const \[isSaving, setIsSaving\] = useState\(false\)/);
	assert.match(source, /const isMountedRef = useRef\(false\)/);
	assert.match(source, /const saveInFlightRef = useRef\(false\)/);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+isMountedRef\.current = true;[\s\S]*?return \(\) => \{\s+isMountedRef\.current = false;\s+saveInFlightRef\.current = false;/,
	);
	assert.match(source, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
	assert.match(source, /saveInFlightRef\.current = true;/);
	assert.match(source, /setIsSaving\(true\);/);
	assert.match(source, /await handleRecordFeed\(\{/);
	assert.doesNotMatch(source, /await onRecordFeed\(\{/);
	assert.match(
		source,
		/finally \{\s+saveInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setIsSaving\(false\);/,
	);
	assert.doesNotMatch(
		source,
		/finally \{\s+saveInFlightRef\.current = false;\s+setIsSaving\(false\);/,
	);
	assert.match(
		source,
		/const submitButtonLabel = isSaving\s*\?\s*["']급여 기록 저장 중["']\s*:\s*["']급여 기록 저장["'];?/,
	);
	assert.match(
		source,
		/const submitButtonText = isSaving\s*\?\s*["']급여 기록 저장 중\.\.\.["']\s*:\s*["']급여 기록 저장["'];?/,
	);
	assert.match(
		source,
		/type="submit"\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}\s+aria-label=\{submitButtonLabel\}\s+title=\{submitButtonLabel\}/,
	);
	assert.match(source, /\{submitButtonText\}/);
	assert.doesNotMatch(
		source,
		/\{isSaving\s*\?\s*["']급여 기록 저장 중\.\.\.["']\s*:\s*["']급여 기록 저장["']\s*\}/,
	);
});

test("feed summaries normalize numeric inputs before aggregation", () => {
	const source = readSource("components/tabs/FeedTab.js");

	assert.match(
		source,
		/import \{ toFiniteNumber \} from ["']@\/lib\/utils["'];?/,
	);
	assert.match(source, /function toValidFeedDate\(value\) \{/);
	assert.match(
		source,
		/const date\s*=\s*value\s*instanceof\s*Date\s*\?\s*new\s+Date\s*\(\s*value\s*\.\s*getTime\s*\(\s*\)\s*\)\s*:\s*new\s+Date\s*\(\s*value\s*\);?/,
	);
	assert.match(source, /const dateKey = value\.trim\(\)\.slice\(0, 10\);/);
	assert.match(source, /date\.toISOString\(\)\.slice\(0, 10\) !== dateKey/);
	assert.match(source, /return date;/);
	assert.match(source, /function getFeedDateTime\(value\) \{/);
	assert.match(
		source,
		/return toValidFeedDate\(value\)\?\.getTime\(\) \?\? Number\.NEGATIVE_INFINITY;/,
	);
	assert.match(source, /function formatFeedDateLabel\(value, options\) \{/);
	assert.match(
		source,
		/return date \? date\.toLocaleDateString\(["']ko-KR["'], options\) : ["']날짜 미등록["'];/,
	);
	assert.match(
		source,
		/getFeedDateTime\(first\.date\) - getFeedDateTime\(second\.date\)/,
	);
	assert.match(
		source,
		/const key\s*=\s*formatFeedDateLabel\(\s*record\.date\s*,\s*\{\s*month\s*:\s*["']short["']\s*,\s*day\s*:\s*["']numeric["']\s*,?\s*\}\s*\);?/,
	);
	assert.match(source, /\{formatFeedDateLabel\(record\.date\)\}/);
	assert.match(
		source,
		/roughageTotal:\s*\(\s*toFiniteNumber\(\s*standard\s*\.\s*roughageKg\s*\)\s*\*\s*count\s*\)\s*\.\s*toFixed\(\s*1\s*,?\s*\)/,
	);
	assert.match(
		source,
		/concentrateTotal:\s*\(\s*toFiniteNumber\(\s*standard\s*\.\s*concentrateKg\s*\)\s*\*\s*count\s*\)\s*\.\s*toFixed\(\s*1\s*,?\s*\)/,
	);
	assert.match(source, /sum \+ toFiniteNumber\(value\.roughageTotal\)/);
	assert.match(source, /sum \+ toFiniteNumber\(value\.concentrateTotal\)/);
	assert.match(
		source,
		/sum \+ toFiniteNumber\(standardsMap\[row\.status\]\?\.roughageKg\)/,
	);
	assert.match(
		source,
		/sum \+ toFiniteNumber\(standardsMap\[row\.status\]\?\.concentrateKg\)/,
	);
	assert.match(
		source,
		/grouped\[key\]\.roughage \+= toFiniteNumber\(record\.roughage\);/,
	);
	assert.match(
		source,
		/grouped\[key\]\.concentrate \+= toFiniteNumber\(record\.concentrate\);/,
	);
	assert.doesNotMatch(source, /const date = new Date\(value\);/);
	assert.doesNotMatch(source, /new Date\(record\.date\)\.toLocaleDateString/);
	assert.doesNotMatch(
		source,
		/new Date\(first\.date\) - new Date\(second\.date\)/,
	);
	assert.doesNotMatch(source, /parseFloat\(value\.roughageTotal\)/);
	assert.doesNotMatch(source, /parseFloat\(value\.concentrateTotal\)/);
	assert.doesNotMatch(
		source,
		/standardsMap\[row\.status\]\?\.roughageKg \|\| 0/,
	);
	assert.doesNotMatch(
		source,
		/standardsMap\[row\.status\]\?\.concentrateKg \|\| 0/,
	);
});

test("feed tab normalizes malformed payloads before rendering", () => {
	const source = readSource("components/tabs/FeedTab.js");

	assert.match(source, /function normalizeFeedItems\(items\) \{/);
	assert.match(
		source,
		/return\s*Array\.isArray\(items\)[\s\S]*?items\.filter\([\s\S]*?item\s*&&\s*typeof\s*item\s*===\s*["']object["']\s*&&\s*!Array\.isArray\(item\)[\s\S]*?\)\s*:\s*\[\];?/,
	);
	assert.match(source, /function normalizeFeedBuildings\(buildings\) \{/);
	assert.match(source, /id: building\.id \?\? `feed-building-\$\{index\}`/);
	assert.match(source, /["']축사 이름 미등록["']/);
	assert.doesNotMatch(source, /["']축사명 미등록["']/);
	assert.match(
		source,
		/const safeCattle = useMemo\(\(\) => normalizeFeedItems\(cattle\), \[cattle\]\);/,
	);
	assert.match(
		source,
		/const safeFeedStandards = useMemo\([\s\S]*?normalizeFeedItems\(feedStandards\)[\s\S]*?\]\s*\);?/,
	);
	assert.match(
		source,
		/const safeFeedHistory = useMemo\([\s\S]*?normalizeFeedItems\(feedHistory\)[\s\S]*?\]\s*\);?/,
	);
	assert.match(
		source,
		/const safeBuildings = useMemo\([\s\S]*?normalizeFeedBuildings\(buildings\)[\s\S]*?\]\s*\);?/,
	);
	assert.match(source, /safeFeedStandards\.forEach\(\(standard\) => \{/);
	assert.match(
		source,
		/safeCattle\.filter\(\(row\) => row\.status === status\)/,
	);
	assert.match(source, /return safeCattle;/);
	assert.match(source, /\[\.\.\.safeFeedHistory\]\.sort/);
	assert.match(source, /safeBuildings\.map\(\(building\) => \(/);
	assert.match(
		source,
		/safeFeedHistory\.slice\(0, 5\)\.map\(\(record, index\) => \(/,
	);
	assert.match(source, /key=\{record\.id \?\? `feed-record-\$\{index\}`\}/);
	assert.doesNotMatch(source, /feedStandards\.forEach\(\(standard\) => \{/);
	assert.doesNotMatch(source, /const count = cattle\.filter/);
	assert.doesNotMatch(source, /return cattle;/);
	assert.doesNotMatch(source, /\[\.\.\.feedHistory\]\.sort/);
	assert.doesNotMatch(source, /buildings\.map\(\(building\) => \(/);
	assert.doesNotMatch(source, /feedHistory\.slice\(0, 5\)\.map/);
});

test("feed building filter chips expose selected state and Korean labels", () => {
	const source = readSource("components/tabs/FeedTab.js");

	assert.match(source, /function normalizeFeedHelperOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === ["']object["'] && !Array\.isArray\(options\)\s*\?\s*options\s*:\s*\{\s*\}\s*;?/,
	);
	assert.match(source, /function FilterChip\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{\s*active,\s*children,\s*onClick,\s*label,\s*disabled = false,\s*\} = normalizeFeedHelperOptions\(options\);/,
	);
	assert.match(
		source,
		/const actionLabel = disabled\s*\?\s*`\$\{label\} - 급여 기록 저장 중에는 변경할 수 없습니다`\s*:\s*label;?/,
	);
	assert.match(source, /disabled=\{disabled\}/);
	assert.match(source, /aria-busy=\{disabled\}/);
	assert.match(source, /aria-pressed=\{active\}/);
	assert.match(source, /aria-label=\{actionLabel\}/);
	assert.match(source, /title=\{actionLabel\}/);
	assert.match(
		source,
		/className=\{`min-h-11 rounded-full px-4 py-2 font-bold text-\[13px\] whitespace-nowrap shadow-sm/,
	);
	assert.match(
		source,
		/const chipText = disabled \? "급여 기록 저장 중\.\.\." : children;?/,
	);
	assert.match(source, /\{chipText\}/);
	assert.match(
		source,
		/label=["']전체 축사 급여 보기["'][\s\S]*?disabled=\{isSaving\}/,
	);
	assert.match(
		source,
		/label=\{`\$\{building\.name\}\s+급여\s+보기`\}[\s\S]*?disabled=\{\s*isSaving\s*\}/,
	);
});

test("feed tab visible copy is readable Korean product copy", () => {
	const source = readSource("components/tabs/FeedTab.js");

	const expectedCopy = [
		"축사를 먼저 선택해 주세요.",
		"급여 기록은 특정 축사 기준으로 저장됩니다.",
		"사료 급여 모니터링",
		"급여 기록 전 축사를 먼저 준비해 주세요",
		"축사를 추가하면 축사별 급여 기준과 오늘 급여 기록 폼을 바로 사용할 수 있습니다.",
		"축사 추가하러 가기",
		"오늘 급여 가이드",
		"조사료 권장량",
		"배합사료 권장량",
		"오늘 급여 기록",
		"기록 날짜",
		"특이사항 메모",
		"사료 상태, 섭취 변화, 축사 메모를 적어 주세요.",
		"급여 기록 저장",
		"최근 급여 추이",
		"최근 기록",
		"날짜 미등록",
	];

	for (const copy of expectedCopy) {
		assert.equal(source.includes(copy), true);
	}

	assert.equal(source.includes("湲됱뿬"), false);
	assert.equal(source.includes("異뺤궗"), false);
	assert.equal(source.includes("議곗궗猷"), false);
	assert.equal(source.includes("諛고빀"), false);
});

test("feed trend chart exposes an accessible chart summary", () => {
	const source = readSource("components/tabs/FeedTab.js");

	assert.match(
		source,
		/const feedChartLabel =\s*["']최근 급여 추이 차트\. 조사료와 배합사료 급여량을 날짜별로 비교합니다\.["'];?/,
	);
	assert.match(
		source,
		/role="img"\s+aria-label=\{feedChartLabel\}\s+title=\{feedChartLabel\}[\s\S]*?<ResponsiveContainer[\s\S]*?width="100%"[\s\S]*?height="100%"[\s\S]*?minWidth=\{0\}[\s\S]*?minHeight=\{0\}[\s\S]*?initialDimension=\{\{ width: 1, height: 1 \}\}/,
	);
});

test("feed record form fields expose labels and validation state", () => {
	const source = readSource("components/tabs/FeedTab.js");

	assert.match(source, /<PremiumLabel htmlFor="feed-date">/);
	assert.match(
		source,
		/id="feed-date"[\s\S]*?aria-invalid=\{Boolean\(errors\.date\)\}/,
	);
	assert.match(source, /<PremiumLabel htmlFor="feed-note">/);
	assert.match(
		source,
		/id="feed-note"[\s\S]*?aria-invalid=\{Boolean\(errors\.note\)\}/,
	);
	assert.match(source, /function Field\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ label, suffix, error, inputProps \} =\s*normalizeFeedHelperOptions\(options\);/,
	);
	assert.match(
		source,
		/const safeInputProps = normalizeFeedHelperOptions\(inputProps\);/,
	);
	assert.match(
		source,
		/const inputName =\s*typeof safeInputProps\.name === ["']string["'] && safeInputProps\.name\.trim\(\)\s*\?\s*safeInputProps\.name\s*:\s*["']field["'];/,
	);
	assert.match(source, /const fieldId = `feed-\$\{inputName\}`;/);
	assert.match(source, /<PremiumLabel htmlFor=\{fieldId\}>/);
	assert.match(
		source,
		/id=\{fieldId\}[\s\S]*?\{\.\.\.safeInputProps\}[\s\S]*?aria-invalid=\{Boolean\(error\)\}/,
	);
});

test("feed record form validation messages are announced with their controls", () => {
	const source = readSource("components/tabs/FeedTab.js");

	assert.match(
		source,
		/id="feed-date"[\s\S]*?aria-describedby=\{errors\.date \? ["']feed-date-error["'] : undefined\}/,
	);
	assert.match(
		source,
		/id="feed-date-error" role="alert"[\s\S]*?\{errors\.date\.message\}/,
	);
	assert.match(
		source,
		/id="feed-note"[\s\S]*?aria-describedby=\{errors\.note \? ["']feed-note-error["'] : undefined\}/,
	);
	assert.match(
		source,
		/id="feed-note-error" role="alert"[\s\S]*?\{errors\.note\.message\}/,
	);
	assert.match(source, /const errorId = `\$\{fieldId\}-error`;/);
	assert.match(source, /aria-describedby=\{error \? errorId : undefined\}/);
	assert.match(
		source,
		/<div id=\{errorId\} role=["']alert["'] style=\{errorTextStyle\}>\s*\{error\}\s*<\/div>/,
	);
});

test("inventory quantity edit preserves input when async save fails", () => {
	const source = readSource("components/tabs/InventoryTab.js");

	assert.match(source, /const handleUpdate = async \(id\) => \{/);
	assert.match(
		source,
		/const parsedQuantity = parseInlineQuantityInput\(editQty\);/,
	);
	assert.match(
		source,
		/const saved = await handleUpdateQuantity\(id, parsedQuantity\);/,
	);
	assert.match(source, /if \(!saved \|\| !isMountedRef\.current\) \{\s+return;\s+\}/);
	assert.doesNotMatch(source, /if \(!saved\) \{\s+return;\s+\}/);
	assert.match(source, /setEditId\(null\);\s+setEditQty\(["']["']\);/);
});

test("inventory create form waits for async saves before re-enabling submit", () => {
	const source = readSource("components/tabs/InventoryTab.js");

	assert.match(source, /import \{ focusElementSafely \} from ["']@\/lib\/safeFocus["'];/);
	assert.match(source, /const isMountedRef = useRef\(false\)/);
	assert.match(source, /const inventoryFormRef = useRef\(null\);/);
	assert.match(source, /const inventoryNameInputRef = useRef\(null\);/);
	assert.match(source, /const saveInFlightRef = useRef\(false\)/);
	assert.match(source, /const inventoryNameRegistration = register\("name"\);/);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+isMountedRef\.current = true;[\s\S]*?return \(\) => \{\s+isMountedRef\.current = false;\s+saveInFlightRef\.current = false;\s+quantityInFlightRef\.current = false;/,
	);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+if \(quickActionIntent\?\.actionId === ["']add-inventory["']\) \{\s+setIsAdding\(true\);\s+\}\s+\}, \[quickActionIntent\?\.actionId, quickActionIntent\?\.nonce\]\);/,
	);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+if \(!isAdding\) \{\s+return;\s+\}[\s\S]*?const timeoutId = window\.setTimeout\(\(\) => \{[\s\S]*?inventoryFormRef\.current\?\.scrollIntoView\(\{\s+behavior: "smooth",\s+block: "start",\s+inline: "nearest",\s+\}\);[\s\S]*?inventoryFormRef\.current\?\.scrollIntoView\(\);[\s\S]*?focusElementSafely\(inventoryNameInputRef\.current\);[\s\S]*?\}, 0\);[\s\S]*?window\.clearTimeout\(timeoutId\);[\s\S]*?\}, \[isAdding, quickActionIntent\?\.nonce\]\);/,
	);
	assert.match(
		source,
		/const submitButtonLabel = isSaving\s*\?\s*["']재고 등록 중["']\s*:\s*["']재고 등록["'];?/,
	);
	assert.doesNotMatch(source, /급여 기록 저장하기/);
	assert.doesNotMatch(source, /재고 등록하기/);
	assert.match(source, /const addFormButtonLabel = isSaving/);
	assert.match(source, /재고 저장 중에는 등록 창을 닫을 수 없습니다/);
	assert.match(source, /재고 등록 취소/);
	assert.match(source, /재고 등록 창 열기/);
	assert.match(source, /const addFormButtonText = isSaving/);
	assert.match(source, /재고 저장 중\.\.\./);
	assert.match(source, /재고 등록 취소/);
	assert.match(source, /: "재고 등록";/);
	assert.doesNotMatch(
		source,
		/const addFormButtonText = isSaving[\s\S]*?\? "재고 저장 중\.\.\."[\s\S]*?: isAdding[\s\S]*?\? "취소"[\s\S]*?: "\+재고 등록";/,
	);
	assert.doesNotMatch(
		source,
		/const addFormButtonText = isSaving[\s\S]*?: isAdding[\s\S]*?\? "취소"/,
	);
	assert.doesNotMatch(source, /"\+재고 등록"/);
	assert.match(source, /const submitNewItem = async \(values\) => \{/);
	assert.match(source, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
	assert.match(source, /saveInFlightRef\.current = true;/);
	assert.match(source, /setIsSaving\(true\);/);
	assert.match(source, /const saved = await handleAddItem\(values\);/);
	assert.match(
		source,
		/finally \{\s+saveInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setIsSaving\(false\);/,
	);
	assert.doesNotMatch(
		source,
		/finally \{\s+saveInFlightRef\.current = false;\s+setIsSaving\(false\);/,
	);
	assert.match(
		source,
		/onClick=\{toggleAddForm\}\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}\s+aria-expanded=\{isAdding\}\s+aria-label=\{addFormButtonLabel\}\s+title=\{addFormButtonLabel\}/,
	);
	assert.match(
		source,
		/className="min-h-11 text-\[13px\] text-green-400 border-green-500\/50 hover:bg-green-500\/10 px-4 py-2 rounded-lg font-bold"/,
	);
	assert.match(source, /\{addFormButtonText\}/);
	assert.match(
		source,
		/<form\s+ref=\{inventoryFormRef\}[\s\S]*?onSubmit=\{handleInventorySubmit\}/,
	);
	assert.match(
		source,
		/id="inventory-name"[\s\S]*?\{\.\.\.inventoryNameRegistration\}[\s\S]*?ref=\{\(element\) => \{\s+inventoryNameRegistration\.ref\(element\);\s+inventoryNameInputRef\.current = element;\s+\}\}/,
	);
	assert.doesNotMatch(
		source,
		/id="inventory-name"[\s\S]{0,240}\{\.\.\.register\("name"\)\}/,
	);
	assert.match(
		source,
		/type="submit"\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}\s+aria-label=\{submitButtonLabel\}\s+title=\{submitButtonLabel\}/,
	);
});

test("inventory quantity edit controls use Korean task labels", () => {
	const source = readSource("components/tabs/InventoryTab.js");

	assert.match(source, /const isQuantitySaving = savingQuantityId === item\.id;/);
	assert.match(source, /const itemQuantitySaveLabel = isQuantitySaving/);
	assert.match(source, /재고 수량 저장 중/);
	assert.match(source, /const itemQuantitySaveText = isQuantitySaving/);
	assert.match(source, /수량 저장 중\.\.\./);
	assert.match(source, /aria-label=\{`\$\{item\.name\} 재고 수량 수정`\}/);
	assert.match(source, /aria-label=\{itemQuantitySaveLabel\}/);
	assert.match(source, /title=\{itemQuantitySaveLabel\}/);
	assert.match(source, /\{itemQuantitySaveText\}/);
	assert.doesNotMatch(source, /\{isQuantitySaving \? "수량 저장 중\.\.\." : "저장"\}/);
	assert.doesNotMatch(source, />\s*OK\s*<\/PremiumButton>/);
});
