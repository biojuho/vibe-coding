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

	assert.match(source, /AI 비서 설정/);
	assert.match(source, /설정 키/);
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
	assert.match(source, /focusElementSafely\(panelRef\.current\);/);
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
	assert.match(source, /궁금한 점을 질문해 주세요/);
	assert.doesNotMatch(source, /궁금한 점을 물어보세요/);
	assert.match(source, /오늘 농장 운영에서 궁금한 부분을 질문해 주세요/);
	assert.doesNotMatch(source, /오늘 농장 운영에서 어떤 부분이 궁금하신가요/);
	assert.match(source, /기본 농장 운영 질문 위주로 안내합니다/);
	assert.match(source, /구체적으로 질문해 주시면 더 정확히 안내합니다/);
	assert.doesNotMatch(source, /안내하고 있어요/);
	assert.doesNotMatch(source, /물어보시면 더 정확히 도와드릴게요/);
	assert.match(source, /<Bot size=\{25\} aria-hidden="true" \/>/);
	assert.doesNotMatch(source, /launcherRef\.current\?\.focus\(\)/);
	assert.doesNotMatch(source, /panelRef\.current\?\.focus\(\)/);
	assert.doesNotMatch(source, />AI\s*<\/button>/);
	assert.doesNotMatch(source, /aria-label="Send"/);
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
});
