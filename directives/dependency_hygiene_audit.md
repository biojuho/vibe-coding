# SOP: 의존성 위생 감사 (Dependency Hygiene Audit)

> 3계층 아키텍처의 1계층(지침). 실행은 `execution/dependency_hygiene_audit.py`.
> 외부 OSS [`fpgmaas/deptry`](https://github.com/fpgmaas/deptry) (MIT)를 도입해
> "선언된 의존성"과 "실제 import"의 불일치를 잡는다.

## 목표

각 Python 프로젝트의 `pyproject.toml` 의존성 집합이 **정확하고 군더더기 없는지** 검증한다.
기존 게이트가 다루지 않는 빈틈을 메운다:

| 도구 | 다루는 것 |
|------|-----------|
| `dependency_security_audit.py` (pip-audit) | 알려진 CVE 취약점 |
| auto-research `dependency_freshness_inventory.py` | 오래된(outdated) 핀 |
| **`dependency_hygiene_audit.py` (deptry)** | **선언 집합 자체의 정확성/군더더기** |

deptry가 잡는 결함:

- **DEP001 missing** — import 하지만 의존성에 미선언 → 클린 설치 시 `ImportError` 위험
- **DEP002 unused** — 선언했지만 한 번도 import 안 함 → 설치 비대화/공격 표면 증가
- **DEP003 transitive** — 직접 import 하지만 간접(transitive)으로만 제공됨 → 중간 제공자가 빠지면 깨짐
- **DEP004 misplaced-dev** — dev 의존성을 프로덕션 코드가 import → 클린 설치 크래시

## 입력

- 대상 프로젝트: `workspace`, `projects/blind-to-x`, `projects/shorts-maker-v2`
  (각각 자체 `pyproject.toml`의 `[tool.deptry]` 설정을 읽는다)

## 실행 (도구 먼저 확인)

```bash
# 전체 프로젝트 감사 (Rich TUI)
python execution/dependency_hygiene_audit.py

# 특정 프로젝트만
python execution/dependency_hygiene_audit.py --project blind-to-x

# 자동화/CI용 JSON
python execution/dependency_hygiene_audit.py --json

# deptry 미설치를 hard fail 로 (CI 게이트용)
python execution/dependency_hygiene_audit.py --strict
```

- exit 0 = 잔여 findings 없음(clean), 1 = findings 있음, 2 = deptry 실행 실패, 3 = deptry 미설치(`--strict`)
- 기본은 **advisory**: deptry 미설치 시(비-strict) 안내만 하고 exit 0 → 훅/CI를 깨지 않음

## 출력

- 프로젝트별 잔여 findings 표 + 코드별 요약. JSON 스키마: `dependency_hygiene_audit.v1`

## 예외 상황(Edge cases) — 신뢰할 수 있는 신호 만들기

deptry는 설정 없이는 **노이즈가 많다**. 각 프로젝트 `[tool.deptry]`에 의도적 패턴을 인코딩해
잔여 findings가 곧 **진짜 신호**가 되도록 한다:

1. **package ↔ module 이름 불일치** → `[tool.deptry.package_module_name_map]`.
   - deptry는 패키지가 환경에 미설치면 "module 이름 = 패키지 이름"으로 가정한다.
     예: `beautifulsoup4`의 실제 import 는 `bs4`. 매핑 없으면 `beautifulsoup4`를 "unused"로,
     `bs4`를 "missing"으로 **이중 오탐**한다. (blind-to-x에서 실제 발생 → 매핑으로 해결)
2. **로컬/형제 모듈** (sys.path 부트스트랩, 크로스 프로젝트 import) → `known_first_party`.
3. **선택적 통합** (try/except 가드, 우아한 강등: redis/celery/torch/whisperx 등) → `per_rule_ignores.DEP001`.
4. **dev 전용 그룹** (ruff/mypy/pytest/pre-commit) → `pep621_dev_dependency_groups = ["dev"]`.
5. **테스트/아카이브 디렉터리** (pytest import는 정상) → `extend_exclude`.
6. **수용된 transitive import** → `per_rule_ignores.DEP003`.

## 자가 수정 루프로 발견한 실제 개선(2026-06-18 도입)

deptry 도입 첫 스캔에서 raw ~168건 → 설정/수정 후 **0건**. 그 과정에서 잡은 진짜 결함:

- **workspace**: `code_evaluator.py`가 `pydantic`을 **무가드 hard import** 하는데 dev 그룹에만 선언
  → 클린 설치 시 크래시. **`pydantic`을 런타임 의존성으로 이동**.
- **workspace**: `yaml`(PyYAML) 직접 import 하나 미선언(간접 제공) → **PyYAML 런타임 선언 추가**.
- **blind-to-x**: `beautifulsoup4`/`google-genai` 이름 불일치 이중 오탐 → 매핑으로 정정
  (실수로 `beautifulsoup4`를 제거했으면 스크래퍼 셀렉터 자동추출이 깨졌을 것 — **제거 전 반드시 사용처 검증**).
- **shorts-maker-v2**: `pydub`는 전부 try/except 가드된 선택적 오디오 백엔드 → 정상(수용).

## JS/TS 쪽: knip (Next.js 대시보드)

Python을 deptry가 맡듯, **JS/TS 모노레포 절반(hanwoo/knowledge 대시보드)은 [`knip`](https://github.com/webpro-nl/knip)**(ISC)가
맡는다. 같은 "선언-vs-사용" 위생 + 데드코드(미사용 파일/export/타입)까지 본다.

```bash
# 각 대시보드 루트에서
npm run knip                 # 사람용 리포트
npx knip --reporter json     # 자동화용
```

각 대시보드는 자체 `knip.json`을 가진다. **deptry와 똑같은 함정**: 설정 없이는 노이즈 폭발.

1. **path alias 미해석** — knip은 기본적으로 `tsconfig.json`만 읽는다. hanwoo는 `jsconfig.json`에
   `@/* → ./src/*`를 두는데 knip이 못 읽어 `@/` import 전부 unresolved → **99개 "미사용 파일" + 68개
   unresolved 허위 보고**. `knip.json`의 `"paths"`로 jsconfig 별칭을 미러링하면 해소(162건 제거).
2. **엔트리포인트 누락** — 서비스워커(`src/sw.js`, serwist `swSrc` 문자열 참조), 독립 CLI
   (`scripts/*.mjs`, `prisma/seed*.js`)는 `"entry"`로 명시. 빌드 산출물(`public/sw.js`,
   `workbox-*.js`)은 `"ignore"`.
3. **시스템 바이너리/transitive** — `python`(npm 패키지 아님) → `ignoreBinaries`;
   `postcss`(Tailwind v4가 간접 제공) → `ignoreDependencies`.

**최대 함정 — "미사용 의존성"이 "미사용 파일"의 부산물일 수 있다(= bs4 교훈의 JS판):**
hanwoo에서 knip이 `@radix-ui/react-avatar` 등 9개를 unused dep으로 보고했지만, 그중 **7개는
`src/components/ui/*.js`(shadcn 래퍼)가 실제로 import** 하고 있었다. 래퍼 파일 자체가 어느 엔트리에서도
도달 안 되는 "데드 섬"이라 dep도 미사용으로 보인 것. **이 7개를 무작정 지웠으면 그 파일들이 깨졌다.**
적대적 검증(import 라인 직접 grep)으로 진짜 고아 dep만 골라냈다 → 실제 제거: hanwoo
`@radix-ui/react-toast`·`react-dropdown-menu`, knowledge `react-separator`·`react-tooltip`(4개,
소스 사용 0 확인). 나머지 데드 UI 프리미티브 섬과 미사용 export/type 은 **숨기지 말고** 백로그로 노출 유지.

> 규칙: knip "unused dependency"는 제거 전 **반드시 `grep`으로 import 확인**. 미사용 *파일*이
> import 하는 dep이면, dep이 아니라 파일을 함께 정리(또는 백로그)해야 한다. 의심되면 보존.

## 운영 노트

- 의존성 **업그레이드 직후** 실행 권장 (업그레이드가 unused/missing 을 만들기 쉽다).
- DEP002(unused)·DEP001(missing) 을 만나면 **무작정 제거/추가하지 말 것**: 먼저 import 가
  try/except 가드(선택적)인지, 환경 미설치로 인한 이름 오탐인지 확인하라.
- 정당한 예외는 코드를 바꾸지 말고 `[tool.deptry]` 설정에 **주석과 함께** 기록한다.
