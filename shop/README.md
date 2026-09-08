# atelierR — storefront

A static, dependency-free storefront for atelierR, a curated Japanese beauty shop in Singapore.
No build step, no framework: open any page directly, or deploy the repository as-is.

Live path once deployed to GitHub Pages: `/shop/`

The site's guiding principle is that a customer should be able to answer every question themselves —
what a product is, whether it suits them, what it costs, whether it is in stock, how to use it,
how to pay, when the order is confirmed, and how delivery works — without messaging atelierR.

---

## Pages

| Page | File | Purpose |
|---|---|---|
| Homepage | `index.html` | Hero, brands, categories, best sellers, sets, tools, philosophy, FAQ preview |
| Shop All | `shop.html` | Full catalogue with category / brand / stock filters and sorting |
| Category | `category.html?c=<id>` | One category: `base-makeup`, `point-makeup`, `skincare`, `tools`, `sets` |
| Brand | `brand.html?b=<id>` | One brand, e.g. `?b=suqqu` |
| Brands index | `brands.html` | All brands with product counts |
| Product | `product.html?id=<id>` | Gallery, price, stock, shades, and the full answer set |
| Compare | `compare.html?c=<cat>&sub=<subcategory>` | Side-by-side comparison |
| Shade Guide | `shade-guide.html` | How to choose a shade without seeing it |
| Cart | `cart.html` | Line items, quantities, totals, PayNow notice |
| Customer details | `checkout.html` | Name, email, WhatsApp, address, postal code, notes |
| Order review | `review.html` | Final review + PayNow acknowledgement, creates the order |
| PayNow payment | `paynow.html?order=<no>` | QR, UEN, reference, amount, instructions |
| Payment confirmation | `payment-confirmation.html?order=<no>` | Screenshot upload or WhatsApp |
| Order status | `order.html?order=<no>` | Order number, total, status tracker, next steps |
| FAQ | `faq.html` | Seven groups, searchable, deep-linkable (`faq.html#payment`) |
| About | `about.html` | Story and selection criteria |
| Contact | `contact.html` | Self-service ladder first, contact last |
| Journal | `journal.html` | Editorial index, lead story plus grid, filtered by category |
| Article | `article.html?a=<slug>` | One story, with its commerce blocks |
| Order desk | `admin.html` | Internal: sign in, see every order, confirm payments |
| Content studio | `studio.html` | Internal: newsletter and Instagram drafts, subscriber CSV |

---

## Checkout flow

```
Product → Add to Cart → Cart → Customer Details → Order Review
        → PayNow Payment Instructions → customer pays manually
        → customer submits payment confirmation
        → "Awaiting Payment Verification"
        → atelierR checks PayNow by hand → order confirmed
```

**PayNow only.** There is no Stripe, Square, card, Apple Pay or Google Pay integration anywhere,
and no card details are collected on any page.

**Nothing is ever marked as paid automatically.** `Orders.submitPaymentProof()` sets
`paymentStatus: 'submitted'` and status `Awaiting Payment Verification` — never `verified`.
Only a person, through `admin.html` or the future backend, moves an order to `Payment Confirmed`.

### Order statuses

`Cart` → `Order Created` → `Awaiting PayNow Payment` → `Awaiting Payment Verification`
→ `Payment Confirmed` → `Preparing Order` → `Shipped` → `Completed`

---

## Files

```
shop/
├── index.html, shop.html, category.html, brand.html, brands.html,
│   product.html, compare.html, shade-guide.html, cart.html, checkout.html,
│   review.html, paynow.html, payment-confirmation.html, order.html,
│   faq.html, about.html, contact.html, admin.html
└── assets/
    ├── css/atelier.css        Design tokens, layout, components. The only stylesheet.
    └── js/
        ├── config.js          Business values: PayNow details, contact, delivery rates
        ├── data/products.js   The catalogue
        ├── data/faqs.js       FAQ content
        ├── imagery.js         Generated SVG product art (no photography, no model faces)
        ├── store.js           Catalogue queries, cart, orders — the persistence layer
        ├── ui.js              Header, footer, drawer, search, product cards, toasts
        ├── listing.js         Filtering and sorting for shop / category / brand
        └── order-view.js      Shared order summary, customer and status blocks
```

---

## Editing content

**Business details** — `assets/js/config.js`.

PayNow is live: the merchant QR at `assets/img/paynow-qr.jpg` encodes UEN `202111608C`
(SALON DE SINGA PTE. LTD, static/reusable, payer enters the amount, SGD), and `config.js`
matches it. Because the registered company name differs from the shop name, the PayNow page and
the FAQ both explain that this is the correct account — keep that wording in step with the QR if
the account ever changes. `payNow.mobile` is blank because this QR pays to a UEN; set it only if
a mobile proxy is added, and the row appears automatically.

Contact channels are rendered only when set, in the footer and on the Contact page, so an unset
channel is never shown as a dead link. WhatsApp (`6586212382`) and Instagram
(`@r.makeup.session`) are live. `contact.email` is deliberately blank until the address customers
should write to is confirmed — set it and the email option reappears everywhere.

