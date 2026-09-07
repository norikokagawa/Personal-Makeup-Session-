/* atelierR — generated product imagery
   No photography and no model faces: every product visual is a soft, editorial
   SVG built from the product's `art` descriptor { shape, tone }.
   Swap `Imagery.render()` for real <img> tags once photography exists. */
(function (global) {
  'use strict';

  var TONES = {
    sand:   ['#EFE8DE', '#E2D8C9', '#C9BAA6'],
    stone:  ['#EEEBE5', '#E0DBD2', '#BFB7AA'],
    rose:   ['#F2E7E2', '#E6D3CB', '#C9A79A'],
    clay:   ['#EDE3DA', '#DCCBBC', '#B79A85'],
    ink:    ['#E9E7E3', '#CFCBC4', '#3A3733'],
    sage:   ['#E9EDE7', '#D8E0D6', '#A9B7A4'],
    gold:   ['#F2ECE0', '#E5D9C1', '#C0A575']
  };

  function tone(name) { return TONES[name] || TONES.sand; }

  /* Each shape returns the foreground markup drawn inside a 400x500 canvas. */
  var SHAPES = {
    // eyeshadow / blush compact
    compact: function (c) {
      return '<rect x="108" y="196" width="184" height="118" rx="3" fill="' + c[2] + '"/>' +
             '<rect x="108" y="196" width="184" height="14" rx="3" fill="#fff" opacity=".18"/>' +
             '<rect x="122" y="222" width="74" height="46" rx="2" fill="#fff" opacity=".55"/>' +
             '<rect x="204" y="222" width="74" height="46" rx="2" fill="#fff" opacity=".32"/>' +
             '<rect x="122" y="276" width="74" height="26" rx="2" fill="#fff" opacity=".22"/>' +
             '<rect x="204" y="276" width="74" height="26" rx="2" fill="#fff" opacity=".42"/>';
    },
    // foundation / serum bottle
    bottle: function (c) {
      return '<rect x="166" y="118" width="68" height="34" rx="2" fill="' + c[2] + '"/>' +
             '<rect x="156" y="150" width="88" height="196" rx="7" fill="' + c[1] + '"/>' +
             '<rect x="156" y="150" width="26" height="196" rx="7" fill="#fff" opacity=".45"/>' +
             '<rect x="176" y="238" width="48" height="1.5" fill="' + c[2] + '" opacity=".5"/>';
    },
    // lipstick
    lipstick: function (c) {
      return '<rect x="180" y="150" width="40" height="92" rx="2" fill="' + c[2] + '"/>' +
             '<path d="M180 152 v-26 a20 20 0 0 1 40 0 v26 z" fill="' + c[1] + '"/>' +
             '<rect x="174" y="242" width="52" height="112" rx="3" fill="' + c[2] + '"/>' +
             '<rect x="174" y="242" width="16" height="112" rx="3" fill="#fff" opacity=".22"/>';
    },
    // loose / pressed powder jar
    jar: function (c) {
      return '<ellipse cx="200" cy="212" rx="94" ry="24" fill="' + c[1] + '"/>' +
             '<path d="M106 212 v78 a94 24 0 0 0 188 0 v-78 z" fill="' + c[2] + '"/>' +
             '<ellipse cx="200" cy="212" rx="94" ry="24" fill="#fff" opacity=".28"/>' +
             '<ellipse cx="200" cy="290" rx="66" ry="15" fill="#fff" opacity=".12"/>';
    },
    // cleanser / cream tube
    tube: function (c) {
      return '<path d="M162 158 h76 v170 a10 10 0 0 1 -10 10 h-56 a10 10 0 0 1 -10 -10 z" fill="' + c[1] + '"/>' +
             '<rect x="174" y="126" width="52" height="34" rx="3" fill="' + c[2] + '"/>' +
             '<rect x="162" y="158" width="20" height="180" fill="#fff" opacity=".4"/>';
    },
    // eyeliner / brow pencil
    pencil: function (c) {
      return '<rect x="188" y="130" width="24" height="180" rx="12" fill="' + c[2] + '"/>' +
             '<path d="M188 310 h24 l-12 34 z" fill="' + c[1] + '"/>' +
             '<rect x="188" y="190" width="24" height="10" fill="#fff" opacity=".35"/>';
    },
    // makeup brush
    brush: function (c) {
      return '<path d="M186 108 q14 -22 28 0 l6 78 q-20 10 -40 0 z" fill="' + c[2] + '"/>' +
             '<rect x="180" y="186" width="40" height="18" rx="3" fill="' + c[1] + '"/>' +
             '<rect x="190" y="204" width="20" height="180" rx="10" fill="#3A3733"/>' +
             '<rect x="190" y="204" width="7" height="180" rx="4" fill="#fff" opacity=".16"/>';
    },
    // wide face brush
    brushWide: function (c) {
      return '<path d="M156 104 q44 -30 88 0 l10 92 q-54 18 -108 0 z" fill="' + c[2] + '"/>' +
             '<rect x="164" y="196" width="72" height="20" rx="3" fill="' + c[1] + '"/>' +
             '<rect x="186" y="216" width="28" height="168" rx="14" fill="#3A3733"/>' +
             '<rect x="186" y="216" width="9" height="168" rx="5" fill="#fff" opacity=".16"/>';
    },
    // eyelash curler
    curler: function (c) {
      return '<path d="M150 150 h100" stroke="' + c[2] + '" stroke-width="12" stroke-linecap="round" fill="none"/>' +
             '<path d="M162 156 v70 a38 38 0 0 0 76 0 v-70" stroke="' + c[2] + '" stroke-width="9" fill="none"/>' +
             '<circle cx="176" cy="300" r="26" stroke="' + c[2] + '" stroke-width="9" fill="none"/>' +
             '<circle cx="234" cy="300" r="26" stroke="' + c[2] + '" stroke-width="9" fill="none"/>';
    },
    // curated set — a small grouped still life
    set: function (c) {
      return '<rect x="86" y="206" width="66" height="140" rx="5" fill="' + c[1] + '"/>' +
             '<rect x="86" y="206" width="20" height="140" rx="5" fill="#fff" opacity=".42"/>' +
             '<rect x="100" y="180" width="38" height="28" rx="2" fill="' + c[2] + '"/>' +
             '<rect x="164" y="248" width="88" height="98" rx="3" fill="' + c[2] + '"/>' +
             '<rect x="176" y="266" width="30" height="30" rx="2" fill="#fff" opacity=".5"/>' +
             '<rect x="212" y="266" width="30" height="30" rx="2" fill="#fff" opacity=".28"/>' +
             '<rect x="266" y="232" width="30" height="114" rx="3" fill="' + c[2] + '"/>' +
             '<path d="M266 232 v-24 a15 15 0 0 1 30 0 v24 z" fill="' + c[1] + '"/>' +
             '<rect x="306" y="196" width="16" height="150" rx="8" fill="#3A3733"/>' +
             '<path d="M306 196 q8 -30 16 0 z" fill="' + c[2] + '"/>';
    },
    // skincare trio
    setSkincare: function (c) {
      return '<rect x="104" y="176" width="62" height="170" rx="6" fill="' + c[1] + '"/>' +
             '<rect x="104" y="176" width="18" height="170" rx="6" fill="#fff" opacity=".45"/>' +
             '<rect x="118" y="150" width="34" height="28" rx="2" fill="' + c[2] + '"/>' +
             '<rect x="182" y="212" width="70" height="134" rx="6" fill="' + c[2] + '"/>' +
             '<rect x="182" y="212" width="20" height="134" rx="6" fill="#fff" opacity=".38"/>' +
             '<rect x="200" y="186" width="34" height="26" rx="2" fill="' + c[1] + '"/>' +
             '<path d="M268 244 h64 v92 a10 10 0 0 1 -10 10 h-44 a10 10 0 0 1 -10 -10 z" fill="' + c[1] + '"/>' +
             '<rect x="284" y="216" width="32" height="28" rx="3" fill="' + c[2] + '"/>';
    },
    // texture swatches used for category tiles
    swatch: function (c) {
      return '<path d="M92 268 q42 -66 108 -40 t108 -6 q-14 76 -108 84 t-108 -38 z" fill="' + c[2] + '" opacity=".85"/>' +
             '<path d="M120 258 q40 -44 88 -22" stroke="#fff" stroke-width="5" fill="none" opacity=".4" stroke-linecap="round"/>';
    },
    powder: function (c) {
      return '<circle cx="200" cy="252" r="86" fill="' + c[2] + '" opacity=".7"/>' +
             '<circle cx="164" cy="220" r="30" fill="' + c[1] + '" opacity=".8"/>' +
             '<circle cx="248" cy="286" r="22" fill="#fff" opacity=".35"/>' +
             '<circle cx="252" cy="212" r="10" fill="#fff" opacity=".5"/>';
    },
    drops: function (c) {
      return '<circle cx="176" cy="238" r="54" fill="none" stroke="' + c[2] + '" stroke-width="3" opacity=".8"/>' +
             '<circle cx="248" cy="286" r="34" fill="none" stroke="' + c[2] + '" stroke-width="3" opacity=".7"/>' +
             '<circle cx="252" cy="196" r="20" fill="none" stroke="' + c[2] + '" stroke-width="3" opacity=".6"/>' +
             '<circle cx="176" cy="238" r="54" fill="#fff" opacity=".25"/>' +
             '<circle cx="248" cy="286" r="34" fill="#fff" opacity=".2"/>';
    },
    stone: function (c) {
      return '<ellipse cx="200" cy="266" rx="104" ry="78" fill="' + c[2] + '" opacity=".55"/>' +
             '<ellipse cx="176" cy="238" rx="62" ry="48" fill="#fff" opacity=".35"/>';
    }
  };

  var Imagery = {
    /* Returns an inline SVG string for a product/decor art descriptor. */
    render: function (art, opts) {
      art = art || {};
      opts = opts || {};
      var shape = SHAPES[art.shape] ? art.shape : 'compact';
      var c = tone(art.tone);
      var id = 'g' + Math.random().toString(36).slice(2, 8);
      var ratio = opts.ratio || '400 500';
      var label = opts.label ? '<title>' + esc(opts.label) + '</title>' : '';
      return '<svg viewBox="0 0 ' + ratio + '" role="img" aria-hidden="' + (opts.label ? 'false' : 'true') + '" ' +
             'xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">' + label +
             '<defs><linearGradient id="' + id + '" x1="0" y1="0" x2="0.6" y2="1">' +
             '<stop offset="0" stop-color="' + c[0] + '"/><stop offset="1" stop-color="' + c[1] + '"/>' +
             '</linearGradient></defs>' +
             '<rect width="100%" height="100%" fill="url(#' + id + ')"/>' +
             '<ellipse cx="200" cy="392" rx="118" ry="18" fill="#000" opacity=".055"/>' +
             SHAPES[shape](c) + '</svg>';
    },
    shapes: Object.keys(SHAPES)
  };

  function esc(s) { return String(s).replace(/[&<>"]/g, function (m) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[m];
  }); }

  global.Imagery = Imagery;
})(window);
