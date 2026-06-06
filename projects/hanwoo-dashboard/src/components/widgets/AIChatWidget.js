"use client";

import { Bot, Loader2, Send, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { focusElementSafely } from "@/lib/safeFocus";

const INITIAL_MESSAGES = [
	{
		role: "system",
		content:
			"안녕하세요. Joolife AI 농장 비서입니다.\n발정, 사양, 급여, 시세 등 궁금한 점을 질문해 주세요.",
	},
];

const CHAT_CONNECTION_ERROR_MESSAGE =
	"AI 비서 연결이 잠시 불안정합니다. 잠시 후 다시 질문해 주세요.";
const STREAMING_PLACEHOLDER_MESSAGE = "답변 생성 중입니다...";
const FALLBACK_GUIDE_PREFIX =
	"AI 연결이 불안정해 기본 운영 가이드로 먼저 안내합니다. 최신 농장 정보 기반 답변은 잠시 후 다시 시도해 주세요.";

const CHAT_PANEL_ID = "ai-farm-assistant-chat";

function buildOfflineReply(question) {
	const q = question.toLowerCase();
	if (q.includes("발정")) {
		return "전제: 실시간 농장 정보가 연결되지 않아 일반적인 발정 확인 기준으로 안내합니다.\n오늘 확인할 것:\n- 승가 허용, 꼬리 들기, 외음부 점액, 활동량 증가를 같은 시간대에 2회 이상 확인하세요.\n- 이력번호와 마지막 관찰 시각을 기록하고, 12~18시간 내 수정 적기 여부를 점검하세요.\n- 발열, 식욕 저하, 통증처럼 질병 징후가 겹치면 수의사 상담을 우선하세요.\n다음에 확인할 정보: 개체 이력번호, 마지막 발정일, 분만/수정 이력";
	}
	if (q.includes("급여") || q.includes("사료")) {
		return "전제: 실시간 사료 재고와 개체 체중을 확인하지 못해 일반 기준으로 안내합니다.\n바로 할 일:\n- 송아지는 초기 사료와 건초 섭취량을 함께 기록하세요.\n- 번식우는 과비를 피하도록 체형 점수와 섭취량을 같이 확인하세요.\n- 비육우는 후기 사료 비중을 급격히 바꾸지 말고 단계적으로 조정하세요.\n다음에 확인할 정보: 개체군, 평균 체중, 현재 급여량, 남은 사료 재고";
	}
	if (q.includes("안녕")) {
		return "안녕하세요. 오늘 농장 운영에서 궁금한 부분을 질문해 주세요.";
	}
	return "전제: 실시간 농장 정보가 연결되지 않아 일반 운영 기준으로 안내합니다.\n바로 할 일:\n- 질문에 관련된 개체 이력번호, 날짜, 증상, 기록값을 먼저 정리하세요.\n- 발정, 급여, 건강관리, 출하, 재고처럼 한 가지 주제로 좁혀 다시 질문하면 더 정확합니다.\n- 응급 질병이나 통증 징후가 있으면 기록보다 수의사 상담을 우선하세요.\n다음에 확인할 정보: 주제, 개체 이력번호, 관찰 시각, 최근 변경 사항";
}

function shouldUseFallbackGuide(errorMsg) {
	const message = typeof errorMsg === "string" ? errorMsg : "";
	const nonRecoverableErrors = [
		"로그인이 필요",
		"질문은",
		"대화 이력",
		"요청 본문",
	];

	return !nonRecoverableErrors.some((token) => message.includes(token));
}

function buildFallbackGuide(question) {
	return `${FALLBACK_GUIDE_PREFIX}\n\n${buildOfflineReply(question)}`;
}

function buildApiHistory(messages) {
	const history = [];
	let hasUserTurn = false;

	messages.forEach((message) => {
		if (!message.content) return;
		if (message.role === "user") {
			hasUserTurn = true;
			history.push({ role: "user", content: message.content });
		} else if (hasUserTurn && message.role === "system") {
			history.push({ role: "system", content: message.content });
		}
	});

	return history;
}

function normalizeStreamChatOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

async function streamChat(options = {}) {
	const {
		message,
		history,
		signal,
		onChunk,
		onDone,
		onError,
	} = normalizeStreamChatOptions(options);
	const handleChunk = typeof onChunk === "function" ? onChunk : () => {};
	const handleDone = typeof onDone === "function" ? onDone : () => {};
	const handleError = typeof onError === "function" ? onError : () => {};

	try {
		const res = await fetch("/api/ai/chat", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ message, history }),
			signal,
		});

		if (!res.ok) {
			const body = await res.json().catch(() => ({}));
			handleError(
				(typeof body.error === "string" && body.error.trim()) ||
					(typeof body.message === "string" && body.message.trim()) ||
					`서버 오류 (${res.status})`,
			);
			return;
		}

		if (!res.body) {
			throw new Error("응답 스트림을 열 수 없습니다.");
		}

		const reader = res.body.getReader();
		const decoder = new TextDecoder();
		let buffer = "";

		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });
			const lines = buffer.split("\n");
			buffer = lines.pop() || "";

			for (const line of lines) {
				const trimmed = line.trim();
				if (!trimmed.startsWith("data: ")) continue;
				const payload = trimmed.slice(6);

				if (payload === "[DONE]") {
					handleDone();
					return;
				}

				try {
					const parsed = JSON.parse(payload);
					if (parsed.error) {
						handleError(parsed.error);
						return;
					}
					if (parsed.text) {
						handleChunk(parsed.text);
					}
				} catch {
					/* ignore malformed JSON chunks */
				}
			}
		}
		handleDone();
	} catch (error) {
		if (error.name !== "AbortError") {
			console.error("AI chat stream failed:", error);
			handleError(CHAT_CONNECTION_ERROR_MESSAGE);
		}
	}
}