**Products** — `assets/js/data/products.js`. Each record:

| Field | Notes |
|---|---|
| `id` | Slug, stable, appears in URLs |
| `brand`, `name` | |
| `category` | `base-makeup` · `point-makeup` · `skincare` · `tools` · `sets` |
| `subcategory` | Free text; also groups the comparison page |
| `priceSGD` | Number |
| `stock` | `0` marks sold out; `≤ 3` shows a low-stock warning |
| `art`, `images` | `{ shape, tone }` — see `imagery.js` for the available shapes and tones |
| `shortDescription` | One line, used on cards |
| `description` | "What it is" |
| `whySelected` | "Why atelierR selected this" |
| `bestFor` | Array, rendered as pills |
| `finish` | `Natural` · `Satin` · `Matte` · `Sheer` · `Luminous` · `—` |
| `howToUse` | Array of numbered steps |
| `shadeInfo` | `{ guide, shades: [{ name, code, hex, note }] }` |
| `related` | Array of ids — "Pair it with" |
| `setContents` | Array of ids, sets only |
| `bestSeller` | Promotes to the homepage |
| `active` | `false` hides it everywhere |

**FAQ** — `assets/js/data/faqs.js`. Set `homepage: true` on an item to promote it to the
homepage preview. Answers are arrays of HTML strings.

**Prices** are plain numbers; `Store.money()` formats every one of them as `SGD n`.

---

## The database

Orders go to Supabase (`assets/js/backend.js`, schema in `supabase/schema.sql`), so atelierR can
see them from any device rather than only the browser that placed them.

The publishable key in `config.js` is public by design — it ships in the page source of every
visitor. Row Level Security is what protects the data: the public may insert an order and a
payment report, and nothing else. There is no select policy for `anon`, so nobody can read orders
back, their own included, and no delete policy exists at all. Reading and updating require a
signed-in atelierR account, which `admin.html` asks for.

**Writes are idempotent.** Checkout navigates to the PayNow page the moment an order is created,
which aborts the in-flight request even though the row has already landed — it looks like a
failure. Every write therefore carries a client-generated `id` and is sent with
`Prefer: resolution=ignore-duplicates`, and a 409 is treated as success, so a replayed write is a
no-op rather than a second order.

**A failed write is queued, not lost.** `Backend` keeps it in `localStorage` and replays it on the
next page load. The customer is never blocked on the network: they get their order number and
PayNow instructions regardless, and the browser keeps its own copy of the order either way.

**The customer can never change an order.** Reporting a payment inserts into `payment_reports`
rather than touching the order row, because a claim is not a confirmation. The order desk derives
"Awaiting Payment Verification" from the presence of a report, and only a person moves an order to
Payment Confirmed.

## Connecting a different database

`store.js` is the seam. `Catalog`, `Cart` and `Orders` are the only code that touches storage,
and each method is already shaped the way its API equivalent would be:

- `Catalog.all()` / `byId()` / `byCategory()` / `byBrand()` → `GET /api/products`
- `Orders.create(customer)` → `POST /api/orders`
- `Orders.submitPaymentProof(no, proof)` → `POST /api/orders/:no/payment-proof`
- `Orders.setStatus(no, statusKey)` → `PATCH /api/orders/:no`

Replace the `read`/`write` helpers with `fetch` calls and make the callers `await`; no page needs
to change. The order record already carries everything a backend needs:

```js
{ orderNumber, customer: { firstName, lastName, email, whatsapp, address, postalCode, notes },
  items: [{ id, brand, name, shade, qty, unitPrice, lineTotal }],
  subtotal, delivery, total, currency, paymentMethod,
  paymentStatus, paymentScreenshot, orderStatus, statusKey,
  history: [{ status, at }], createdAt, updatedAt }
```

Until then, carts and orders live in the browser's `localStorage`, which is why `admin.html` only
sees orders placed on the same device. A screenshot that exceeds the storage quota is dropped from
the record rather than losing the order — the transfer is still verifiable in the PayNow account.

---

## Product photography

Photos are opt-in per product and require no code change. Drop a file into
`assets/img/products/` named after the product id and it replaces the generated artwork
everywhere — cards, gallery, cart, search and comparison:

    suqqu-signature-color-eyes.jpg      main image
    suqqu-signature-color-eyes-2.jpg    second gallery image
    suqqu-signature-color-eyes-3.jpg    third gallery image

`.jpg` is tried first, then `.png`. `Imagery.enhance()` swaps the SVG for an `<img>` only once the
file has loaded, so a product without a photo keeps its generated art and never shows a broken
image. Photos can therefore be added a few at a time.

Which photos exist is read from `assets/img/products/manifest.json`, regenerated by the deploy
workflow on every push — so a page makes one small request instead of guessing per product. The
manifest is never committed (see the `.gitignore` beside it); a stale one would hide a photo that
is really there. Without a manifest — local preview, or a deploy predating it — the code falls
back to probing each name once per session, so photos still appear either way.

