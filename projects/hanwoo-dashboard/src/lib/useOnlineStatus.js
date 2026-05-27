"use client";

import { useEffect, useState } from "react";

function readNavigatorOnlineStatus() {
	if (typeof navigator === "undefined") {
		return true;
	}

	try {
		return navigator.onLine;
	} catch {
		return true;
	}
}

export function useOnlineStatus() {
	const [isOnline, setIsOnline] = useState(() => {
		if (typeof window === "undefined") {
			return true;
		}

		return readNavigatorOnlineStatus();
	});

	useEffect(() => {
		if (typeof window === "undefined") {
			return undefined;
		}

		const goOnline = () => setIsOnline(true);
		const goOffline = () => setIsOnline(false);

		try {
			window.addEventListener("online", goOnline);
			window.addEventListener("offline", goOffline);
		} catch {
			return undefined;
		}

		return () => {
			try {
				window.removeEventListener("online", goOnline);
				window.removeEventListener("offline", goOffline);
			} catch {}
		};
	}, []);

	return isOnline;
}
