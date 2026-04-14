import assert from 'node:assert/strict';
import test from 'node:test';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const SRC_ROOT = path.join(PROJECT_ROOT, 'src');

const ALIAS_PREFIX = '@/';
const ALIAS_TARGET = SRC_ROOT;
const RESOLVE_EXTS = ['.mjs', '.js', '.jsx', '.ts', '.tsx', '.json'];
const IGNORED_SOURCE_EXTS = new Set([
  '.css', '.scss', '.sass', '.less',
  '.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico',
  '.woff', '.woff2', '.ttf', '.otf',
  '.md', '.txt',
]);
const SCAN_ROOTS = [
  path.join(SRC_ROOT, 'components'),
  path.join(SRC_ROOT, 'app'),
];
const SKIP_NAMES = new Set(['node_modules', '.next', '.turbo', '__snapshots__']);

function walk(dir, out = []) {
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const entry of entries) {
    if (SKIP_NAMES.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, out);
    } else if (
      /\.(m?jsx?|tsx?)$/.test(entry.name)
      && !/\.test\.m?jsx?$/.test(entry.name)
      && !entry.name.startsWith('__')
    ) {
      out.push(full);
    }
  }
  return out;
}

function resolveLocalModule(specifier, fromFile) {
  let absolute;
  if (specifier.startsWith(ALIAS_PREFIX)) {
    absolute = path.join(ALIAS_TARGET, specifier.slice(ALIAS_PREFIX.length));
  } else if (specifier.startsWith('.')) {
    absolute = path.resolve(path.dirname(fromFile), specifier);
  } else {
    return null;
  }

  const specifierExt = path.extname(absolute).toLowerCase();
  if (specifierExt && !RESOLVE_EXTS.includes(specifierExt)) {
    if (IGNORED_SOURCE_EXTS.has(specifierExt)) return { absolute, ignored: true };
  }

  if (specifierExt && RESOLVE_EXTS.includes(specifierExt)) {
    try {
      if (statSync(absolute).isFile()) return { absolute };
    } catch {}
    return null;
  }

  for (const ext of RESOLVE_EXTS) {
    const candidate = absolute + ext;
    try {
      if (statSync(candidate).isFile()) return { absolute: candidate };
    } catch {}
  }
  for (const ext of RESOLVE_EXTS) {
    const candidate = path.join(absolute, 'index' + ext);
    try {
      if (statSync(candidate).isFile()) return { absolute: candidate };
    } catch {}
  }
  try {
    if (statSync(absolute).isFile()) return { absolute };
  } catch {}
  return null;
}

