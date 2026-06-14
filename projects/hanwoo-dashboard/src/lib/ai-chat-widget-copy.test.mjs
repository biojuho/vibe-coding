import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

test("AI chat widget handles Korean configuration errors and exposes an accessible launcher", () => {
	const source = readSource("components/widgets/AIChatWidget.js");

	assert.match(
		source,
		/import \{ focusElementSafely \} from ["']@\/lib\/safeFocus["'];/,
	);

	assert.match(source, /AI 연결이 불안정해 기본 운영 가이드/);
	assert.match(source, /shouldUseFallbackGuide/);
	assert.match(
		source,
		/const STREAMING_PLACEHOLDER_MESSAGE = ["']답변 생성 중입니다\.\.\.["'];/,
	);
	assert.match(source, /aria-label="AI 농장 비서 열기"/);
	assert.match(source, /title="AI 농장 비서 열기"/);
	assert.match(source, /const launcherRef = useRef\(null\)/);
	assert.match(source, /const CHAT_PANEL_ID = "ai-farm-assistant-chat";/);
	assert.match(source, /aria-haspopup="dialog"/);
	assert.match(source, /aria-expanded="false"/);
	assert.match(source, /aria-controls=\{CHAT_PANEL_ID\}/);
	assert.match(source, /const shouldRestoreLauncherFocusRef = useRef\(false\)/);
	assert.match(source, /shouldRestoreLauncherFocusRef\.current = true/);
	assert.match(source, /focusElementSafely\(launcherRef\.current\);/);
	assert.match(source, /ref=\{launcherRef\}/);
	assert.match(source, /role="dialog"/);
	assert.match(source, /id=\{CHAT_PANEL_ID\}/);
	assert.match(source, /aria-modal="true"/);
	assert.match(
		source,
		/<span\s+aria-hidden="true"[\s\S]*?animation: ["']pulse 1s infinite["']/,
	);
	assert.match(source, /aria-label="AI 농장 비서 채팅"/);
	assert.match(source, /const panelRef = useRef\(null\)/);
	assert.match(source, /const inputRef = useRef\(null\)/);
	assert.match(source, /focusElementSafely\(inputRef\.current \|\| panelRef\.current\);/);
	assert.match(source, /ref=\{panelRef\}/);
	assert.match(source, /const isMountedRef = useRef\(false\)/);
	assert.match(source, /isMountedRef\.current = true;/);
	assert.match(source, /return \(\) => \{\s+isMountedRef\.current = false;/);
	assert.match(
		source,
		/if \(abortRef\.current\) \{\s+abortRef\.current\.abort\(\);\s+abortRef\.current = null;/,
	);
	assert.match(source, /tabIndex=\{-1\}/);
	assert.match(source, /role="log"/);
	assert.match(source, /aria-live="polite"/);
	assert.match(source, /aria-relevant="additions text"/);
	assert.match(source, /aria-busy=\{isStreaming\}/);
	assert.match(source, /aria-label="AI 농장 비서 대화 내용"/);
	assert.match(source, /STREAMING_PLACEHOLDER_MESSAGE/);
	assert.match(source, /if \(event\.key === ["']Escape["']\)/);
	assert.match(source, /closeWidget\(\)/);
	assert.match(
		source,
		/onClick=\{closeWidget\}[\s\S]*?aria-label="AI 농장 비서 닫기"[\s\S]*?title="AI 농장 비서 닫기"/,
	);
	assert.match(source, /const inputLabel = isStreaming/);
	assert.match(source, /답변 생성 중에는 질문을 입력할 수 없습니다/);
	assert.match(source, /AI 농장 비서에게 보낼 질문/);
	assert.match(source, /aria-label=\{inputLabel\}/);
	assert.match(source, /title=\{inputLabel\}/);
	assert.match(source, /ref=\{inputRef\}/);
	assert.match(source, /const sendButtonLabel = isStreaming/);
	assert.match(source, /input\.trim\(\)\.length === 0/);
	assert.match(source, /질문을 입력하면 보낼 수 있습니다/);
	assert.match(source, /aria-label=\{sendButtonLabel\}/);
	assert.match(source, /title=\{sendButtonLabel\}/);
	assert.match(
		source,
		/const sendButtonLabel = isStreaming\s+\? ["']답변 생성 중["']\s+:[\s\S]*?["']질문 보내기["'];/,
	);
	assert.doesNotMatch(source, /aria-label=\{isStreaming \? ["']답변 생성 중["']/);
	assert.doesNotMatch(source, /title=\{isStreaming \? ["']답변 생성 중["']/);
	assert.match(source, /AI 비서 연결이 잠시 불안정합니다/);
	assert.match(source, /const FALLBACK_GUIDE_PREFIX/);
	assert.match(source, /AI 연결이 불안정해 기본 운영 가이드로 먼저 안내합니다/);
	assert.match(source, /최신 농장 정보 기반 답변은 잠시 후 다시 시도해 주세요/);
	assert.match(source, /궁금한 점을 질문해 주세요/);
	assert.doesNotMatch(source, /궁금한 점을 물어보세요/);
	assert.match(source, /오늘 농장 운영에서 궁금한 부분을 질문해 주세요/);
	assert.doesNotMatch(source, /오늘 농장 운영에서 어떤 부분이 궁금하신가요/);
	assert.match(source, /전제: 실시간 농장 정보가 연결되지 않아 일반적인 발정 확인 기준으로 안내합니다/);
	assert.match(source, /오늘 확인할 것/);
	assert.match(source, /승가 허용/);
	assert.match(source, /수의사 상담을 우선하세요/);
	assert.match(source, /다음에 확인할 정보: 개체 이력번호/);
	assert.match(source, /function shouldUseFallbackGuide\(errorMsg\) \{/);
	assert.match(source, /const nonRecoverableErrors = \[/);
	assert.match(source, /function buildFallbackGuide\(question\) \{/);
	assert.match(source, /buildOfflineReply\(question\)/);
	assert.match(
		source,
		/if \(!res\.ok\) \{[\s\S]*?handleError\([\s\S]*?body\.error[\s\S]*?body\.message[\s\S]*?`서버 오류 \(\$\{res\.status\}\)`[\s\S]*?return;[\s\S]*?\}/,
	);
	assert.doesNotMatch(source, /throw new Error\(body\.error/);
	assert.doesNotMatch(source, /기본 농장 운영 질문 위주로 안내합니다/);
	assert.doesNotMatch(source, /구체적으로 질문해 주시면 더 정확히 안내합니다/);
	assert.doesNotMatch(source, /안내하고 있어요/);
	assert.doesNotMatch(source, /물어보시면 더 정확히 도와드릴게요/);
	assert.match(source, /<Bot size=\{25\} aria-hidden="true" \/>/);
	assert.doesNotMatch(source, /launcherRef\.current\?\.focus\(\)/);
	assert.doesNotMatch(source, /panelRef\.current\?\.focus\(\)/);
	assert.doesNotMatch(source, />AI\s*<\/button>/);
	assert.doesNotMatch(source, /aria-label="Send"/);
	assert.match(source, /function normalizeStreamChatOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(source, /async function streamChat\(options = \{\}\) \{/);
	assert.match(source, /\} = normalizeStreamChatOptions\(options\);/);
	assert.match(
		source,
		/const handleChunk = typeof onChunk === ["']function["'] \? onChunk : \(\) => \{\};/,
	);
	assert.match(
		source,
		/const handleDone = typeof onDone === ["']function["'] \? onDone : \(\) => \{\};/,
	);
	assert.match(
		source,
		/const handleError = typeof onError === ["']function["'] \? onError : \(\) => \{\};/,
	);
	assert.match(source, /handleDone\(\);/);
	assert.match(source, /handleError\(parsed\.error\);/);
	assert.match(source, /handleChunk\(parsed\.text\);/);
	assert.match(source, /handleError\(CHAT_CONNECTION_ERROR_MESSAGE\);/);
	assert.doesNotMatch(
		source,
		/async function streamChat\(\{\s+message,/,
	);
	assert.doesNotMatch(source, /onError\(parsed\.error\);/);
	assert.doesNotMatch(source, /onChunk\(parsed\.text\);/);
	assert.doesNotMatch(source, /onDone\(\);/);
	assert.doesNotMatch(source, /onError\(error\.message/);
});

test("AI chat send action is disabled until a question is ready", () => {
	const source = readSource("components/widgets/AIChatWidget.js");

	assert.match(source, /const sendInFlightRef = useRef\(false\)/);
	assert.match(
		source,
		/const canSend = input\.trim\(\)\.length > 0 && !isStreaming;/,
	);
	assert.match(source, /disabled=\{!canSend\}/);
	assert.match(source, /aria-busy=\{isStreaming\}/);
	assert.match(source, /opacity: canSend \? 1 : 0\.6/);
	assert.match(source, /cursor: canSend \? ["']pointer["'] : ["']not-allowed["']/);
	assert.match(
		source,
		/if \(!trimmed \|\| sendInFlightRef\.current \|\| isStreaming\) return;/,
	);
	assert.match(source, /sendInFlightRef\.current = true;/);
	assert.match(source, /onChunk: \(text\) => \{\s+if \(!isMountedRef\.current\) \{/);
	assert.match(
		source,
		/onDone: \(\) => \{\s+if \(!isMountedRef\.current\) \{\s+return;\s+\}\s+sendInFlightRef\.current = false;/,
	);
	assert.match(
		source,
		/onError: \(errorMsg\) => \{[\s\S]*?if \(!isMountedRef\.current\) \{\s+return;\s+\}[\s\S]*?sendInFlightRef\.current = false;[\s\S]*?setIsStreaming\(false\);/,
	);
	assert.match(source, /const useFallbackGuide = shouldUseFallbackGuide\(errorMsg\);/);
	assert.match(source, /content: buildFallbackGuide\(trimmed\)/);
	assert.match(source, /retryQuestion: trimmed/);
	assert.doesNotMatch(source, /const isApiKeyError =/);
	assert.match(
		source,
		/sendInFlightRef\.current = false;\s+setIsStreaming\(false\);\s+shouldRestoreLauncherFocusRef\.current = true;\s+setIsOpen\(false\);/,
	);
	assert.match(
		source,
		/if \(isMountedRef\.current && controller\.signal\.aborted && !accumulated\) \{/,
	);
	assert.match(
		source,
		/if \(isMountedRef\.current && abortRef\.current === controller\) \{/,
	);
	assert.match(source, /const handleRetryQuestion = useCallback\(/);
	assert.match(source, /setInput\(nextQuestion\);/);
	assert.match(source, /focusElementSafely\(inputRef\.current\);/);
	assert.match(source, /message\.retryQuestion && !isStreaming/);
	assert.match(source, /aria-label="같은 질문을 입력창에 다시 넣기"/);
	assert.match(source, /같은 질문 다시 보내기/);
});

test("AI chat panel keeps narrow mobile layout and icon actions touch safe", () => {
	const source = readSource("components/widgets/AIChatWidget.js");

	assert.match(source, /width: ["']min\(340px, calc\(100vw - 32px\)\)["']/);
	assert.match(
		source,
		/aria-label="AI 농장 비서 닫기"[\s\S]*?width: ["']44px["'][\s\S]*?height: ["']44px["']/,
	);
	assert.match(
		source,
		/aria-label=\{sendButtonLabel\}[\s\S]*?width: ["']44px["'][\s\S]*?height: ["']44px["']/,
	);
	assert.match(
		source,
		/aria-label="같은 질문을 입력창에 다시 넣기"[\s\S]*?minHeight: ["']44px["']/,
	);
	assert.doesNotMatch(source, /width: ["']28px["']/);
	assert.doesNotMatch(source, /height: ["']28px["']/);
	assert.doesNotMatch(source, /width: ["']42px["']/);
	assert.doesNotMatch(source, /height: ["']42px["']/);
});

test("AI chat route normalizes Gemini stream helper options before provider setup", () => {
	const route = readSource("app/api/ai/chat/route.js");

	assert.match(route, /function normalizeGeminiChatStreamOptions\(options\) \{/);
	assert.match(
		route,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(route, /function createGeminiChatStream\(options = \{\}\) \{/);
	assert.match(
		route,
		/\} = normalizeGeminiChatStreamOptions\(options\);/,
	);
	assert.match(route, /return createAiChatSseStream\(\{ chat, message \}\);/);
	assert.doesNotMatch(
		route,
		/function createGeminiChatStream\(\{\s+apiKey,/,
	);
});

test("AIChatWidget traps Tab focus in both premium chat panel and upsell panel", () => {
	const source = readSource("components/widgets/AIChatWidget.js");

	// Tab trap inside handlePanelKeyDown (shared by both panels via event.currentTarget)
	assert.match(source, /event\.key === ["']Tab["']/);
	assert.match(source, /event\.currentTarget/);
	assert.match(source, /querySelectorAll[\s\S]{0,200}button:not\(\[disabled\]\)/);
	assert.match(source, /document\.activeElement === first/);
	assert.match(source, /document\.activeElement === last/);
	assert.match(source, /event\.shiftKey/);

	// Upsell panel connects to handlePanelKeyDown and is focusable
	assert.match(source, /aria-label="AI 농장 비서 - 구독 필요"[\s\S]{0,200}tabIndex=\{-1\}/);
	assert.match(source, /aria-label="AI 농장 비서 - 구독 필요"[\s\S]{0,200}onKeyDown=\{handlePanelKeyDown\}/);
});
