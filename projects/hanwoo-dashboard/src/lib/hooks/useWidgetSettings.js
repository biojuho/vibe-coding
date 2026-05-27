"use client";

import { useState } from "react";

export const WIDGET_REGISTRY = [
	{ id: "weather", label: "날씨 / THI", icon: "🌤️", defaultOn: true },
	{ id: "market", label: "시세 정보", icon: "💰", defaultOn: true },
	{
		id: "notification",
		label: "알림 (발정/분만)",
		icon: "🔔",
		defaultOn: true,
	},
	{ id: "financial", label: "경영 분석 차트", icon: "📊", defaultOn: true },
	{
		id: "profitability",
		label: "출하 수익성 예측",
		icon: "📈",
		defaultOn: true,
	},
	{
		id: "aiInsight",
		label: "AI 인사이트",
		icon: "🤖",
		defaultOn: false,
		description: "켜면 농장 요약 정보를 AI 분석 API로 전송합니다.",
	},
	{ id: "estrus", label: "발정 알림 배너", icon: "💕", defaultOn: true },
	{ id: "calving", label: "분만 알림 배너", icon: "🍼", defaultOn: true },
	{ id: "stats", label: "핵심 통계", icon: "📈", defaultOn: true },
];

const WIDGETS_STORAGE_KEY = "joolife-widgets";
const WIDGET_ID_SET = new Set(WIDGET_REGISTRY.map((widget) => widget.id));

function getDefaultWidgetVisibility() {
	return Object.fromEntries(
		WIDGET_REGISTRY.map((widget) => [widget.id, widget.defaultOn]),
	);
}

function normalizeStoredWidgetVisibility(value) {
	const defaults = getDefaultWidgetVisibility();
	if (!value || typeof value !== "object" || Array.isArray(value)) {
		return defaults;
	}

	return Object.fromEntries(
		WIDGET_REGISTRY.map((widget) => [
			widget.id,
			typeof value[widget.id] === "boolean"
				? value[widget.id]
				: defaults[widget.id],
		]),
	);
}

function readStoredWidgetVisibility() {
	const defaults = getDefaultWidgetVisibility();
	if (typeof window === "undefined") return defaults;

	try {
		const saved = localStorage.getItem(WIDGETS_STORAGE_KEY);
		if (saved) {
			return normalizeStoredWidgetVisibility(JSON.parse(saved));
		}
	} catch {}

	return defaults;
}

function writeStoredWidgetVisibility(visibility) {
	try {
		localStorage.setItem(WIDGETS_STORAGE_KEY, JSON.stringify(visibility));
	} catch {}
}

/**
 * 위젯 ON/OFF 설정 훅.
 * localStorage에 영속화되며, WIDGET_REGISTRY 기본값과 merge됩니다.
 */
export function useWidgetSettings() {
	const [visible, setVisible] = useState(() => readStoredWidgetVisibility());

	const toggle = (id) => {
		if (!WIDGET_ID_SET.has(id)) {
			return;
		}

		setVisible((prev) => {
			const next = { ...prev, [id]: !prev[id] };
			writeStoredWidgetVisibility(next);
			return next;
		});
	};

	return { visible, toggle };
}