function sliceTopImportBlock(source) {
  const lines = source.split(/\r?\n/);
  const keep = [];
  let seenCode = false;
  for (const rawLine of lines) {
    const line = rawLine;
    const trimmed = line.trim();
    if (!seenCode) {
      if (trimmed === '') { keep.push(line); continue; }
      if (trimmed.startsWith('//')) { keep.push(line); continue; }
      if (trimmed.startsWith('/*') || trimmed.startsWith('*') || trimmed.endsWith('*/')) { keep.push(line); continue; }
      if (/^['"]use (client|server|strict)['"];?$/.test(trimmed)) { keep.push(line); continue; }
      if (/^(import|export)\b/.test(trimmed)) { keep.push(line); continue; }
      seenCode = true;
    } else {
      if (/^(import|export)\b.*\bfrom\s+['"][^'"]+['"]/.test(trimmed)) { keep.push(line); continue; }
      if (/^import\s+['"][^'"]+['"]/.test(trimmed)) { keep.push(line); continue; }
    }
  }
  return keep.join('\n');
}

const FROM_RE = /(import|export)\s+(?:type\s+)?([\s\S]*?)\bfrom\s+['"]([^'"]+)['"]/g;
const SIDE_EFFECT_RE = /(?:^|\n|;)\s*import\s+['"]([^'"]+)['"]/g;
const NAMED_BLOCK_RE = /{([\s\S]*?)}/;
const DEFAULT_BINDING_RE = /^\s*([A-Za-z_$][\w$]*)\s*(?:,|$)/;
const NAMESPACE_RE = /\*\s+as\s+([A-Za-z_$][\w$]*)/;

function parseImportStatements(source) {
  const block = sliceTopImportBlock(source);
  const statements = [];

  FROM_RE.lastIndex = 0;
  let match;
  while ((match = FROM_RE.exec(block)) !== null) {
    const keyword = match[1];
    const bindingsRaw = match[2];
    const specifier = match[3];
    const named = [];
    let hasDefault = false;
    let hasNamespace = false;

    const namedBlock = NAMED_BLOCK_RE.exec(bindingsRaw);
    if (namedBlock) {
      for (const part of namedBlock[1].split(',')) {
        const name = part.replace(/\s+/g, ' ').trim();
        if (!name) continue;
        const [imported] = name.split(/\s+as\s+/);
        if (imported && /^[A-Za-z_$][\w$]*$/.test(imported.trim())) {
          named.push(imported.trim());
        }
      }
    }

    if (NAMESPACE_RE.test(bindingsRaw)) hasNamespace = true;

    const beforeBrace = bindingsRaw.split('{')[0];
    const defaultMatch = DEFAULT_BINDING_RE.exec(beforeBrace);
    if (defaultMatch && !/^\*/.test(beforeBrace.trim())) {
      hasDefault = true;
    }

    statements.push({
      keyword,
      specifier,
      named,
      hasDefault: keyword === 'import' && hasDefault,
      hasNamespace,
    });
  }

  SIDE_EFFECT_RE.lastIndex = 0;
  while ((match = SIDE_EFFECT_RE.exec(block)) !== null) {
    statements.push({
      keyword: 'import',
      specifier: match[1],
      named: [],
      hasDefault: false,
      hasNamespace: false,
      sideEffect: true,
    });
  }

  return statements;
}

const EXPORT_DECL_RE = /export\s+(?:async\s+)?(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)/g;
const EXPORT_DESTRUCTURE_RE = /export\s+(?:const|let|var)\s*{([^}]+)}\s*=/g;
const EXPORT_LIST_LOCAL_RE = /export\s*{([^}]+)}(?!\s*from)/g;
const EXPORT_LIST_REEXPORT_RE = /export\s*{([^}]+)}\s*from\s+['"]([^'"]+)['"]/g;
const EXPORT_DEFAULT_RE = /export\s+default\b/;
const EXPORT_STAR_RE = /export\s*\*\s*from\s+['"]([^'"]+)['"]/g;

function collectExports(absPath, visited = new Set()) {
  if (visited.has(absPath)) return { names: new Set(), hasDefault: false };
  visited.add(absPath);

  let source;
  try {
    source = readFileSync(absPath, 'utf8');
  } catch {
    return { names: new Set(), hasDefault: false };
  }

  const names = new Set();
  let hasDefault = EXPORT_DEFAULT_RE.test(source);

  let m;
  EXPORT_DECL_RE.lastIndex = 0;
  while ((m = EXPORT_DECL_RE.exec(source)) !== null) {
    names.add(m[1]);
  }

  EXPORT_DESTRUCTURE_RE.lastIndex = 0;
  while ((m = EXPORT_DESTRUCTURE_RE.exec(source)) !== null) {
    for (const part of m[1].split(',')) {
      const token = part.trim();
      if (!token) continue;
      const [, aliased] = token.split(/\s*:\s*/);
      const exported = (aliased ?? token).trim();
      if (/^[A-Za-z_$][\w$]*$/.test(exported)) names.add(exported);
    }
  }

  EXPORT_LIST_REEXPORT_RE.lastIndex = 0;
  const reexportRanges = [];
  while ((m = EXPORT_LIST_REEXPORT_RE.exec(source)) !== null) {
    reexportRanges.push([m.index, m.index + m[0].length]);
    const fromSpec = m[2];
    const resolved = resolveLocalModule(fromSpec, absPath);
    let childExports = null;
    if (resolved && !resolved.ignored) {
      childExports = collectExports(resolved.absolute, visited);
    }
    for (const part of m[1].split(',')) {
      const token = part.trim();
      if (!token) continue;
      const [, aliased] = token.split(/\s+as\s+/);
      const exported = (aliased ?? token).trim();
      if (exported === 'default') continue;
      if (/^[A-Za-z_$][\w$]*$/.test(exported)) names.add(exported);
    }
    if (childExports?.hasDefault && m[1].includes('default')) {
      // `export { default } from './x'` forwards the default.
      hasDefault = true;
    }
  }

  const inRange = (idx) => reexportRanges.some(([s, e]) => idx >= s && idx < e);
  EXPORT_LIST_LOCAL_RE.lastIndex = 0;
  while ((m = EXPORT_LIST_LOCAL_RE.exec(source)) !== null) {
    if (inRange(m.index)) continue;
    for (const part of m[1].split(',')) {
      const token = part.trim();
      if (!token) continue;
      const [, aliased] = token.split(/\s+as\s+/);
      const exported = (aliased ?? token).trim();
      if (exported === 'default') continue;
      if (/^[A-Za-z_$][\w$]*$/.test(exported)) names.add(exported);
    }
  }

  EXPORT_STAR_RE.lastIndex = 0;
  while ((m = EXPORT_STAR_RE.exec(source)) !== null) {
    const resolved = resolveLocalModule(m[1], absPath);
    if (resolved && !resolved.ignored) {
      const child = collectExports(resolved.absolute, visited);
      for (const name of child.names) names.add(name);
    }
  }

  return { names, hasDefault };
}

