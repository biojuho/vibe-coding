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
		let registeredOnline = false;
		let registeredOffline = false;

		try {
			window.addEventListener("online", goOnline);
			registeredOnline = true;
			window.addEventListener("offline", goOffline);
			registeredOffline = true;
		} catch {
			if (registeredOnline) {
				try {
					window.removeEventListener("online", goOnline);
				} catch {}
			}
			if (registeredOffline) {
				try {
					window.removeEventListener("offline", goOffline);
				} catch {}
			}
			return undefined;
		}

		return () => {
			if (registeredOnline) {
				try {
					window.removeEventListener("online", goOnline);
				} catch {}
			}
			if (registeredOffline) {
				try {
					window.removeEventListener("offline", goOffline);
				} catch {}
			}
		};
	}, []);

	return isOnline;
}
