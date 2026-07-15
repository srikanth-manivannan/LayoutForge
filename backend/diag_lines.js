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
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const lines = Array.from(document.querySelectorAll('.lf-line'));
    return lines.map(lineEl => {
      const boxRect = lineEl.getBoundingClientRect();
      const lineCs = getComputedStyle(lineEl);
      const walker = document.createTreeWalker(lineEl, NodeFilter.SHOW_TEXT);
      const firstNode = walker.nextNode();
      if (!firstNode) return { text: '(empty)' };
      const parentEl = firstNode.parentElement;
      const runCs = getComputedStyle(parentEl);
      const r0 = document.createRange();
      r0.setStart(firstNode, 0);
      r0.setEnd(firstNode, 1);
      const rect0 = r0.getClientRects()[0];
      const fontStr = `${runCs.fontStyle} ${runCs.fontWeight} ${runCs.fontSize} ${runCs.fontFamily}`;
      ctx.font = fontStr;
      const ch = firstNode.textContent[0];
      const m = ctx.measureText(ch);
      return {
        text: lineEl.textContent.trim().slice(0, 20),
        char: ch,
        boxTop: Math.round(boxRect.top * 1000) / 1000,
        inkTop: rect0 ? Math.round(rect0.top * 1000) / 1000 : null,
        lineFontSize: lineCs.fontSize,
        lineLineHeight: lineCs.lineHeight,
        lineMarginTop: lineCs.marginTop,
        runFontSize: runCs.fontSize,
        runFontFamily: runCs.fontFamily,
        canvasFontStr: fontStr,
        actualBoundingBoxAscent: m.actualBoundingBoxAscent,
        fontBoundingBoxAscent: m.fontBoundingBoxAscent,
        reconstructedBaseline: (rect0 ? rect0.top : null) + m.actualBoundingBoxAscent,
        reconstructedBaselineFontBox: (rect0 ? rect0.top : null) + m.fontBoundingBoxAscent,
      };
    });
  });
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
