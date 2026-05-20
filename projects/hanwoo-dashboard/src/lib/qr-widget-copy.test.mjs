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

test('qr widget print action uses Korean operator copy and icon button', () => {
  const source = readSource('components/widgets/QRCodeWidget.js');

  assert.match(source, /QR 출력/);
  assert.match(source, /QR 라벨 인쇄/);
  assert.match(source, /import \{ Printer \} from 'lucide-react'/);
  assert.doesNotMatch(source, /QR Code/);
  assert.doesNotMatch(source, /🖨️/);
});
