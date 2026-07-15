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

    function measureLine(lineEl) {
      const cs = getComputedStyle(lineEl);
      // Whole-line ink rect: min top, min left, max right across every
      // character range (spans multiple text nodes if the line has
      // style-differing runs).
      const walker = document.createTreeWalker(lineEl, NodeFilter.SHOW_TEXT);
      let node;
      let minTop = Infinity, minLeft = Infinity, maxRight = -Infinity;
      let firstNode = null, firstCharRect = null;
      const allText = [];
      while ((node = walker.nextNode())) {
        allText.push(node.textContent);
        const r = document.createRange();
        r.selectNodeContents(node);
        for (const rect of r.getClientRects()) {
          minTop = Math.min(minTop, rect.top);
          minLeft = Math.min(minLeft, rect.left);
          maxRight = Math.max(maxRight, rect.right);
        }
        if (!firstNode && node.textContent.length > 0) {
          firstNode = node;
        }
      }
      // Baseline: ink-top of the FIRST character + that character's own
      // actualBoundingBoxAscent (canvas-measured against the run's actual
      // computed font), tying the baseline to a specific, well-defined
      // glyph metric rather than a font-level nominal ascent.
      let baseline = null;
      if (firstNode) {
        const parentEl = firstNode.parentElement;
        const runCs = getComputedStyle(parentEl.tagName === 'SPAN' ? parentEl : lineEl);
        const r0 = document.createRange();
        r0.setStart(firstNode, 0);
        r0.setEnd(firstNode, 1);
        const rect0 = r0.getClientRects()[0];
        ctx.font = `${runCs.fontStyle} ${runCs.fontWeight} ${runCs.fontSize} ${runCs.fontFamily}`;
        const ch = firstNode.textContent[0];
        const m = ctx.measureText(ch);
        if (rect0) {
          baseline = rect0.top + m.actualBoundingBoxAscent;
        }
      }
      const text = allText.join('').trim();
      const words = text.split(/\s+/).filter(Boolean);
      return {
        text: text.slice(0, 50),
        firstWord: words[0] || '',
        lastWord: words[words.length - 1] || '',
        baseline,
        left: minLeft === Infinity ? null : minLeft,
        right: maxRight === -Infinity ? null : maxRight,
        width: (minLeft === Infinity || maxRight === -Infinity) ? null : maxRight - minLeft,
      };
    }

    const lines = Array.from(document.querySelectorAll('.lf-line'));
    return lines.map(measureLine);
  });
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
