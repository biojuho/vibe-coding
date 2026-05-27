"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "joolife-theme";
const DARK_CLASS = "dark";

function getDocumentRoot() {
	if (typeof document === "undefined") {
		return null;
	}

	try {
		return document.documentElement;
	} catch {
		return null;
	}
}

function applyTheme(theme) {
	const root = getDocumentRoot();
	if (!root) {
		return;
	}

	try {
		root.setAttribute("data-theme", theme);
		root.classList.toggle(DARK_CLASS, theme === "dark");
	} catch {}
}

function getSystemTheme() {
	try {
		return window.matchMedia("(prefers-color-scheme: dark)").matches
			? "dark"
			: "light";
	} catch {
		return "light";
	}
}

function readStoredTheme() {
	if (typeof window === "undefined") {
		return "light";
	}

	try {
		const saved = localStorage.getItem(STORAGE_KEY);
		if (saved === "dark" || saved === "light") {
			return saved;
		}
	} catch {}

	return getSystemTheme();
}

function writeStoredTheme(theme) {
	try {
		localStorage.setItem(STORAGE_KEY, theme);
	} catch {}
}

export function useTheme() {
	const [theme, setTheme] = useState(() => readStoredTheme());

	useEffect(() => {
		applyTheme(theme);

		if (typeof window !== "undefined") {
			writeStoredTheme(theme);
		}
	}, [theme]);

	const toggleTheme = useCallback(() => {
		setTheme((prev) => {
			const next = prev === "light" ? "dark" : "light";
			return next;
		});
	}, []);

	return { theme, toggleTheme };
}
