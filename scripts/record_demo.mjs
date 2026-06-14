// Record one screen-capture per narration beat, timed to the TTS manifest, so
// assemble_video.sh can pair clip_00N.mp4 with clip_00N.mp3.
// Usage: node scripts/record_demo.mjs <baseUrl> [clipsDir] [audioDir]
import { chromium } from 'playwright';
import { readFileSync, mkdirSync, renameSync } from 'node:fs';

const base = process.argv[2] || 'http://127.0.0.1:3001';
const clipsDir = process.argv[3] || 'demo/clips';
const audioDir = process.argv[4] || 'demo/audio';
mkdirSync(clipsDir, { recursive: true });

const manifest = JSON.parse(readFileSync(`${audioDir}/manifest.json`, 'utf8'));
const dur = id => (manifest.find(b => b.id === id)?.seconds || 30) * 1000;
const SIZE = { width: 1280, height: 800 };

// Per-beat: reach the state, do the highlighted action, hold to fill the narration.
const beats = {
  1: async p => { await goto(p); await p.waitForTimeout(dur(1)); },
  2: async p => { await goto(p); await p.click('.chip[data-ex="water"]');
    await p.waitForSelector('#resultBody .price-big', { timeout: 20000 }); await p.waitForTimeout(dur(2)); },
  3: async p => { await goto(p); await p.click('.chip[data-ex="water"]');
    await p.waitForSelector('#resultBody .price-big', { timeout: 20000 }).catch(()=>{});
    await p.waitForTimeout(1500); await p.click('.chip[data-ex="ood"]');
    await p.waitForTimeout(2500); await p.waitForTimeout(dur(3)); },
  4: async p => { await goto(p); await tab(p, 'evaluate'); await p.waitForTimeout(dur(4)); },
  5: async p => { await goto(p); await tab(p, 'evaluate'); await p.waitForTimeout(1500);
    await p.evaluate(() => document.querySelector('#catRows')?.scrollIntoView({behavior:'smooth'}));
    await p.waitForTimeout(dur(5)); },
  6: async p => { await goto(p); await tab(p, 'model'); await p.waitForTimeout(dur(6)); },
  7: async p => { await goto(p); await tab(p, 'model'); await p.waitForTimeout(1500);
    await p.evaluate(() => window.scrollTo({ top: 400, behavior: 'smooth' }));
    await p.waitForTimeout(dur(7)); },
  8: async p => { await goto(p); await tab(p, 'api'); await p.waitForTimeout(1500);
    await p.click('#runApi'); await p.waitForTimeout(2500); await p.waitForTimeout(dur(8)); },
  9: async p => { await goto(p); await tab(p, 'estimate'); await p.waitForTimeout(dur(9)); },
};

async function goto(p) {
  await p.goto(base, { waitUntil: 'networkidle' });
  await p.waitForFunction(() => !/loading/.test(document.getElementById('ver')?.textContent || ''), { timeout: 15000 }).catch(()=>{});
}
async function tab(p, name) {
  await p.click(`.nav button[data-screen="${name}"]`);
  await p.waitForTimeout(800);
}

const browser = await chromium.launch();
for (const id of Object.keys(beats).map(Number)) {
  const ctx = await browser.newContext({ viewport: SIZE, recordVideo: { dir: clipsDir, size: SIZE } });
  const page = await ctx.newPage();
  await beats[id](page);
  const video = page.video();
  await ctx.close();                       // finalizes the video file
  const tmp = await video.path();
  const target = `${clipsDir}/clip_${String(id).padStart(3, '0')}.mp4`;
  renameSync(tmp, target);
  console.log(`beat ${id} -> ${target}  (${(dur(id)/1000).toFixed(1)}s)`);
}
await browser.close();
console.log('done.');
