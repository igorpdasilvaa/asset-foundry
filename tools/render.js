const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  // CHROME_PATH: usa um Chrome já instalado (sem baixar o Chromium do Playwright).
  const b = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
  const p = await b.newPage({ deviceScaleFactor: 2 });
  for (const f of process.argv.slice(2)) {
    const svg = fs.readFileSync(f, 'utf8');
    await p.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
    await p.locator('svg').first().screenshot({ path: f.replace('.svg', '.png'), omitBackground: true, timeout: 600000 });
  }
  await b.close();
})();
