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
