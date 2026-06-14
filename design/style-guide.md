# HouseAccount — Style Guide (captured)

Reference for the UI builder. Tokens below were **measured live** from
`https://houseaccount.com` (homepage + `/providers` + `/about-us`) at 1440px
desktop width on 2026-06-14 via `scripts/capture_style.mjs`. Raw extraction lives
in `design/tokens.json`; reference screenshots in `design/home.png`,
`design/providers.png`, `design/about.png`.

> Screenshots are **references, not assets**. Capture the system (type, color,
> spacing, shape) — do not lift HouseAccount's logo or imagery into shippable UI.

---

## Character

Clean consumer-marketplace for home services — **trustworthy and approachable**,
built on a confident **deep-navy** base with one warm **amber** call-to-action.
Generous whitespace, big friendly headlines, soft rounded cards (8px) and fully
pill-shaped buttons, low-contrast navy-tinted shadows. Feels like a friendly,
fintech-adjacent consumer brand: calm, premium, not flashy.

---

## CSS variables (drop-in)

```css
:root {
  /* ---- Brand ---- */
  --color-navy:            #143c55; /* primary brand / dark sections / button text */
  --color-navy-deep:       #133c55; /* near-identical alt navy used on site */
  --color-amber:           #ffb959; /* PRIMARY CTA fill (warm, high-attention) */
  --color-blue:            #2d62ff; /* link / accent / focus ring */
  --color-blue-bright:     #2d85ff; /* feature-icon + section accent fill */
  --color-blue-light:      #d9e5ff; /* soft blue tint backgrounds */
  --color-sky:             #def2ff; /* lightest blue wash */
  --color-orange:          #ff7e28; /* secondary brand accent (sparingly) */
  --color-pink:            #dd23bb; /* tertiary brand accent (sparingly) */

  /* ---- Neutrals ---- */
  --color-black:           #000000; /* primary body text */
  --color-ink:             #111111;
  --color-gray-darker:     #222222;
  --color-gray-dark:       #444444;
  --color-gray:            #666666;
  --color-gray-muted:      #6e777d; /* muted/secondary copy on light bg */
  --color-gray-light:      #aaaaaa;
  --color-gray-lighter:    #cccccc;
  --color-gray-lightest:   #eeeeee; /* default border / hairline */
  --color-white:           #ffffff;

  /* ---- Surfaces ---- */
  --bg-page:               var(--color-white);
  --bg-section-dark:       var(--color-navy);   /* hero + dark feature bands */
  --bg-card:               var(--color-white);
  --border-default:        var(--color-gray-lightest);

  /* ---- Text ---- */
  --text-primary:          var(--color-black);
  --text-secondary:        var(--color-gray-muted);
  --text-on-dark:          var(--color-white);
  --text-heading:          var(--color-navy);   /* navy headings on light bg */
  --link:                  var(--color-blue);

  /* ---- System ---- */
  --success:               #cef5ca;  --success-fg: #114e0b;
  --warning:               #fcf8d8;  --warning-fg: #5e5515;
  --error:                 #f8e4e4;  --error-fg:   #3b0b0b;
  --focus-ring:            #2d62ff;

  /* ---- Type ---- */
  --font-heading: "Circular", "Circular Std", "Inter", system-ui, Arial, sans-serif;
  --font-body:    "Circular", "Circular Std", "Inter", system-ui, Arial, sans-serif;
  --fw-light:   300;   /* body default on the live site */
  --fw-regular: 400;   /* buttons */
  --fw-bold:    700;   /* all headings */

  --fs-body:   16px;   --lh-body:   24px;   /* 1.5 */
  --fs-h2:     48px;   --lh-h2:     56px;
  --fs-h1:     88px;   --lh-h1:     88px;   /* hero scale; clamp down on mobile */
  --fs-h1-sub: 24px;   --lh-h1-sub: 32px;   /* "section eyebrow" headings */

  /* ---- Shape ---- */
  --radius-sm:   8px;    /* cards, inputs, tiles (dominant radius) */
  --radius-md:   20px;   /* occasional larger panels */
  --radius-pill: 100px;  /* all buttons / chips */

  /* ---- Elevation (soft, navy-tinted, low opacity) ---- */
  --shadow-card: 0 10px 30px rgba(20, 60, 85, 0.08);
  --shadow-soft: 0 10px 16px rgba(39, 56, 66, 0.08);

  /* ---- Spacing (generous; ~8px rhythm, ~31px block gaps on home) ---- */
  --space-1: 4px;  --space-2: 8px;  --space-3: 16px;
  --space-4: 24px; --space-5: 32px; --space-6: 48px;
  --space-7: 64px; --space-8: 96px; /* section padding runs large */
}
```

