import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import test from 'node:test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, '..');
const SCAN_ROOTS = ['app', 'components'];
const SOURCE_EXTENSIONS = new Set(['.js', '.jsx', '.tsx']);

function listSourceFiles(relativeDir) {
  const absoluteDir = path.join(SRC_ROOT, relativeDir);
  const files = [];

  for (const entry of readdirSync(absoluteDir)) {
    const absolutePath = path.join(absoluteDir, entry);
    const relativePath = path.join(relativeDir, entry);
    const stats = statSync(absolutePath);

    if (stats.isDirectory()) {
      files.push(...listSourceFiles(relativePath));
      continue;
    }

    if (SOURCE_EXTENSIONS.has(path.extname(entry))) {
      files.push(relativePath);
    }
  }

  return files;
}

function getLineNumber(source, offset) {
  return source.slice(0, offset).split('\n').length;
}

function findButtonTagsWithoutType(relativePath) {
  const source = readFileSync(path.join(SRC_ROOT, relativePath), 'utf8');
  const matches = source.matchAll(/<button\b(?:(?!<\/button>).)*?>/gs);
  const missingType = [];

  for (const match of matches) {
    const tag = match[0];

    if (!/\btype\s*=/.test(tag)) {
      missingType.push(`${relativePath}:${getLineNumber(source, match.index)}`);
    }
  }

  return missingType;
}

test('plain button elements declare an explicit type', () => {
  const sourceFiles = SCAN_ROOTS.flatMap(listSourceFiles);
  const missingType = sourceFiles.flatMap(findButtonTagsWithoutType);

  assert.deepEqual(missingType, []);
});
