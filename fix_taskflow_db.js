const { db } = require('./lib/prisma');

async function main() {
  const ws = await db.workspace.findUnique({ where: { id: 'ws_142835b98316485e' } });
  if (!ws) {
    console.log('Workspace ws_142835b98316485e not found');
    return;
  }
  console.log('Current fileData:', JSON.stringify(ws.fileData.dependencies));
  
  const updatedData = {
    ...ws.fileData,
    dependencies: {
      ...(ws.fileData.dependencies || {}),
      "debug": "^4.3.4",
      "follow-redirects": "^1.15.6"
    }
  };

  await db.workspace.update({
    where: { id: 'ws_142835b98316485e' },
    data: { fileData: updatedData }
  });
  console.log('Updated TaskFlow workspace dependencies in DB successfully!');
}

main().finally(() => db.$disconnect());
