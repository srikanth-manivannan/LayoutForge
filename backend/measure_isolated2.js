const { chromium } = require('playwright');
const path = require('path');
const HTML = process.argv[2];
const ids = ['L9','L10','L12','L13_2','L15','L17','L19_86','L19_875','L22','L30','L50','Lnormal'];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 700, height: 1200 } });
  await page.goto('file:///' + path.resolve(HTML).replace(/\\/g, '/'));
  await page.evaluate(() => document.fonts.ready);

  const report = await page.evaluate((ids) => {
    const results = {};
    for (const id of ids) {
      const el = document.getElementById(id);
      const rect = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      const textNode = walker.nextNode();
      const marker = document.createElement('span');
      marker.style.display = 'inline-block';
      marker.style.width = '0';
      marker.style.height = '0';
      marker.style.verticalAlign = 'baseline';
      el.insertBefore(marker, el.firstChild);
      const markerTop = marker.getBoundingClientRect().top;
      marker.remove();
      results[id] = {
        lineHeight: cs.lineHeight,
        boxTop: rect.top,
        boxHeight: rect.height,
        markerTop,
        offset: markerTop - rect.top,
      };
    }
    return results;
  }, ids);
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
