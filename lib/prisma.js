import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";
import { Pool } from "pg";
import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "@prisma/client";

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);

// Ensure environment variables are loaded accurately from both cwd and project directory
const projectRoot = path.resolve(dirname, "..");
dotenv.config({ path: path.resolve(projectRoot, ".env.local"), override: true });
dotenv.config({ path: path.resolve(projectRoot, ".env"), override: true });
dotenv.config({ path: path.resolve(process.cwd(), ".env.local"), override: true });
dotenv.config({ path: path.resolve(process.cwd(), ".env"), override: true });

const globalForPrisma = globalThis;

const connectionString =
  process.env.DATABASE_URL || process.env.DIRECT_URL;

if (!connectionString) {
  throw new Error(
    "DATABASE_URL or DIRECT_URL is not configured in environment variables."
  );
}

// Invalidate stale client if connection configuration changed during dev server lifecycle
if (globalForPrisma.prisma && globalForPrisma._currentDbUrl !== connectionString) {
  try {
    globalForPrisma.prisma.$disconnect?.().catch(() => {});
  } catch (_) {}
  globalForPrisma.prisma = undefined;
}

function parseDatabaseUrl(url) {
  try {
    const u = new URL(url);
    return {
      connectionString: url,
      user: decodeURIComponent(u.username),
      password: decodeURIComponent(u.password),
      host: u.hostname,
      port: parseInt(u.port, 10) || 5432,
      database: u.pathname.replace(/^\//, "") || "postgres",
    };
  } catch (_) {
    return { connectionString: url };
  }
}

function createPrismaClient() {
  const dbConfig = parseDatabaseUrl(connectionString);
  const pool = new Pool({
    connectionString: dbConfig.connectionString || connectionString,
    connectionTimeoutMillis: 20000,
    idleTimeoutMillis: 30000,
    keepAlive: true,
    ssl: { rejectUnauthorized: false },
  });

  const adapter = new PrismaPg(pool);
  globalForPrisma._currentDbUrl = connectionString;
  return new PrismaClient({ adapter });
}

export const db = globalForPrisma.prisma ?? createPrismaClient();

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = db;

