---
name: windows-safe-scripting
description: "Windows 11 + 한글 홈경로(박주호) 환경의 안전 스크립팅 규칙. Use when PowerShell 런처, MCP 시작 스크립트, 또는 execution/ 파이썬 스크립트를 작성하거나 수정 시 적용한다."
---

# Windows Safe Scripting

이 PC는 Windows 11 + PowerShell 5.1 + 한글 홈경로(`C:\Users\박주호`) 환경이다.
이 조합에서 반복적으로 스크립트가 깨졌다. `.ai/CONTEXT.md`의 Minefield "Windows 실행 장벽"을
인코딩한 규칙으로, 스크립트를 쓰기 전에 점검한다.

## When to Use This Skill

- PowerShell 런처(`.ps1`)나 MCP 시작 스크립트를 작성·수정할 때
- `execution/`의 파이썬 스크립트를 새로 만들거나 고칠 때
- 콘솔/CLI 도구가 한글을 출력하거나 한글 경로를 다룰 때
- cp949 mojibake로 깨진 파일을 복구할 때

## 규칙

### 1. PowerShell core cmdlet 오토로드 깨짐 → .NET API 우선
`-NoProfile` 세션(대부분의 자동화)에서 `Split-Path`, `Test-Path`, `Get-Content`,
`Select-Object` 같은 core cmdlet이 로드되지 않을 수 있다. 다음 .NET API로 작성한다:

- 경로 분해: `[System.IO.Path]::GetDirectoryName(...)`, `GetFileName(...)`
- 존재 확인: `[System.IO.File]::Exists(...)`, `[System.IO.Directory]::Exists(...)`
- 파일 읽기: `[System.IO.File]::ReadAllText(path, [System.Text.Encoding]::UTF8)`
- 환경 변수: `[System.Environment]::GetEnvironmentVariable(...)`
- 정규식: `[System.Text.RegularExpressions.Regex]`

### 2. Python stdout/stderr 인코딩
스크립트 상단에서 스트림을 UTF-8로 강제 재구성한다. 이모지·비ASCII를 stdout/stderr로
직접 출력하면 cp949에서 `UnicodeEncodeError`가 난다.

```python
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
```

### 3. 파일은 항상 UTF-8 클린
콘솔이 cp949로 한글을 깨뜨려 보여도, 실제 **파일·데이터는 UTF-8로 깨끗하게 저장**한다.
한글이 든 경로의 해시/인코딩이 필요하면 strict가 아니라 `errors="surrogateescape"`를 쓴다.

### 4. Node 바이너리 실행
`.cmd`/`.bat` 확장자를 명시하거나 `PATHEXT`를 존중한다.

### 5. 재귀 탐색 전 존재 확인
`Get-ChildItem -Recurse` 등은 없는 디렉터리를 만나면 에러가 난다. 탐색 전 타깃 존재를 확인한다.

### 6. cp949 mojibake 복구
깨진 바이트는 Edit 툴이 매칭에 실패한다(원문과 안 맞음). 라인번호 기반 Python rewrite로
파일을 다시 쓰고, codepoint(`ord()`)로 한글 범위를 검증한 뒤 저장한다.

## 주의

- 규칙 원문은 `.ai/CONTEXT.md`의 Minefield "Windows 실행 장벽" 절에 있다.
- 검증된 사례: 글로벌 npm 래퍼 cmdlet 로딩, knowledge-dashboard mojibake 복구.
