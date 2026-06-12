import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "@/generated/prisma/client";

/**
 * Prisma 7 DB Client — PrismaPg Driver Adapter + Supabase PgBouncer.
 *
 * Connection Pool 설정 근거 (2026 Best Practice):
 * - max: Supabase Free tier PgBouncer pool = 15, production = 60
 *        Node.js 워커 1개 기준 10 (prod) / 5 (dev) 안전 여유
 * - idleTimeout: 20s — idle 커넥션 빠른 회수 (서버리스 환경 최적)
 * - connectionTimeout: 10s — 느린 연결 빠르게 포기 + fallback 가능
 *
 * N+1 방지 가이드:
 *   ❌ const cattle = await prisma.cattle.findMany();
 *      for (const c of cattle) await prisma.building.findUnique({where:{id:c.buildingId}});
 *   ✅ const cattle = await prisma.cattle.findMany({ include: { building: true } });
 */
/**
 * Build the Postgres TLS config. Supabase requires SSL, but certificate
 * verification should be ON in production to prevent MITM. Configure via env:
 *   - DB_SSL_CA: the Supabase project CA certificate (PEM contents)
 *   - DB_SSL_REJECT_UNAUTHORIZED: "true" to verify (recommended in prod)
 * Defaults stay backward-compatible (no verification) so existing deployments
 * keep working until the CA is provisioned.
 */
export function buildDbSslConfig(env = process.env) {
	const ca =
		typeof env.DB_SSL_CA === "string" && env.DB_SSL_CA.trim()
			? env.DB_SSL_CA
			: undefined;
	const rejectUnauthorized = env.DB_SSL_REJECT_UNAUTHORIZED === "true";

	return ca ? { ca, rejectUnauthorized } : { rejectUnauthorized };
}

const createPrismaClient = () => {
	const poolMax = process.env.NODE_ENV === "production" ? 10 : 5;
	const logLevel =
		process.env.NODE_ENV === "production" ? ["error"] : ["warn", "error"];

	try {
		const adapter = new PrismaPg({
			connectionString: process.env.DATABASE_URL,
			ssl: buildDbSslConfig(), // configurable; see buildDbSslConfig
			pool: {
				max: poolMax,
				idleTimeout: 20, // seconds — recycle idle connections
				connectionTimeout: 10_000, // ms — fail fast on stale connections
			},
		});

		return new PrismaClient({ adapter, log: logLevel });
	} catch {
		// When DATABASE_URL is invalid (e.g. CI smoke environments), the PrismaPg
		// adapter throws at construction time.  Fall back to a bare PrismaClient so
		// that Next.js can still register route handlers.  Any actual query will
		// fail at call-time, which auth-guard.js already converts to a 401.
		console.warn(
			"[db] PrismaPg adapter creation failed – falling back to bare PrismaClient",
		);
		return new PrismaClient({ log: logLevel });
	}
};

const globalForPrisma = globalThis;

const prisma = globalForPrisma.prisma ?? createPrismaClient();

export default prisma;

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;
