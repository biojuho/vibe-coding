import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

// Resolve project root from this file's location:
// src/lib/dashboard/use-cache-config.test.mjs -> project root (3 levels up)
const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../../..');

// ============================================================
// A-3: use cache configuration & integration smoke tests
//
// These are static analysis tests that verify wiring by reading
// source files — they do NOT require the Next.js runtime.
// ============================================================

describe('use cache — configuration', () => {
  it('next.config.mjs enables cacheComponents: true', () => {
    const configContent = readFileSync(
      resolve(ROOT, 'next.config.mjs'),
      'utf-8',
    );
    assert.ok(
      configContent.includes('cacheComponents: true'),
      'cacheComponents must be enabled in next.config.mjs',
    );
  });
});

describe('use cache — cached-queries module', () => {
  it('cached-queries.js declares "use cache" directive', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/lib/dashboard/cached-queries.js'),
      'utf-8',
    );
    assert.ok(
      content.trimStart().startsWith("'use cache'"),
      'cached-queries.js must start with "use cache" directive',
    );
  });

  it('declares getCachedDashboardSummary function', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/lib/dashboard/cached-queries.js'),
      'utf-8',
    );
    assert.ok(
      content.includes('async function getCachedDashboardSummary'),
      'must export getCachedDashboardSummary',
    );
  });

  it('declares getCachedCattleList function', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/lib/dashboard/cached-queries.js'),
      'utf-8',
    );
    assert.ok(
      content.includes('async function getCachedCattleList'),
      'must export getCachedCattleList',
    );
  });

  it('declares getCachedSalesList function', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/lib/dashboard/cached-queries.js'),
      'utf-8',
    );
    assert.ok(
      content.includes('async function getCachedSalesList'),
      'must export getCachedSalesList',
    );
  });

  it('uses cacheTag for invalidation targeting', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/lib/dashboard/cached-queries.js'),
      'utf-8',
    );
    assert.ok(content.includes("cacheTag('dashboard-summary')"), 'must tag dashboard-summary');
    assert.ok(content.includes("cacheTag('cattle-list')"), 'must tag cattle-list');
    assert.ok(content.includes("cacheTag('sales-list')"), 'must tag sales-list');
  });
});

describe('use cache — revalidateTag integration', () => {
  it('_helpers.js imports revalidateTag from next/cache', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/lib/actions/_helpers.js'),
      'utf-8',
    );
    assert.ok(
      content.includes("revalidateTag") && content.includes("next/cache"),
      '_helpers.js must import revalidateTag from next/cache',
    );
  });

  it('invalidates dashboard-summary tag', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/lib/actions/_helpers.js'),
      'utf-8',
    );
    assert.ok(
      content.includes("revalidateTag('dashboard-summary')"),
      '_helpers.js must call revalidateTag for dashboard-summary',
    );
  });

  it('invalidates cattle-list tag on cattleListPages mutation', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/lib/actions/_helpers.js'),
      'utf-8',
    );
    assert.ok(
      content.includes("revalidateTag('cattle-list')"),
      '_helpers.js must call revalidateTag for cattle-list',
    );
  });

  it('invalidates sales-list tag on salesListPages mutation', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/lib/actions/_helpers.js'),
      'utf-8',
    );
    assert.ok(
      content.includes("revalidateTag('sales-list')"),
      '_helpers.js must call revalidateTag for sales-list',
    );
  });
});

describe('use cache — page.js migration', () => {
  it('page.js does NOT use force-dynamic', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/app/page.js'),
      'utf-8',
    );
    assert.ok(
      !content.includes('force-dynamic'),
      'page.js must NOT contain force-dynamic after migration',
    );
  });

  it('page.js imports cached query wrappers', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/app/page.js'),
      'utf-8',
    );
    assert.ok(
      content.includes('getCachedDashboardSummary'),
      'page.js must use getCachedDashboardSummary',
    );
    assert.ok(
      content.includes('getCachedCattleList'),
      'page.js must use getCachedCattleList',
    );
    assert.ok(
      content.includes('getCachedSalesList'),
      'page.js must use getCachedSalesList',
    );
  });

  it('page.js does NOT directly import prisma', () => {
    const content = readFileSync(
      resolve(ROOT, 'src/app/page.js'),
      'utf-8',
    );
    assert.ok(
      !content.includes("from '@/lib/db'"),
      'page.js should not directly import prisma client',
    );
  });
});
