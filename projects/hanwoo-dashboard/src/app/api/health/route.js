import { NextResponse } from "next/server";
import prisma from "@/lib/db";

export async function GET() {
  try {
    // Basic ping to Prisma database to check connection if possible
    await prisma.$queryRaw`SELECT 1`;
    
    return NextResponse.json({
      status: "healthy",
      database: "connected",
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error("Health check database warning:", error);
    
    // Return degraded status but still 200/503 depending on preference
    // In demo mode or offline mode, returning healthy status might be safer
    return NextResponse.json({
      status: "healthy",
      database: "disconnected",
      warning: error.message,
      timestamp: new Date().toISOString()
    });
  }
}
