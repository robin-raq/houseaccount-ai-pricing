// Phase 2 — Capture HouseAccount's visual style from the LIVE site only.
//
// Launches headless Chromium at 1440px desktop width, screenshots the homepage
// plus one or two discoverable sub-pages, and extracts REAL computed design
// tokens (getComputedStyle on representative elements, plus :root --vars).
//
// Writes:
//   design/home.png        full-page homepage screenshot
//   design/<name>.png      screenshots of discovered sub-pages
//   design/tokens.json     extracted tokens + capture report
// and prints tokens.json to stdout.
//
// Constraint: capture the SYSTEM (type, color, spacing, shape) only — never
// lift logos or proprietary imagery into shippable output.

import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '..');
const DESIGN_DIR = resolve(PROJECT_ROOT, 'design');

// Candidate homepages, tried in order. First that loads real content wins.
const HOME_CANDIDATES = [
  'https://houseaccount.com',
  'https://www.houseaccount.com',
  'https://start.houseaccount.com',
];

const VIEWPORT = { width: 1440, height: 900 };
const NAV_TIMEOUT = 45000;

// ---------------------------------------------------------------------------
// In-page extraction. Runs in the browser context; returns plain JSON.
// ---------------------------------------------------------------------------
function extractTokens() {
  const px = (v) => (v == null ? null : String(v).trim());
  const gcs = (el) => (el ? getComputedStyle(el) : null);

  // Pick the most prominent element matching any selector that is visible.
  const pick = (selectors) => {
    for (const sel of selectors) {
      const els = Array.from(document.querySelectorAll(sel));
      for (const el of els) {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        if (r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none') {
          return el;
        }
      }
    }
    return null;
  };

  // Heuristic: find the primary CTA button (largest, most saturated bg).
  const findPrimaryButton = () => {
    const candidates = Array.from(
      document.querySelectorAll(
        'button, a[role="button"], a.button, .btn, [class*="button"], [class*="Button"], input[type="submit"]'
      )
    );
    const scored = [];
    for (const el of candidates) {
      const r = el.getBoundingClientRect();
      if (r.width < 40 || r.height < 20) continue;
      const s = getComputedStyle(el);
      const bg = s.backgroundColor;
      // Skip transparent / white-ish backgrounds — those are secondary.
      const m = bg.match(/rgba?\(([^)]+)\)/);
      if (!m) continue;
      const [r0, g0, b0, a0 = 1] = m[1].split(',').map((n) => parseFloat(n));
      if (a0 < 0.5) continue;
      const isWhiteish = r0 > 235 && g0 > 235 && b0 > 235;
      if (isWhiteish) continue;
      // Saturation-ish score: distance from gray.
      const max = Math.max(r0, g0, b0);
      const min = Math.min(r0, g0, b0);
      const sat = max - min;
      const area = r.width * r.height;
      scored.push({ el, score: sat * 2 + area / 1000 });
    }
    scored.sort((a, b) => b.score - a.score);
    return scored.length ? scored[0].el : null;
  };

  const summarize = (el) => {
    if (!el) return null;
    const s = getComputedStyle(el);
    return {
      tag: el.tagName.toLowerCase(),
      fontFamily: px(s.fontFamily),
      fontSize: px(s.fontSize),
      fontWeight: px(s.fontWeight),
      lineHeight: px(s.lineHeight),
      letterSpacing: px(s.letterSpacing),
      color: px(s.color),
      backgroundColor: px(s.backgroundColor),
      borderRadius: px(s.borderRadius),
      borderColor: px(s.borderColor),
      borderWidth: px(s.borderWidth),
      padding: px(s.padding),
      boxShadow: px(s.boxShadow),
      textTransform: px(s.textTransform),
    };
  };

  // Representative elements.
  const bodyEl = document.body;
  const h1El = pick(['h1']);
  const h2El = pick(['h2']);
  const headingEl = h1El || h2El;
  const linkEl = pick(['nav a', 'header a', 'main a', 'a[href]']);
  const cardEl = pick([
    '[class*="card" i]',
    'article',
    '[class*="Card"]',
    'section [class*="box" i]',
    'li[class*="item" i]',
  ]);
  const primaryBtn = findPrimaryButton();

  // Page-level background: walk from body up/down for a real fill.
  const bodyBg = px(gcs(bodyEl)?.backgroundColor);
  const htmlBg = px(gcs(document.documentElement)?.backgroundColor);

  // :root custom properties.
  const rootVars = {};
  try {
    for (const sheet of Array.from(document.styleSheets)) {
      let rules;
      try {
        rules = sheet.cssRules;
      } catch {
        continue; // cross-origin sheet
      }
      if (!rules) continue;
      for (const rule of Array.from(rules)) {
        if (rule.selectorText && /(^|\s|,):root\b/.test(rule.selectorText) && rule.style) {
          for (const name of Array.from(rule.style)) {
            if (name.startsWith('--')) {
              rootVars[name] = rule.style.getPropertyValue(name).trim();
            }
          }
        }
      }
    }
  } catch {
    /* ignore */
  }
  // Also read computed --vars off documentElement (covers inline / runtime sets).
  const computedRoot = getComputedStyle(document.documentElement);
  // No direct enumeration of computed custom props; rely on stylesheet scan above.

  // Census of border-radius and box-shadow values actually in use, plus a
  // color frequency census across visible elements (backgrounds + text).
  const radiusCount = {};
  const shadowCount = {};
  const bgColorCount = {};
  const textColorCount = {};
  const all = Array.from(document.querySelectorAll('*')).slice(0, 4000);
  let visibleCount = 0;
  let totalVGap = 0;
  let gapSamples = 0;

  const bump = (obj, key) => {
    if (!key || key === 'none' || key === '0px' || key === 'rgba(0, 0, 0, 0)') return;
    obj[key] = (obj[key] || 0) + 1;
  };

  for (const el of all) {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    visibleCount++;
    bump(radiusCount, s.borderRadius);
    bump(shadowCount, s.boxShadow);
    bump(bgColorCount, s.backgroundColor);
    bump(textColorCount, s.color);
    // crude vertical-rhythm sample: margin-bottom on block-ish elements
    const mb = parseFloat(s.marginBottom);
    if (mb > 0 && mb < 200) {
      totalVGap += mb;
      gapSamples++;
    }
  }

  const topN = (obj, n) =>
    Object.entries(obj)
      .sort((a, b) => b[1] - a[1])
      .slice(0, n)
      .map(([value, count]) => ({ value, count }));

  return {
    title: document.title || null,
    url: location.href,
    rootVars,
    body: {
      ...summarize(bodyEl),
      resolvedBackground: bodyBg !== 'rgba(0, 0, 0, 0)' ? bodyBg : htmlBg,
    },
    heading: summarize(headingEl),
    h1: summarize(h1El),
    h2: summarize(h2El),
    link: summarize(linkEl),
    primaryButton: summarize(primaryBtn),
    card: summarize(cardEl),
    census: {
      visibleElements: visibleCount,
      borderRadius: topN(radiusCount, 6),
      boxShadow: topN(shadowCount, 5),
      backgroundColors: topN(bgColorCount, 8),
      textColors: topN(textColorCount, 6),
      avgVerticalGapPx: gapSamples ? Math.round(totalVGap / gapSamples) : null,
    },
  };
}

