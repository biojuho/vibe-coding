import assert from "node:assert/strict";
import test from "node:test";

import {
	DASHBOARD_SESSION_COOKIE,
	DASHBOARD_SESSION_TTL_SEC,
	createDashboardSessionToken,
	getDashboardApiKey,
	isDashboardRequestAuthorized,
	verifyDashboardSessionToken,
} from "./dashboard-auth.ts";

const KEY = "super-secret-api-key";
const T0 = 1_700_000_000_000; // fixed reference instant (ms)
const TTL_MS = DASHBOARD_SESSION_TTL_SEC * 1000;
const SKEW_MS = 5 * 60 * 1000;

// `import type { NextRequest } from "next/server"` is erased at runtime, so a
// structural mock with the two accessors the helper touches is sufficient.
function mockRequest({
	authHeader,
	cookieToken,
}: {
	authHeader?: string;
	cookieToken?: string;
}) {
	return {
		headers: {
			get(name: string) {
				return name.toLowerCase() === "authorization"
					? (authHeader ?? null)
					: null;
			},
		},
		cookies: {
			get(name: string) {
				if (name === DASHBOARD_SESSION_COOKIE && cookieToken !== undefined) {
					return { value: cookieToken };
				}
				return undefined;
			},
		},
	} as unknown as Parameters<typeof isDashboardRequestAuthorized>[0];
}

function withApiKey<T>(value: string | undefined, run: () => T): T {
	const previous = process.env.DASHBOARD_API_KEY;
	if (value === undefined) {
		delete process.env.DASHBOARD_API_KEY;
	} else {
		process.env.DASHBOARD_API_KEY = value;
	}
	try {
		return run();
	} finally {
		if (previous === undefined) {
			delete process.env.DASHBOARD_API_KEY;
		} else {
			process.env.DASHBOARD_API_KEY = previous;
		}
	}
}

test("a freshly issued token verifies within its lifetime", () => {
	const token = createDashboardSessionToken(KEY, T0);
	assert.equal(verifyDashboardSessionToken(token, KEY, T0), true);
	// just before expiry
	assert.equal(
		verifyDashboardSessionToken(token, KEY, T0 + TTL_MS - 1000),
		true,
	);
});

test("a token is rejected once its TTL elapses", () => {
	const token = createDashboardSessionToken(KEY, T0);
	assert.equal(verifyDashboardSessionToken(token, KEY, T0 + TTL_MS + 1), false);
});

test("clock-skew window is honored but not exceeded", () => {
	// Issued slightly in the future but within the allowed skew.
	const within = createDashboardSessionToken(KEY, T0 + SKEW_MS - 1000);
	assert.equal(verifyDashboardSessionToken(within, KEY, T0), true);

	// Issued further in the future than the skew tolerance.
	const beyond = createDashboardSessionToken(KEY, T0 + SKEW_MS + 1000);
	assert.equal(verifyDashboardSessionToken(beyond, KEY, T0), false);
});

test("tampered signatures and wrong keys are rejected", () => {
	const token = createDashboardSessionToken(KEY, T0);
	const [issuedAt, signature] = token.split(".");

	const tampered = `${issuedAt}.${signature}x`;
	assert.equal(verifyDashboardSessionToken(tampered, KEY, T0), false);

	// Correct structure, different signing key.
	assert.equal(verifyDashboardSessionToken(token, "other-key", T0), false);

	// Forged issuedAt with the old signature.
	const forged = `${Number(issuedAt) + 1}.${signature}`;
	assert.equal(verifyDashboardSessionToken(forged, KEY, T0), false);
});

test("malformed, empty, and non-numeric tokens are rejected", () => {
	assert.equal(verifyDashboardSessionToken(undefined, KEY, T0), false);
	assert.equal(verifyDashboardSessionToken("", KEY, T0), false);
	assert.equal(verifyDashboardSessionToken("no-dot-here", KEY, T0), false);
	assert.equal(verifyDashboardSessionToken(".only-signature", KEY, T0), false);
	assert.equal(verifyDashboardSessionToken("issued-only.", KEY, T0), false);
	assert.equal(
		verifyDashboardSessionToken("notanumber.sig", KEY, T0),
		false,
	);
});

test("getDashboardApiKey trims and treats blank as unset", () => {
	assert.equal(
		withApiKey("  padded-key  ", () => getDashboardApiKey()),
		"padded-key",
	);
	assert.equal(
		withApiKey("   ", () => getDashboardApiKey()),
		null,
	);
	assert.equal(
		withApiKey(undefined, () => getDashboardApiKey()),
		null,
	);
});

test("isDashboardRequestAuthorized returns 503 when no key is configured", () => {
	withApiKey(undefined, () => {
		const result = isDashboardRequestAuthorized(
			mockRequest({ authHeader: `Bearer ${KEY}` }),
		);
		assert.equal(result.ok, false);
		assert.equal(result.ok === false && result.status, 503);
	});
});

test("a matching bearer header authorizes the request", () => {
	withApiKey(KEY, () => {
		const result = isDashboardRequestAuthorized(
			mockRequest({ authHeader: `Bearer ${KEY}` }),
		);
		assert.equal(result.ok, true);
	});
});

test("a valid session cookie authorizes the request", () => {
	withApiKey(KEY, () => {
		const token = createDashboardSessionToken(KEY);
		const result = isDashboardRequestAuthorized(
			mockRequest({ cookieToken: token }),
		);
		assert.equal(result.ok, true);
	});
});

test("missing/invalid credentials yield 401 when a key is configured", () => {
	withApiKey(KEY, () => {
		const noCreds = isDashboardRequestAuthorized(mockRequest({}));
		assert.equal(noCreds.ok, false);
		assert.equal(noCreds.ok === false && noCreds.status, 401);

		const wrongBearer = isDashboardRequestAuthorized(
			mockRequest({ authHeader: "Bearer nope" }),
		);
		assert.equal(wrongBearer.ok, false);
		assert.equal(wrongBearer.ok === false && wrongBearer.status, 401);

		const staleCookie = isDashboardRequestAuthorized(
			mockRequest({ cookieToken: "0.deadbeef" }),
		);
		assert.equal(staleCookie.ok, false);
		assert.equal(staleCookie.ok === false && staleCookie.status, 401);
	});
});
