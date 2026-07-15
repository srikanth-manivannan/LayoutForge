const { chromium } = require('playwright');
const path = require('path');
const PAGE_HTML = process.argv[2];
const NEEDLE = process.argv[3] || 'Copyright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 700, height: 700 } });
  const fileUrl = 'file:///' + path.resolve(PAGE_HTML).replace(/\\/g, '/');
  await page.goto(fileUrl);
  await page.evaluate(() => document.fonts.ready);

  const report = await page.evaluate((needle) => {
    const lines = Array.from(document.querySelectorAll('.lf-line'));
    const lineEl = lines.find(l => l.textContent.includes(needle));
    if (!lineEl) return { error: 'not found', candidates: lines.map(l => l.textContent.slice(0, 20)) };

    const pageEl = document.querySelector('.lf-page');
    const regionEl = lineEl.closest('.lf-region');
    const paraEl = lineEl.closest('.lf-paragraph');

    const pageRect = pageEl.getBoundingClientRect();
    const regionRect = regionEl.getBoundingClientRect();
    const lineRect = lineEl.getBoundingClientRect();
    const lineCs = getComputedStyle(lineEl);

    const marker = document.createElement('span');
    marker.style.display = 'inline-block';
    marker.style.width = '0';
    marker.style.height = '0';
    marker.style.verticalAlign = 'baseline';
    lineEl.insertBefore(marker, lineEl.firstChild);
    const markerRect = marker.getBoundingClientRect();
    marker.remove();

    return {
      text: lineEl.textContent,
      pageRect: { top: pageRect.top, left: pageRect.left },
      regionInlineTop: regionEl.style.top,
      regionInlineLeft: regionEl.style.left,
      regionRect: { top: regionRect.top, left: regionRect.left },
      lineInlineTop: lineCs.top,
      lineInlineLeft: lineCs.left,
      lineInlineLineHeight: lineCs.lineHeight,
      lineInlineFontSize: lineCs.fontSize,
      lineRect: { top: lineRect.top, left: lineRect.left, bottom: lineRect.bottom, height: lineRect.height },
      markerTop: markerRect.top,
      markerLeft: markerRect.left,
      devicePixelRatio: window.devicePixelRatio,
    };
  }, NEEDLE);
  console.log(JSON.stringify(report, null, 4));
  await browser.close();
})();
