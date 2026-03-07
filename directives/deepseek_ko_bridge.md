# DeepSeek 한국어 브릿지 지침

## 목적
- DeepSeek를 1차 저비용 모델로 유지하면서 최종 산출물은 한국어 품질과 UTF-8 안전성을 보장한다.
- 중국어/한자 혼입, 문자 깨짐, JSON 파싱 실패를 자동 검출하고 필요 시 재작성 또는 fallback을 수행한다.

## 기본 정책
- 기본 출력 언어: `ko-KR`
- 기본 모드: `shadow`
- 기본 우선순위: `deepseek -> google -> openai -> 나머지 활성 프로바이더`
- 기본 repair 횟수: `1`

## 사용 위치
- 공통 sync 경로: `execution/llm_client.py`
- 주제 자동 생성: `execution/topic_auto_generator.py`
- shorts-maker-v2 라우터: `shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`

## 환경 변수
- `LLM_BRIDGE_MODE=off|shadow|enforce`
- `LLM_BRIDGE_TARGET_LANGUAGE=ko-KR`
- `LLM_BRIDGE_ALLOWED_TERMS=DeepSeek,JSON,OpenAI`
- `LLM_BRIDGE_FALLBACKS=deepseek,google,openai`
- `LLM_BRIDGE_REPAIR_ATTEMPTS=1`
- `LLM_BRIDGE_STRICT_KOREAN=true|false`
- `LLM_BRIDGE_ENFORCE_JSON_SCHEMA=true|false`
- `LLM_BRIDGE_MIN_HANGUL_RATIO=0.75`
- `LLM_BRIDGE_MAX_CJK_RATIO=0.02`
- `LLM_BRIDGE_MAX_JAMO_RATIO=0.05`
- `LLM_BRIDGE_JSON_KEY_EXEMPTIONS=title,id,url`
- 권장 운영 기본값 예시는 루트 `.env.bridge.example` 참고

## 운영 권장값
- 초기 운영: `LLM_BRIDGE_MODE=shadow`
- 한글 비율: `LLM_BRIDGE_MIN_HANGUL_RATIO=0.72`
- CJK 비율: `LLM_BRIDGE_MAX_CJK_RATIO=0.03`
- 자모 비율: `LLM_BRIDGE_MAX_JAMO_RATIO=0.05`
- repair 횟수: `LLM_BRIDGE_REPAIR_ATTEMPTS=1`
- shadow reason code를 3일 이상 관찰한 뒤 `enforce` 전환

## 동작 순서
1. 입력/프롬프트를 `NFC`로 정규화한다.
2. 한국어 강제 규칙을 시스템 프롬프트 앞에 주입한다.
3. DeepSeek를 1차 모델로 호출한다.
4. 결과를 검수한다.
5. `shadow` 모드에서는 품질 문제를 로그에 남기고 결과를 그대로 반환한다.
6. `enforce` 모드에서는 repair 1회 후 다음 프로바이더로 fallback한다.

## 검수 기준
- `U+FFFD` 포함 시 `mojibake`
- CJK 비율 초과 시 `mixed_language`
- 한글 비율 미달 시 `low_hangul_ratio`
- 분해 자모 비율 초과 시 `decomposed_jamo`
- JSON 파싱 실패 시 `json_parse_error`
- 빈 응답 시 `empty_content`

## 구현 메모
- 브릿지 정책과 검수 로직은 `execution/language_bridge.py`에 둔다.
- API 사용량 추적 시 `bridge_mode`, `reason_codes`, `repair_count`, `fallback_used`, `language_score`, `provider_used`를 함께 남긴다.
- `blind-to-x`의 async 생성기는 2차 적용 대상으로 둔다.
