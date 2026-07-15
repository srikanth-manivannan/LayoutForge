const { chromium } = require('playwright');
const path = require('path');
const HTML = process.argv[2];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 700, height: 700 } });
  await page.goto('file:///' + path.resolve(HTML).replace(/\\/g, '/'));
  await page.evaluate(() => document.fonts.ready);

  const report = await page.evaluate(() => {
    const results = {};
    for (const id of ['a', 'b', 'c']) {
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
        markerTop,
        offset: markerTop - rect.top,
      };
    }
    return results;
  });
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
