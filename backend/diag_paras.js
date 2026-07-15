const { chromium } = require('playwright');
const path = require('path');
const PAGE_HTML = process.argv[2];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 700, height: 700 } });
  const fileUrl = 'file:///' + path.resolve(PAGE_HTML).replace(/\\/g, '/');
  await page.goto(fileUrl);
  await page.evaluate(() => document.fonts.ready);

  const report = await page.evaluate(() => {
    const paras = Array.from(document.querySelectorAll('.lf-paragraph'));
    return paras.map(p => {
      const r = p.getBoundingClientRect();
      const cs = getComputedStyle(p);
      return {
        text: p.textContent.trim().slice(0, 20),
        cssMarginTop: cs.marginTop,
        boxTop: Math.round(r.top * 1000) / 1000,
        boxBottom: Math.round(r.bottom * 1000) / 1000,
        boxHeight: Math.round(r.height * 1000) / 1000,
      };
    });
  });
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
