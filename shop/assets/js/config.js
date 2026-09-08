/* atelierR — site configuration
   Single place for every business value. Change here, not in the pages. */
window.ATELIER_CONFIG = {
  brandName: 'atelierR',
  tagline: 'Beauty lives a little lighter',
  location: 'Singapore',
  currency: 'SGD',

  // --- PayNow ---
  // Taken from the merchant QR at assets/img/paynow-qr.jpg, which encodes:
  //   SG.PAYNOW · proxy type 2 (UEN) · 202111608C · SALON DE SINGA PTE. LTD
  //   static/reusable, amount entered by the payer, currency SGD
  payNow: {
    uen: '202111608C',
    mobile: '',               // this QR pays to a UEN, not a mobile — leave blank to hide the row
    accountName: 'SALON DE SINGA PTE. LTD',
    qrImage: 'assets/img/paynow-qr.jpg',   // blank falls back to a placeholder frame
    verificationHours: 'within 1 business day'
  },

  // --- Contact (last-resort channels only) ---
  // Blank values are hidden rather than rendered, so an unset channel is never
  // shown to a customer as a dead link.
  contact: {
    whatsapp: '6586212382',   // digits only, no '+' — Singapore mobile 8621 2382
    email: '',                // TODO: confirm the address customers should write to
    instagram: 'https://www.instagram.com/r.makeup.session',
    instagramHandle: '@r.makeup.session'
  },

  // --- Delivery ---
  delivery: {
    flatRate: 8,
    freeThreshold: 150,
    leadTime: '2–4 business days after payment is verified',
    areas: 'All Singapore addresses'
  },

  // --- Supabase ---
  // The publishable key is public by design: it ships in the page source of
  // every visitor. Access is controlled by the Row Level Security policies in
  // supabase/schema.sql, which let the public insert an order and nothing
  // else — no reading, updating or deleting. Never put a `sb_secret_` key here.
  supabase: {
    url: 'https://niztrbssnsildyfykyva.supabase.co',
    key: 'sb_publishable_1Pq_BvuCs7u_LqLWybm8lw_lCvEJ6Mk'
  },

  // Where new-order notifications should go once email is wired up.
  notifyEmail: 'noriko.kagawa@atelier-r-make.com',

  // --- Storage keys (the browser keeps its own copy of every order) ---
  keys: { cart: 'atelierR.cart', orders: 'atelierR.orders', lastOrder: 'atelierR.lastOrder' }
};
