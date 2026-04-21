import { PrismaClient } from '@/generated/prisma/client';
import { PrismaPg } from '@prisma/adapter-pg';

const createPrismaClient = () => {
  // Connection pool limits: match Supabase PgBouncer pool size
  const poolMax = process.env.NODE_ENV === 'production' ? 10 : 5;
  const logLevel = process.env.NODE_ENV === 'production' ? ['error'] : ['warn', 'error'];

  try {
    const adapter = new PrismaPg({
      connectionString: process.env.DATABASE_URL,
      ssl: { rejectUnauthorized: false }, // Supabase pooler requires SSL
      pool: {
        max: poolMax,
        idleTimeout: 20, // seconds — recycle idle connections
      },
    });

    return new PrismaClient({ adapter, log: logLevel });
  } catch {
    // When DATABASE_URL is invalid (e.g. CI smoke environments), the PrismaPg
    // adapter throws at construction time.  Fall back to a bare PrismaClient so
    // that Next.js can still register route handlers.  Any actual query will
    // fail at call-time, which auth-guard.js already converts to a 401.
    console.warn('[db] PrismaPg adapter creation failed – falling back to bare PrismaClient');
    return new PrismaClient({ log: logLevel });
  }
};

const globalForPrisma = globalThis;

const prisma = globalForPrisma.prisma ?? createPrismaClient();

export default prisma;

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;
