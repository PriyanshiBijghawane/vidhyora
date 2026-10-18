const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

async function main() {
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
  }
}

main();
