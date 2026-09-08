/* atelierR — Supabase backend
   ---------------------------------------------------------------------------
   Orders live in the database so atelierR can see them from any device. The
   customer's browser keeps its own copy regardless, because losing an order to
   a dropped connection is not acceptable: every write is queued and retried,
   and the customer is never blocked on the network.

   The key below is public by design — it is in the page source of every
   visitor. What protects the data is the Row Level Security in
   supabase/schema.sql, which lets the public insert and nothing else.
   --------------------------------------------------------------------------- */
(function (global) {
  'use strict';

  var CFG = global.ATELIER_CONFIG.supabase || {};
  var QUEUE_KEY = 'atelierR.pendingWrites';
  var TOKEN_KEY = 'atelierR.session';

  function configured() { return !!(CFG.url && CFG.key); }

  /* Every write carries a client-generated id so it can be replayed safely.
     This matters because checkout navigates to the PayNow page the instant an
     order is created: the browser aborts the in-flight request, which looks
     like a failure even though the row already landed. Without an id, the
     retry would insert the order a second time. */
  function uuid() {
    if (global.crypto && global.crypto.randomUUID) return global.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }
  function endpoint(path) { return CFG.url.replace(/\/$/, '') + path; }

  function headers(extra) {
    var h = {
      'apikey': CFG.key,
      'Authorization': 'Bearer ' + CFG.key,
      'Content-Type': 'application/json'
    };
    if (extra) Object.keys(extra).forEach(function (k) { h[k] = extra[k]; });
    return h;
  }

  /* ---------- the retry queue ----------
     A failed write is not lost. It is kept and replayed on the next page load,
     so a customer on a flaky connection still reaches atelierR's order list. */
  function queue() {
    try { return JSON.parse(localStorage.getItem(QUEUE_KEY)) || []; }
    catch (e) { return []; }
  }
  function saveQueue(list) {
    try { localStorage.setItem(QUEUE_KEY, JSON.stringify(list.slice(-30))); } catch (e) {}
  }
  function enqueue(table, row) {
    var list = queue();
    list.push({ table: table, row: row, at: Date.now() });
    saveQueue(list);
  }

  function insert(table, row) {
    if (!configured()) return Promise.reject(new Error('backend not configured'));
    return fetch(endpoint('/rest/v1/' + table), {
      method: 'POST',
      /* ignore-duplicates makes a replayed write a no-op rather than an error */
      headers: headers({ 'Prefer': 'return=minimal,resolution=ignore-duplicates' }),
      body: JSON.stringify(row)
    }).then(function (r) {
      if (r.ok) return true;
      /* A conflict means the row is already there — the write succeeded, we
         simply did not get to hear about it the first time. */
      if (r.status === 409) return true;
      return r.text().then(function (t) {
        if (/duplicate key|already exists/i.test(t)) return true;
        throw new Error(r.status + ' ' + t);
      });
    });
  }

  /* Writes, then falls back to the queue. Never rejects: the caller is a
     checkout flow, and a customer must not be stopped by our infrastructure. */
  function write(table, row) {
    if (!configured()) return Promise.resolve({ ok: false, reason: 'not-configured' });
    return insert(table, row)
      .then(function () { return { ok: true }; })
      .catch(function (err) {
        enqueue(table, row);
        return { ok: false, reason: String(err && err.message || err) };
      });
  }

  function flush() {
    if (!configured()) return Promise.resolve(0);
    var list = queue();
    if (!list.length) return Promise.resolve(0);
    saveQueue([]);
    var failed = [], done = 0;
    return list.reduce(function (chain, item) {
      return chain.then(function () {
        return insert(item.table, item.row)
          .then(function () { done++; })
          .catch(function () { failed.push(item); });
      });
    }, Promise.resolve()).then(function () {
      if (failed.length) saveQueue(failed);
      return done;
    });
  }

  /* ---------- shaping ----------
     The database column names are snake_case; the site's objects are camelCase.
     Converting here keeps that difference from leaking into the pages. */
  function orderRow(order) {
    return {
      id: order.writeId || (order.writeId = uuid()),
      order_number: order.orderNumber,
      customer: order.customer,
      items: order.items,
      subtotal: order.subtotal,
      delivery: order.delivery,
      total: order.total,
      currency: order.currency,
      payment_method: order.paymentMethod,
      payment_status: 'unpaid',        // the schema rejects anything else
      order_status: order.orderStatus,
      status_key: order.statusKey === 'AWAITING_PAYMENT' ? 'AWAITING_PAYMENT' : 'CREATED',
      history: order.history,
      created_at: order.createdAt
    };
  }

  function fromRow(row) {
    return {
      orderNumber: row.order_number,
      customer: row.customer,
      items: row.items,
      subtotal: Number(row.subtotal),
      delivery: Number(row.delivery),
      total: Number(row.total),
      currency: row.currency,
      paymentMethod: row.payment_method,
      paymentStatus: row.payment_status,
      orderStatus: row.order_status,
      statusKey: row.status_key,
      history: row.history || [],
      createdAt: row.created_at,
      updatedAt: row.updated_at
    };
  }

  /* ---------- staff session ---------- */
  function session() {
    try { return JSON.parse(localStorage.getItem(TOKEN_KEY)); } catch (e) { return null; }
  }
  function setSession(s) {
    try {
      if (s) localStorage.setItem(TOKEN_KEY, JSON.stringify(s));
      else localStorage.removeItem(TOKEN_KEY);
    } catch (e) {}
  }
  function authHeaders() {
    var s = session();
    return headers(s ? { 'Authorization': 'Bearer ' + s.access_token } : null);
  }

  var Backend = {
    configured: configured,

    /* Records a new order. Resolves either way — see write(). */
    saveOrder: function (order) { return write('orders', orderRow(order)); },

    /* Records that the customer says they have paid. Deliberately a separate
       table: a claim is not a confirmation, and the order row is untouchable
       by the public. */
    reportPayment: function (orderNumber, proof) {
      return write('payment_reports', {
        id: uuid(),
        order_number: orderNumber,
        channel: proof && proof.channel === 'whatsapp' ? 'whatsapp' : 'upload',
        screenshot: proof && proof.dataUrl ? proof.dataUrl : null,
        note: proof && proof.name ? proof.name : null
      });
    },

    /* Newsletter signups ride the same queue as orders, so a signup made on a
       bad connection is replayed rather than dropped. */
    subscribe: function (record) {
      return write('subscribers', {
        id: uuid(),
        email: record.email,
        first_name: record.first_name,
        source: record.source,
        status: record.status,
        consented_at: record.consented_at
      });
    },

    listSubscribers: function () {
      return fetch(endpoint('/rest/v1/subscribers?select=*&order=consented_at.desc&limit=500'),
                   { headers: authHeaders() })
        .then(function (r) { return r.ok ? r.json() : []; })
        .catch(function () { return []; });
    },

    retryPending: flush,
    pendingCount: function () { return queue().length; },

    /* ---------- staff ---------- */
    signIn: function (email, password) {
      return fetch(endpoint('/auth/v1/token?grant_type=password'), {
        method: 'POST', headers: headers(),
        body: JSON.stringify({ email: email, password: password })
      }).then(function (r) {
        return r.json().then(function (data) {
          if (!r.ok) throw new Error(data.error_description || data.msg || data.error || 'Sign in failed');
          setSession(data);
          return data;
        });
      });
    },
    signOut: function () { setSession(null); },
    signedIn: function () { return !!session(); },

    listOrders: function () {
      return fetch(endpoint('/rest/v1/orders?select=*&order=created_at.desc&limit=200'),
                   { headers: authHeaders() })
        .then(function (r) {
          if (r.status === 401) { setSession(null); throw new Error('Session expired — please sign in again.'); }
          if (!r.ok) return r.text().then(function (t) { throw new Error(t); });
          return r.json();
        })
        .then(function (rows) { return rows.map(fromRow); });
    },

    listPaymentReports: function () {
      return fetch(endpoint('/rest/v1/payment_reports?select=*&order=created_at.desc&limit=200'),
                   { headers: authHeaders() })
        .then(function (r) { return r.ok ? r.json() : []; })
        .catch(function () { return []; });
    },

    updateOrder: function (orderNumber, patch) {
      return fetch(endpoint('/rest/v1/orders?order_number=eq.' + encodeURIComponent(orderNumber)), {
        method: 'PATCH',
        headers: authHeaders(),
        body: JSON.stringify(patch)
      }).then(function (r) {
        if (!r.ok) return r.text().then(function (t) { throw new Error(t); });
        return true;
      });
    }
  };

  /* Replay anything stranded by an earlier failure. */
  if (configured() && global.addEventListener) {
    global.addEventListener('load', function () { flush(); });
  }

  global.Backend = Backend;
})(window);
