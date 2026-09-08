/* atelierR — newsletter signup
   One component, mounted wherever a signup belongs: homepage, footer, journal
   pages and the order page. Subscribers go to the same database as orders, and
   the local copy means a signup is never lost to a dropped connection.

   The subscriber record is deliberately the shape every email platform expects,
   so exporting to Mailchimp, Klaviyo, Brevo or Resend later is a mapping job
   and not a migration:
       { email, first_name, source, status, consented_at } */
(function (global) {
  'use strict';

  var S = global.Store, esc = S.esc;
  var LOCAL_KEY = 'atelierR.subscribers';

  var COPY = {
    title: 'Beauty notes from atelierR',
    body: 'New stories, product edits and recommendations from Noriko.',
    button: 'Subscribe',
    done: 'Thank you — you’re on the list.',
    doneBody: 'The next note from atelierR will arrive in your inbox.'
  };

  function localList() {
    try { return JSON.parse(localStorage.getItem(LOCAL_KEY)) || []; }
    catch (e) { return []; }
  }
  function remember(record) {
    var list = localList().filter(function (r) { return r.email !== record.email; });
    list.push(record);
    try { localStorage.setItem(LOCAL_KEY, JSON.stringify(list.slice(-50))); } catch (e) {}
  }
  function alreadySubscribed(email) {
    return localList().some(function (r) { return r.email === String(email).toLowerCase(); });
  }

  function subscribe(firstName, email, source) {
    var record = {
      email: String(email).trim().toLowerCase(),
      first_name: String(firstName || '').trim(),
      source: source || 'site',
      status: 'subscribed',
      consented_at: new Date().toISOString()
    };
    remember(record);
    if (global.Backend && global.Backend.configured()) {
      return global.Backend.subscribe(record).then(function () { return record; });
    }
    return Promise.resolve(record);
  }

  /* opts: { variant: 'panel' | 'quiet' | 'footer', source: 'homepage', title, body } */
  function markup(opts) {
    opts = opts || {};
    var id = 'nl' + Math.random().toString(36).slice(2, 7);
    var cls = 'nl' + (opts.variant === 'quiet' ? ' nl-quiet' : '');
    return '<section class="' + cls + '" data-newsletter data-source="' + esc(opts.source || 'site') + '">' +
      '<div class="nl-inner">' +
        '<p class="eyebrow mb-8">Newsletter</p>' +
        '<p class="h3 serif">' + esc(opts.title || COPY.title) + '</p>' +
        '<p class="small mt-8">' + esc(opts.body || COPY.body) + '</p>' +
        '<form class="nl-form" novalidate>' +
          /* .field is what carries the invalid state and reveals .field-error */
          '<div class="field">' +
            '<label class="sr-only" for="' + id + 'n">First name</label>' +
            '<input id="' + id + 'n" name="firstName" type="text" placeholder="First name" autocomplete="given-name">' +
          '</div>' +
          '<div class="field">' +
            '<label class="sr-only" for="' + id + 'e">Email</label>' +
            '<input id="' + id + 'e" name="email" type="email" placeholder="Email address" autocomplete="email" required>' +
            '<p class="field-error">Please enter a valid email address.</p>' +
          '</div>' +
          '<button class="btn" type="submit">' + esc(COPY.button) + '</button>' +
        '</form>' +
        '<p class="tiny mt-16">No more than a few notes a month. Unsubscribe any time.</p>' +
      '</div>' +
    '</section>';
  }

  function bind(root) {
    (root || document).querySelectorAll('[data-newsletter]').forEach(function (el) {
      if (el._bound) return;
      el._bound = true;
      var form = el.querySelector('form');

      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var name = form.elements.firstName.value;
        var email = form.elements.email.value.trim();
        var valid = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
        form.elements.email.closest('.field').classList.toggle('invalid', !valid);
        if (!valid) { form.elements.email.focus(); return; }

        var btn = form.querySelector('button');
        btn.disabled = true;
        btn.textContent = 'Subscribing…';

        var was = alreadySubscribed(email);
        subscribe(name, email, el.getAttribute('data-source')).then(function () {
          el.querySelector('.nl-inner').innerHTML =
            '<p class="eyebrow mb-8">Newsletter</p>' +
            '<p class="h3 serif">' + esc(was ? 'You’re already on the list.' : COPY.done) + '</p>' +
            '<p class="small mt-8">' + esc(was
              ? 'No need to sign up again — we have this address.'
              : COPY.doneBody) + '</p>';
        }).catch(function () {
          /* Kept locally regardless, so the signup is not lost. */
          el.querySelector('.nl-inner').innerHTML =
            '<p class="eyebrow mb-8">Newsletter</p>' +
            '<p class="h3 serif">' + esc(COPY.done) + '</p>' +
            '<p class="small mt-8">' + esc(COPY.doneBody) + '</p>';
        });
      });
    });
  }

  /* Renders into every [data-newsletter-slot] on the page. */
  function mount(root) {
    (root || document).querySelectorAll('[data-newsletter-slot]').forEach(function (slot) {
      if (slot._filled) return;
      slot._filled = true;
      slot.innerHTML = markup({
        variant: slot.getAttribute('data-variant') || 'panel',
        source: slot.getAttribute('data-source') || 'site',
        title: slot.getAttribute('data-title') || null,
        body: slot.getAttribute('data-body') || null
      });
    });
    bind(root);
  }

  global.Newsletter = {
    COPY: COPY, markup: markup, bind: bind, mount: mount,
    subscribe: subscribe, local: localList
  };
})(window);
