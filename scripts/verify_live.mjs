// Live-verify the deployed (or local) app: load it, exercise a real estimate,
// confirm the evaluation numbers render, capture console errors + screenshots.
// Usage: node scripts/verify_live.mjs [baseUrl]
import { chromium } from 'playwright';

const base = process.argv[2] || 'http://127.0.0.1:3001';
const errors = [];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push(String(e)));

await page.goto(base, { waitUntil: 'networkidle' });

// 1) live model version pill populated from /demo/model
await page.waitForFunction(() => !/loading/.test(document.getElementById('ver')?.textContent || ''), { timeout: 15000 });
const ver = await page.textContent('#ver');
console.log('model pill:', ver.trim());

// 2) run a real estimate via an example chip (POSTs /demo/estimates)
await page.click('.chip[data-ex="water"]');
await page.waitForSelector('#resultBody', { state: 'visible', timeout: 20000 });
await page.waitForFunction(() => document.querySelector('#resultBody .price-big'), { timeout: 20000 });
const price = await page.textContent('#resultBody .price-big');
const conf = await page.textContent('#resultBody .conf-val');
console.log('estimate rendered:', price.trim(), '| confidence', conf.trim());
await page.screenshot({ path: 'design/_live_estimate.png', fullPage: false });

// 2b) manual field edit + Get estimate button (a novel description, not a cached pill)
await page.fill('#f-zip', '60614');
await page.fill('#f-desc', 'Install a new 240V outlet for an EV charger in the garage');
await page.click('#getBtn');
await page.waitForFunction(() => document.querySelector('#resultBody .price-big'), { timeout: 15000 });
console.log('manual edit + Get estimate:', (await page.textContent('#resultBody .price-big')).trim());

// 3) OOD example
await page.click('.chip[data-ex="ood"]');
await page.waitForTimeout(2500);
const oodTag = await page.textContent('#resultBody .tag-warn').catch(() => null);
console.log('OOD example tag:', oodTag ? oodTag.trim().slice(0, 60) + '…' : '(none)');

// 4) evaluation screen with live numbers
await page.click('.nav button[data-screen="evaluate"]');
await page.waitForFunction(() => !/—/.test(document.getElementById('evBlended')?.textContent || document.querySelector('#evalCards .big')?.textContent || '—'), { timeout: 10000 }).catch(() => {});
await page.waitForTimeout(500);
await page.screenshot({ path: 'design/_live_eval.png', fullPage: false });
const badges = await page.$$eval('#evalCards .badge', els => els.map(e => e.textContent.trim()));
console.log('eval badges:', badges.join(' | '));

// 5) API screen recent log
await page.click('.nav button[data-screen="api"]');
await page.waitForTimeout(800);
await page.screenshot({ path: 'design/_live_api.png', fullPage: false });

await browser.close();
console.log(`\nconsole/page errors: ${errors.length}`);
errors.forEach(e => console.log('  ✗', e));
process.exit(errors.length ? 1 : 0);
