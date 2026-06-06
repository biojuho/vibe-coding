const BLOCKED_REDIRECT_PREFIXES = ["/api/", "/_next/"];

function isBlockedRedirectPath(pathname) {
	return pathname === "/login" || BLOCKED_REDIRECT_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export function getSafeLoginRedirectTarget(locationHref) {
	if (typeof locationHref !== "string" || locationHref.length === 0) {
		return "/";
	}

	try {
		const currentUrl = new URL(locationHref);
		const callbackUrl = currentUrl.searchParams.get("callbackUrl");
		if (!callbackUrl) {
			return "/";
		}

		const redirectUrl = new URL(callbackUrl, currentUrl.origin);
		if (redirectUrl.origin !== currentUrl.origin || isBlockedRedirectPath(redirectUrl.pathname)) {
			return "/";
		}

		return `${redirectUrl.pathname}${redirectUrl.search}${redirectUrl.hash}` || "/";
	} catch {
		return "/";
	}
}
