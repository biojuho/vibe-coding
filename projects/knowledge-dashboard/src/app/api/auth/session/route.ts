import { NextResponse } from "next/server";

import {
	applyDashboardSession,
	clearDashboardSession,
	getDashboardApiKey,
	isDashboardRequestAuthorized,
	isSameOriginRequest,
	verifyDashboardApiKey,
} from "@/lib/dashboard-auth";
import { clientIpFromHeaders, SlidingWindowRateLimiter } from "@/lib/rate-limit";

export const dynamic = "force-dynamic";

// Best-effort brute-force guard: 10 failed-or-attempted logins per IP per minute.
// Single-instance/local-first, so an in-process limiter is sufficient.
const loginLimiter = new SlidingWindowRateLimiter({
	limit: 10,
	windowMs: 60_000,
});

export async function POST(request: Request) {
	// Login-CSRF guard: reject genuine cross-site browser POSTs.
	if (!isSameOriginRequest(request)) {
		return NextResponse.json({ error: "Cross-site request blocked" }, {
			status: 403,
		});
	}

	const validKey = getDashboardApiKey();
	if (!validKey) {
		return NextResponse.json(
			{ error: "Dashboard API key is not configured" },
			{ status: 503 },
		);
	}

	const clientIp = clientIpFromHeaders(request.headers);
	const limit = loginLimiter.check(clientIp);
	if (!limit.allowed) {
		return NextResponse.json(
			{ error: "Too many attempts. Try again later." },
			{
				status: 429,
				headers: { "retry-after": `${limit.retryAfterSec}` },
			},
		);
	}

	const payload = await request.json().catch(() => null);
	const apiKey =
		typeof payload?.apiKey === "string" ? payload.apiKey.trim() : "";

	if (!verifyDashboardApiKey(apiKey, validKey)) {
		return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
	}

	// Successful login clears the throttle so honest typo-then-correct flows
	// are not penalised.
	loginLimiter.reset(clientIp);
	return applyDashboardSession(NextResponse.json({ ok: true }), validKey);
}

export async function DELETE(request: Request) {
	if (!isSameOriginRequest(request)) {
		return NextResponse.json({ error: "Cross-site request blocked" }, {
			status: 403,
		});
	}

	return clearDashboardSession(NextResponse.json({ ok: true }));
}

export async function GET(request: import("next/server").NextRequest) {
	const auth = isDashboardRequestAuthorized(request);
	if (!auth.ok) {
		if (auth.status === 401) {
			return NextResponse.json({ authenticated: false });
		}

		return NextResponse.json(
			{ authenticated: false, error: auth.message },
			{ status: auth.status },
		);
	}

	return NextResponse.json({ authenticated: true });
}
