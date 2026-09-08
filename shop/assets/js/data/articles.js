/* atelierR — Journal
   ---------------------------------------------------------------------------
   ADDING A STORY
   Copy the last entry, change the fields, put it at the top of the array.
   Nothing else needs editing: the journal page, the article page, the homepage
   section, the newsletter draft and the Instagram captions all read from here.

   FIELDS
     slug        String   the URL — article.html?a=<slug>. Lowercase, hyphens.
     title       String
     date        String   'YYYY-MM-DD'. Newest first is not required — the site
                          sorts by this, so a story can be dropped in anywhere.
     excerpt     String   one or two sentences, used on cards and in the newsletter
     category    String   one of JOURNAL_CATEGORIES below
     art         Object   { shape, tone } — generated hero art, replaced by a
                          photo at assets/img/journal/<slug>.jpg if one exists
     body        Array    the article itself, see BODY BLOCKS
     todaysPick  String   a product id, shown as "Today's Pick"
     products    [String] product ids for "Products Mentioned" at the foot
     newsletter  Boolean  true = include when preparing a newsletter draft
     instagram   Object   optional overrides; captions are generated when absent
     published   Boolean  false hides the story everywhere

   BODY BLOCKS — an array; each entry is one of:
     { p: 'text' }                        a paragraph
     { h: 'text' }                        a subheading
     { quote: 'text' }                    a pulled quote
     { list: ['a', 'b'] }                 a simple list
     { steps: ['first', 'second'] }       numbered steps
     { note: 'text' }                     a quiet aside
     { image: {shape,tone}, caption: '' } an inline image
     { shop: ['id'], title: 'Shop This Look' }   product cards inside the article
     { pick: 'id' }                       a single highlighted product
   --------------------------------------------------------------------------- */

window.JOURNAL_CATEGORIES = [
  { id: 'makeup-notes',   name: 'Makeup Notes',   note: 'What happens in the chair, written down.' },
  { id: 'product-edit',   name: 'Product Edit',   note: 'A close look at one thing we carry.' },
  { id: 'skincare',       name: 'Skincare',       note: 'The layer everything else sits on.' },
  { id: 'how-to',         name: 'How To',         note: 'Professional method, at home.' },
  { id: 'seasonal-edit',  name: 'Seasonal Edit',  note: 'What the weather asks of your face.' },
  { id: 'atelierr-picks', name: 'atelierR Picks', note: 'The short list.' },
  { id: 'new-arrivals',   name: 'New Arrivals',   note: 'Newly on the shelf.' }
];

