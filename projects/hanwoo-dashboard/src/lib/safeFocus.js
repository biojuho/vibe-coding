export function focusElementSafely(element) {
	if (!element || typeof element.focus !== "function") {
		return;
	}

	try {
		element.focus();
	} catch {}
}
