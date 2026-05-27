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

test("excel export button uses a real decorative download icon", () => {
	const source = readSource("components/widgets/ExcelExportButton.js");

	assert.match(source, /import \{ useRef, useState \} from ["']react["'];/);
	assert.match(source, /import \{ Download \} from ["']lucide-react["'];/);
	assert.match(
		source,
		/<Download size=\{14\} className="text-\[#1D6F42\]" aria-hidden="true" \/>/,
	);
	assert.match(source, /aria-busy=\{isPreparing\}/);
	assert.match(
		source,
		/aria-label=\{\s*isPreparing \? ["']개체 엑셀 다운로드 준비 중["'] : ["']개체 엑셀 다운로드["']\s*\}/,
	);
	assert.match(
		source,
		/title=\{\s*isPreparing \? ["']개체 엑셀 다운로드 준비 중["'] : ["']개체 엑셀 다운로드["']\s*\}/,
	);
	assert.match(source, /개체 엑셀 다운로드/);
	assert.match(
		source,
		/\{isPreparing \? ["']개체 엑셀 다운로드 준비 중\.\.\.["'] : ["']개체 엑셀 다운로드["']\}/,
	);
	assert.doesNotMatch(source, /\? ["']엑셀 다운로드 준비 중["'] : ["']엑셀 다운로드["']/);
	assert.doesNotMatch(source, /\{isPreparing \? ["']엑셀 준비 중\.\.\.["'] : ["']엑셀 다운로드["']\}/);
	assert.match(source, /내보내기 파일을 만들지 못했습니다/);
	assert.match(source, /다운로드할 개체 목록이 없습니다/);
	assert.doesNotMatch(source, /다운로드할 개체 데이터가 없습니다/);
	assert.doesNotMatch(
		source,
		/<span className="text-\[#1D6F42\] text-\[14px\]">\?<\/span>/,
	);
	assert.doesNotMatch(
		source,
		/description: error instanceof Error \? error\.message/,
	);
});

test("excel export button blocks duplicate downloads while the export is preparing", () => {
	const source = readSource("components/widgets/ExcelExportButton.js");

	assert.match(source, /const preparingRef = useRef\(false\);/);
	assert.match(source, /if \(preparingRef\.current\) return;/);
	assert.match(source, /preparingRef\.current = true;/);
	assert.match(source, /const rows =[\s\S]*?await resolveCattleList\(\)/);
	assert.match(
		source,
		/finally \{[\s\S]*?preparingRef\.current = false;\s+setIsPreparing\(false\);/,
	);
	assert.match(source, /disabled=\{isPreparing\}/);
	assert.match(source, /aria-busy=\{isPreparing\}/);
});

test("excel export button always cleans up temporary download resources", () => {
	const source = readSource("components/widgets/ExcelExportButton.js");

	assert.match(source, /function removeTemporaryDownloadLink\(downloadLink\) \{/);
	assert.match(source, /function revokeTemporaryDownloadUrl\(downloadUrl\) \{/);
	assert.match(source, /if \(!downloadLink\?\.parentNode\) \{\s*return;\s*\}/);
	assert.match(source, /if \(!downloadUrl\) \{\s*return;\s*\}/);
	assert.match(
		source,
		/try \{\s*downloadLink\.parentNode\.removeChild\(downloadLink\);[\s\S]*?\} catch \{\}/,
	);
	assert.match(
		source,
		/try \{\s*URL\.revokeObjectURL\(downloadUrl\);[\s\S]*?\} catch \{\}/,
	);
	assert.match(source, /let downloadUrl = null;/);
	assert.match(source, /let downloadLink = null;/);
	assert.match(source, /downloadUrl = URL\.createObjectURL\(blob\);/);
	assert.match(source, /downloadLink = document\.createElement\("a"\);/);
	assert.match(source, /document\.body\.appendChild\(downloadLink\);/);
	assert.match(source, /downloadLink\.click\(\);/);
	assert.match(
		source,
		/finally \{[\s\S]*?removeTemporaryDownloadLink\(downloadLink\);[\s\S]*?revokeTemporaryDownloadUrl\(downloadUrl\);[\s\S]*?preparingRef\.current = false;/,
	);
	assert.doesNotMatch(source, /URL\.revokeObjectURL\(url\);/);
	assert.doesNotMatch(source, /document\.body\.removeChild\(link\);/);
	assert.doesNotMatch(source, /finally \{[\s\S]*?downloadLink\.parentNode\.removeChild\(downloadLink\);/);
	assert.doesNotMatch(source, /finally \{[\s\S]*?URL\.revokeObjectURL\(downloadUrl\);/);
});
