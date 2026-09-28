// Renders the orb mark to PNG icons with headless Chromium (Playwright).
// Run once when the mark changes: `node scripts/make-icons.mjs` (needs Playwright + Chromium available).
import { chromium } from 'playwright';

const html = (size, pad) => `<!doctype html><html><body style="margin:0">
<div style="width:${size}px;height:${size}px;background:#F0E8DC;display:flex;align-items:center;justify-content:center">
  <div style="width:${size - pad * 2}px;height:${size - pad * 2}px;border-radius:50%;position:relative;
    background:conic-gradient(from 200deg,#B8893A,#6E4E88,#607D5A,#B5542E,#8A4860,#4A6E8A,#B8893A)">
    <div style="position:absolute;inset:${((size - pad * 2) * 0.135).toFixed(2)}px;border-radius:50%;background:#F0E8DC"></div>
  </div>
</div></body></html>`;

const targets = [
  ['public/icon-192.png', 192, 26],
  ['public/icon-512.png', 512, 70],
  ['public/apple-touch-icon.png', 180, 26],
  ['assets/icon.png', 1024, 150],
  ['assets/splash-icon.png', 512, 110],
  ['assets/favicon.png', 48, 4],
  ['assets/android-icon-foreground.png', 432, 110],
];

const browser = await chromium.launch();
const page = await browser.newPage();
for (const [out, size, pad] of targets) {
  await page.setViewportSize({ width: size, height: size });
  await page.setContent(html(size, pad));
  await page.screenshot({ path: out, clip: { x: 0, y: 0, width: size, height: size } });
  console.log('wrote', out);
}
await browser.close();
