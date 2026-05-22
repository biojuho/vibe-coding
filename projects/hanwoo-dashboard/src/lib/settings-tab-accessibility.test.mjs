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
	const hookSource = readSource("lib/hooks/useWidgetSettings.js");

	assert.match(
		dashboardSource,
		/import\s*\{\s*[\s\S]*?useWidgetSettings[\s\S]*?\}\s*from\s*['"]@\/lib\/hooks\/useWidgetSettings['"];?/,
	);
	assert.doesNotMatch(dashboardSource, /const WIDGET_REGISTRY = \[/);
	assert.match(hookSource, /label:\s*['"]날씨 \/ THI['"]/);
	assert.match(hookSource, /label:\s*['"]시세 정보['"]/);
	assert.match(hookSource, /label:\s*['"]알림 \(발정\/분만\)['"]/);
	assert.match(hookSource, /label:\s*['"]경영 분석 차트['"]/);
	assert.match(hookSource, /label:\s*['"]출하 수익성 예측['"]/);
	assert.match(hookSource, /label:\s*['"]핵심 통계['"]/);
	assert.doesNotMatch(hookSource, /[筌욃첎쳸疫]/);
});

test("settings tab building delete buttons identify the target building", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(source, /aria-label=\{`\$\{building\.name\} 동 삭제`\}/);
	assert.match(source, /title=\{`\$\{building\.name\} 동 삭제`\}/);
});

test("settings tab normalizes malformed building payloads before rendering", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(source, /function normalizeSettingsBuildings\(buildings\) \{/);
	assert.match(source, /Array\.isArray\(buildings\)/);
	assert.match(
		source,
		/\.filter\(\s*\(\s*building\s*\)\s*=>\s*building\s*&&\s*typeof\s*building\s*===\s*['"]object['"]\s*&&\s*building\.id\s*!=\s*null,?\s*\)/,
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
		/const safeBuildings = useMemo\(\s*\(\s*\)\s*=>\s*normalizeSettingsBuildings\(buildings\),\s*\[buildings\],?\s*\);/,
	);
	assert.match(source, /\{safeBuildings\.map\(\(building\) => \(/);
	assert.doesNotMatch(source, /\{buildings\.map\(\(building\) => \(/);
});

test("settings forms expose explicit labels and invalid state", () => {
	const source = readSource("components/tabs/SettingsTab.js");

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
		/<PremiumLabel htmlFor="farm-latitude">[\s\S]*?위도 \(Latitude\)[\s\S]*?<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="farm-latitude"[\s\S]*?aria-invalid=\{Boolean\(farmErrors\.latitude\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="farm-longitude">[\s\S]*?경도 \(Longitude\)[\s\S]*?<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="farm-longitude"[\s\S]*?aria-invalid=\{Boolean\(farmErrors\.longitude\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="building-name">[\s\S]*?동 이름[\s\S]*?<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="building-name"[\s\S]*?aria-invalid=\{Boolean\(buildingErrors\.name\)\}/,
	);
	assert.match(
		source,
		/<PremiumLabel htmlFor="building-pen-count">[\s\S]*?칸 수 \(Pen Count\)[\s\S]*?<\/PremiumLabel>/,
	);
	assert.match(
		source,
		/id="building-pen-count"[\s\S]*?aria-invalid=\{Boolean\(buildingErrors\.penCount\)\}/,
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
	assert.match(source, /const buildingSaveInFlightRef = useRef\(false\);/);
	assert.match(
		source,
		/if \(buildingSaveInFlightRef\.current\) \{\s+return;\s+\}/,
	);
	assert.match(source, /buildingSaveInFlightRef\.current = true;/);
	assert.match(source, /setIsSavingBuilding\(true\);/);
	assert.match(source, /const saved = await onCreateBuilding\(values\);/);
	assert.match(
		source,
		/finally \{\s+buildingSaveInFlightRef\.current = false;\s+setIsSavingBuilding\(false\);/,
	);
	assert.match(
		source,
		/const buildingSubmitButtonLabel = isSavingBuilding\s*\?\s*['"]축사 등록 중['"]\s*:\s*['"]축사 등록하기['"];/,
	);
	assert.match(source, /size="sm"\s+disabled=\{isSavingBuilding\}/);
	assert.match(
		source,
		/type="submit"\s+variant="primary"\s+disabled=\{isSavingBuilding\}\s+aria-busy=\{isSavingBuilding\}\s+aria-label=\{buildingSubmitButtonLabel\}\s+title=\{buildingSubmitButtonLabel\}/,
	);
});

test("settings farm form waits for async saves before re-enabling submit", () => {
	const source = readSource("components/tabs/SettingsTab.js");

	assert.match(
		source,
		/const \[isSavingFarm, setIsSavingFarm\] = useState\(false\)/,
	);
	assert.match(source, /const farmSaveInFlightRef = useRef\(false\);/);
	assert.match(source, /const submitFarmSettings = async \(values\) => \{/);
	assert.match(source, /if \(farmSaveInFlightRef\.current\) \{\s+return;\s+\}/);
	assert.match(source, /farmSaveInFlightRef\.current = true;/);
	assert.match(source, /setIsSavingFarm\(true\);/);
	assert.match(source, /await onUpdateFarmSettings\(values\);/);
	assert.match(
		source,
		/finally \{\s+farmSaveInFlightRef\.current = false;\s+setIsSavingFarm\(false\);/,
	);
	assert.match(
		source,
		/const farmSubmitButtonLabel = isSavingFarm\s*\?\s*['"]농장 정보 저장 중['"]\s*:\s*['"]농장 정보 저장하기['"];/,
	);
	assert.match(
		source,
		/type="submit"\s+disabled=\{isSavingFarm\}\s+aria-busy=\{isSavingFarm\}\s+aria-label=\{farmSubmitButtonLabel\}\s+title=\{farmSubmitButtonLabel\}/,
	);
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
		/import \{ useEffect, useMemo, useRef, useState \} from ['"]react['"];/,
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
	assert.match(
		source,
		/if \(!shouldDelete\) \{\s+deleteBuildingInFlightRef\.current = false;\s+return;\s+\}/,
	);
	assert.match(source, /setDeletingBuildingId\(id\);/);
	assert.match(source, /await onDeleteBuilding\(id\);/);
	assert.match(source, /finally \{\s+setDeletingBuildingId\(null\);/);
	assert.match(
		source,
		/setDeletingBuildingId\(null\);\s+deleteBuildingInFlightRef\.current = false;/,
	);
	assert.match(source, /disabled=\{deletingBuildingId === building\.id\}/);
	assert.match(source, /aria-busy=\{deletingBuildingId === building\.id\}/);
});
