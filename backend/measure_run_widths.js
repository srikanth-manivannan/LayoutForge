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
    function marker() {
      const m = document.createElement('span');
      m.style.display = 'inline-block';
      m.style.width = '0';
      m.style.height = '0';
      m.style.verticalAlign = 'baseline';
      return m;
    }

    const lines = Array.from(document.querySelectorAll('.lf-line'));
    return lines.map(lineEl => {
      // "Runs" here = every direct child of the line: text nodes (base
      // style) and <span style> elements (differing runs) — same
      // granularity as Rich IDM Run nodes, in DOM order.
      const children = Array.from(lineEl.childNodes).filter(
        n => n.nodeType === Node.TEXT_NODE ? n.textContent.length > 0 : true
      );
      const runs = [];
      // Insert boundary markers around every child, then measure each
      // marker's left position — a run's rendered advance width is the
      // distance between its start marker and its end marker, exactly
      // analogous to the PDF's pen-origin-to-pen-origin measurement.
      const boundaryMarkers = [];
      for (let i = 0; i < children.length; i++) {
        const startM = marker();
        lineEl.insertBefore(startM, children[i]);
        boundaryMarkers.push(startM);
      }
      const endM = marker();
      lineEl.appendChild(endM);
      boundaryMarkers.push(endM);

      const positions = boundaryMarkers.map(m => m.getBoundingClientRect().left);
      // clean up markers so text content stays exactly as it was
      boundaryMarkers.forEach(m => m.remove());

      for (let i = 0; i < children.length; i++) {
        const child = children[i];
        const text = child.nodeType === Node.TEXT_NODE ? child.textContent : child.textContent;
        const isSpan = child.nodeType === Node.ELEMENT_NODE;
        runs.push({
          text,
          isStyledSpan: isSpan,
          width: positions[i + 1] - positions[i],
        });
      }
      return {
        lineText: lineEl.textContent,
        runs,
      };
    });
  });
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
