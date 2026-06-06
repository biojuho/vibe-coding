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

test("settings tab switch controls expose Korean accessible names and checked state", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(source, /role="switch"/);
	assert.match(source, /aria-checked=\{isDark\}/);
	assert.match(
		source,
		/aria-label=\{\s*isDark\s*\?\s*["']다크모드 끄기["']\s*:\s*["']다크모드 켜기["']\s*\}/,
	);
	assert.match(
		source,
		/title=\{\s*isDark\s*\?\s*["']다크모드 끄기["']\s*:\s*["']다크모드 켜기["']\s*\}/,
	);
	assert.match(source, /aria-checked=\{isOn\}/);
	assert.match(
		source,
		/aria-label=\{\s*`\s*\$\{widget\.label\}\s*위젯\s*\$\{isOn\s*\?\s*["']숨기기["']\s*:\s*["']보이기["']\}\s*`\s*\}/,
	);
	assert.match(
		source,
		/title=\{\s*`\s*\$\{widget\.label\}\s*위젯\s*\$\{isOn\s*\?\s*["']숨기기["']\s*:\s*["']보이기["']\}\s*`\s*\}/,
	);
	assert.match(
		source,
		/<Settings\s+size=\{20\}\s+className=["']text-\[color:var\(--color-text\)\]["']\s+aria-hidden=["']true["']\s*\/>/,
	);
	assert.match(source, /<MapPin size=\{16\} aria-hidden=["']true["'] \/>/);
	assert.doesNotMatch(source, /aria-label="Theme"/);
	assert.doesNotMatch(source, /aria-label="Widget"/);
});

test("theme hook persists settings without breaking on browser storage failures", () => {
	const source = readSource("lib/useTheme.js");

	assert.match(source, /function getDocumentRoot\(\) \{/);
	assert.match(source, /function getSystemTheme\(\) \{/);
	assert.match(source, /function readStoredTheme\(\) \{/);
	assert.match(source, /function writeStoredTheme\(theme\) \{/);
	assert.match(source, /if \(typeof window === "undefined"\) \{\s*return "light";/);
	assert.match(source, /if \(typeof document === "undefined"\) \{\s*return null;/);
	assert.match(
		source,
		/try \{\s*return document\.documentElement;\s*\} catch \{\s*return null;\s*\}/,
	);
	assert.match(source, /const root = getDocumentRoot\(\);/);
	assert.match(source, /if \(!root\) \{\s*return;\s*\}/);
	assert.match(
		source,
		/try \{\s*root\.setAttribute\("data-theme", theme\);\s*root\.classList\.toggle\(DARK_CLASS, theme === "dark"\);[\s\S]*?\} catch \{\}/,
	);
	assert.match(source, /const saved = localStorage\.getItem\(STORAGE_KEY\);/);
	assert.match(source, /if \(saved === "dark" \|\| saved === "light"\) \{/);
	assert.match(source, /return getSystemTheme\(\);/);
	assert.match(
		source,
		/try \{\s*return window\.matchMedia\("\(prefers-color-scheme: dark\)"\)\.matches[\s\S]*?\} catch \{\s*return "light";\s*\}/,
	);
	assert.match(source, /useState\(\(\) => readStoredTheme\(\)\)/);
	assert.match(source, /writeStoredTheme\(theme\);/);
	assert.match(
		source,
		/try \{\s*localStorage\.setItem\(STORAGE_KEY, theme\);[\s\S]*?\} catch \{\}/,
	);
	assert.doesNotMatch(
		source,
		/useState\(\(\) => \{[\s\S]*?window\.matchMedia\("\(prefers-color-scheme: dark\)"\)\.matches[\s\S]*?\}\)/,
	);
	assert.doesNotMatch(
		source,
		/if \(typeof window !== "undefined"\) \{\s*localStorage\.setItem\(STORAGE_KEY, theme\);/,
	);
	assert.doesNotMatch(source, /document\.documentElement\.setAttribute/);
	assert.doesNotMatch(source, /document\.documentElement\.classList\.toggle/);
});

test("settings tab decorative text icons are hidden from assistive tech", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(
		source,
		/<span aria-hidden=["']true["'] style=\{\{\s*fontSize:\s*['"]20px['"]\s*\}\}>\s*\{isDark\s*\?\s*['"]야['"]\s*:\s*['"]주['"]\}\s*<\/span>/,
	);
	assert.match(
		source,
		/<span aria-hidden=["']true["'] style=\{\{\s*fontSize:\s*['"]18px['"]\s*\}\}>\s*위젯\s*<\/span>/,
	);
	assert.match(
		source,
		/<span aria-hidden=["']true["'] style=\{\{\s*fontSize:\s*['"]16px['"]\s*\}\}>\s*\{widget\.icon\}\s*<\/span>/,
	);
});

test("dashboard widget registry is centralized with readable Korean labels", () => {
	const dashboardSource = readSource("components/DashboardClient.js");
	const settingsSource = readSource("components/tabs/SettingsTab.js");
	const hookSource = readSource("lib/hooks/useWidgetSettings.js");

	assert.match(
		dashboardSource,
		/import\s*\{\s*[\s\S]*?useWidgetSettings[\s\S]*?\}\s*from\s*['"]@\/lib\/hooks\/useWidgetSettings['"];?/,
	);
	assert.doesNotMatch(dashboardSource, /const WIDGET_REGISTRY = \[/);
	assert.match(
		settingsSource,
		/\{widget\.description \? \([\s\S]*?\{widget\.description\}[\s\S]*?\) : null\}/,
	);
	assert.match(
		hookSource,
		/description:\s*['"]켜면 농장 요약 정보를 AI 분석 API로 전송합니다\.['"]/,
	);
	assert.doesNotMatch(hookSource, /농장 요약 데이터를 AI 분석 API로 전송/);
	assert.match(hookSource, /label:\s*['"]날씨 \/ THI['"]/);
	assert.match(hookSource, /label:\s*['"]시세 정보['"]/);
	assert.match(hookSource, /label:\s*['"]알림 \(발정\/분만\)['"]/);
	assert.match(hookSource, /label:\s*['"]경영 분석 차트['"]/);
	assert.match(hookSource, /label:\s*['"]출하 수익성 예측['"]/);
	assert.match(hookSource, /label:\s*['"]핵심 통계['"]/);
	assert.doesNotMatch(hookSource, /[筌욃첎쳸疫]/);
});

test("widget settings normalize persisted visibility safely", () => {
	const hookSource = readSource("lib/hooks/useWidgetSettings.js");

	assert.match(hookSource, /function getDefaultWidgetVisibility\(\) \{/);
	assert.match(hookSource, /function normalizeStoredWidgetVisibility\(value\) \{/);
	assert.match(hookSource, /function readStoredWidgetVisibility\(\) \{/);
	assert.match(hookSource, /function writeStoredWidgetVisibility\(visibility\) \{/);
	assert.match(
		hookSource,
		/const WIDGET_ID_SET = new Set\(WIDGET_REGISTRY\.map\(\(widget\) => widget\.id\)\);/,
	);
	assert.match(
		hookSource,
		/if \(!value \|\| typeof value !== "object" \|\| Array\.isArray\(value\)\) \{/,
	);
	assert.match(
		hookSource,
		/typeof value\[widget\.id\] === "boolean"\s*\?\s*value\[widget\.id\]\s*:\s*defaults\[widget\.id\]/,
	);
	assert.match(
		hookSource,
		/return normalizeStoredWidgetVisibility\(JSON\.parse\(saved\)\);/,
	);
	assert.match(hookSource, /useState\(\(\) => readStoredWidgetVisibility\(\)\)/);
	assert.match(
		hookSource,
		/const toggle = \(id\) => \{\s+if \(!WIDGET_ID_SET\.has\(id\)\) \{\s+return;\s+\}/,
	);
	assert.match(
		hookSource,
		/if \(!WIDGET_ID_SET\.has\(id\)\) \{\s+return;\s+\}\s+setVisible\(\(prev\) => \{/,
	);
	assert.match(
		hookSource,
		/try \{\s*localStorage\.setItem\(WIDGETS_STORAGE_KEY, JSON\.stringify\(visibility\)\);[\s\S]*?\} catch \{\}/,
	);
	assert.match(hookSource, /writeStoredWidgetVisibility\(next\);/);
	assert.doesNotMatch(hookSource, /\{\s*\.\.\.defaults,\s*\.\.\.JSON\.parse\(saved\)\s*\}/);
	assert.doesNotMatch(
		hookSource,
		/localStorage\.setItem\(WIDGETS_STORAGE_KEY, JSON\.stringify\(next\)\);/,
	);
});

test("settings tab building delete buttons identify the target building", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(source, /const isDeletingBuilding = deletingBuildingId === building\.id;/);
	assert.match(source, /const buildingDeleteButtonLabel = isDeletingBuilding/);
	assert.match(source, /축사 삭제 중/);
	assert.match(source, /축사 삭제`/);
	assert.match(source, /aria-label=\{buildingDeleteButtonLabel\}/);
	assert.match(source, /title=\{buildingDeleteButtonLabel\}/);
	assert.match(source, /\{isDeletingBuilding \? "축사 삭제 중\.\.\." : "축사 삭제"\}/);
	assert.doesNotMatch(source, /동 삭제/);
	assert.doesNotMatch(source, /\{isDeletingBuilding \? "축사 삭제 중\.\.\." : "삭제"\}/);
});

test("settings diagnostics link exposes an explicit navigation label", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(
		source,
		/href="\/admin\/diagnostics"[\s\S]*?aria-label="시스템 진단 도구 열기"[\s\S]*?title="시스템 진단 도구 열기"/,
	);
});

test("settings tab normalizes malformed building payloads before rendering", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(source, /function normalizeSettingsTabOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export default function SettingsTab\(options = \{\}\) \{/);
	assert.match(source, /normalizeSettingsTabOptions\(options\);/);
	assert.match(source, /function normalizeSettingsBuildings\(buildings\) \{/);
	assert.match(source, /Array\.isArray\(buildings\)/);
	assert.match(
		source,
		/\.filter\(\s*\(\s*building\s*\)\s*=>[\s\S]*?building\s*&&[\s\S]*?typeof\s*building\s*===\s*['"]object['"][\s\S]*?!Array\.isArray\(building\)[\s\S]*?building\.id\s*!=\s*null,?\s*\)/,
	);
	assert.match(
		source,
		/name:\s*typeof building\.name === ['"]string['"] && building\.name\.trim\(\)/,
	);
	assert.match(source, /: ['"]축사 이름 미등록['"]/);
	assert.match(
		source,
		/penCount:\s*Number\.isFinite\(Number\(building\.penCount\)\)\s*\?\s*building\.penCount\s*:\s*0/,
	);
	assert.match(
		source,
		/const safeBuildings = normalizeSettingsBuildings\(buildings\);/,
	);
	assert.match(source, /\{safeBuildings\.map\(\(building\) => \{/);
	assert.doesNotMatch(source, /export default function SettingsTab\(\{\s+buildings/);
	assert.doesNotMatch(source, /\{buildings\.map\(\(building\) => \(/);
});

test("settings tab normalizes widget controls and callbacks before rendering", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(source, /function normalizeSettingsWidgetRegistry\(widgets\) \{/);
	assert.match(
		source,
		/Array\.isArray\(widgets\)[\s\S]*?\? widgets\.filter\([\s\S]*?\(widget\) => widget && typeof widget === ["']object["'] && !Array\.isArray\(widget\)[\s\S]*?\)[\s\S]*?: \[\]/,
	);
	assert.match(source, /function normalizeSettingsWidgetVisible\(widgetVisible\) \{/);
	assert.match(
		source,
		/typeof widgetVisible === ["']object["'][\s\S]*?!Array\.isArray\(widgetVisible\)[\s\S]*?\?\s*widgetVisible\s*:\s*\{\}/,
	);
	assert.match(
		source,
		/const safeWidgetRegistry = normalizeSettingsWidgetRegistry\(widgetRegistry\);/,
	);
	assert.match(
		source,
		/const safeWidgetVisible = normalizeSettingsWidgetVisible\(widgetVisible\);/,
	);
	assert.match(
		source,
		/const handleToggleTheme =\s*typeof onToggleTheme === ["']function["'] \? onToggleTheme : \(\) => \{\};/,
	);
	assert.match(
		source,
		/const handleToggleWidget =\s*typeof onToggleWidget === ["']function["'] \? onToggleWidget : \(\) => \{\};/,
	);
	assert.match(source, /onClick=\{handleToggleTheme\}/);
	assert.match(source, /\{safeWidgetRegistry\.length > 0 \? \(/);
	assert.match(source, /\{safeWidgetRegistry\.map\(\(widget\) => \{/);
	assert.match(source, /const isOn = safeWidgetVisible\[widget\.id\] !== false;/);
	assert.match(source, /onClick=\{\(\) => handleToggleWidget\(widget\.id\)\}/);
	assert.doesNotMatch(source, /widgetRegistry\.length > 0/);
	assert.doesNotMatch(source, /widgetRegistry\.map\(\(widget\) => \{/);
	assert.doesNotMatch(source, /widgetVisible\[widget\.id\] !== false/);
	assert.doesNotMatch(source, /onClick=\{onToggleTheme\}/);
	assert.doesNotMatch(source, /onClick=\{\(\) => onToggleWidget\(widget\.id\)\}/);
});

test("settings forms expose explicit labels and invalid state", () => {
	const source = readSource("components/tabs/SettingsTab.js");
	const formSchemaSource = readSource("lib/formSchemas.js");
	const actionValidationSource = readSource("lib/action-validation.mjs");

	assert.match(
		source,
		/<PremiumLabel htmlFor="farm-name">[\s\S]*?농장 이름[\s\S]*?<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="farm-name"[\s\S]*?aria-invalid=\{Boolean\(farmErrors\.name\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="farm-location-select">[\s\S]*?지역 선택 \(자동 입력\)[\s\S]*?<\/PremiumLabel>/,
	);
	assert.match(source, /id="farm-location-select"/);
	assert.match(
		source,
		/<PremiumLabel htmlFor="farm-location">[\s\S]*?지역명[\s\S]*?<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="farm-location"[\s\S]*?aria-invalid=\{Boolean\(farmErrors\.location\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="farm-latitude">[\s\S]*?위도[\s\S]*?<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="farm-latitude"[\s\S]*?aria-invalid=\{Boolean\(farmErrors\.latitude\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="farm-longitude">[\s\S]*?경도[\s\S]*?<\/PremiumLabel>/,
	);
	assert.doesNotMatch(source, /Latitude/);
	assert.doesNotMatch(source, /Longitude/);
	assert.match(
		source,
		/id="farm-longitude"[\s\S]*?aria-invalid=\{Boolean\(farmErrors\.longitude\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="building-name">[\s\S]*?축사 이름[\s\S]*?<\/PremiumLabel>/,
	);
	assert.match(source, /placeholder="축사 이름을 입력해 주세요\."/);
	assert.match(formSchemaSource, /name: requiredText\("축사 이름을 입력해 주세요\.", 40\)/);
	assert.match(actionValidationSource, /name: requiredText\("축사 이름을 입력해 주세요\.", 40\)/);
	assert.doesNotMatch(source, /동 이름/);
	assert.doesNotMatch(formSchemaSource, /동 이름을 입력해 주세요/);
	assert.doesNotMatch(actionValidationSource, /동 이름을 입력해 주세요/);
	assert.match(
		source,
		/id="building-name"[\s\S]*?aria-invalid=\{Boolean\(buildingErrors\.name\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="building-pen-count">[\s\S]*?칸 수[\s\S]*?<\/PremiumLabel>/,
	);
	assert.doesNotMatch(source, /Pen Count/);
	assert.match(
		source,
		/id="building-pen-count"[\s\S]*?aria-invalid=\{Boolean\(buildingErrors\.penCount\)\}/,
	);
});

test("setup quick action brings the building form into view and focus", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(source, /import \{ focusElementSafely \} from ["']@\/lib\/safeFocus["'];/);
	assert.match(source, /const buildingFormRef = useRef\(null\);/);
	assert.match(source, /const buildingNameInputRef = useRef\(null\);/);
	assert.match(source, /const buildingNameRegistration = registerBuilding\("name"\);/);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+if \(!isAdding\) \{\s+return;\s+\}[\s\S]*?const timeoutId = window\.setTimeout\(\(\) => \{[\s\S]*?buildingFormRef\.current\?\.scrollIntoView\(\{\s+behavior: "smooth",\s+block: "start",\s+inline: "nearest",\s+\}\);[\s\S]*?buildingFormRef\.current\?\.scrollIntoView\(\);[\s\S]*?focusElementSafely\(buildingNameInputRef\.current\);[\s\S]*?\}, 0\);[\s\S]*?window\.clearTimeout\(timeoutId\);[\s\S]*?\}, \[isAdding, quickActionIntent\?\.nonce\]\);/,
	);
	assert.match(
		source,
		/<form\s+ref=\{buildingFormRef\}[\s\S]*?onSubmit=\{handleBuildingSubmit\}/,
	);
	assert.match(
		source,
		/id="building-name"[\s\S]*?\{\.\.\.buildingNameRegistration\}[\s\S]*?ref=\{\(element\) => \{\s+buildingNameRegistration\.ref\(element\);\s+buildingNameInputRef\.current = element;\s+\}\}/,
	);
	assert.doesNotMatch(
		source,
		/id="building-name"[\s\S]{0,240}\{\.\.\.registerBuilding\("name"\)\}/,
	);
});

test("settings form validation messages are announced with their controls", () => {
	const source = readSource("components/tabs/SettingsTab.js");
	const fields = [
		["farmErrors", "name", "farm-name-error"],
		["farmErrors", "location", "farm-location-error"],
		["farmErrors", "latitude", "farm-latitude-error"],
		["farmErrors", "longitude", "farm-longitude-error"],
		["buildingErrors", "name", "building-name-error"],
		["buildingErrors", "penCount", "building-pen-count-error"],
	];

	for (const [errorObject, errorPath, errorId] of fields) {
		assert.match(
			source,
			new RegExp(
				`aria-describedby=\\{\\s*${errorObject}\\.${errorPath}\\s*\\?\\s*["']${errorId}["']\\s*:\\s*undefined\\s*\\}`,
			),
		);
		assert.match(
			source,
			new RegExp(`<div\\s+[^>]*id=["']${errorId}["'][^>]*role=["']alert["']`),
		);
	}
});

test("settings building form waits for async saves before re-enabling actions", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(
		source,
		/const \[isSavingBuilding, setIsSavingBuilding\] = useState\(false\)/,
	);
	assert.match(source, /const isMountedRef = useRef\(false\);/);
	assert.match(source, /const buildingSaveInFlightRef = useRef\(false\);/);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+isMountedRef\.current = true;[\s\S]*?return \(\) => \{\s+isMountedRef\.current = false;\s+farmSaveInFlightRef\.current = false;\s+buildingSaveInFlightRef\.current = false;\s+deleteBuildingInFlightRef\.current = false;/,
	);
	assert.match(
		source,
		/if \(buildingSaveInFlightRef\.current\) \{\s+return;\s+\}/,
	);
	assert.match(source, /buildingSaveInFlightRef\.current = true;/);
	assert.match(source, /setIsSavingBuilding\(true\);/);
	assert.match(
		source,
		/const handleCreateBuilding =\s*typeof onCreateBuilding === ["']function["'] \? onCreateBuilding : async \(\) => false;/,
	);
	assert.match(source, /const saved = await handleCreateBuilding\(values\);/);
	assert.doesNotMatch(source, /const saved = await onCreateBuilding\(values\);/);
	assert.match(
		source,
		/if \(!saved \|\| !isMountedRef\.current\) \{\s+return;\s+\}/,
	);
	assert.doesNotMatch(source, /if \(!saved\) \{\s+return;\s+\}/);
	assert.match(
		source,
		/finally \{\s+buildingSaveInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setIsSavingBuilding\(false\);/,
	);
	assert.doesNotMatch(
		source,
		/finally \{\s+buildingSaveInFlightRef\.current = false;\s+setIsSavingBuilding\(false\);/,
	);
	assert.match(
		source,
		/const buildingSubmitButtonLabel = isSavingBuilding\s*\?\s*['"]축사 등록 중['"]\s*:\s*['"]축사 등록['"];/,
	);
	assert.match(
		source,
		/const buildingSubmitButtonText = isSavingBuilding\s*\?\s*['"]축사 등록 중\.\.\.['"]\s*:\s*['"]축사 등록['"];/,
	);
	assert.match(source, /const buildingAddFormButtonLabel = isSavingBuilding/);
	assert.match(source, /축사 저장 중에는 등록 창을 닫을 수 없습니다/);
	assert.match(source, /축사 등록 취소/);
	assert.match(source, /축사 등록 창 열기/);
	assert.match(source, /const buildingAddFormButtonText = isSavingBuilding/);
	assert.match(source, /축사 저장 중\.\.\./);
	assert.match(source, /축사 등록 취소/);
	assert.match(source, /: "축사 등록";/);
	assert.match(source, /축사 관리/);
	assert.match(source, /새 축사 등록/);
	assert.doesNotMatch(source, /축사 동 관리/);
	assert.doesNotMatch(source, /새 축사 동 등록/);
	assert.doesNotMatch(
		source,
		/const buildingAddFormButtonText = isSavingBuilding[\s\S]*?\? "축사 저장 중\.\.\."[\s\S]*?: isAdding[\s\S]*?\? "취소"[\s\S]*?: "\+ 동 추가";/,
	);
	assert.doesNotMatch(
		source,
		/const buildingAddFormButtonText = isSavingBuilding[\s\S]*?: isAdding[\s\S]*?\? "취소"/,
	);
	assert.doesNotMatch(source, /"\+ 동 추가"/);
	assert.match(
		source,
		/size="sm"\s+disabled=\{isSavingBuilding\}\s+aria-busy=\{isSavingBuilding\}\s+aria-label=\{buildingAddFormButtonLabel\}\s+title=\{buildingAddFormButtonLabel\}/,
	);
	assert.match(source, /\{buildingAddFormButtonText\}/);
	assert.match(
		source,
		/type="submit"\s+variant="primary"\s+disabled=\{isSavingBuilding\}\s+aria-busy=\{isSavingBuilding\}\s+aria-label=\{buildingSubmitButtonLabel\}\s+title=\{buildingSubmitButtonLabel\}/,
	);
	assert.match(source, /\{buildingSubmitButtonText\}/);
	assert.doesNotMatch(source, /\{isSavingBuilding \? ["']축사 등록 중\.\.\.["'] : ["']등록하기["']\}/);
	assert.doesNotMatch(source, /축사 등록하기/);
});

test("settings farm form waits for async saves before re-enabling submit", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(
		source,
		/const \[isSavingFarm, setIsSavingFarm\] = useState\(false\)/,
	);
	assert.match(source, /const isMountedRef = useRef\(false\);/);
	assert.match(source, /const farmSaveInFlightRef = useRef\(false\);/);
	assert.match(source, /const submitFarmSettings = async \(values\) => \{/);
	assert.match(source, /if \(farmSaveInFlightRef\.current\) \{\s+return;\s+\}/);
	assert.match(source, /farmSaveInFlightRef\.current = true;/);
	assert.match(source, /setIsSavingFarm\(true\);/);
	assert.match(
		source,
		/const handleUpdateFarmSettings =\s*typeof onUpdateFarmSettings === ["']function["'][\s\S]*?\? onUpdateFarmSettings[\s\S]*?: async \(\) => false;/,
	);
	assert.match(source, /await handleUpdateFarmSettings\(values\);/);
	assert.doesNotMatch(source, /await onUpdateFarmSettings\(values\);/);
	assert.match(
		source,
		/finally \{\s+farmSaveInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setIsSavingFarm\(false\);/,
	);
	assert.doesNotMatch(
		source,
		/finally \{\s+farmSaveInFlightRef\.current = false;\s+setIsSavingFarm\(false\);/,
	);
	assert.match(
		source,
		/const farmSubmitButtonLabel = isSavingFarm\s*\?\s*['"]농장 정보 저장 중['"]\s*:\s*['"]농장 정보 저장['"];/,
	);
	assert.match(
		source,
		/const farmSubmitButtonText = isSavingFarm\s*\?\s*['"]농장 정보 저장 중\.\.\.['"]\s*:\s*['"]농장 정보 저장['"];/,
	);
	assert.doesNotMatch(source, /농장 정보 저장하기/);
	assert.match(
		source,
		/type="submit"\s+disabled=\{isSavingFarm\}\s+aria-busy=\{isSavingFarm\}\s+aria-label=\{farmSubmitButtonLabel\}\s+title=\{farmSubmitButtonLabel\}/,
	);
	assert.match(source, /\{farmSubmitButtonText\}/);
});

test("settings farm form locks editable fields while saving", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(
		source,
		/const handleLocationSelect = \(event\) => \{\s+if \(farmSaveInFlightRef\.current \|\| isSavingFarm\) \{\s+return;\s+\}/,
	);
	assert.match(source, /id="farm-name"[\s\S]*?disabled=\{isSavingFarm\}/);
	assert.match(
		source,
		/id="farm-location-select"[\s\S]*?disabled=\{isSavingFarm\}/,
	);
	assert.match(source, /id="farm-location"[\s\S]*?disabled=\{isSavingFarm\}/);
	assert.match(source, /id="farm-latitude"[\s\S]*?disabled=\{isSavingFarm\}/);
	assert.match(source, /id="farm-longitude"[\s\S]*?disabled=\{isSavingFarm\}/);
});

test("settings building delete action waits for async deletes before re-enabling the row action", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(
		source,
		/import \{ useEffect, useRef, useState \} from ['"]react['"];/,
	);
	assert.match(
		source,
		/const \[deletingBuildingId, setDeletingBuildingId\] = useState\(null\)/,
	);
	assert.match(source, /const deleteBuildingInFlightRef = useRef\(false\);/);
	assert.match(
		source,
		/if \(deleteBuildingInFlightRef\.current\) \{\s+return;\s+\}/,
	);
	assert.match(source, /deleteBuildingInFlightRef\.current = true;/);
	assert.match(source, /title: `\$\{name\} 축사를 삭제할까요\?`/);
	assert.doesNotMatch(source, /title: `\$\{name\} 동을 삭제할까요\?`/);
	assert.match(
		source,
		/if \(!shouldDelete \|\| !isMountedRef\.current\) \{\s+deleteBuildingInFlightRef\.current = false;\s+return;\s+\}/,
	);
	assert.doesNotMatch(
		source,
		/if \(!shouldDelete\) \{\s+deleteBuildingInFlightRef\.current = false;\s+return;\s+\}/,
	);
	assert.match(source, /confirmLabel: "축사 삭제"/);
	assert.match(source, /cancelLabel: "축사 삭제 취소"/);
	assert.doesNotMatch(
		source,
		/confirmLabel: "삭제"[\s\S]*?cancelLabel: "취소"/,
	);
	assert.match(source, /setDeletingBuildingId\(id\);/);
	assert.match(
		source,
		/const handleDeleteBuildingAction =\s*typeof onDeleteBuilding === ["']function["'] \? onDeleteBuilding : async \(\) => false;/,
	);
	assert.match(source, /await handleDeleteBuildingAction\(id\);/);
	assert.doesNotMatch(source, /await onDeleteBuilding\(id\);/);
	assert.match(
		source,
		/finally \{\s+deleteBuildingInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setDeletingBuildingId\(null\);/,
	);
	assert.doesNotMatch(source, /finally \{\s+setDeletingBuildingId\(null\);/);
	assert.doesNotMatch(
		source,
		/setDeletingBuildingId\(null\);\s+deleteBuildingInFlightRef\.current = false;/,
	);
	assert.match(source, /disabled=\{isDeletingBuilding\}/);
	assert.match(source, /aria-busy=\{isDeletingBuilding\}/);
});
