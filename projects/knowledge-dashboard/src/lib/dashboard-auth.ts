import { createHmac, timingSafeEqual } from "node:crypto";

import type { NextRequest, NextResponse } from "next/server";

export const DASHBOARD_SESSION_COOKIE = "knowledge_dashboard_session";
export const DASHBOARD_SESSION_TTL_SEC = 60 * 60 * 12;

function createSessionSignature(issuedAt: string, validKey: string) {
	return createHmac("sha256", validKey).update(issuedAt).digest("base64url");
}

function safeEqual(left: string, right: string) {
	const leftBuffer = Buffer.from(left);
	const rightBuffer = Buffer.from(right);

	if (leftBuffer.length !== rightBuffer.length) {
		return false;
	}

	return timingSafeEqual(leftBuffer, rightBuffer);
}

export function getDashboardApiKey() {
	return process.env.DASHBOARD_API_KEY?.trim() || null;
}

// Constant-time comparison of a client-supplied key against the configured key.
// Used by the session-exchange route so the primary credential check does not
// leak length/prefix information through response timing.
export function verifyDashboardApiKey(candidate: string, validKey: string) {
	if (!candidate) {
		return false;
	}

	return safeEqual(candidate, validKey);
}

// The secret used to sign session cookies. Defaults to the API key so existing
// single-secret deploys keep working, but a dedicated DASHBOARD_SESSION_SECRET
// lets operators rotate the signing key (invalidating all sessions) WITHOUT
// changing the user-facing login key or breaking Bearer ops integrations.
export function getSessionSigningSecret(validKey: string) {
	return process.env.DASHBOARD_SESSION_SECRET?.trim() || validKey;
}

// Login-CSRF guard. Browsers send Sec-Fetch-Site on every request; a genuine
// cross-site POST is "cross-site". Server-to-server callers (ops/smoke) omit the
// header entirely, so absence is treated as allowed. The JSON content-type
// already blocks classic cross-site form posts; this closes the residual gap.
export function isSameOriginRequest(request: { headers: Headers }) {
	const site = request.headers.get("sec-fetch-site");
	return site !== "cross-site";
}

export function createDashboardSessionToken(
	validKey: string,
	now = Date.now(),
) {
	const issuedAt = `${now}`;
	const signature = createSessionSignature(issuedAt, validKey);
	return `${issuedAt}.${signature}`;
}

export function verifyDashboardSessionToken(
	token: string | undefined,
	validKey: string,
	now = Date.now(),
) {
	if (!token) {
		return false;
	}

	const [issuedAt, signature] = token.split(".");
	if (!issuedAt || !signature) {
		return false;
	}

	const issuedAtMs = Number(issuedAt);
	if (!Number.isFinite(issuedAtMs)) {
		return false;
	}

	const expiresAt = issuedAtMs + DASHBOARD_SESSION_TTL_SEC * 1000;
	const allowedClockSkewMs = 5 * 60 * 1000;

	if (issuedAtMs > now + allowedClockSkewMs || expiresAt <= now) {
		return false;
	}

	const expectedSignature = createSessionSignature(issuedAt, validKey);
	return safeEqual(signature, expectedSignature);
}

export function applyDashboardSession(
	response: NextResponse,
	validKey: string,
) {
	response.cookies.set(
		DASHBOARD_SESSION_COOKIE,
		createDashboardSessionToken(getSessionSigningSecret(validKey)),
		{
			httpOnly: true,
			sameSite: "lax",
			secure: process.env.NODE_ENV === "production",
			path: "/",
			maxAge: DASHBOARD_SESSION_TTL_SEC,
		},
	);

	return response;
}

export function clearDashboardSession(response: NextResponse) {
	response.cookies.set(DASHBOARD_SESSION_COOKIE, "", {
		httpOnly: true,
		sameSite: "lax",
		secure: process.env.NODE_ENV === "production",
		path: "/",
		maxAge: 0,
	});

	return response;
}

export function isDashboardRequestAuthorized(request: NextRequest) {
	const validKey = getDashboardApiKey();
	if (!validKey) {
		return {
			ok: false as const,
			status: 503,
			message: "Dashboard API key is not configured",
		};
	}

	const authHeader = request.headers.get("authorization");
	if (authHeader?.startsWith("Bearer ")) {
		// Constant-time check of the ops Bearer credential (see verifyDashboardApiKey).
		if (safeEqual(authHeader.slice("Bearer ".length), validKey)) {
			return { ok: true as const, validKey };
		}
	}

	const sessionToken = request.cookies.get(DASHBOARD_SESSION_COOKIE)?.value;
	if (
		verifyDashboardSessionToken(sessionToken, getSessionSigningSecret(validKey))
	) {
		return { ok: true as const, validKey };
	}

	return { ok: false as const, status: 401, message: "Unauthorized" };
}