Shoot guidance and the full filename list live in `assets/img/products/README.md`.

### Filenames

### ベースメイク

| 商品 | ファイル名 |
|---|---|
| RMK Liquid Foundation | `rmk-liquid-foundation.jpg` |
| RMK Translucent Face Powder | `rmk-face-powder.jpg` |
| THREE Angelic Glow Primer | `three-glow-primer.jpg` |
| ADDICTION The Concealer | `addiction-the-concealer.jpg` |
| Celvoke Reventive Cushion Foundation | `celvoke-cushion.jpg` |

### ポイントメイク

| 商品 | ファイル名 |
|---|---|
| SUQQU Signature Color Eyes | `suqqu-signature-color-eyes.jpg` |
| SUQQU Blurring Color Blush | `suqqu-blurring-color-blush.jpg` |
| SUQQU Moisture Glaze Lipstick | `suqqu-moisture-glaze-lipstick.jpg` |
| Celvoke Indicate Eyebrow Powder | `celvoke-indicate-eyebrow-powder.jpg` |
| RMK Eye Defining Pencil | `rmk-eye-defining-pencil.jpg` |
| ADDICTION The Matte Lip Liquid | `addiction-matte-lip-liquid.jpg` |
| THREE Velvet Last Lipstick | `three-velvet-lipstick.jpg` |

### スキンケア

| 商品 | ファイル名 |
|---|---|
| NOEVIR Herbal Skin Lotion | `noevir-herbal-skin-lotion.jpg` |
| NOEVIR Herbal Milk Lotion | `noevir-herbal-milk-lotion.jpg` |
| THREE Balancing Cleansing Oil | `three-cleansing-oil.jpg` |
| Celvoke Concentrate Serum | `celvoke-concentrate-serum.jpg` |

### ツール

| 商品 | ファイル名 |
|---|---|
| BROWN ÉTOILE Eyeshadow Brush (A) | `brownetoile-eyeshadow-brush-a.jpg` |
| BROWN ÉTOILE Blending Brush | `brownetoile-blending-brush.jpg` |
| BROWN ÉTOILE Eyebrow Brush | `brownetoile-eyebrow-brush.jpg` |
| BROWN ÉTOILE Face Powder Brush | `brownetoile-face-powder-brush.jpg` |
| BROWN ÉTOILE Blush Brush | `brownetoile-blush-brush.jpg` |
| BROWN ÉTOILE Concealer Brush (M) | `brownetoile-concealer-brush-m.jpg` |
| BROWN ÉTOILE Eyelash Curler | `brownetoile-eyelash-curler.jpg` |

### セット

| 商品 | ファイル名 |
|---|---|
| atelierR Base Makeup Set | `base-makeup-set.jpg` |
| atelierR Skincare Set — Starter | `skincare-set-starter.jpg` |
| atelierR Skincare Set — Complete | `skincare-set-complete.jpg` |

## The Journal

Stories live in `assets/js/data/articles.js`; `assets/js/journal.js` renders them. Adding a story
is adding one object — the journal index, the article page, the homepage strip, the newsletter
draft and the Instagram captions all read from the same record. `JOURNAL.md` is the author's
guide, in Japanese.

Articles are commerce-enabled: `{ shop: [ids], title }` and `{ pick: id }` blocks place product
cards inside the piece, `todaysPick` opens the story, and `products` closes it. A product is never
shown twice in one story, and headings do not collide — a body block titled "Products Mentioned"
pushes the closing row to "Also in this story", and a second highlighted product is labelled
"atelierR Recommends" rather than a second "Today's Pick".

Hero images follow the product convention: `assets/img/journal/<slug>.jpg` replaces the generated
artwork. These are probed directly rather than carried in the product manifest — there are few of
them and they are named for the story.

### Newsletter

`assets/js/newsletter.js` is one component mounted into any `[data-newsletter-slot]` — homepage,
footer, journal, article, PayNow confirmation and order pages. Subscribers go to the `subscribers`
table and to `localStorage`, so a signup survives a dropped connection, and the record is already
the shape every email platform expects:

```js
{ email, first_name, source, status, consented_at }
```

`studio.html` derives a newsletter draft and Instagram captions from each story and exports the
subscriber list as CSV. **It sends and posts nothing** — there is no send button anywhere in it,
by design. Connecting Mailchimp, Klaviyo, Brevo or Resend later is a mapping job against the
fields above, not a migration.

The subscriber list is a list of customers' email addresses, so — like orders — the public may
insert into it and can never read it back.

## Design notes

Warm ivory and stone palette, Cormorant Garamond over Jost, generous white space, mobile-first.
No model faces anywhere. Until a product has photography, its visual is generated as an SVG by
`imagery.js` from the product's `art` descriptor; see **Product photography** above for how a real
photo takes over.

Google Fonts is the only external request. If it is unavailable the pages fall back to system
serif and sans-serif and remain fully usable.
