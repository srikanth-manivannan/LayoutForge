const { chromium } = require('playwright');
const path = require('path');
const PAGE_HTML = process.argv[2];
const NEEDLE = process.argv[3];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 700, height: 700 } });
  await page.goto('file:///' + path.resolve(PAGE_HTML).replace(/\\/g, '/'));
  await page.evaluate(() => document.fonts.ready);

  const result = await page.evaluate((needle) => {
    const lines = Array.from(document.querySelectorAll('.lf-line'));
    for (const lineEl of lines) {
      const spans = Array.from(lineEl.querySelectorAll('span'));
      for (const span of spans) {
        if (span.textContent.includes(needle)) {
          const walker = document.createTreeWalker(span, NodeFilter.SHOW_TEXT);
          let node, minLeft = Infinity, maxRight = -Infinity;
          while ((node = walker.nextNode())) {
            const r = document.createRange();
            r.selectNodeContents(node);
            for (const rect of r.getClientRects()) {
              minLeft = Math.min(minLeft, rect.left);
              maxRight = Math.max(maxRight, rect.right);
            }
          }
          // caret position right after the span (start-of-next-sibling or end)
          const afterMarker = document.createElement('span');
          afterMarker.style.cssText = 'display:inline-block;width:0;height:0;vertical-align:baseline';
          span.after(afterMarker);
          const caretAfter = afterMarker.getBoundingClientRect().left;
          afterMarker.remove();
          const beforeMarker = document.createElement('span');
          beforeMarker.style.cssText = 'display:inline-block;width:0;height:0;vertical-align:baseline';
          span.before(beforeMarker);
          const caretBefore = beforeMarker.getBoundingClientRect().left;
          beforeMarker.remove();
          return {
            text: span.textContent,
            inkLeft: minLeft, inkRight: maxRight, inkWidth: maxRight - minLeft,
            caretBefore, caretAfter, caretWidth: caretAfter - caretBefore,
            computedLetterSpacing: getComputedStyle(span).letterSpacing,
          };
        }
      }
    }
    return null;
  }, NEEDLE);
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
})();
