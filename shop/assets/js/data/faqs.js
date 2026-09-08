/* atelierR — FAQ content
   Grouped so the FAQ page and the homepage preview read from one source.
   `homepage: true` promotes a question to the homepage preview. */
window.FAQ_GROUPS = [
  {
    id: 'payment',
    title: 'Payment',
    items: [
      { q: 'How do I pay?',
        homepage: true,
        a: ['<p>All orders are paid by <strong>PayNow</strong>. After you place your order you will see a PayNow page with the QR code, the UEN, your order number and the exact amount to transfer.</p>',
            '<p>You scan the QR code or transfer manually in your banking app, then let us know by uploading your payment screenshot on the confirmation page.</p>'] },
      { q: 'Can I pay by credit card?',
        a: ['<p>Not at the moment. atelierR accepts PayNow only. This keeps prices lower and the process simple, and it is the payment method almost every customer in Singapore already has in their banking app.</p>'] },
      { q: 'When is my order confirmed?',
        homepage: true,
        a: ['<p>Your order is confirmed once atelierR has checked the PayNow transfer against your order — usually within one business day of receiving your payment screenshot.</p>',
            '<p>Until then your order status shows <strong>Awaiting Payment Verification</strong>. Placing an order and sending a screenshot does not confirm it on its own; a person checks every payment.</p>'] },
      { q: 'The payment shows a different company name — is that right?',
        a: ['<p>Yes, that is correct. PayNow transfers are received by <strong>SALON DE SINGA PTE. LTD</strong>, the registered company behind atelierR. Seeing that name in your banking app means you are paying the right account.</p>'] },
      { q: 'What should I write in the PayNow reference?',
        a: ['<p>Write your <strong>order number</strong> — for example <em>ATR-240915-1043</em>. If your banking app limits the reference length, your full name is fine instead.</p>',
            '<p>The reference is how we match your transfer to your order, so an order without one takes longer to verify.</p>'] },
      { q: 'What happens if I forget to send the payment screenshot?',
        a: ['<p>Nothing is lost. We still see the transfer in the PayNow account and will match it using the reference you entered.</p>',
            '<p>Sending the screenshot simply makes verification faster and lets us contact you if anything does not match.</p>'] },
      { q: 'Is my payment held or refunded if something is out of stock?',
        a: ['<p>If an item sells out between your order and our verification, we contact you before confirming. You may swap the item, wait for restock, or receive a refund by PayNow for that item.</p>'] }
    ]
  },
  {
    id: 'delivery',
    title: 'Delivery',
    items: [
      { q: 'Where do you deliver?',
        a: ['<p>Anywhere in Singapore. We do not ship overseas at the moment.</p>'] },
      { q: 'How long does delivery take?',
        homepage: true,
        a: ['<p>Orders are sent <strong>2–4 business days after payment has been verified</strong>. The clock starts at verification, not at the time the order is placed.</p>',
            '<p>Orders placed over a weekend or a public holiday are verified on the next business day.</p>'] },
      { q: 'How much is delivery?',
        a: ['<p>A flat <strong>SGD 8</strong> anywhere in Singapore, and <strong>free for orders of SGD 150 and above</strong>. Delivery is calculated in your cart before you check out, so the total on the PayNow page is the final amount.</p>'] },
      { q: 'Will I receive tracking information?',
        a: ['<p>Yes. When your order is shipped we send the tracking number to the email address and WhatsApp number on your order.</p>'] },
      { q: 'Can I collect my order instead?',
        a: ['<p>Self-collection can be arranged for customers who have booked a makeup session. Please add a note in the order notes field at checkout and we will confirm the arrangement when we verify your payment.</p>'] }
    ]
  },
  {
    id: 'returns',
    title: 'Returns & Changes',
    items: [
      { q: 'Can I cancel my order?',
        homepage: true,
        a: ['<p>Yes, at any point <strong>before payment has been verified</strong>. Simply do not complete the PayNow transfer — an unpaid order is closed automatically after 48 hours and nothing is charged.</p>',
            '<p>If you have already paid and want to cancel, contact us the same day and we will refund the full amount by PayNow.</p>'] },
      { q: 'Can I change my order after payment?',
        homepage: true,
        a: ['<p>Changes are possible while your order status is <strong>Awaiting Payment Verification</strong> or <strong>Preparing Order</strong>. Contact us with your order number and what you would like to change.</p>',
            '<p>Once the status shows <strong>Shipped</strong>, the order can no longer be changed.</p>'] },
      { q: 'Can cosmetics be returned?',
        a: ['<p>For hygiene reasons, opened cosmetics and skincare cannot be returned or exchanged. This is standard practice for beauty retail in Singapore.</p>',
            '<p>Unopened items in their original seal can be returned within 7 days of delivery.</p>'] },
      { q: 'What happens if I receive a damaged item?',
        a: ['<p>Photograph the item and the outer packaging and contact us within 48 hours of delivery. Damaged items are replaced at no cost, or refunded in full by PayNow if a replacement is not available.</p>'] }
    ]
  },
  {
    id: 'products',
    title: 'Products',
    items: [
      { q: 'Are these authentic products?',
        a: ['<p>Yes. Every product is genuine and sourced through proper channels. atelierR uses these same products professionally, which is the reason authenticity is not negotiable here.</p>'] },
      { q: 'Are products sourced from Japan?',
        a: ['<p>Yes. The brands carried here are Japanese, and stock is sourced from Japan. Some products are Japan-domestic versions, which occasionally differ in packaging or shade naming from the international release.</p>'] },
      { q: 'What happens if a product is sold out?',
        homepage: true,
        a: ['<p>Sold out products are shown clearly on the product page and cannot be added to the cart, so you will never pay for something unavailable.</p>',
            '<p>If an item sells out after you order but before we verify payment, we contact you to swap it, hold it for restock, or refund that item.</p>'] },
      { q: 'Will products be restocked?',
        a: ['<p>Most core products are restocked within two to four weeks. Limited and seasonal releases are not restocked once they are gone.</p>'] },
      { q: 'Do the products have an expiry date?',
        a: ['<p>All stock is current. Japanese cosmetics are generally best used within three years unopened, and within one year of opening. Skincare is best used within six months of opening.</p>'] }
    ]
  },
  {
    id: 'shades',
    title: 'Shade Selection',
    items: [
      { q: 'How do I choose the right shade?',
        homepage: true,
        a: ['<p>Every colour product on this site has a <strong>Shade guide</strong> section on its product page, with a plain description of who each shade suits. That is the fastest way to decide.</p>',
            '<p>Three rules cover most cases:</p>',
            '<ul><li>Foundation: choose the shade that disappears at the jawline in daylight. Between two shades, take the deeper one.</li><li>Lipstick: one or two steps deeper than your natural lip for everyday wear.</li><li>Brow: one shade lighter than your hair if your hair is black or dark brown.</li></ul>'] },
      { q: 'Can atelierR recommend a shade?',
        a: ['<p>Yes, but read the shade guide on the product page first — it answers most questions, and it is available at any hour.</p>',
            '<p>If you are still unsure after that, contact us with a photo taken in natural daylight, without makeup and without a filter, and we will recommend a shade.</p>'] },
      { q: 'What is the difference between the finishes?',
        a: ['<ul><li><strong>Natural</strong> — looks like skin, neither matte nor shiny.</li><li><strong>Satin</strong> — a soft, low sheen. The most wearable for most people.</li><li><strong>Matte</strong> — no shine, longest wear, best for evening.</li><li><strong>Sheer</strong> — translucent colour that lets your own tone show through.</li><li><strong>Luminous</strong> — reflects light softly, for a fresh or dewy look.</li></ul>'] },
      { q: 'What if the shade does not suit me when it arrives?',
        a: ['<p>Opened products cannot be returned for hygiene reasons, which is why we would rather spend time on the shade before you order than after. Use the shade guide, and ask if it is still unclear.</p>'] }
    ]
  },
  {
    id: 'orders',
    title: 'Orders',
    items: [
      { q: 'How do I know my order went through?',
        a: ['<p>You are given an order number immediately, on screen, along with the PayNow instructions and the next steps. Keep the order number — it is the reference for everything that follows.</p>'] },
      { q: 'What do the order statuses mean?',
        a: ['<ul><li><strong>Order Created</strong> — your order exists and is waiting for payment.</li><li><strong>Awaiting PayNow Payment</strong> — we are waiting for your transfer.</li><li><strong>Awaiting Payment Verification</strong> — you have paid and atelierR is checking the transfer.</li><li><strong>Payment Confirmed</strong> — payment verified, your order is confirmed.</li><li><strong>Preparing Order</strong> — your order is being packed.</li><li><strong>Shipped</strong> — on its way, with a tracking number sent to you.</li><li><strong>Completed</strong> — delivered.</li></ul>'] },
      { q: 'Do I need an account?',
        a: ['<p>No. Orders are placed with your name, email and WhatsApp number only. There is no password to remember.</p>'] }
    ]
  },
  {
    id: 'sessions',
    title: 'Makeup Session Purchases',
    items: [
      { q: 'Can I buy the products used during my makeup session?',
        homepage: true,
        a: ['<p>Yes. Everything used in a session is available here, and your makeup artist will note down what was used on your face so you can find it afterwards.</p>',
            '<p>Add a note at checkout mentioning your session date and we will double-check that the shades match what was used on you.</p>'] },
      { q: 'Will you tell me the exact shades used on me?',
        a: ['<p>Yes. Ask at the end of your session and the shade names and codes are written down for you. If you have lost the note, contact us with your session date and we will look it up.</p>'] },
      { q: 'Can I order before my session?',
        a: ['<p>You can, but it is usually better to wait. Shade decisions are far more accurate after seeing the products on your own skin during a session.</p>'] }
    ]
  }
];