function collectCandidateFiles() {
  const files = [];
  for (const root of SCAN_ROOTS) walk(root, files);
  return files;
}

const files = collectCandidateFiles();
const fileExportCache = new Map();
function exportsFor(absPath) {
  if (!fileExportCache.has(absPath)) {
    fileExportCache.set(absPath, collectExports(absPath));
  }
  return fileExportCache.get(absPath);
}

test('component files are present for import smoke check', () => {
  assert.ok(files.length > 0, 'expected at least one component file under src/components or src/app');
});

test('every local import resolves to an existing file', () => {
  const problems = [];
  for (const file of files) {
    const source = readFileSync(file, 'utf8');
    const statements = parseImportStatements(source);
    for (const stmt of statements) {
      const spec = stmt.specifier;
      if (!spec.startsWith('.') && !spec.startsWith(ALIAS_PREFIX)) continue;
      const ext = path.extname(spec).toLowerCase();
      if (IGNORED_SOURCE_EXTS.has(ext)) continue;
      const resolved = resolveLocalModule(spec, file);
      if (!resolved) {
        problems.push(`${path.relative(PROJECT_ROOT, file)} → '${spec}' (unresolved)`);
      }
    }
  }
  assert.deepEqual(problems, [], `unresolved local imports:\n  ${problems.join('\n  ')}`);
});

test('named imports reference symbols actually exported by target modules', () => {
  const problems = [];
  for (const file of files) {
    const source = readFileSync(file, 'utf8');
    const statements = parseImportStatements(source);
    for (const stmt of statements) {
      if (stmt.sideEffect) continue;
      const spec = stmt.specifier;
      if (!spec.startsWith('.') && !spec.startsWith(ALIAS_PREFIX)) continue;
      const ext = path.extname(spec).toLowerCase();
      if (IGNORED_SOURCE_EXTS.has(ext)) continue;
      const resolved = resolveLocalModule(spec, file);
      if (!resolved || resolved.ignored) continue;
      const { names, hasDefault } = exportsFor(resolved.absolute);
      for (const name of stmt.named) {
        if (!names.has(name)) {
          problems.push(
            `${path.relative(PROJECT_ROOT, file)} imports { ${name} } from '${spec}' but ${path.relative(PROJECT_ROOT, resolved.absolute)} does not export it`
          );
        }
      }
      if (stmt.hasDefault && !hasDefault) {
        problems.push(
          `${path.relative(PROJECT_ROOT, file)} imports default from '${spec}' but ${path.relative(PROJECT_ROOT, resolved.absolute)} has no default export`
        );
      }
    }
  }
  assert.deepEqual(problems, [], `missing exports:\n  ${problems.join('\n  ')}`);
});
