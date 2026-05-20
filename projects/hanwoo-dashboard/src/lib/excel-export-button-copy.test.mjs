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

test('excel export button uses a real decorative download icon', () => {
  const source = readSource('components/widgets/ExcelExportButton.js');

  assert.match(source, /import \{ Download \} from 'lucide-react';/);
  assert.match(source, /<Download size=\{14\} className="text-\[#1D6F42\]" aria-hidden="true" \/>/);
  assert.match(source, /aria-busy=\{isPreparing\}/);
  assert.match(source, /엑셀 다운로드/);
  assert.match(source, /내보내기 파일을 만들지 못했습니다/);
  assert.doesNotMatch(source, /<span className="text-\[#1D6F42\] text-\[14px\]">\?<\/span>/);
  assert.doesNotMatch(source, /description: error instanceof Error \? error\.message/);
});
