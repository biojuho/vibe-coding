# 23 · Tool Calling · Function Calling · Harness Boundary

> Provider-native tool/function calling과 로컬 하네스/MCP 권한 경계를 분리하는 운영 페이지.
> 코드 사실은 2026-06-08 현재 HEAD 기준으로 `workspace/execution/llm_client.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/research_step.py`, `workspace/execution/harness_tool_registry.py`, `docs/wiki/llm/09-agent-harness.md`에서 재확인했다.

## 왜 따로 보나

`function calling`, `tool use`, `structured output`, `MCP`, `agent harness`는 같은 문제가 아니다.

- **Structured output**: 모델의 최종 응답 형식을 스키마에 맞추는 문제다. 도구 실행 권한을 주지 않는다. 이 repo의 현행 공통 경로는 OpenAI-compatible `response_format={"type": "json_object"}`, Gemini `response_mime_type="application/json"`, Anthropic 프롬프트 기반 JSON 파싱 수준이다([10-structured-outputs](10-structured-outputs.md)).
- **Provider-native tool/function calling**: 모델이 "이 도구를 이런 인자로 호출하라"는 구조화된 요청을 반환하는 API 기능이다. 실제 실행은 앱 코드나 provider server tool 계층이 맡는다.
- **Provider-native computer use**: 모델이 screenshot을 보고 click/type/scroll 같은 GUI action을 요청하는 특수 도구 계층이다. 자세한 운영 기준은 [33-computer-use-browser-qa-boundary](33-computer-use-browser-qa-boundary.md)에서 다룬다.
- **MCP**: 도구/리소스/프롬프트를 연결하는 프로토콜이다. MCP 서버가 있다고 해서 해당 LLM workflow에 자동 실행 권한이 생기는 것은 아니다.
- **Local harness**: 이 workspace가 직접 정하는 권한·HITL·예산·감사 정책이다. provider tool call이나 MCP 호출보다 안쪽의 안전 경계로 봐야 한다.

따라서 "모델이 tool call을 만들 수 있다"와 "우리 앱이 파일/네트워크/셸/MCP를 실행해도 된다"는 별도 승인 단계다.

## 현재 구현 사실

### 1) 공통 `LLMClient`는 provider-neutral tool API가 없다

`workspace/execution/llm_client.py`의 핵심 호출부는 세 가지 기본 생성 형태만 노출한다.

- OpenAI-compatible provider: `client.chat.completions.create(**kwargs)`에 `messages`, `temperature`, 선택적 `response_format={"type": "json_object"}`만 전달한다(L414-427).
- Gemini provider: `client.models.generate_content(...)`에 `system_instruction`, `temperature`, 선택적 JSON MIME만 전달한다(L435-449).
- Anthropic provider: `client.messages.create(**create_kwargs)`에 `system`, `messages`, `max_tokens=2000`, `temperature`를 전달한다(L453-477).
- public method는 `generate_json(...)`, `generate_text(...)`, bridged 변형이다(L686-735, L953-987). `tools`, `tool_choice`, `function_call`, `function_declarations` 같은 provider-neutral 인자는 없다.

이 선택은 9-provider fallback의 최소공통분모 전략과 맞다. 반대로 tool calling을 추가할 때 공통 `LLMClient`에 무심코 인자를 뚫으면 provider별 semantics, 권한, 비용, citation, HITL이 한꺼번에 섞인다.

### 2) 실제 provider-native tool 사용은 Shorts Maker research path에 있다

`projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/research_step.py`는 Gemini Google Search Grounding을 명시적으로 사용한다.

```python
response = self.google_client.client.models.generate_content(
    model="gemini-2.5-flash",
    contents=user_prompt,
    config=types.GenerateContentConfig(
        system_instruction=_RESEARCH_SYSTEM_PROMPT,
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.3,
    ),
)
```

