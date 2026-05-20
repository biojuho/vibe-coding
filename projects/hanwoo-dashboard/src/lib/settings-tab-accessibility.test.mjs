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
