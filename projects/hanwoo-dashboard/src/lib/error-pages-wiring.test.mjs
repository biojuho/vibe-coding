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

test('not-found page is a server component with a route home and title metadata', () => {
  const source = readSource('app/not-found.js');

  assert.match(source, /export default function NotFound/);
  assert.doesNotMatch(source, /'use client'/);
  assert.match(source, /export const metadata/);
  assert.match(source, /href="\/"/);
  assert.match(source, /Joolife 한우 운영/);
  assert.match(source, /페이지를 찾을 수 없어요/);
  assert.doesNotMatch(source, /Joolife Operations/);
});

test('route error boundary is a client component exposing retry and home actions', () => {
  const source = readSource('app/error.js');

  assert.match(source, /^'use client';/);
  assert.match(source, /export default function RouteError\(\{ error, reset \}\)/);
  assert.match(source, /onClick=\{\(\) => reset\(\)\}/);
  assert.match(source, /href="\/"/);
  assert.match(source, /console\.error/);
  assert.match(source, /Joolife 한우 운영/);
  assert.doesNotMatch(source, /Joolife Operations/);
});

test('global error boundary renders its own html/body and a reset action', () => {
  const source = readSource('app/global-error.js');

  assert.match(source, /^'use client';/);
  assert.match(source, /export default function GlobalError\(\{ error, reset \}\)/);
  assert.match(source, /<html lang="ko">/);
  assert.match(source, /<body/);
  assert.match(source, /onClick=\{\(\) => reset\(\)\}/);
  assert.match(source, /Joolife 한우 운영/);
  assert.doesNotMatch(source, /Joolife Operations/);
});

test('login page operator eyebrow uses Korean product copy', () => {
  const source = readSource('app/login/page.js');

  assert.match(source, /Joolife 한우 운영/);
  assert.doesNotMatch(source, /Joolife Operations/);
});