---

## Buttons (measured)

```css
/* Primary CTA — warm amber, navy label, full pill. The one strong accent. */
.btn-primary {
  background: var(--color-amber);
  color: var(--color-navy);
  border: 0;
  border-radius: var(--radius-pill);
  padding: 10px 24px;
  font-weight: var(--fw-regular);
  line-height: 28px;
}

/* Secondary CTA — solid navy, white label, same pill, 2px navy border. */
.btn-secondary {
  background: var(--color-navy);
  color: var(--color-white);
  border: 2px solid var(--color-navy);
  border-radius: var(--radius-pill);
  padding: 10px 24px;
  font-weight: var(--fw-regular);
  line-height: 28px;
}
```

- Primary amber button is reserved for the single most important action per view
  (it's the only warm color on an otherwise navy/blue/white palette).
- Navy is the secondary/utility button and the dark-section background.
- `#2d62ff` blue is for inline links and focus, not button fills.

---

## Typography

| Role        | Family            | Weight | Size / line-height |
|-------------|-------------------|--------|--------------------|
| Hero H1     | Circular          | 700    | 88 / 88            |
| Section H2  | Circular          | 700    | 48 / 56            |
| Eyebrow H   | Circular          | 700    | 24 / 32            |
| Body        | Circular          | 300    | 16 / 24            |
| Button      | Circular          | 400    | 16 / 28            |
| Muted copy  | Circular          | 300    | 16 / 24 in `#6e777d` |

**Font pairing:** HouseAccount uses **one geometric-sans family for both headings
and body** (`Circularxx`, a Circular variant) — a single-family system, contrast
comes from weight (700 headings vs 300 body), not from mixing families.

**Circular is a proprietary licensed font (Lineto).** Do not embed it in
shippable UI. Use a free, near-identical geometric sans as the working substitute:

```html
<!-- Google Fonts substitute for Circular (geometric, friendly, similar metrics) -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;700&display=swap" rel="stylesheet">
```

- **Recommended free substitute:** **Inter** (closest free match for proportions
  and x-height). Alternatives if a more geometric look is wanted: **Poppins** or
  **Manrope**.
- Keep the **300 body / 700 heading** weight split — it's the load-bearing part of
  the brand's feel.
- H1 88px is a desktop hero scale; clamp it down for narrower viewports, e.g.
  `font-size: clamp(40px, 7vw, 88px)`.

---

## Layout & shape notes

- **Page background:** white. **Hero and select feature bands:** solid navy
  (`#143c55`) with white text and faint translucent-white sub-copy.
- **Cards / tiles:** white on white page, `8px` radius, soft navy-tinted shadow
  (`--shadow-card`), thin `#eee` hairline borders where used.
- **Radius census:** `8px` dominates (cards/inputs), `100px` for all pills,
  `20px` occasionally.
- **Shadows:** always soft and low-opacity (0.08 alpha), tinted navy — never harsh.
- **Whitespace:** generous; large vertical section padding and ~31px block gaps on
  the homepage. Lean roomy, not dense.
- **Accent discipline:** navy + blue + white do the structural work; **amber is the
  single warm accent** — use it only for primary CTAs and key highlights.

---

## Measured vs inferred

**Measured (from live computed styles + `:root` vars):**
- All hex colors, the full brand variable system, font family, all weights and
  sizes, button fill/text/radius/padding, link/accent color, page + section
  backgrounds, border + shadow values, radius census, whitespace density.

**Inferred / chosen by us (clearly noted):**
- The spacing scale (`--space-*`) is a clean 8px-rhythm scale derived from observed
  gaps (~31px block gaps, 8px-based radii); the site doesn't expose a named spacing
  token set.
- The **Inter** substitution and the geometric-sans fallback stack — chosen to
  approximate proprietary **Circular**, which can't be shipped.
- `--color-navy-deep #133c55` vs `--color-navy #143c55`: the site uses both
  near-identical navies; treat `#143c55` as canonical.

_Nothing here is a blind guess — every color and type value traces to
`design/tokens.json`._
