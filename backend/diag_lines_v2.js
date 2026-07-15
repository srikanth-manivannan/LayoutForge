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
    const lines = Array.from(document.querySelectorAll('.lf-line'));
    return lines.map(lineEl => {
      const boxRect = lineEl.getBoundingClientRect();
      const lineCs = getComputedStyle(lineEl);
      const paraEl = lineEl.closest('.lf-paragraph');
      const paraCs = paraEl ? getComputedStyle(paraEl) : null;
      const paraRect = paraEl ? paraEl.getBoundingClientRect() : null;

      const marker = document.createElement('span');
      marker.style.display = 'inline-block';
      marker.style.width = '0';
      marker.style.height = '0';
      marker.style.verticalAlign = 'baseline';
      lineEl.insertBefore(marker, lineEl.firstChild);
      const baseline = marker.getBoundingClientRect().top;
      marker.remove();

      return {
        text: lineEl.textContent.trim().slice(0, 25),
        paraMarginTop: paraCs ? paraCs.marginTop : null,
        paraBoxTop: paraRect ? Math.round(paraRect.top * 1000) / 1000 : null,
        lineBoxTop: Math.round(boxRect.top * 1000) / 1000,
        lineMarginTop: lineCs.marginTop,
        lineLineHeight: lineCs.lineHeight,
        lineFontSize: lineCs.fontSize,
        baselineMarker: Math.round(baseline * 1000) / 1000,
        boxTopToBaseline: Math.round((baseline - boxRect.top) * 1000) / 1000,
      };
    });
  });
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
