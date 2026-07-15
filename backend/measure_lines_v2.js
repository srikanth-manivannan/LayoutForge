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
      // Baseline: insert a zero-size inline-block marker with
      // vertical-align:baseline as the line's first child. Per CSS2.1
      // 10.8, a replaced/inline-block element with no baseline of its
      // own uses its bottom margin edge as its baseline, which the
      // browser then aligns to the surrounding text's baseline exactly
      // — independent of font metrics, hinting, or canvas discrepancies.
      const marker = document.createElement('span');
      marker.style.display = 'inline-block';
      marker.style.width = '0';
      marker.style.height = '0';
      marker.style.verticalAlign = 'baseline';
      lineEl.insertBefore(marker, lineEl.firstChild);
      const baseline = marker.getBoundingClientRect().top;
      marker.remove();

      // Width / first-last word: ink extent via Range over all text nodes.
      const walker = document.createTreeWalker(lineEl, NodeFilter.SHOW_TEXT);
      let node;
      let minLeft = Infinity, maxRight = -Infinity;
      const allText = [];
      while ((node = walker.nextNode())) {
        allText.push(node.textContent);
        const r = document.createRange();
        r.selectNodeContents(node);
        for (const rect of r.getClientRects()) {
          minLeft = Math.min(minLeft, rect.left);
          maxRight = Math.max(maxRight, rect.right);
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
    });
  });
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
