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
    const response = buildHealthResponse({
      connected: false,
      warning: error,
      timestamp: new Date().toISOString()
    });

    if (!isProductionLike) {
      console.error("Health check database warning:", response.body.warning);
    }

    return NextResponse.json(response.body, response.init);
  }
}
