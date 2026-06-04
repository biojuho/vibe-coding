import { access } from "node:fs/promises";

import { NextResponse } from "next/server";

import { getDashboardApiKey } from "@/lib/dashboard-auth";
import { dashboardDataFile } from "@/lib/dashboard-data";

export const dynamic = "force-dynamic";

// Unauthenticated liveness/readiness probe for load balancers, uptime monitors,
// and container orchestrators. It deliberately exposes only booleans (never the
// key value or data contents), so it is safe to leave open. Returns 503 while
// the hard requirement (DASHBOARD_API_KEY) is unset so a misconfigured deploy
// fails its health check instead of silently serving 401s to every user.
export async function GET() {
	const apiKeyConfigured = getDashboardApiKey() !== null;

	let dataPresent = false;
	try {
		await access(dashboardDataFile("dashboard_data.json"));
		dataPresent = true;
	} catch {
		dataPresent = false;
	}

	const healthy = apiKeyConfigured;

	return NextResponse.json(
		{
			status: healthy ? "ok" : "degraded",
			service: "knowledge-dashboard",
			timestamp: new Date().toISOString(),
			checks: { apiKeyConfigured, dataPresent },
		},
		{
			status: healthy ? 200 : 503,
			headers: { "cache-control": "no-store" },
		},
	);
}
