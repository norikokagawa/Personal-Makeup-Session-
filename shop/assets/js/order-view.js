/* atelierR — order rendering
   Shared blocks used by the PayNow, payment confirmation and order pages, so
   an order looks and reads identically wherever the customer sees it. */
(function (global) {
  'use strict';
  var S = global.Store, esc = S.esc, money = S.money;

  var OrderView = {

    notFound: function () {
      return '<div class="empty">' +
        '<p class="h2 serif">Order not found</p>' +
        '<p class="lede center" style="margin:0 auto 24px">We could not find that order on this device. ' +
        'Orders are stored in the browser you ordered from — try that browser, or contact atelierR with your order number.</p>' +
        '<div class="row" style="justify-content:center">' +
          '<a class="btn btn-outline" href="shop.html">Shop All</a>' +
          '<a class="btn btn-quiet" href="contact.html">Contact atelierR</a>' +
        '</div></div>';
    },

    /* Items + totals */
    summary: function (order) {
      return '<div class="panel">' +
        '<h2 class="section-title mb-16">Order Summary</h2>' +
        '<div class="kv"><dt>Order number</dt><dd><strong style="font-weight:400">' + esc(order.orderNumber) + '</strong></dd></div>' +
        '<div class="kv"><dt>Placed</dt><dd>' + esc(formatDate(order.createdAt)) + '</dd></div>' +
        '<div class="kv"><dt>Status</dt><dd>' + esc(order.orderStatus) + '</dd></div>' +
        '<div class="mt-16">' +
          order.items.map(function (i) {
            return '<div class="summary-row"><span>' + esc(i.name) +
              (i.shade ? ' <span class="tiny">(' + esc(i.shade) + ')</span>' : '') +
              ' <span class="muted">× ' + i.qty + '</span></span><span>' + money(i.lineTotal) + '</span></div>';
          }).join('') +
        '</div>' +
        '<div class="summary-row" style="border-top:1px solid var(--line);margin-top:8px;padding-top:14px">' +
          '<span>Subtotal</span><span>' + money(order.subtotal) + '</span></div>' +
        '<div class="summary-row"><span>Delivery</span><span>' +
          (order.delivery === 0 ? 'Free' : money(order.delivery)) + '</span></div>' +
        '<div class="summary-row summary-total"><span>Total</span><span>' + money(order.total) + '</span></div>' +
      '</div>';
    },

    customer: function (order) {
      var c = order.customer;
      return '<div class="panel mt-24">' +
        '<h2 class="section-title mb-16">Delivery to</h2>' +
        '<dl>' +
          '<div class="kv"><dt>Name</dt><dd>' + esc(c.firstName + ' ' + c.lastName) + '</dd></div>' +
          '<div class="kv"><dt>Email</dt><dd>' + esc(c.email) + '</dd></div>' +
          '<div class="kv"><dt>WhatsApp</dt><dd>' + esc(c.whatsapp) + '</dd></div>' +
          '<div class="kv"><dt>Address</dt><dd style="max-width:62%">' + esc(c.address) + ', ' + esc(c.postalCode) + '</dd></div>' +
          (c.notes ? '<div class="kv"><dt>Notes</dt><dd style="max-width:62%">' + esc(c.notes) + '</dd></div>' : '') +
        '</dl>' +
      '</div>';
    },

    /* The full status lifecycle, with the current step marked. */
    tracker: function (order) {
      var current = S.Orders.flowIndex(order.statusKey);
      return '<div class="panel mt-24">' +
        '<h2 class="section-title mb-16">Order Status</h2>' +
        '<ul class="status-track">' +
          S.Orders.FLOW.map(function (step, i) {
            var cls = i < current ? 'done' : (i === current ? 'now' : '');
            return '<li class="' + cls + '"><span>' + esc(step.label) +
              (i === current ? '<small>' + esc(step.note) + '</small>' : '') + '</span></li>';
          }).join('') +
        '</ul>' +
        (order.statusKey === 'AWAITING_VERIFICATION'
          ? '<p class="tiny">atelierR verifies every PayNow transfer by hand. Nothing is marked as paid automatically.</p>'
          : '') +
      '</div>';
    }
  };

  function formatDate(iso) {
    try {
      return new Date(iso).toLocaleString('en-SG', {
        day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
      });
    } catch (e) { return iso; }
  }

  OrderView.formatDate = formatDate;
  global.OrderView = OrderView;
})(window);
