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
| Order desk | `admin.html` | Internal preview: manually confirm payments and advance status |

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

## Connecting a database

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

## Design notes

Warm ivory and stone palette, Cormorant Garamond over Jost, generous white space, mobile-first.
There is no photography and there are no model faces: every product visual is generated as an SVG
by `imagery.js` from the product's `art` descriptor. To move to real photography, replace
`Imagery.render()` with an `<img>` tag — the call sites already pass a label for the `alt` text.

Google Fonts is the only external request. If it is unavailable the pages fall back to system
serif and sans-serif and remain fully usable.