// ---------------------------------------------------------------------------
// Discover up to 2 important internal sub-pages from the nav.
// ---------------------------------------------------------------------------
async function discoverSubpages(page, origin) {
  const wanted = ['pricing', 'how-it-works', 'how_it_works', 'howitworks', 'providers', 'provider', 'about', 'services', 'homeowners'];
  const links = await page.evaluate(() => {
    const out = [];
    const seen = new Set();
    const scope = document.querySelector('nav, header') || document.body;
    for (const a of Array.from(scope.querySelectorAll('a[href]'))) {
      const href = a.getAttribute('href') || '';
      const text = (a.textContent || '').trim().toLowerCase();
      if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) continue;
      if (seen.has(href)) continue;
      seen.add(href);
      out.push({ href, text });
    }
    return out;
  });

  const picks = [];
  for (const w of wanted) {
    const hit = links.find(
      (l) => l.href.toLowerCase().includes(w) || l.text.includes(w.replace(/[-_]/g, ' '))
    );
    if (hit) {
      let abs;
      try {
        abs = new URL(hit.href, origin).href;
      } catch {
        continue;
      }
      // same-site only
      if (new URL(abs).origin !== new URL(origin).origin) continue;
      if (!picks.find((p) => p.url === abs)) {
        picks.push({ name: w.replace(/[-_]/g, '-'), url: abs });
      }
    }
    if (picks.length >= 2) break;
  }
  return picks;
}

