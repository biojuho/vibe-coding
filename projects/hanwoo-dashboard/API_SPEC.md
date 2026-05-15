# Hanwoo Dashboard API Spec

This file records the backend API contract used by the dashboard client. All non-auth API routes must protect access with `requireAuthenticatedSession()` unless explicitly documented otherwise.

## Common Envelope

JSON failures use:

```json
{
  "success": false,
  "message": "Human-readable error",
  "error": "Human-readable error"
}
```

Existing dashboard and payment routes may omit `error` for legacy clients, but new or updated routes should include both `message` and `error` while clients migrate.

## `POST /api/ai/chat`

Streams an authenticated farm-assistant answer as Server-Sent Events.

### Auth

Requires an active Auth.js session. Unauthenticated requests return `401`.

### Request

```json
{
  "message": "How should I adjust feed this week?",
  "history": [
    { "role": "user", "content": "Previous user question" },
    { "role": "system", "content": "Previous assistant answer" }
  ]
}
```

Rules:

- `message` is required, must be a non-empty string, and is capped at 1000 characters after trimming.
- `history` is optional.
- `history` must be an array with at most 20 items.
- Each history item must have `role` of `user` or `system` and non-empty string `content`.
- Each history item `content` is capped at 4000 characters after trimming.

### Success Response

Status: `200`

Headers:

- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`

SSE chunks:

```text
data: {"text":"partial answer"}

data: [DONE]
```

Provider errors after streaming starts are returned as SSE error chunks:

```text
data: {"error":"Failed to generate an AI response."}
```

### Failure Responses

- `400` for malformed JSON or invalid input.
- `401` for missing or invalid session.
- `500` when `GEMINI_API_KEY` is not configured or chat startup fails.

## Existing API Surface

- `GET /api/dashboard/summary`: authenticated dashboard aggregate summary.
- `GET /api/dashboard/cattle`: authenticated cattle list with cursor pagination and query validation.
- `GET /api/dashboard/sales`: authenticated sales list with cursor pagination and query validation.
- `POST /api/payments/prepare`: authenticated server-owned Toss Payments order preparation.
- `POST /api/payments/confirm`: authenticated payment confirmation and subscription activation.
