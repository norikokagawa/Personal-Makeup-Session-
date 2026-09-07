/* atelierR — shared interface
   Header, drawer, search, footer, product cards, toasts, accordions.
   Every page includes this and calls UI.mount(). */
(function (global) {
  'use strict';

  var S = global.Store, CFG = global.ATELIER_CONFIG, esc = S.esc, money = S.money;

  var NAV = [
    { label: 'Shop All',     href: 'shop.html' },
    { label: 'Base Makeup',  href: 'category.html?c=base-makeup' },
    { label: 'Point Makeup', href: 'category.html?c=point-makeup' },
    { label: 'Skincare',     href: 'category.html?c=skincare' },
    { label: 'Tools',        href: 'category.html?c=tools' },
    { label: 'Sets',         href: 'category.html?c=sets' },
    { label: 'Brands',       href: 'brands.html' },
    { label: 'FAQ',          href: 'faq.html' },
    { label: 'About',        href: 'about.html' }
  ];

  var ICONS = {
    search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M16.5 16.5 21 21"/></svg>',
    bag: '<svg viewBox="0 0 24 24"><path d="M6 8h12l1 12H5L6 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg>',
    menu: '<svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    close: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>'
  };

  var UI = {

    /* ---------- header ---------- */
    header: function (current) {
      return '' +
      '<header class="header">' +
        '<div class="wrap header-inner">' +
          '<a class="logo" href="index.html" aria-label="atelierR home">' +
            '<span class="logo-mark">atelier<b>R</b></span>' +
            '<span class="logo-tag">' + esc(CFG.tagline) + '</span>' +
          '</a>' +
          '<nav class="nav" aria-label="Main">' +
            NAV.map(function (n) {
              var on = current && n.href.indexOf(current) === 0 ? ' aria-current="page"' : '';
              return '<a href="' + n.href + '"' + on + '>' + esc(n.label) + '</a>';
            }).join('') +
          '</nav>' +
          '<div class="header-actions">' +
            '<button class="icon-btn" data-search-open aria-label="Search products">' + ICONS.search + '</button>' +
            '<a class="icon-btn" href="cart.html" aria-label="Cart">' + ICONS.bag +
              '<span class="cart-count" data-cart-count hidden>0</span></a>' +
            '<button class="icon-btn burger" data-drawer-open aria-label="Open menu">' + ICONS.menu + '</button>' +
          '</div>' +
        '</div>' +
      '</header>' +

      '<div class="drawer" data-drawer hidden>' +
        '<div class="wrap">' +
          '<div class="drawer-head">' +
            '<span class="logo-mark">atelier<b>R</b></span>' +
            '<button class="icon-btn" data-drawer-close aria-label="Close menu">' + ICONS.close + '</button>' +
          '</div>' +
          '<nav aria-label="Mobile">' +
            NAV.slice(0, 6).map(function (n) { return '<a href="' + n.href + '">' + esc(n.label) + '</a>'; }).join('') +
            '<div class="drawer-sub">' +
              NAV.slice(6).map(function (n) { return '<a href="' + n.href + '">' + esc(n.label) + '</a>'; }).join('') +
              '<a href="shade-guide.html">Shade Guide</a>' +
              '<a href="cart.html">Cart</a>' +
            '</div>' +
          '</nav>' +
        '</div>' +
      '</div>' +

      '<div class="search-overlay" data-search>' +
        '<div class="wrap wrap-narrow">' +
          '<div class="row row-between mb-16">' +
            '<span class="eyebrow">Search</span>' +
            '<button class="icon-btn" data-search-close aria-label="Close search">' + ICONS.close + '</button>' +
          '</div>' +
          '<input class="search-field" type="search" placeholder="Foundation, brush, SUQQU…" data-search-input aria-label="Search products">' +
          '<div class="search-results" data-search-results></div>' +
        '</div>' +
      '</div>';
    },

    /* ---------- footer ---------- */
    footer: function () {
      return '' +
      '<footer class="footer">' +
        '<div class="wrap">' +
          '<div class="footer-grid">' +
            '<div>' +
              '<span class="logo-mark">atelier<b>R</b></span>' +
              '<p class="small mt-16" style="max-width:34ch">Japanese beauty, curated through professional makeup practice. Delivered across Singapore.</p>' +
            '</div>' +
            '<div>' +
              '<h4>Shop</h4>' +
              '<ul>' +
                '<li><a href="shop.html">Shop All</a></li>' +
                '<li><a href="category.html?c=base-makeup">Base Makeup</a></li>' +
                '<li><a href="category.html?c=point-makeup">Point Makeup</a></li>' +
                '<li><a href="category.html?c=skincare">Skincare</a></li>' +
                '<li><a href="category.html?c=tools">Tools</a></li>' +
                '<li><a href="category.html?c=sets">Sets</a></li>' +
                '<li><a href="brands.html">Brands</a></li>' +
              '</ul>' +
            '</div>' +
            '<div>' +
              '<h4>Help</h4>' +
              '<ul>' +
                '<li><a href="faq.html#payment">Payment</a></li>' +
                '<li><a href="faq.html#delivery">Delivery</a></li>' +
                '<li><a href="faq.html#returns">Returns</a></li>' +
                '<li><a href="shade-guide.html">Shade Guide</a></li>' +
                '<li><a href="faq.html">FAQ</a></li>' +
                '<li><a href="contact.html">Contact</a></li>' +
              '</ul>' +
            '</div>' +
            '<div>' +
              '<h4>atelierR</h4>' +
              '<ul>' +
                '<li><a href="about.html">Our Story</a></li>' +
                '<li><a href="' + esc(CFG.contact.instagram) + '" target="_blank" rel="noopener">Instagram ' + esc(CFG.contact.instagramHandle) + '</a></li>' +
                '<li><a href="mailto:' + esc(CFG.contact.email) + '">' + esc(CFG.contact.email) + '</a></li>' +
              '</ul>' +
              '<p class="tiny mt-16">Payment by PayNow only.<br>Orders are confirmed after payment is verified.</p>' +
            '</div>' +
          '</div>' +
          '<div class="footer-base">' +
            '<span>atelierR — Singapore</span>' +
            '<span>Beauty brings a little more light to your life.</span>' +
            '<span>© ' + new Date().getFullYear() + ' atelierR. All prices in SGD.</span>' +
          '</div>' +
        '</div>' +
      '</footer>';
    },

    /* ---------- product card ---------- */
    card: function (p, opts) {
      opts = opts || {};
      var stock = S.Catalog.stockLabel(p);
      var sold = p.stock <= 0;
      var url = 'product.html?id=' + encodeURIComponent(p.id);
      return '' +
      '<article class="card">' +
        '<a class="card-media" href="' + url + '" aria-label="' + esc(p.brand + ' ' + p.name) + '">' +
          global.Imagery.render(p.art, { label: p.brand + ' ' + p.name }) +
          (sold ? '<span class="flag">Sold out</span>' : (p.bestSeller && opts.flagBest ? '<span class="flag">Best seller</span>' : '')) +
        '</a>' +
        '<p class="card-brand">' + esc(p.brand) + '</p>' +
        '<h3 class="card-name"><a href="' + url + '">' + esc(p.name) + '</a></h3>' +
        '<p class="card-desc">' + esc(p.shortDescription) + '</p>' +
        '<p class="card-price">' + money(p.priceSGD) + '</p>' +
        '<p class="stock ' + stock.cls + ' mb-8">' + esc(stock.text) + '</p>' +
        '<div class="card-foot">' +
          (sold
            ? '<span class="btn btn-quiet" aria-disabled="true">Sold out</span>'
            : '<button class="btn" data-add="' + esc(p.id) + '">Add to Cart</button>') +
          '<a class="btn btn-quiet" href="' + url + '">View Product</a>' +
        '</div>' +
      '</article>';
    },

    grid: function (products, opts) {
      return products.map(function (p) { return UI.card(p, opts); }).join('');
    },

    /* ---------- toast ---------- */
    toast: function (msg, linkHtml) {
      var el = document.querySelector('[data-toast]');
      if (!el) {
        el = document.createElement('div');
        el.className = 'toast';
        el.setAttribute('data-toast', '');
        el.setAttribute('role', 'status');
        document.body.appendChild(el);
      }
      el.innerHTML = '<span>' + esc(msg) + '</span>' + (linkHtml || '');
      requestAnimationFrame(function () { el.classList.add('show'); });
      clearTimeout(el._t);
      el._t = setTimeout(function () { el.classList.remove('show'); }, 3600);
    },

    /* ---------- accordions ---------- */
    accordion: function (root) {
      (root || document).querySelectorAll('.acc-q').forEach(function (btn) {
        if (btn._bound) return;
        btn._bound = true;
        btn.setAttribute('aria-expanded', 'false');
        btn.addEventListener('click', function () {
          var item = btn.closest('.acc-item');
          var open = item.classList.toggle('open');
          btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
      });
    },

    /* ---------- cart badge ---------- */
    refreshCart: function () {
      var n = S.Cart.count();
      document.querySelectorAll('[data-cart-count]').forEach(function (el) {
        el.textContent = n;
        el.hidden = n === 0;
      });
    },

    /* ---------- mount ---------- */
    mount: function (opts) {
      opts = opts || {};
      var head = document.querySelector('[data-header]');
      var foot = document.querySelector('[data-footer]');
      if (head) head.outerHTML = UI.header(opts.current);
      if (foot) foot.outerHTML = UI.footer();

      var drawer = document.querySelector('[data-drawer]');
      var search = document.querySelector('[data-search]');

      function openDrawer(on) {
        if (!drawer) return;
        drawer.hidden = false;
        drawer.classList.toggle('open', on);
        document.body.classList.toggle('no-scroll', on);
      }
      function openSearch(on) {
        if (!search) return;
        search.classList.toggle('open', on);
        document.body.classList.toggle('no-scroll', on);
        if (on) setTimeout(function () { search.querySelector('[data-search-input]').focus(); }, 40);
      }

      document.addEventListener('click', function (e) {
        var t = e.target.closest('[data-drawer-open],[data-drawer-close],[data-search-open],[data-search-close],[data-add]');
        if (!t) return;
        if (t.hasAttribute('data-drawer-open')) openDrawer(true);
        if (t.hasAttribute('data-drawer-close')) openDrawer(false);
        if (t.hasAttribute('data-search-open')) openSearch(true);
        if (t.hasAttribute('data-search-close')) openSearch(false);
        if (t.hasAttribute('data-add')) {
          var id = t.getAttribute('data-add');
          var p = S.Catalog.byId(id);
          if (S.Cart.add(id, 1)) {
            UI.toast('Added — ' + p.name, '<a href="cart.html">View cart</a>');
          }
        }
      });

      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { openDrawer(false); openSearch(false); }
      });

      /* live search */
      var input = search && search.querySelector('[data-search-input]');
      var results = search && search.querySelector('[data-search-results]');
      if (input) {
        input.addEventListener('input', function () {
          var q = input.value;
          var found = S.Catalog.search(q);
          if (q.trim().length < 2) { results.innerHTML = '<p class="small">Type at least two letters.</p>'; return; }
          if (!found.length) {
            results.innerHTML = '<p class="small">No products match “' + esc(q) + '”. Try a brand name, or <a class="link-under" href="shop.html">browse everything</a>.</p>';
            return;
          }
          results.innerHTML = found.map(function (p) {
            return '<a class="search-result" href="product.html?id=' + encodeURIComponent(p.id) + '">' +
              '<span class="thumb">' + global.Imagery.render(p.art) + '</span>' +
              '<span><span class="card-brand">' + esc(p.brand) + '</span>' +
              '<span class="card-name" style="display:block;margin:2px 0">' + esc(p.name) + '</span>' +
              '<span class="small">' + money(p.priceSGD) + '</span></span></a>';
          }).join('');
        });
      }

      document.addEventListener('cart:change', UI.refreshCart);
      UI.refreshCart();
      UI.accordion();
    }
  };

  global.UI = UI;
})(window);
