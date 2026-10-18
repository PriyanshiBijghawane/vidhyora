const { db } = require('./lib/prisma');

async function main() {
  const ws = await db.workspace.findUnique({ where: { id: 'ws_142835b98316485e' } });
  if (!ws || !ws.fileData?.files) return;
  for (const [path, fObj] of Object.entries(ws.fileData.files)) {
    const code = typeof fObj === 'object' ? fObj.code : String(fObj);
    console.log(`=== ${path} ===`);
    code.split('\n').filter(l => l.trim().startsWith('import') || l.trim().startsWith('export')).forEach(l => console.log('  ', l));
  }
}

main().finally(() => db.$disconnect());