// ---------------------------------------------------------------------------
async function loadPage(page, url) {
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    // best-effort network idle; don't fail the whole run if it never settles
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1200); // let fonts/CSS settle
    return true;
  } catch (err) {
    return err.message || String(err);
  }
}

async function main() {
  await mkdir(DESIGN_DIR, { recursive: true });

  const report = {
    capturedAt: new Date().toISOString(),
    viewport: VIEWPORT,
    pagesAttempted: [],
    pagesCaptured: [],
    pagesFailed: [],
    homepageUrl: null,
  };

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,
    userAgent:
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
  });
  const page = await context.newPage();

  let tokens = null;
  let homepageOrigin = null;

  // Try homepage candidates until one loads with real content.
  for (const candidate of HOME_CANDIDATES) {
    report.pagesAttempted.push(candidate);
    const res = await loadPage(page, candidate);
    if (res !== true) {
      report.pagesFailed.push({ url: candidate, reason: res });
      continue;
    }
    const finalUrl = page.url();
    homepageOrigin = new URL(finalUrl).origin;
    try {
      await page.screenshot({ path: resolve(DESIGN_DIR, 'home.png'), fullPage: true });
    } catch (e) {
      // fullPage can fail on huge/animated pages; fall back to viewport shot
      await page.screenshot({ path: resolve(DESIGN_DIR, 'home.png'), fullPage: false });
    }
    tokens = await page.evaluate(extractTokens);
    report.homepageUrl = finalUrl;
    report.pagesCaptured.push({ name: 'home', url: finalUrl, file: 'design/home.png' });
    break;
  }

  // Sub-pages (only if homepage loaded).
  const subTokens = [];
  if (homepageOrigin) {
    let subpages = [];
    try {
      subpages = await discoverSubpages(page, homepageOrigin);
    } catch {
      subpages = [];
    }
    const usedNames = new Set(['home']);
    for (const sp of subpages) {
      let name = sp.name;
      while (usedNames.has(name)) name += '-2';
      usedNames.add(name);
      report.pagesAttempted.push(sp.url);
      const res = await loadPage(page, sp.url);
      if (res !== true) {
        report.pagesFailed.push({ url: sp.url, reason: res });
        continue;
      }
      const file = `design/${name}.png`;
      try {
        await page.screenshot({ path: resolve(DESIGN_DIR, `${name}.png`), fullPage: true });
      } catch {
        await page.screenshot({ path: resolve(DESIGN_DIR, `${name}.png`), fullPage: false });
      }
      const t = await page.evaluate(extractTokens);
      subTokens.push({ name, ...t });
      report.pagesCaptured.push({ name, url: page.url(), file });
    }
  }

  await browser.close();

  const output = {
    report,
    tokens, // homepage tokens (primary source of truth)
    subpages: subTokens,
    measured: Boolean(tokens),
  };

  await writeFile(resolve(DESIGN_DIR, 'tokens.json'), JSON.stringify(output, null, 2), 'utf8');
  process.stdout.write(JSON.stringify(output, null, 2) + '\n');

  if (!tokens) {
    process.stderr.write(
      '\n[capture_style] WARNING: no homepage loaded — styling must be INFERRED.\n'
    );
    process.exitCode = 0; // do not stall the pipeline; downstream notes inference
  }
}

main().catch((err) => {
  process.stderr.write(`[capture_style] fatal: ${err && err.stack ? err.stack : err}\n`);
  process.exitCode = 1;
});