이 경로는 provider server tool에 가깝다. 앱이 검색 API를 직접 실행하고 결과를 다시 넣는 루프가 아니라, Gemini가 `google_search` 도구를 사용하도록 요청하고 `grounding_metadata`에서 출처 제목을 보강한다(L156-180). 그래서 이 기능의 운영 기준은 "동적 agent 권한"보다는 [28-grounding-citation-source-attribution](28-grounding-citation-source-attribution.md)의 외부 검색/grounding/citation/비용/프라이버시 경계에 더 가깝다.

### 3) 로컬 하네스는 deny-by-default 권한 계층이지만 미배선이다

`workspace/execution/harness_tool_registry.py`의 `ToolRegistry`는 등록되지 않은 도구를 거부하고, 경로 glob, path traversal, 세션별 invocation cap, HITL 플래그를 검사한다(L106-203). `authorize(...)`는 결과를 invocation log에 기록하고, HITL handler가 없으면 HITL-required 작업을 거부한다(L203-292).

기본 권한 세트는 다음처럼 나뉜다(L316-426).

| 범주 | 도구 | 기본 정책 |
|---|---|---|
| read-safe | `file_read`, `list_dir`, `grep_search` | workspace root 하위만 |
| write-moderate | `file_write`, `file_create` | `projects/`, `workspace/`, `.tmp/`, `.ai/`; session cap |
| delete-moderate | `file_delete` | `.tmp/`만, HITL 필요 |
| execute-dangerous | `shell_command`, `python_exec` | HITL 필요 |
| network-dangerous | `http_request`, `mcp_call` | HITL 필요 |

테스트도 이 shape를 잠근다. `workspace/tests/test_harness_tool_registry.py`는 `mcp_call`이 기본 registry에 포함되는지, `file_delete`가 HITL인지, path traversal과 session budget이 막히는지 확인한다(L12-82).

단, [09-agent-harness](09-agent-harness.md)의 결론처럼 이 하네스는 구현/테스트돼 있지만 현재 production LLM pipeline에 배선돼 있지 않다. `HARNESS_ENABLED=1`만으로 안전하게 켜졌다고 보면 안 된다.

## Provider 공식 기준

### OpenAI

OpenAI는 tool/function calling을 "앱이 모델에게 도구 목록을 제공하고, 모델이 tool call을 반환하면 앱이 실행한 뒤 tool output을 다시 보내 최종 응답을 받는 다단계 흐름"으로 설명한다. 함수는 요청의 `tools`에 선언하고, `tool_choice`로 auto/required/forced/allowed/none 계열 제어를 할 수 있다. `strict: true`는 structured outputs 기반으로 function arguments의 스키마 준수를 강화하지만, 실행 안전을 대신하지 않는다.

이 repo 적용:

- 현재 공통 `LLMClient`는 OpenAI Responses API의 `tools` 흐름이 아니라 Chat Completions compatible 생성 경로다. API surface와 parser evidence는 [37-api-surface-sdk-compatibility-boundary](37-api-surface-sdk-compatibility-boundary.md)의 artifact 계약을 따른다.
- function calling을 도입한다면 provider wrapper나 workflow-specific client에서 먼저 실험하고, 앱 실행부는 `ToolRegistry` 권한 확인을 통과해야 한다.
- OpenAI structured output 문서도 "시스템의 tool/function/data에 연결할 때는 function calling, 최종 응답 형식을 정할 때는 structured output"으로 구분한다. 이 구분을 유지한다.

### Anthropic/Claude

Claude client tool은 API 요청의 `tools` 최상위 파라미터에 선언한다. 각 tool은 `name`, `description`, `input_schema`를 갖고, `tool_choice`는 `auto`, `any`, `tool`, `none`을 지원한다. Claude가 client tool을 쓰면 응답에는 `tool_use` block이 오고, 앱은 `name`, `id`, `input`을 읽어 실제 도구를 실행한 뒤 `tool_result` block을 바로 이어 보내야 한다. Anthropic 문서는 tool result의 외부 콘텐츠를 untrusted로 보고 prompt injection 방어를 요구한다.

