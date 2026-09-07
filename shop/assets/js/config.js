/* atelierR — site configuration
   Single place for every business value. Change here, not in the pages. */
window.ATELIER_CONFIG = {
  brandName: 'atelierR',
  tagline: 'Beauty lives a little lighter',
  location: 'Singapore',
  currency: 'SGD',

  // --- PayNow (replace placeholders with the real merchant details) ---
  payNow: {
    uen: 'PLACEHOLDER-UEN-202XXXXXXK',
    mobile: '+65 0000 0000',
    accountName: 'ATELIER R PTE. LTD.',
    qrImage: '',              // e.g. 'assets/img/paynow-qr.png' — blank shows a placeholder frame
    verificationHours: 'within 1 business day'
  },

  // --- Contact (last-resort channels only) ---
  contact: {
    whatsapp: '6500000000',   // digits only, no '+' — placeholder
    email: 'hello@atelier-r-make.com',
    instagram: 'https://instagram.com/',
    instagramHandle: '@atelierr.sg'
  },

  // --- Delivery ---
  delivery: {
    flatRate: 8,
    freeThreshold: 150,
    leadTime: '2–4 business days after payment is verified',
    areas: 'All Singapore addresses'
  },

  // --- Storage keys (swap this layer for an API later) ---
  keys: { cart: 'atelierR.cart', orders: 'atelierR.orders', lastOrder: 'atelierR.lastOrder' }
};
