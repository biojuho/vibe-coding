import { NextResponse } from "next/server";
import { buildHealthResponse } from "@/lib/health-response.mjs";
import prisma from "@/lib/db";

export async function GET() {
  const isBuildPhase =
    process.env.NEXT_PHASE === "phase-production-build" ||
    process.env.CI === "1";

  if (isBuildPhase) {
    const response = buildHealthResponse({
      skipped: true,
      timestamp: new Date().toISOString()
    });
    return NextResponse.json(response.body, response.init);
  }

  try {
    // Basic ping to Prisma database to check connection if possible
    await prisma.$queryRaw`SELECT 1`;

    const response = buildHealthResponse({
      connected: true,
      timestamp: new Date().toISOString()
    });
    return NextResponse.json(response.body, response.init);
  } catch (error) {
    const isProductionLike = process.env.NODE_ENV === "production";

    // Always log server-side so operators see DB incidents in production
    // (the previous guard inverted this: it logged only in dev).
    console.error("Health check database warning:", error);

    // Never expose raw DB/infra error text (host, region, auth strings) to
    // anonymous callers in production; fall back to the generic warning.
    const response = buildHealthResponse({
      connected: false,
      warning: isProductionLike ? undefined : error,
      timestamp: new Date().toISOString()
    });

    return NextResponse.json(response.body, response.init);
  }
}