이 repo 적용:

- 현재 `LLMClient` Anthropic 경로는 `tools`를 넘기지 않는다.
- Anthropic strict tool use는 구조화 입력 정확도에는 유용하지만, `shell_command`/`mcp_call` 같은 side effect를 승인하지 않는다.
- tool result는 [08-security](08-security.md)의 indirect prompt injection 표면으로 취급한다. 외부 검색, 이메일, 업로드, API 응답을 system prompt나 일반 user text로 섞지 않는다.

### Gemini

Gemini function calling은 `types.Tool(function_declarations=[...])`와 `GenerateContentConfig(tools=[...])`로 함수 선언을 제공하고, 모델이 function call name/arguments/id를 반환하는 구조다. 별도로 Google Search Grounding은 `types.Tool(google_search=types.GoogleSearch())`를 설정하면 모델이 검색, 처리, citation/grounding metadata 생성을 한 API 호출 안에서 처리한다.

이 repo 적용:

- Shorts Maker research step의 Google Search Grounding은 이미 이 provider-native server tool 패턴이다.
- function calling으로 side-effecting action을 추가하는 것은 별도 문제다. 검색 grounding은 "정보 보강"이고, 파일/네트워크/DB 변경은 "권한 실행"이다.
- `grounding_metadata`는 출처 표시와 디버깅에 중요하다. 결과 텍스트만 저장하지 말고 검색 query/source/citation 메타데이터를 [28-grounding-citation-source-attribution](28-grounding-citation-source-attribution.md)의 sidecar artifact로 보존하는 쪽이 안전하다.

### MCP

MCP tool spec은 서버가 `tools/list`로 도구 schema를 노출하고, client가 `tools/call`로 name/arguments를 보내는 JSON-RPC 흐름을 정의한다. 같은 spec은 trust/safety 때문에 사용자가 도구 노출과 호출을 볼 수 있어야 하고, 민감 작업에는 confirmation prompt를 둘 것을 권한다. MCP authorization spec은 HTTP transport의 OAuth 기반 인가를 다루지만, authorization은 구현별 선택이고 STDIO transport는 환경에서 credential을 가져오는 방식이다.

이 repo 적용:

- `.mcp.json`이나 MCP diagnostic script가 존재해도 LLM pipeline이 자동으로 `mcp_call` 권한을 얻는 것은 아니다.
- 이 workspace의 local policy는 `mcp_call`을 dangerous network tool로 분류하고 HITL을 요구한다.
- MCP server tool description/annotation도 신뢰 서버가 아니면 untrusted metadata로 취급한다.

## A/B 운영 선택

| 선택 | 장점 | 리스크 | 이 repo 권장 |
|---|---|---|---|
| A. 현행 유지: fixed workflow + no tools in `LLMClient` | fallback 단순, 비용/로그/테스트 안정 | 최신 검색/외부 action은 workflow별 구현 필요 | 기본값 |
| B. workflow-specific provider tool | Google Search Grounding처럼 필요한 곳만 정확히 사용 | provider lock-in, citation/비용/프라이버시 관리 필요 | 검색/근거 보강에만 선별 적용 |
| C. 공통 `LLMClient` tool abstraction | 호출 API가 한 곳으로 모임 | provider semantics와 권한 정책이 섞임, fallback 복잡도 급증 | 아직 비권장 |
| D. local harness/MCP agent layer | side effect를 중앙 권한/HITL/감사로 통제 | 현재 미배선, stale API 먼저 수정 필요 | 동적 agent 전에 필수 선행 |

**결론:** 공통 `LLMClient`는 no-tools 기본값을 유지한다. provider-native tool은 `research_step.py`처럼 workflow wrapper에서 명시적으로 사용한다. 파일/네트워크/셸/MCP 실행을 동적으로 허용하는 agent는 `ToolRegistry` + sandbox + HITL + audit log가 실제로 배선된 뒤에만 연다.

## 추가할 때의 체크리스트

