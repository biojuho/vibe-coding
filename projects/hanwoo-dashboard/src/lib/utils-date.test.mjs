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

test('date utility calculations use a fresh or injected current date', () => {
  const utilsSource = readSource('lib/utils.js');
  const constantsSource = readSource('lib/constants.js');

  assert.match(utilsSource, /const DAY_MS = 86400000;/);
  assert.match(utilsSource, /function toDate\(value\)/);
  assert.match(utilsSource, /export function getMonthAge\(birthDate, now = new Date\(\)\)/);
  assert.match(utilsSource, /export function getNextEstrusDate\(lastEstrus, now = new Date\(\)\)/);
  assert.match(utilsSource, /export function getDaysUntilEstrus\(lastEstrus, now = new Date\(\)\)/);
  assert.match(utilsSource, /const next = getNextEstrusDate\(lastEstrus, today\);/);
  assert.match(utilsSource, /export function isEstrusAlert\(lastEstrus, now = new Date\(\)\)/);
  assert.match(utilsSource, /getDaysUntilEstrus\(lastEstrus, now\)/);
  assert.match(utilsSource, /export function getDaysUntilCalving\(pregnancyDate, now = new Date\(\)\)/);
  assert.match(utilsSource, /Math\.ceil\(\(calvingDate - today\) \/ DAY_MS\)/);
  assert.match(utilsSource, /export function isCalvingAlert\(pregnancyDate, now = new Date\(\)\)/);
  assert.match(utilsSource, /getDaysUntilCalving\(pregnancyDate, now\)/);
  assert.doesNotMatch(utilsSource, /TODAY/);
  assert.doesNotMatch(constantsSource, /TODAY = new Date\(\)/);
});
