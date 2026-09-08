/* atelierR — Journal
   Reads window.ARTICLES and renders the journal index, article pages, the
   homepage strip, and the derived newsletter and Instagram drafts. Adding a
   story means adding an object to articles.js — never touching a layout. */
(function (global) {
  'use strict';

  var S = global.Store, esc = S.esc, money = S.money;

  function all() {
    return (global.ARTICLES || [])
      .filter(function (a) { return a.published !== false; })
      .sort(function (a, b) { return (b.date || '').localeCompare(a.date || ''); });
  }

  function bySlug(slug) {
    return all().filter(function (a) { return a.slug === slug; })[0] || null;
  }

  function category(id) {
    return (global.JOURNAL_CATEGORIES || []).filter(function (c) { return c.id === id; })[0] || null;
  }

  function categoryName(id) {
    var c = category(id);
    return c ? c.name : id;
  }

  function formatDate(iso) {
    try {
      return new Date(iso + 'T00:00:00').toLocaleDateString('en-SG',
        { day: 'numeric', month: 'long', year: 'numeric' });
    } catch (e) { return iso; }
  }

  function url(a) { return 'article.html?a=' + encodeURIComponent(a.slug); }

  function absoluteUrl(a) {
    var base = global.location.href.replace(/[^/]*$/, '');
    return base + url(a);
  }

  /* Hero art, replaced by a photo at assets/img/journal/<slug>.jpg when one
     exists — the same arrangement the product photos use. */
  function hero(a, opts) {
    opts = opts || {};
    return '<span class="jr-media" data-photo="' + esc(a.slug) + '" data-photo-dir="journal" ' +
      'data-photo-alt="' + esc(a.title) + '">' +
      global.Imagery.render(a.art || { shape: 'stone', tone: 'stone' },
        { ratio: opts.ratio || '400 260', label: a.title }) + '</span>';
  }

  /* ---------- article body ---------- */
  function productRow(ids, title) {
    var list = S.Catalog.byIds(ids || []);
    if (!list.length) return '';
    return '<div class="jr-shop">' +
      (title ? '<p class="jr-shop-title">' + esc(title) + '</p>' : '') +
      '<div class="product-grid cols-3">' + global.UI.grid(list) + '</div>' +
    '</div>';
  }

  function pickBlock(id, label) {
    var p = S.Catalog.byId(id);
    if (!p) return '';
    var stock = S.Catalog.stockLabel(p);
    return '<aside class="jr-pick">' +
      '<a class="jr-pick-media" href="product.html?id=' + esc(p.id) + '" ' +
        'data-photo="' + esc(p.id) + '" aria-label="' + esc(p.brand + ' ' + p.name) + '">' +
        global.Imagery.render(p.art, { ratio: '400 440' }) + '</a>' +
      '<div class="jr-pick-body">' +
        '<p class="eyebrow">' + esc(label || 'Today’s Pick') + '</p>' +
        '<p class="card-brand mt-8">' + esc(p.brand) + '</p>' +
        '<h3 class="h3 serif" style="margin:4px 0 8px">' +
          '<a href="product.html?id=' + esc(p.id) + '">' + esc(p.name) + '</a></h3>' +
        '<p class="small">' + esc(p.shortDescription) + '</p>' +
        '<p class="card-price mt-8">' + money(p.priceSGD) + '</p>' +
        '<p class="stock ' + stock.cls + ' mb-16">' + esc(stock.text) + '</p>' +
        '<div class="row">' +
          (p.stock > 0
            ? '<button class="btn btn-sm" data-add="' + esc(p.id) + '">Add to Cart</button>'
            : '<span class="btn btn-quiet btn-sm" aria-disabled="true">Sold out</span>') +
          '<a class="btn btn-quiet btn-sm" href="product.html?id=' + esc(p.id) + '">View</a>' +
        '</div>' +
      '</div>' +
    '</aside>';
  }

  /* `shown` collects the product ids already displayed, so the same product is
     never shown twice in one story: a pick repeated from the top slot is
     dropped, and the closing "Products Mentioned" only lists what the reader
     has not already met. */
  function renderBody(blocks, shown, opts) {
    shown = shown || [];
    opts = opts || {};
    var usedTitles = opts.usedTitles || [];
    /* A second highlighted product in the same story is a recommendation, not
       a second "Today's Pick". */
    var pickLabel = opts.pickLabel || 'Today’s Pick';
    function unseen(ids) {
      return (ids || []).filter(function (id) {
        if (shown.indexOf(id) > -1) return false;
        shown.push(id);
        return true;
      });
    }
    return (blocks || []).map(function (b) {
      if (b.p)     return '<p>' + esc(b.p) + '</p>';
      if (b.h)     return '<h2 class="jr-h">' + esc(b.h) + '</h2>';
      if (b.quote) return '<blockquote class="jr-quote">' + esc(b.quote) + '</blockquote>';
      if (b.note)  return '<div class="notice jr-note">' + esc(b.note) + '</div>';
      if (b.list)  return '<ul class="jr-list">' + b.list.map(function (i) {
                            return '<li>' + esc(i) + '</li>'; }).join('') + '</ul>';
      if (b.steps) return '<ol class="steps-list jr-steps">' + b.steps.map(function (i) {
                            return '<li>' + esc(i) + '</li>'; }).join('') + '</ol>';
      if (b.image) return '<figure class="jr-figure">' +
                            global.Imagery.render(b.image, { ratio: '400 240' }) +
                            (b.caption ? '<figcaption class="tiny">' + esc(b.caption) + '</figcaption>' : '') +
                          '</figure>';
      if (b.shop) {
        var title = b.title || 'Shop the Products';
        usedTitles.push(String(title).toLowerCase());
        return productRow(unseen(b.shop), title);
      }
      if (b.pick)  return unseen([b.pick]).length ? pickBlock(b.pick, b.label || pickLabel) : '';
      return '';
    }).join('');
  }

  /* ---------- cards ---------- */
  function card(a, opts) {
    opts = opts || {};
    var linked = S.Catalog.byIds((a.products || []).slice(0, 3));
    return '<article class="jr-card">' +
      '<a class="jr-card-media" href="' + url(a) + '" aria-label="' + esc(a.title) + '">' +
        hero(a, { ratio: opts.ratio || '400 260' }) + '</a>' +
      '<p class="jr-meta">' + esc(categoryName(a.category)) + ' · ' + esc(formatDate(a.date)) + '</p>' +
      '<h3 class="jr-title"><a href="' + url(a) + '">' + esc(a.title) + '</a></h3>' +
      '<p class="jr-excerpt">' + esc(a.excerpt) + '</p>' +
      (opts.showProducts !== false && linked.length
        ? '<p class="tiny jr-linked">In this story: ' + linked.map(function (p) {
            return '<a class="link-under" href="product.html?id=' + esc(p.id) + '">' +
                   esc(p.name) + '</a>';
          }).join(' · ') + '</p>'
        : '') +
      '<p class="mt-8"><a class="link-more" href="' + url(a) + '">Read</a></p>' +
    '</article>';
  }

  /* ---------- derived drafts ----------
     Nothing here sends anything. Both produce text for a person to approve. */
  function plainBody(a) {
    return (a.body || []).filter(function (b) { return b.p; })
      .map(function (b) { return b.p; });
  }

  function newsletterDraft(a) {
    var pick = S.Catalog.byId(a.todaysPick);
    var products = S.Catalog.byIds(a.products || []);
    var link = absoluteUrl(a);
    return {
      subject: a.title + ' — Beauty notes from atelierR',
      preheader: a.excerpt,
      title: a.title,
      category: categoryName(a.category),
      date: formatDate(a.date),
      summary: a.excerpt,
      intro: plainBody(a).slice(0, 2),
      pick: pick ? { name: pick.name, brand: pick.brand, price: money(pick.priceSGD),
                     url: link.replace(/article\.html.*$/, 'product.html?id=' + pick.id),
                     description: pick.shortDescription } : null,
      products: products.map(function (p) {
        return { name: p.name, brand: p.brand, price: money(p.priceSGD),
                 url: link.replace(/article\.html.*$/, 'product.html?id=' + p.id) };
      }),
      readMoreUrl: link,
      shopUrl: link.replace(/article\.html.*$/, 'shop.html'),
      status: 'draft'
    };
  }

  function instagramDrafts(a) {
    var ig = a.instagram || {};
    var pick = S.Catalog.byId(a.todaysPick);
    var tags = ['#atelierR', '#japanesebeauty', '#singaporebeauty', '#quietluxury',
                '#' + String(categoryName(a.category)).replace(/[^A-Za-z]/g, '')];
    var link = absoluteUrl(a);

    var short = ig.short || (a.title + '\n\n' + a.excerpt + '\n\nRead the full note — link in bio.\n\n' + tags.join(' '));

    var longCaption = ig.long || ([a.title, '', a.excerpt, '']
      .concat(plainBody(a).slice(0, 3))
      .concat(['', pick ? 'Today’s Pick — ' + pick.brand + ' ' + pick.name + ', ' + money(pick.priceSGD) : '',
               '', 'Full story on the atelierR Journal — link in bio.', '', tags.join(' ')])
      .filter(function (l, i, arr) { return !(l === '' && arr[i - 1] === ''); })
      .join('\n'));

    var story = ig.story || (a.title + '\n' + a.excerpt.split('.')[0] + '.\n\nSwipe up / link in bio');

    return { short: short, long: longCaption, story: story, url: link,
             hashtags: tags.join(' '), status: 'draft' };
  }

  /* The whole article body, including the Today's Pick slot and the closing
     product row, assembled so nothing repeats. */
  function renderArticle(a) {
    var shown = [], usedTitles = [];
    var head = '';
    var hasTopPick = !!(a.todaysPick && S.Catalog.byId(a.todaysPick));
    if (hasTopPick) {
      shown.push(a.todaysPick);
      head = pickBlock(a.todaysPick, 'Today’s Pick');
    }

    var body = renderBody(a.body, shown, {
      usedTitles: usedTitles,
      /* Only one thing in a story is Today's Pick. */
      pickLabel: hasTopPick ? 'atelierR Recommends' : 'Today’s Pick'
    });

    /* Whatever the story has not already shown, under a heading the story has
       not already used. */
    var rest = (a.products || []).filter(function (id) { return shown.indexOf(id) === -1; });
    var tailTitle = usedTitles.indexOf('products mentioned') > -1
      ? 'Also in this story' : 'Products Mentioned';
    var tail = rest.length ? productRow(rest, tailTitle) : '';
    return { head: head, body: body, tail: tail };
  }

  global.Journal = {
    renderArticle: renderArticle,
    all: all, bySlug: bySlug, url: url, absoluteUrl: absoluteUrl,
    category: category, categoryName: categoryName, formatDate: formatDate,
    hero: hero, card: card, renderBody: renderBody,
    productRow: productRow, pickBlock: pickBlock,
    categories: function () { return global.JOURNAL_CATEGORIES || []; },
    latest: function (n) { return all().slice(0, n || 3); },
    byCategory: function (id) {
      return all().filter(function (a) { return a.category === id; });
    },
    newsletterDraft: newsletterDraft,
    instagramDrafts: instagramDrafts
  };
})(window);
