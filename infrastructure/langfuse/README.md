# Langfuse 셀프호스트 (Local-First)

`directives/llm_observability_langfuse.md`의 1단계 인프라입니다.

이 compose 파일은 Langfuse v3 로컬 셀프호스트 구조를 따릅니다: web, worker,
Postgres, ClickHouse, Redis, MinIO. 모든 공개 포트는 `127.0.0.1`에만
바인딩합니다.

## 정책

- **외부 노출 금지**: 모든 포트는 `127.0.0.1` 바인딩만 사용합니다.
- **opt-in**: 워크스페이스 LLMClient는 기본적으로 trace를 보내지 않습니다.
  `.env`의 `LANGFUSE_ENABLED=1`일 때만 활성화됩니다.
- **재생성 가능**: 로컬 관측 데이터는 디버깅용입니다. 필요하면 `down -v`로
  전부 지우고 다시 만들 수 있어야 합니다.

## 1회성 셋업

1. `.env`에 다음 값을 설정합니다.

   ```env
   LANGFUSE_ENABLED=0
   LANGFUSE_HOST=http://127.0.0.1:3030
   LANGFUSE_PUBLIC_KEY=
   LANGFUSE_SECRET_KEY=

   LANGFUSE_DB_PASSWORD=__set_strong_password__
   LANGFUSE_NEXTAUTH_SECRET=__openssl_rand_base64_32__
   LANGFUSE_SALT=__openssl_rand_base64_32__
   LANGFUSE_ENCRYPTION_KEY=__openssl_rand_hex_32__
   LANGFUSE_CLICKHOUSE_PASSWORD=__set_strong_password__
   LANGFUSE_REDIS_AUTH=__set_strong_password__
   LANGFUSE_MINIO_ROOT_PASSWORD=__set_strong_password__
   ```

   Windows PowerShell에서 64자리 hex key 생성 예:

   ```powershell
   -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
   ```

2. 컨테이너를 기동합니다.

   ```bash
   docker compose -f infrastructure/langfuse/docker-compose.yml up -d
   ```

3. <http://127.0.0.1:3030> 접속 후 계정과 프로젝트를 만들고, Settings에서
   public/secret key를 발급해 `.env`의 `LANGFUSE_PUBLIC_KEY`,
   `LANGFUSE_SECRET_KEY`에 입력합니다.

4. 추적을 켤 때만 `.env`를 `LANGFUSE_ENABLED=1`로 변경합니다.

## 운영

- 중단: `docker compose -f infrastructure/langfuse/docker-compose.yml down`
- 완전 wipe: `docker compose -f infrastructure/langfuse/docker-compose.yml down -v`
- 상태: `docker compose -f infrastructure/langfuse/docker-compose.yml ps`
- 로그: `docker compose -f infrastructure/langfuse/docker-compose.yml logs -f langfuse-web langfuse-worker`

## 트러블슈팅

- **컨테이너가 unhealthy**: `ps`로 실패 서비스를 확인한 뒤 해당 서비스 로그에서
  비밀번호 누락, 권한, 포트 충돌을 확인합니다.
- **UI 접속 안 됨**: 3030 포트 충돌 가능성이 큽니다. 점유 프로세스를 종료하거나
  compose의 `ports` 매핑을 변경합니다.
- **trace가 안 보임**: `LANGFUSE_ENABLED=1`, `LANGFUSE_PUBLIC_KEY`,
  `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`를 확인합니다. 훅은 silent drop으로
  동작하므로 LLM 응답 자체를 막지 않습니다.

## 비고

- Langfuse v3는 trace/observation 저장에 ClickHouse가 필요합니다. Postgres만
  사용하는 v2 compose로 축소하지 않습니다.
- Langfuse 자체 텔레메트리는 OFF입니다 (`TELEMETRY_ENABLED=false`).
