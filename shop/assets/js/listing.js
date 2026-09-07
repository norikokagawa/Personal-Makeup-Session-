/* atelierR — product listing engine
   Powers shop.html, category.html and brand.html from one place.
   Filters live in the URL, so a filtered view can be linked and shared. */
(function (global) {
  'use strict';
  var S = global.Store, esc = S.esc;

  var SORTS = [
    { id: 'curated', label: 'Curated' },
    { id: 'popular', label: 'Best selling' },
    { id: 'price-asc', label: 'Price: low to high' },
    { id: 'price-desc', label: 'Price: high to low' },
    { id: 'name', label: 'A – Z' }
  ];

  function sortProducts(list, sort) {
    var out = list.slice();
    if (sort === 'price-asc') out.sort(function (a, b) { return a.priceSGD - b.priceSGD; });
    else if (sort === 'price-desc') out.sort(function (a, b) { return b.priceSGD - a.priceSGD; });
    else if (sort === 'name') out.sort(function (a, b) { return (a.brand + a.name).localeCompare(b.brand + b.name); });
    else if (sort === 'popular') out.sort(function (a, b) { return (b.bestSeller ? 1 : 0) - (a.bestSeller ? 1 : 0); });
    /* 'curated' keeps catalogue order, which is the order atelierR arranged. */
    return out;
  }

  var Listing = {
    /* opts: { root, products, lockCategory, lockBrand } */
    init: function (opts) {
      var root = document.querySelector(opts.root || '[data-listing]');
      if (!root) return;

      var state = {
        category: opts.lockCategory || S.param('c') || 'all',
        brand: opts.lockBrand || S.param('b') || 'all',
        stock: S.param('stock') || 'all',
        sort: S.param('sort') || 'curated'
      };

      var base = opts.products || S.Catalog.all();

      function apply() {
        var list = base.filter(function (p) {
          if (state.category !== 'all' && p.category !== state.category) return false;
          if (state.brand !== 'all' && S.slug(p.brand) !== state.brand) return false;
          if (state.stock === 'in' && p.stock <= 0) return false;
          return true;
        });
        return sortProducts(list, state.sort);
      }

      function chips(name, options, active) {
        return options.map(function (o) {
          return '<button class="chip" data-filter="' + name + '" data-value="' + esc(o.id) + '" ' +
                 'aria-pressed="' + (active === o.id ? 'true' : 'false') + '">' + esc(o.label) + '</button>';
        }).join('');
      }

      function render() {
        var list = apply();
        var parts = [];

        /* filter bar */
        parts.push('<div class="filters">');
        if (!opts.lockCategory) {
          parts.push('<div class="filter-bar-scroll">' + chips('category',
            [{ id: 'all', label: 'All' }].concat(S.Catalog.categories.map(function (c) {
              return { id: c.id, label: c.name };
            })), state.category) + '</div>');
        }
        parts.push('</div>');

        parts.push('<div class="filters">');
        if (!opts.lockBrand) {
          parts.push('<div class="filter-bar-scroll">' + chips('brand',
            [{ id: 'all', label: 'All brands' }].concat(S.Catalog.brands.map(function (b) {
              return { id: b.id, label: b.name };
            })), state.brand) + '</div>');
        }
        parts.push('</div>');

        parts.push('<div class="filters" style="border:0">' +
          '<span class="result-count">' + list.length + (list.length === 1 ? ' product' : ' products') + '</span>' +
          '<span style="flex:1"></span>' +
          '<button class="chip" data-filter="stock" data-value="' + (state.stock === 'in' ? 'all' : 'in') + '" ' +
            'aria-pressed="' + (state.stock === 'in' ? 'true' : 'false') + '">In stock only</button>' +
          '<label class="sr-only" for="sortSel">Sort by</label>' +
          '<select id="sortSel" data-sort style="width:auto;padding:8px 12px;font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase">' +
            SORTS.map(function (s) {
              return '<option value="' + s.id + '"' + (state.sort === s.id ? ' selected' : '') + '>' + esc(s.label) + '</option>';
            }).join('') +
          '</select>' +
        '</div>');

        /* results */
        if (!list.length) {
          parts.push('<div class="empty"><p class="h2 serif">Nothing here yet</p>' +
            '<p class="lede center" style="margin:0 auto 24px">No products match this combination. ' +
            'Try removing a filter, or browse the full collection.</p>' +
            '<a class="btn btn-outline" href="shop.html">Shop All</a></div>');
        } else {
          parts.push('<div class="product-grid mt-32">' + global.UI.grid(list) + '</div>');
        }

        root.innerHTML = parts.join('');
      }

      root.addEventListener('click', function (e) {
        var b = e.target.closest('[data-filter]');
        if (!b) return;
        state[b.getAttribute('data-filter')] = b.getAttribute('data-value');
        render();
      });
      root.addEventListener('change', function (e) {
        if (!e.target.matches('[data-sort]')) return;
        state.sort = e.target.value;
        render();
      });

      render();
    }
  };

  global.Listing = Listing;
})(window);
