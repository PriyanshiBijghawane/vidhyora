const { Pool } = require('pg');
const { PrismaPg } = require('@prisma/adapter-pg');
const { PrismaClient } = require('@prisma/client');

async function main() {
  const connectionString = "postgresql://postgres.yntjarpcglijjentttak:R%40dhey20%2524@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres";
  const pool = new Pool({
    connectionString,
    connectionTimeoutMillis: 20000,
    keepAlive: true,
    ssl: { rejectUnauthorized: false }
  });

  const adapter = new PrismaPg(pool);
  const prisma = new PrismaClient({ adapter });

  const email = 'priyanshibijghavane14@gmail.com';
  const newClerkId = 'user_3F54FZu5ZEsHNzEZAdQRHG2QsyO';

  try {
    const user = await prisma.user.update({
      where: { email },
      data: { clerkId: newClerkId },
    });
    console.log('User updated successfully:', user);
  } catch (error) {
    console.error('Error updating user:', error);
  } finally {
    await prisma.$disconnect();
    await pool.end();
  }
}

main();
