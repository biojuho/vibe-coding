import { PrismaClient } from '@/generated/prisma/client';
import { PrismaPg } from '@prisma/adapter-pg';

const createPrismaClient = () => {
  // Connection pool limits: match Supabase PgBouncer pool size
  const poolMax = process.env.NODE_ENV === 'production' ? 10 : 5;

  const adapter = new PrismaPg({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }, // Supabase pooler requires SSL
    pool: {
      max: poolMax,
      idleTimeout: 20, // seconds — recycle idle connections
    },
  });

  return new PrismaClient({
    adapter,
    log: process.env.NODE_ENV === 'production' ? ['error'] : ['warn', 'error'],
  });
};

const globalForPrisma = globalThis;

const prisma = globalForPrisma.prisma ?? createPrismaClient();

export default prisma;

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;
