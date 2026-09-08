/* atelierR — data + state layer
   ---------------------------------------------------------------------------
   Everything the pages need in order to read products and to move an order
   through its lifecycle. Persistence goes through the `Store` object only, so
   swapping localStorage for a real API means rewriting this file and nothing
   else. Each method is already async-shaped where a backend would need it.
   --------------------------------------------------------------------------- */
(function (global) {
  'use strict';

  var CFG = global.ATELIER_CONFIG;

  /* ---------- helpers ---------- */
  function money(n) { return 'SGD ' + Number(n).toLocaleString('en-SG', { minimumFractionDigits: 0, maximumFractionDigits: 2 }); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (m) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
    });
  }
  function read(key, fallback) {
    try { var v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; }
    catch (e) { return fallback; }
  }
  function write(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); return true; }
    catch (e) { return false; }
  }
  function param(name) {
    return new URLSearchParams(global.location.search).get(name);
  }
  function slug(s) { return String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }

  /* ---------- taxonomy ---------- */
  var CATEGORIES = [
    { id: 'base-makeup',  name: 'Base Makeup',  blurb: 'Foundation, primer, powder', art: { shape: 'swatch', tone: 'sand' } },
    { id: 'point-makeup', name: 'Point Makeup', blurb: 'Eyes, cheeks, lips',         art: { shape: 'powder', tone: 'rose' } },
    { id: 'skincare',     name: 'Skincare',     blurb: 'Cleanse, hydrate, treat',    art: { shape: 'drops',  tone: 'sage' } },
    { id: 'tools',        name: 'Tools',        blurb: 'Brushes and accessories',    art: { shape: 'brush',  tone: 'stone' } },
    { id: 'sets',         name: 'Sets',         blurb: 'Curated, complete routines', art: { shape: 'set',    tone: 'clay' } }
  ];

  var BRANDS = [
    { id: 'suqqu',         name: 'SUQQU',         note: 'Refined colour, exceptional powder texture.' },
    { id: 'rmk',           name: 'RMK',           note: 'Modern, weightless base makeup.' },
    { id: 'three',         name: 'THREE',         note: 'Botanical formulas with a luminous finish.' },
    { id: 'noevir',        name: 'NOEVIR',        note: 'Herbal skincare, built on simple routines.' },
    { id: 'celvoke',       name: 'Celvoke',       note: 'Plant-led skincare and quiet colour.' },
    { id: 'brown-etoile',  name: 'BROWN ÉTOILE',  note: 'Brushes and tools for precise, gentle work.' },
    { id: 'addiction',     name: 'ADDICTION',     note: 'Pigment-rich colour with a clean finish.' },
    { id: 'atelierr',      name: 'atelierR',      note: 'Curated sets assembled by atelierR.' }
  ];

  /* ---------- catalogue ---------- */
  var Catalog = {
    all: function () { return (global.PRODUCTS || []).filter(function (p) { return p.active !== false; }); },
    byId: function (id) {
      var list = global.PRODUCTS || [];
      for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
      return null;
    },
    byIds: function (ids) {
      return (ids || []).map(Catalog.byId).filter(function (p) { return p && p.active !== false; });
    },
    byCategory: function (cat) { return Catalog.all().filter(function (p) { return p.category === cat; }); },
    byBrand: function (brandId) { return Catalog.all().filter(function (p) { return slug(p.brand) === brandId; }); },
    bestSellers: function (limit) {
      var list = Catalog.all().filter(function (p) { return p.bestSeller; });
      return limit ? list.slice(0, limit) : list;
    },
    search: function (q) {
      q = String(q || '').trim().toLowerCase();
      if (q.length < 2) return [];
      return Catalog.all().filter(function (p) {
        return (p.name + ' ' + p.brand + ' ' + p.subcategory + ' ' + p.shortDescription + ' ' +
                (p.bestFor || []).join(' ') + ' ' + p.finish).toLowerCase().indexOf(q) > -1;
      }).slice(0, 8);
    },
    categories: CATEGORIES,
    brands: BRANDS,
    category: function (id) { return CATEGORIES.filter(function (c) { return c.id === id; })[0] || null; },
    brand: function (id) { return BRANDS.filter(function (b) { return b.id === id; })[0] || null; },
    brandSlug: slug,
    /* Stock is a number; these describe it in words the customer understands. */
    stockLabel: function (p) {
      if (!p) return { text: '', cls: 'stock-out' };
      if (p.stock <= 0) return { text: 'Sold out', cls: 'stock-out' };
      if (p.stock <= 3) return { text: 'Low stock — ' + p.stock + ' left', cls: 'stock-low' };
      return { text: 'In stock', cls: 'stock-in' };
    }
  };

  /* ---------- cart ---------- */
  var Cart = {
    items: function () {
      return read(CFG.keys.cart, []).filter(function (l) { return Catalog.byId(l.id); });
    },
    save: function (items) { write(CFG.keys.cart, items); document.dispatchEvent(new CustomEvent('cart:change')); },
    count: function () {
      return Cart.items().reduce(function (n, l) { return n + l.qty; }, 0);
    },
    add: function (id, qty, shade) {
      var product = Catalog.byId(id);
      if (!product || product.stock <= 0) return false;
      qty = Math.max(1, parseInt(qty, 10) || 1);
      var items = Cart.items();
      var key = id + '::' + (shade || '');
      var existing = items.filter(function (l) { return l.key === key; })[0];
      if (existing) existing.qty = Math.min(product.stock, existing.qty + qty);
      else items.push({ key: key, id: id, shade: shade || '', qty: Math.min(product.stock, qty) });
      Cart.save(items);
      return true;
    },
    setQty: function (key, qty) {
      var items = Cart.items();
      items.forEach(function (l) {
        if (l.key !== key) return;
        var p = Catalog.byId(l.id);
        l.qty = Math.max(1, Math.min(p ? p.stock : 1, parseInt(qty, 10) || 1));
      });
      Cart.save(items);
    },
    remove: function (key) {
      Cart.save(Cart.items().filter(function (l) { return l.key !== key; }));
    },
    clear: function () { Cart.save([]); },
    /* Cart lines joined to their product records, plus totals. */
    detailed: function () {
      var lines = Cart.items().map(function (l) {
        var p = Catalog.byId(l.id);
        return {
          key: l.key, id: l.id, shade: l.shade, qty: l.qty, product: p,
          unitPrice: p.priceSGD, lineTotal: p.priceSGD * l.qty
        };
      });
      var subtotal = lines.reduce(function (n, l) { return n + l.lineTotal; }, 0);
      var delivery = subtotal === 0 ? 0 : (subtotal >= CFG.delivery.freeThreshold ? 0 : CFG.delivery.flatRate);
      return { lines: lines, subtotal: subtotal, delivery: delivery, total: subtotal + delivery,
               count: lines.reduce(function (n, l) { return n + l.qty; }, 0) };
    }
  };

  /* ---------- orders ---------- */
  /* The full lifecycle. `atelierR` must confirm payment manually: nothing in
     this file ever advances an order past AWAITING_VERIFICATION. */
  var STATUS = {
    CART:                  'Cart',
    CREATED:               'Order Created',
    AWAITING_PAYMENT:      'Awaiting PayNow Payment',
    AWAITING_VERIFICATION: 'Awaiting Payment Verification',
    CONFIRMED:             'Payment Confirmed',
    PREPARING:             'Preparing Order',
    SHIPPED:               'Shipped',
    COMPLETED:             'Completed'
  };
  var STATUS_FLOW = [
    { key: 'CREATED',               label: STATUS.CREATED,               note: 'Your order has been created and saved.' },
    { key: 'AWAITING_PAYMENT',      label: STATUS.AWAITING_PAYMENT,      note: 'Transfer the total by PayNow.' },
    { key: 'AWAITING_VERIFICATION', label: STATUS.AWAITING_VERIFICATION, note: 'atelierR is checking your PayNow transfer.' },
    { key: 'CONFIRMED',             label: STATUS.CONFIRMED,             note: 'Payment verified — your order is confirmed.' },
    { key: 'PREPARING',             label: STATUS.PREPARING,             note: 'Your order is being packed.' },
    { key: 'SHIPPED',               label: STATUS.SHIPPED,               note: 'On its way. Tracking is sent to you.' },
    { key: 'COMPLETED',             label: STATUS.COMPLETED,             note: 'Delivered.' }
  ];

  function orderNumber() {
    var d = new Date();
    var stamp = String(d.getFullYear()).slice(2) +
                String(d.getMonth() + 1).padStart(2, '0') +
                String(d.getDate()).padStart(2, '0');
    var rand = String(Math.floor(1000 + Math.random() * 9000));
    return 'ATR-' + stamp + '-' + rand;
  }

  var Orders = {
    STATUS: STATUS,
    FLOW: STATUS_FLOW,

    all: function () { return read(CFG.keys.orders, []); },
    byNumber: function (num) {
      return Orders.all().filter(function (o) { return o.orderNumber === num; })[0] || null;
    },

    /* Creates the order record from the cart + customer details. */
    create: function (customer) {
      var cart = Cart.detailed();
      if (!cart.lines.length) return null;
      var now = new Date().toISOString();
      var order = {
        orderNumber: orderNumber(),
        customer: {
          firstName: customer.firstName, lastName: customer.lastName,
          email: customer.email, whatsapp: customer.whatsapp,
          address: customer.address, postalCode: customer.postalCode,
          notes: customer.notes || ''
        },
        items: cart.lines.map(function (l) {
          return { id: l.id, brand: l.product.brand, name: l.product.name, shade: l.shade,
                   qty: l.qty, unitPrice: l.unitPrice, lineTotal: l.lineTotal };
        }),
        subtotal: cart.subtotal,
        delivery: cart.delivery,
        total: cart.total,
        currency: CFG.currency,
        paymentMethod: 'PayNow',
        paymentStatus: 'unpaid',          // unpaid | submitted | verified
        paymentScreenshot: null,          // { name, dataUrl, uploadedAt } or { channel: 'whatsapp' }
        orderStatus: STATUS.CREATED,
        statusKey: 'CREATED',
        history: [{ status: STATUS.CREATED, at: now }],
        createdAt: now,
        updatedAt: now
      };
      var orders = Orders.all();
      orders.unshift(order);
      write(CFG.keys.orders, orders.slice(0, 40));
      write(CFG.keys.lastOrder, order.orderNumber);

      /* The browser's copy is authoritative for the customer; the database
         copy is what lets atelierR see the order at all. The write is fired
         but never awaited, and a failure is queued rather than surfaced —
         the customer already has their order number and must not be stopped. */
      if (global.Backend && global.Backend.configured()) {
        global.Backend.saveOrder(order);
      }
      return order;
    },

    /* Moves an order to a new status. Guarded: verification is manual only. */
    setStatus: function (num, statusKey, patch) {
      var orders = Orders.all(), changed = null;
      orders.forEach(function (o) {
        if (o.orderNumber !== num) return;
        var now = new Date().toISOString();
        o.statusKey = statusKey;
        o.orderStatus = STATUS[statusKey];
        o.updatedAt = now;
        o.history.push({ status: o.orderStatus, at: now });
        if (patch) Object.keys(patch).forEach(function (k) { o[k] = patch[k]; });
        changed = o;
      });
      /* A screenshot data URL can exceed the storage quota. If the write fails,
         keep the order and the status change and drop only the image bytes —
         atelierR still verifies against the PayNow account itself. */
      if (!write(CFG.keys.orders, orders)) {
        orders.forEach(function (o) {
          if (o.paymentScreenshot && o.paymentScreenshot.dataUrl) {
            o.paymentScreenshot = {
              name: o.paymentScreenshot.name,
              uploadedAt: o.paymentScreenshot.uploadedAt,
              stored: false
            };
          }
        });
        write(CFG.keys.orders, orders);
      }
      return changed;
    },

    markAwaitingPayment: function (num) { return Orders.setStatus(num, 'AWAITING_PAYMENT'); },

    /* The customer says they have paid. This NEVER means "paid" — it means a
       human at atelierR still has to check PayNow and confirm. */
    submitPaymentProof: function (num, proof) {
      if (global.Backend && global.Backend.configured()) {
        global.Backend.reportPayment(num, proof);
      }
      return Orders.setStatus(num, 'AWAITING_VERIFICATION', {
        paymentStatus: 'submitted',
        paymentScreenshot: proof || { channel: 'whatsapp', uploadedAt: new Date().toISOString() }
      });
    },

    last: function () {
      var num = read(CFG.keys.lastOrder, null);
      return num ? Orders.byNumber(num) : null;
    },

    /* Index of a status within the flow, for rendering the tracker. */
    flowIndex: function (statusKey) {
      for (var i = 0; i < STATUS_FLOW.length; i++) if (STATUS_FLOW[i].key === statusKey) return i;
      return 0;
    },

    /* Pre-written WhatsApp message for sending a payment screenshot. */
    whatsappLink: function (order) {
      var msg = 'Hi atelierR, I’ve completed the PayNow payment for Order #' + order.orderNumber + '.\n' +
                'Name: ' + order.customer.firstName + ' ' + order.customer.lastName + '\n' +
                'Amount: ' + money(order.total) + '\n' +
                'Payment screenshot attached.';
      return 'https://wa.me/' + CFG.contact.whatsapp + '?text=' + encodeURIComponent(msg);
    }
  };

  global.Store = {
    CFG: CFG, Catalog: Catalog, Cart: Cart, Orders: Orders,
    money: money, esc: esc, param: param, slug: slug, read: read, write: write
  };
})(window);
