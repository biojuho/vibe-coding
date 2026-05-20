import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, '..');

function readSource(relativePath) {
  return readFileSync(path.join(SRC_ROOT, relativePath), 'utf8');
}

test('settings tab switch controls expose Korean accessible names and checked state', () => {
  const source = readSource('components/tabs/SettingsTab.js');

  assert.match(source, /role="switch"/);
  assert.match(source, /aria-checked=\{isDark\}/);
  assert.match(source, /aria-label=\{isDark \? '다크모드 끄기' : '다크모드 켜기'\}/);
  assert.match(source, /title=\{isDark \? '다크모드 끄기' : '다크모드 켜기'\}/);
  assert.match(source, /aria-checked=\{isOn\}/);
  assert.match(source, /aria-label=\{`\$\{widget\.label\} 위젯 \$\{isOn \? '숨기기' : '보이기'\}`\}/);
  assert.match(source, /title=\{`\$\{widget\.label\} 위젯 \$\{isOn \? '숨기기' : '보이기'\}`\}/);
  assert.match(source, /<Settings size=\{20\} className="text-\[color:var\(--color-text\)\]" aria-hidden="true" \/>/);
  assert.match(source, /<MapPin size=\{16\} aria-hidden="true" \/>/);
  assert.doesNotMatch(source, /aria-label="Theme"/);
  assert.doesNotMatch(source, /aria-label="Widget"/);
});

test('settings tab decorative text icons are hidden from assistive tech', () => {
  const source = readSource('components/tabs/SettingsTab.js');

  assert.match(source, /<span aria-hidden="true" style=\{\{ fontSize: '20px' \}\}>\{isDark \? '야' : '주'\}<\/span>/);
  assert.match(source, /<span aria-hidden="true" style=\{\{ fontSize: '18px' \}\}>위젯<\/span>/);
  assert.match(source, /<span aria-hidden="true" style=\{\{ fontSize: '16px' \}\}>\{widget\.icon\}<\/span>/);
});

test('settings tab building delete buttons identify the target building', () => {
  const source = readSource('components/tabs/SettingsTab.js');

  assert.match(source, /aria-label=\{`\$\{building\.name\} 동 삭제`\}/);
  assert.match(source, /title=\{`\$\{building\.name\} 동 삭제`\}/);
});

test('settings forms expose explicit labels and invalid state', () => {
  const source = readSource('components/tabs/SettingsTab.js');

  assert.match(source, /<PremiumLabel htmlFor="farm-name">[\s\S]*?농장 이름[\s\S]*?<\/PremiumLabel>/);
  assert.match(source, /id="farm-name"[\s\S]*?aria-invalid=\{Boolean\(farmErrors\.name\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="farm-location-select">[\s\S]*?지역 선택 \(자동 입력\)[\s\S]*?<\/PremiumLabel>/);
  assert.match(source, /id="farm-location-select"/);
  assert.match(source, /<PremiumLabel htmlFor="farm-location">[\s\S]*?지역명[\s\S]*?<\/PremiumLabel>/);
  assert.match(source, /id="farm-location"[\s\S]*?aria-invalid=\{Boolean\(farmErrors\.location\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="farm-latitude">[\s\S]*?위도 \(Latitude\)[\s\S]*?<\/PremiumLabel>/);
  assert.match(source, /id="farm-latitude"[\s\S]*?aria-invalid=\{Boolean\(farmErrors\.latitude\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="farm-longitude">[\s\S]*?경도 \(Longitude\)[\s\S]*?<\/PremiumLabel>/);
  assert.match(source, /id="farm-longitude"[\s\S]*?aria-invalid=\{Boolean\(farmErrors\.longitude\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="building-name">[\s\S]*?동 이름[\s\S]*?<\/PremiumLabel>/);
  assert.match(source, /id="building-name"[\s\S]*?aria-invalid=\{Boolean\(buildingErrors\.name\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="building-pen-count">[\s\S]*?칸 수 \(Pen Count\)[\s\S]*?<\/PremiumLabel>/);
  assert.match(source, /id="building-pen-count"[\s\S]*?aria-invalid=\{Boolean\(buildingErrors\.penCount\)\}/);
});

test('settings form validation messages are announced with their controls', () => {
  const source = readSource('components/tabs/SettingsTab.js');
  const fields = [
    ['farmErrors', 'name', 'farm-name-error'],
    ['farmErrors', 'location', 'farm-location-error'],
    ['farmErrors', 'latitude', 'farm-latitude-error'],
    ['farmErrors', 'longitude', 'farm-longitude-error'],
    ['buildingErrors', 'name', 'building-name-error'],
    ['buildingErrors', 'penCount', 'building-pen-count-error'],
  ];

  for (const [errorObject, errorPath, errorId] of fields) {
    assert.match(
      source,
      new RegExp(`aria-describedby=\\{${errorObject}\\.${errorPath} \\? "${errorId}" : undefined\\}`),
    );
    assert.match(source, new RegExp(`<div id="${errorId}" role="alert"`));
  }
});

test('settings building form waits for async saves before re-enabling actions', () => {
  const source = readSource('components/tabs/SettingsTab.js');

  assert.match(source, /const \[isSavingBuilding, setIsSavingBuilding\] = useState\(false\)/);
  assert.match(source, /setIsSavingBuilding\(true\);/);
  assert.match(source, /const saved = await onCreateBuilding\(values\);/);
  assert.match(source, /finally \{\s+setIsSavingBuilding\(false\);/);
  assert.match(source, /size="sm"\s+disabled=\{isSavingBuilding\}/);
  assert.match(source, /type="submit"\s+variant="primary"\s+disabled=\{isSavingBuilding\}\s+aria-busy=\{isSavingBuilding\}/);
});

test('settings farm form waits for async saves before re-enabling submit', () => {
  const source = readSource('components/tabs/SettingsTab.js');

  assert.match(source, /const \[isSavingFarm, setIsSavingFarm\] = useState\(false\)/);
  assert.match(source, /const submitFarmSettings = async \(values\) => \{/);
  assert.match(source, /setIsSavingFarm\(true\);/);
  assert.match(source, /await onUpdateFarmSettings\(values\);/);
  assert.match(source, /finally \{\s+setIsSavingFarm\(false\);/);
  assert.match(source, /type="submit"\s+disabled=\{isSavingFarm\}\s+aria-busy=\{isSavingFarm\}/);
});

test('settings building delete action waits for async deletes before re-enabling the row action', () => {
  const source = readSource('components/tabs/SettingsTab.js');

  assert.match(source, /const \[deletingBuildingId, setDeletingBuildingId\] = useState\(null\)/);
  assert.match(source, /if \(deletingBuildingId\) \{\s+return;\s+\}/);
  assert.match(source, /setDeletingBuildingId\(id\);/);
  assert.match(source, /await onDeleteBuilding\(id\);/);
  assert.match(source, /finally \{\s+setDeletingBuildingId\(null\);/);
  assert.match(source, /disabled=\{deletingBuildingId === building\.id\}/);
  assert.match(source, /aria-busy=\{deletingBuildingId === building\.id\}/);
});