export default function AIChatWidget() {
	const [isOpen, setIsOpen] = useState(false);
	const [messages, setMessages] = useState(INITIAL_MESSAGES);
	const [input, setInput] = useState("");
	const [isStreaming, setIsStreaming] = useState(false);
	const scrollRef = useRef(null);
	const launcherRef = useRef(null);
	const panelRef = useRef(null);
	const inputRef = useRef(null);
	const abortRef = useRef(null);
	const isMountedRef = useRef(false);
	const sendInFlightRef = useRef(false);
	const shouldRestoreLauncherFocusRef = useRef(false);
	const canSend = input.trim().length > 0 && !isStreaming;
	const inputLabel = isStreaming
		? "답변 생성 중에는 질문을 입력할 수 없습니다"
		: "AI 농장 비서에게 보낼 질문";
	const sendButtonLabel = isStreaming
		? "답변 생성 중"
		: input.trim().length === 0
			? "질문을 입력하면 보낼 수 있습니다"
			: "질문 보내기";

	useEffect(() => {
		if (scrollRef.current) {
			scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
		}
	}, [isOpen, messages]);

	useEffect(() => {
		isMountedRef.current = true;

		return () => {
			isMountedRef.current = false;
			if (abortRef.current) {
				abortRef.current.abort();
				abortRef.current = null;
			}
			sendInFlightRef.current = false;
		};
	}, []);

	useEffect(() => {
		if (isOpen) {
			focusElementSafely(inputRef.current || panelRef.current);
			return;
		}

		if (shouldRestoreLauncherFocusRef.current) {
			shouldRestoreLauncherFocusRef.current = false;
			focusElementSafely(launcherRef.current);
		}
	}, [isOpen]);

	const closeWidget = useCallback(() => {
		if (abortRef.current) {
			abortRef.current.abort();
			abortRef.current = null;
		}
		sendInFlightRef.current = false;
		setIsStreaming(false);
		shouldRestoreLauncherFocusRef.current = true;
		setIsOpen(false);
	}, []);

	const handleSend = useCallback(async () => {
		const trimmed = input.trim();
		if (!trimmed || sendInFlightRef.current || isStreaming) return;

		sendInFlightRef.current = true;
		const userMessage = { role: "user", content: trimmed };
		const historyForApi = buildApiHistory(messages);

		setMessages((prev) => [...prev, userMessage]);
		setInput("");
		setIsStreaming(true);

		const controller = new AbortController();
		abortRef.current = controller;

		const streamingMsg = { role: "system", content: "" };
		setMessages((prev) => [...prev, streamingMsg]);

		let accumulated = "";

		await streamChat({
			message: trimmed,
			history: historyForApi,
			signal: controller.signal,
			onChunk: (text) => {
				if (!isMountedRef.current) {
					return;
				}
				accumulated += text;
				setMessages((prev) => {
					const updated = [...prev];
					updated[updated.length - 1] = {
						role: "system",
						content: accumulated,
					};
					return updated;
				});
			},
			onDone: () => {
				if (!isMountedRef.current) {
					return;
				}
				sendInFlightRef.current = false;
				setIsStreaming(false);
				if (abortRef.current === controller) {
					abortRef.current = null;
				}
			},
			onError: (errorMsg) => {
				const useFallbackGuide = shouldUseFallbackGuide(errorMsg);
				const fallbackMessage = useFallbackGuide
					? {
							role: "system",
							content: buildFallbackGuide(trimmed),
							retryQuestion: trimmed,
						}
					: { role: "system", content: `오류: ${errorMsg}` };

				if (!isMountedRef.current) {
					return;
				}

				setMessages((prev) => {
					const updated = [...prev];
					updated[updated.length - 1] = fallbackMessage;
					return updated;
				});
				sendInFlightRef.current = false;
				setIsStreaming(false);
				if (abortRef.current === controller) {
					abortRef.current = null;
				}
			},
		});

		if (isMountedRef.current && controller.signal.aborted && !accumulated) {
			setMessages((prev) => {
				const updated = [...prev];
				if (
					updated.at(-1)?.role === "system" &&
					updated.at(-1)?.content === ""
				) {
					updated.pop();
				}
				return updated;
			});
		}
		if (isMountedRef.current && abortRef.current === controller) {
			abortRef.current = null;
			sendInFlightRef.current = false;
			setIsStreaming(false);
		}
	}, [input, isStreaming, messages]);

	const handleKeyDown = (event) => {
		if (event.key === "Enter" && !event.shiftKey) {
			event.preventDefault();
			handleSend();
		}
	};

	const handleRetryQuestion = useCallback(
		(question) => {
			if (isStreaming || typeof question !== "string") return;
			const nextQuestion = question.trim();
			if (!nextQuestion) return;

			setInput(nextQuestion);
			requestAnimationFrame(() => {
				focusElementSafely(inputRef.current);
			});
		},
		[isStreaming],
	);

	const handlePanelKeyDown = (event) => {
		if (event.key === "Escape") {
			event.preventDefault();
			closeWidget();
		}
	};

	if (!isOpen) {
		return (
			<button
				ref={launcherRef}
				type="button"
				aria-haspopup="dialog"
				aria-expanded="false"
				aria-controls={CHAT_PANEL_ID}
				onClick={() => setIsOpen(true)}
				className="animate-scaleIn"
				style={{
					position: "fixed",
					bottom: "90px",
					right: "20px",
					width: "60px",
					height: "60px",
					borderRadius: "var(--radius-full)",
					background:
						"linear-gradient(135deg, var(--color-primary-light), var(--color-primary))",
					color: "white",
					boxShadow: "0 6px 20px rgba(62, 47, 28, 0.4)",
					border: "none",
					fontSize: "26px",
					cursor: "pointer",
					zIndex: 999,
					transition: "all var(--transition-normal)",
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
				}}
				aria-label="AI 농장 비서 열기"
				title="AI 농장 비서 열기"
			>
				<Bot size={25} aria-hidden="true" />
			</button>
		);
	}

	return (
		<div
			id={CHAT_PANEL_ID}
			ref={panelRef}
			className="animate-scaleIn"
			role="dialog"
			aria-modal="true"
			aria-label="AI 농장 비서 채팅"
			tabIndex={-1}
			onKeyDown={handlePanelKeyDown}
			style={{
				position: "fixed",
				bottom: "90px",
				right: "20px",
				width: "340px",
				height: "500px",
				background: "var(--color-bg-card)",
				borderRadius: "var(--radius-xl)",
				boxShadow: "var(--shadow-lg)",
				zIndex: 999,
				display: "flex",
				flexDirection: "column",
				overflow: "hidden",
				border: "1px solid var(--color-border)",
			}}
		>
			{/* Header */}
			<div
				style={{
					padding: "16px 20px",
					background:
						"linear-gradient(135deg, var(--color-primary-light), var(--color-primary))",
					color: "white",
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
				}}
			>
				<div
					style={{
						fontWeight: 700,
						fontSize: "15px",
						display: "flex",
						alignItems: "center",
						gap: "8px",
					}}
				>
					<Bot size={17} aria-hidden="true" />
					<span>AI 농장 비서</span>
					{isStreaming && (
						<span
							aria-hidden="true"
							style={{
								width: "8px",
								height: "8px",
								borderRadius: "50%",
								background: "#4ade80",
								animation: "pulse 1s infinite",
							}}
						/>
					)}
				</div>
				<button
					type="button"
					onClick={closeWidget}
					aria-label="AI 농장 비서 닫기"
					title="AI 농장 비서 닫기"
					style={{
						background: "rgba(255,255,255,0.2)",
						border: "none",
						color: "white",
						fontSize: "16px",
						cursor: "pointer",
						width: "28px",
						height: "28px",
						borderRadius: "var(--radius-full)",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
					}}
				>
					<X size={16} aria-hidden="true" />
				</button>
			</div>

			{/* Messages */}
			<div
				ref={scrollRef}
				role="log"
				aria-live="polite"
				aria-relevant="additions text"
				aria-busy={isStreaming}
				aria-label="AI 농장 비서 대화 내용"
				style={{
					flex: 1,
					padding: "18px",
					overflowY: "auto",
					background: "var(--color-border-light)",
					display: "flex",
					flexDirection: "column",
					gap: "14px",
				}}
			>
				{messages.map((message, index) => (
					<div
						key={`${message.role}-${index}`}
						className="animate-fadeInUp"
						style={{
							alignSelf: message.role === "user" ? "flex-end" : "flex-start",
							maxWidth: "85%",
							background:
								message.role === "user"
									? "linear-gradient(135deg, var(--color-primary-light), var(--color-primary))"
									: "var(--color-bg-card)",
							color: message.role === "user" ? "white" : "var(--color-text)",
							padding: "12px 16px",
							borderRadius: "var(--radius-lg)",
							borderBottomRightRadius:
								message.role === "user" ? "4px" : "var(--radius-lg)",
							borderTopLeftRadius:
								message.role === "system" ? "4px" : "var(--radius-lg)",
							fontSize: "13px",
							lineHeight: "1.6",
							boxShadow: "var(--shadow-sm)",
							whiteSpace: "pre-wrap",
						}}
					>
						{message.content ||
							(isStreaming && index === messages.length - 1
								? STREAMING_PLACEHOLDER_MESSAGE
								: "")}
						{message.retryQuestion && !isStreaming ? (
							<button
								type="button"
								onClick={() => handleRetryQuestion(message.retryQuestion)}
								aria-label="같은 질문을 입력창에 다시 넣기"
								title="같은 질문을 입력창에 다시 넣기"
								style={{
									marginTop: "10px",
									width: "100%",
									border: "1px solid var(--color-border)",
									borderRadius: "var(--radius-md)",
									background: "var(--color-bg-card)",
									color: "var(--color-primary)",
									fontWeight: 700,
									fontSize: "12px",
									padding: "8px 10px",
									cursor: "pointer",
								}}
							>
								같은 질문 다시 보내기
							</button>
						) : null}
					</div>
				))}
			</div>

			{/* Input */}
			<div
				style={{
					padding: "14px",
					background: "var(--color-bg-card)",
					borderTop: "1px solid var(--color-border)",
					display: "flex",
					gap: "10px",
				}}
			>
				<input
					ref={inputRef}
					type="text"
					value={input}
					onChange={(event) => setInput(event.target.value)}
					onKeyDown={handleKeyDown}
					aria-label={inputLabel}
					title={inputLabel}
					placeholder={
						isStreaming ? "답변 생성 중..." : "질문을 입력해 주세요."
					}
					disabled={isStreaming}
					className="input"
					style={{
						flex: 1,
						padding: "12px 16px",
						borderRadius: "var(--radius-full)",
						border: "1.5px solid var(--color-border)",
						fontSize: "13px",
						opacity: isStreaming ? 0.6 : 1,
					}}
				/>
				<button
					type="button"
					onClick={handleSend}
					disabled={!canSend}
					aria-busy={isStreaming}
					aria-label={sendButtonLabel}
					title={sendButtonLabel}
					className="btn btn-primary btn-icon"
					style={{
						width: "42px",
						height: "42px",
						padding: 0,
						fontSize: "16px",
						flexShrink: 0,
						opacity: canSend ? 1 : 0.6,
						cursor: canSend ? "pointer" : "not-allowed",
					}}
				>
					{isStreaming ? (
						<Loader2
							size={16}
							aria-hidden="true"
							style={{ animation: "spin 0.9s linear infinite" }}
						/>
					) : (
						<Send size={16} aria-hidden="true" />
					)}
				</button>
			</div>

			{/* Streaming indicators */}
			<style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
		</div>
	);
}
