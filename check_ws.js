const { db } = require('./lib/prisma');

async function main() {
  const wsList = await db.workspace.findMany();
  console.log('Workspaces count:', wsList.length);
  for (const ws of wsList) {
    console.log('ID:', ws.id, 'Title:', ws.title);
    console.log('Dependencies:', ws.fileData?.dependencies);
    if (ws.fileData?.files) {
      console.log('Files:', Object.keys(ws.fileData.files));
      for (const [path, fObj] of Object.entries(ws.fileData.files)) {
        const code = typeof fObj === 'object' ? fObj.code : String(fObj);
        if (code.includes('follow-redirects') || code.includes('axios') || code.includes('debug')) {
          console.log(`Matching imports in ${path}:`);
          code.split('\n').filter(l => l.includes('import') || l.includes('require')).forEach(l => console.log('  ', l));
        }
      }
    }
  }
}

main().finally(() => db.$disconnect());
