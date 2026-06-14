// Standalone check of ui/mockup.html: loads it as a file://, captures console
// errors, clicks every nav tab, asserts each screen becomes visible, and
// screenshots two screens for a visual sanity check.
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const file = pathToFileURL(path.resolve('ui/mockup.html')).href;
const screens = ['estimate', 'evaluate', 'model', 'api'];
const errors = [];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push(String(e)));

await page.goto(file, { waitUntil: 'networkidle' });

for (const id of screens) {
  await page.click(`.nav button[data-screen="${id}"]`);
  await page.waitForTimeout(120);
  const visible = await page.isVisible(`#${id}.screen.active`);
  console.log(`screen ${id.padEnd(9)} -> ${visible ? 'OK visible' : 'FAIL hidden'}`);
  if (!visible) errors.push(`screen ${id} did not activate`);
}

// visual captures: estimate (default) and the OOD example on the same screen
await page.click('.nav button[data-screen="estimate"]');
await page.screenshot({ path: 'design/_mockup_estimate.png', fullPage: true });
await page.click('.chip[data-example="ood"]');
await page.waitForTimeout(150);
await page.screenshot({ path: 'design/_mockup_ood.png', fullPage: false });
await page.click('.nav button[data-screen="evaluate"]');
await page.waitForTimeout(150);
await page.screenshot({ path: 'design/_mockup_eval.png', fullPage: false });

await browser.close();
console.log(`\nconsole/page errors: ${errors.length}`);
errors.forEach(e => console.log('  ✗ ' + e));
process.exit(errors.length ? 1 : 0);