window.ARTICLES = [

  {
    slug: 'foundation-that-disappears',
    title: 'The foundation that disappears',
    date: '2026-09-05',
    category: 'product-edit',
    excerpt: 'Most people wear a base one shade too light and one layer too thick. A note on why the right foundation is the one you stop noticing.',
    art: { shape: 'bottle', tone: 'sand' },
    todaysPick: 'rmk-liquid-foundation',
    products: ['rmk-liquid-foundation', 'rmk-face-powder', 'brownetoile-face-powder-brush'],
    newsletter: true,
    published: true,
    body: [
      { p: 'A client sat down last week and said the sentence I hear most often: “I don’t really like how foundation looks on me.” She was wearing a good one. It was simply a shade too light, applied in one thick pass, and set with more powder than her skin needed.' },
      { p: 'Base makeup fails in predictable ways, and almost none of them are the product’s fault.' },

      { h: 'The shade is chosen in the wrong light' },
      { p: 'Shop lighting is warm and flattering, and it hides about half a shade of mismatch. Daylight does not. Test along the jawline, near a window, with nothing else on your face — and if you sit between two shades, take the deeper one. Skin darkens slightly through the year here, and a base that is marginally too deep reads as healthy. One that is too light reads as makeup.' },

      { quote: 'The right shade disappears. If you can see where it starts, it is the wrong one.' },

      { h: 'It goes on as one thick layer' },
      { p: 'Coverage comes from layering thinly, not from applying heavily. Two dots on each cheek, one on the forehead, one on the chin — blended outward from the centre, where evenness matters most. Then stop. Add a second sheer pass only where you still want it. The edges of the face barely need any.' },

      { h: 'It is set as though it were wet paint' },
      { p: 'Powder holds a base in place; it is not supposed to bury it. A large brush, a small amount, and only across the centre of the face where shine appears first. Leave the outer cheeks alone so the skin keeps some of its own light.' },

      { shop: ['rmk-liquid-foundation', 'rmk-face-powder', 'brownetoile-face-powder-brush'],
        title: 'Shop This Look' },

      { h: 'What changed for her' },
      { p: 'We went one shade deeper, applied half as much, and set only the T-zone. Same brand, same formula, same person. She asked what the new foundation was. It was hers.' },

      { note: 'Not sure which shade is yours? The shade guide on each product page describes who every shade suits, and the FAQ covers matching in daylight.' }
    ]
  },

  {
    slug: 'humidity-and-your-base',
    title: 'Making makeup last in Singapore humidity',
    date: '2026-08-28',
    category: 'how-to',
    excerpt: 'Makeup does not slide off because it is bad. It slides off because the skin underneath was never prepared for this climate.',
    art: { shape: 'drops', tone: 'sage' },
    todaysPick: 'noevir-herbal-skin-lotion',
    products: ['noevir-herbal-skin-lotion', 'noevir-herbal-milk-lotion', 'rmk-face-powder', 'celvoke-cushion'],
    newsletter: true,
    published: true,
    body: [
      { p: 'Every makeup artist who moves to Singapore learns the same lesson in the first month: technique that works in a dry climate does not survive here. Bases separate by lunchtime. Powder goes patchy. Cream blush migrates.' },
      { p: 'The instinct is to use more product, or a stronger one. It is almost always the wrong move.' },

      { h: 'Dehydrated skin is the actual problem' },
      { p: 'Air-conditioned offices are dry; the street outside is not. Skin moving between the two loses water quickly and compensates by producing oil, and it is that oil — not the humidity itself — that breaks a base down. Skin that is properly hydrated underneath produces less, and the makeup on top of it stays where it was put.' },

      { steps: [
        'Skin lotion first, pressed in with the palms rather than wiped across.',
        'A second layer on the dry areas only — usually the cheeks and around the mouth.',
        'Milk lotion while the skin is still slightly damp, to hold that water in.',
        'Wait two full minutes before any base makeup. This step is the one everyone skips.'
      ] },

      { pick: 'noevir-herbal-skin-lotion' },

      { h: 'Then use less, not more' },
      { p: 'A thin base survives humidity; a thick one has further to slide. Powder only where shine appears — the centre panel of the face — and carry something you can press on at midday rather than reapplying a full layer.' },

      { quote: 'Skin that is hydrated underneath produces less oil. Everything else follows from that.' },

      { h: 'Touching up without making it worse' },
      { p: 'Blot first, always. Adding powder to oil makes a paste; removing the oil first and then pressing a little product over the top does not. A cushion is easier than a compact for this because you can do it in thirty seconds without a mirror and a full kit.' },

      { shop: ['noevir-herbal-skin-lotion', 'noevir-herbal-milk-lotion', 'celvoke-cushion'],
        title: 'atelierR Recommends' }
    ]
  },

  {
    slug: 'one-palette-three-steps',
    title: 'One palette, three steps',
    date: '2026-08-20',
    category: 'makeup-notes',
    excerpt: 'The eye makeup I do most often takes three movements and one compact. It works on almost everyone, which is exactly why I keep returning to it.',
    art: { shape: 'compact', tone: 'clay' },
    todaysPick: 'suqqu-signature-color-eyes',
    products: ['suqqu-signature-color-eyes', 'brownetoile-eyeshadow-brush-a', 'brownetoile-blending-brush', 'rmk-eye-defining-pencil'],
    newsletter: true,
    published: true,
    body: [
      { p: 'People assume eye makeup is complicated because tutorials make it look that way. In a session I usually do three things, and the result is the one clients photograph afterwards.' },

      { steps: [
        'Sweep the lightest shade across the whole lid with a flat brush. This is not a colour decision; it is a surface, so that everything after it blends instead of gripping.',
        'Place the second shade along the socket line and blend upward with a soft brush, working only at the edge of the colour. Never blend in the middle — that removes what you just put down.',
        'Press the deepest shade into the lash line with a small brush. Not a drawn line above the lashes; colour between them, so the lashes look denser rather than the eye looking lined.'
      ] },

      { p: 'That is the whole thing. The fourth shade in the compact is for the centre of the lid, if you want more light, and most days you will not.' },

      { h: 'Why a coordinated palette rather than singles' },
      { p: 'Buying eyeshadows individually means making four colour decisions and hoping they agree with each other. A palette built as a set has already resolved that. It is why a complete eye takes three steps here instead of six.' },

      { pick: 'suqqu-signature-color-eyes' },

      { h: 'The brushes matter more than the palette' },
      { p: 'Most people already own a workable palette and simply cannot place the colour. A flat brush puts shadow where you want it; a loose tapered brush softens the boundary. Those two do almost everything.' },

      { shop: ['brownetoile-eyeshadow-brush-a', 'brownetoile-blending-brush'],
        title: 'The Two Brushes' },

      { note: 'If you are choosing a first palette, take a neutral beige brown. It suits nearly every skin tone and works with everything else in the shop.' }
    ]
  },

  {
    slug: 'september-edit',
    title: 'September edit — quieter colour',
    date: '2026-09-01',
    category: 'seasonal-edit',
    excerpt: 'A short list for the turn of the season: softer lips, warmer cheeks, and one serum for skin that has had enough of the sun.',
    art: { shape: 'lipstick', tone: 'rose' },
    todaysPick: 'suqqu-moisture-glaze-lipstick',
    products: ['suqqu-moisture-glaze-lipstick', 'suqqu-blurring-color-blush', 'celvoke-concentrate-serum', 'three-velvet-lipstick'],
    newsletter: true,
    published: true,
    body: [
      { p: 'The light changes at this time of year even here, where the seasons are supposed to be one long season. Bright coral that looked right in June starts to look loud. Skin that has spent months under sun and air conditioning looks flatter than it did.' },
      { p: 'Three small changes, no new routine required.' },

      { h: 'A softer lip' },
      { p: 'Move one step away from bright and one step towards muted. A glaze finish is the easiest way to do this without it feeling like a different face — the colour stays translucent, so it reads as your own lip in better condition.' },

      { h: 'Warmer cheeks, placed higher' },
      { p: 'Cooler pinks can look severe against tired skin. A soft peach along the cheekbone, swept towards the temple rather than dropped in a circle on the apple, lifts the whole face.' },

      { shop: ['suqqu-moisture-glaze-lipstick', 'suqqu-blurring-color-blush'], title: 'Shop This Look' },

      { h: 'One serum, at night' },
      { p: 'If your skin looks like it has lost its light rather than its moisture, that is a tone problem, not a hydration one. A concentrated serum between hydration and emulsion is the step that changes how foundation reflects — which is more useful than any amount of extra coverage.' },

      { pick: 'celvoke-concentrate-serum' },

      { quote: 'Skin that has lost its light does not need more coverage. It needs the light back.' }
    ]
  },

  {
    slug: 'what-a-session-teaches',
    title: 'What a makeup session actually teaches you',
    date: '2026-08-12',
    category: 'atelierr-picks',
    excerpt: 'Clients often expect to leave with a face. They usually leave with three or four small corrections that change everything afterwards.',
    art: { shape: 'set', tone: 'sand' },
    todaysPick: 'brownetoile-eyelash-curler',
    products: ['brownetoile-eyelash-curler', 'brownetoile-blush-brush', 'addiction-the-concealer', 'base-makeup-set'],
    newsletter: true,
    published: true,
    body: [
      { p: 'A personal session is not really a lesson in products. It is an hour of watching what your hands do without thinking, and correcting the two or three habits that are working against you.' },
      { p: 'These come up almost every time.' },

      { h: 'Concealer is being applied before foundation' },
      { p: 'Foundation first, always — it evens most of what you were about to conceal, and you end up needing a third of the product. Then three small dots in the inner corner triangle only, tapped rather than dragged.' },

      { h: 'Blush is starting in the wrong place' },
      { p: 'Loading the brush and putting it straight on the apple of the cheek drops the most pigment where you want the least. Tap the brush off first, start at the cheekbone, sweep towards the temple.' },

      { h: 'Lashes are never curled' },
      { p: 'The cheapest tool in the kit, and the one that changes a face most. Curl at the base and hold; move halfway up and press more lightly. Often it turns out mascara was not needed at all.' },

      { pick: 'brownetoile-eyelash-curler' },

      { h: 'Everything used on you is written down' },
      { p: 'At the end of a session your artist notes the shades used on your face, so you can find them again without guessing. If you have lost that note, tell us your session date and we will look it up.' },

      { shop: ['brownetoile-blush-brush', 'addiction-the-concealer', 'base-makeup-set'],
        title: 'atelierR Recommends' },

      { note: 'Buying products used in your session? Add the session date in the order notes at checkout and we will double-check the shades match what was on your face.' }
    ]
  }
];