### Provider-native function/tool calling

1. 도구가 "정보 조회"인지 "side effect"인지 먼저 분류한다.
2. provider별 schema를 workflow-local로 둔다. 공통 `LLMClient` 인자에 바로 추가하지 않는다.
3. function arguments는 모델 출력이다. JSON schema가 맞아도 업무 규칙 검증, enum allowlist, path/domain allowlist를 다시 한다.
4. 실행 결과는 error/success를 구조화하고, 외부 텍스트는 untrusted tool result로 표시한다.
5. 검색/grounding tool은 query, source title/URI, citation metadata, 비용/요청 수를 evidence에 남긴다([28-grounding-citation-source-attribution](28-grounding-citation-source-attribution.md)).
6. 테스트는 provider SDK를 mock해서 tool call parsing, invalid argument rejection, fallback when tool unavailable을 고정한다.

### MCP/local tool execution

1. `ToolRegistry.default(root)` 또는 explicit registry에 도구를 등록한다.
2. `RiskLevel`, `allowed_path_globs`, `requires_hitl`, `max_invocations_per_session`을 도구별로 정한다.
3. `authorize(...)` 결과가 allowed일 때만 실제 도구를 실행한다.
4. dangerous/network 도구는 HITL handler 없으면 실패해야 한다.
5. shell/python/file delete/MCP는 prompt 지시만으로 실행하지 않는다.
6. 실행 로그를 남기고, tool output이 길거나 외부 origin이면 context offload/요약 정책을 적용한다([09-agent-harness](09-agent-harness.md)).

## 지뢰밭

- **Tool call != tool execution.** 모델은 호출 요청을 만든다. 앱 또는 provider server tool layer가 실행한다.
- **Schema adherence != authorization.** strict schema는 인자 형태를 잡을 뿐, side effect를 안전하게 만들지 않는다.
- **MCP available != MCP allowed.** 연결 설정과 실행 권한은 별개다.
- **Search grounding != web scraper.** Gemini Google Search Grounding은 citation metadata를 돌려주는 provider tool이다. raw crawler처럼 저장/재사용하면 출처·약관·freshness 기준이 달라진다.
- **Prompt injection risk moves into tool results.** 검색 결과, API 응답, MCP tool output은 다시 모델 입력으로 들어가므로 untrusted content 경계를 유지한다.
- **Dynamic agent는 LLM01 + LLM06을 동시에 키운다.** 외부 텍스트가 tool choice나 function args에 영향을 주는 순간 prompt injection과 excessive agency가 결합된다.
- **Computer-use success != browser QA pass.** 모델이 화면을 보고 한 번 클릭에 성공한 것은 deterministic Playwright assertion, console/network check, retained screenshot evidence를 대체하지 않는다([33-computer-use-browser-qa-boundary](33-computer-use-browser-qa-boundary.md)).

## 출처 (1차 우선, 2026-06-08 확인)

- OpenAI, *Function calling*: <https://developers.openai.com/api/docs/guides/function-calling>
- OpenAI, *Using tools*: <https://developers.openai.com/api/docs/guides/tools>
- OpenAI, *Structured model outputs*: <https://developers.openai.com/api/docs/guides/structured-outputs>
- Anthropic/Claude, *Define tools*: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools>
- Anthropic/Claude, *Handle tool calls*: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls>
- Gemini API, *Function calling*: <https://ai.google.dev/gemini-api/docs/function-calling>
- Gemini API, *Grounding with Google Search*: <https://ai.google.dev/gemini-api/docs/google-search>
- Model Context Protocol, *Tools specification 2025-06-18*: <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>
- Model Context Protocol, *Authorization specification 2025-06-18*: <https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization>
- 코드 근거: `workspace/execution/llm_client.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/research_step.py`, `workspace/execution/harness_tool_registry.py`, `workspace/tests/test_harness_tool_registry.py` (2026-06-08 현재 HEAD)

*외부 자료 검증일: 2026-06-08*
