/* atelierR — product catalogue
   ---------------------------------------------------------------------------
   This file is the single source of product truth today. Every record uses the
   exact field names an `products` table / API response would use, so replacing
   this array with `await fetch('/api/products')` requires no other change.

   SCHEMA
     id                String   slug, stable, used in URLs
     brand             String
     name              String
     category          String   base-makeup | point-makeup | skincare | tools | sets
     subcategory       String
     priceSGD          Number
     stock             Number   0 = sold out
     art               Object   { shape, tone } — generated imagery (see imagery.js)
     images            Array    extra art descriptors for the gallery
     shortDescription  String   one line, used on cards
     description       String   "What it is"
     whySelected       String   "Why atelierR selected this"
     bestFor           [String]
     finish            String   Natural | Satin | Matte | Sheer | Luminous | —
     howToUse          [String]
     shadeInfo         Object   { guide: String, shades: [{name, code, hex, note}] }
     related           [String] product ids
     setContents       [String] for sets only
     bestSeller        Boolean
     active            Boolean  inactive products are never rendered
   --------------------------------------------------------------------------- */
window.PRODUCTS = [

  /* ===================== BASE MAKEUP ===================== */
  {
    id: 'rmk-liquid-foundation',
    brand: 'RMK',
    name: 'Liquid Foundation',
    category: 'base-makeup',
    subcategory: 'Foundation',
    priceSGD: 120,
    stock: 8,
    art: { shape: 'bottle', tone: 'sand' },
    images: [{ shape: 'bottle', tone: 'sand' }, { shape: 'swatch', tone: 'sand' }, { shape: 'stone', tone: 'stone' }],
    shortDescription: 'A weightless liquid base with a soft, dewy finish.',
    description: 'A fluid foundation that evens tone without covering the skin. It contains a high proportion of moisturising oils, so it settles into a thin, flexible layer that moves with the face rather than sitting on top of it.',
    whySelected: 'This is the base atelierR reaches for most often during sessions, because it photographs naturally and never looks powdery on Singapore skin. It suits clients who say previous foundations felt heavy or mask-like.',
    bestFor: ['Dry skin', 'Normal skin', 'Natural finish', 'Soft everyday makeup', 'Mature skin'],
    finish: 'Luminous',
    howToUse: [
      'Apply after skincare has fully settled — wait about two minutes.',
      'Place two small dots on each cheek, one on the forehead and one on the chin.',
      'Blend outward with fingertips or a damp sponge, working from the centre of the face.',
      'Build a second sheer layer only where you want more evenness.'
    ],
    shadeInfo: {
      guide: 'Shades run from 101 (light, neutral) to 204 (medium-deep, warm). Choose the shade that disappears along the jawline in daylight. If you sit between two shades, take the lighter one for winter and the deeper one for year-round wear in Singapore.',
      shades: [
        { name: 'Light Neutral', code: '101', hex: '#F0D9C4', note: 'Fair skin, neutral undertone' },
        { name: 'Light Beige', code: '102', hex: '#E8CBB0', note: 'Fair to light, warm undertone' },
        { name: 'Natural Beige', code: '103', hex: '#DDBA9C', note: 'Light to medium, the most chosen shade' },
        { name: 'Warm Beige', code: '201', hex: '#CFA684', note: 'Medium, golden undertone' },
        { name: 'Deep Beige', code: '204', hex: '#B98C68', note: 'Medium-deep, warm undertone' }
      ]
    },
    related: ['rmk-face-powder', 'three-glow-primer', 'brownetoile-concealer-brush-m'],
    bestSeller: true,
    active: true
  },
  {
    id: 'rmk-face-powder',
    brand: 'RMK',
    name: 'Translucent Face Powder',
    category: 'base-makeup',
    subcategory: 'Powder',
    priceSGD: 60,
    stock: 12,
    art: { shape: 'jar', tone: 'stone' },
    images: [{ shape: 'jar', tone: 'stone' }, { shape: 'powder', tone: 'stone' }, { shape: 'stone', tone: 'sand' }],
    shortDescription: 'A fine loose powder that sets makeup without dulling it.',
    description: 'A finely milled translucent powder that controls shine while keeping the skin looking like skin. It sets a liquid base gently, so the finish stays soft rather than flat.',
    whySelected: 'Humidity is the real test in Singapore. This is the powder atelierR uses to hold a base in place through a whole day without the chalky edge that heavier setting powders leave.',
    bestFor: ['All skin types', 'Humid weather', 'Natural finish', 'Long wear'],
    finish: 'Natural',
    howToUse: [
      'Tap a small amount into the lid and press it into the brush — never pour it directly.',
      'Dust lightly across the centre of the face, where shine appears first.',
      'Leave the outer cheeks lighter so the skin keeps some natural light.'
    ],
    shadeInfo: { guide: 'Translucent — one shade suits every skin tone.', shades: [] },
    related: ['rmk-liquid-foundation', 'brownetoile-face-powder-brush', 'suqqu-blurring-color-blush'],
    bestSeller: true,
    active: true
  },
  {
    id: 'three-glow-primer',
    brand: 'THREE',
    name: 'Angelic Glow Primer',
    category: 'base-makeup',
    subcategory: 'Primer',
    priceSGD: 78,
    stock: 6,
    art: { shape: 'bottle', tone: 'gold' },
    images: [{ shape: 'bottle', tone: 'gold' }, { shape: 'drops', tone: 'gold' }],
    shortDescription: 'A luminous primer that softens texture before base makeup.',
    description: 'A lightweight primer with a fine pearl finish. It smooths the look of pores and gives the skin a quiet inner glow that carries through the foundation applied over it.',
    whySelected: 'atelierR uses this when a client wants radiance without shimmer. One layer under foundation is usually enough to change how the whole base reads.',
    bestFor: ['Dull skin', 'Dry skin', 'Luminous finish', 'Special occasions'],
    finish: 'Luminous',
    howToUse: [
      'Use a pea-sized amount after moisturiser.',
      'Press it into the high points of the face — cheekbones, bridge of the nose, brow bone.',
      'Wait one minute before applying foundation.'
    ],
    shadeInfo: { guide: 'One universal shade with a soft pearl finish.', shades: [] },
    related: ['rmk-liquid-foundation', 'celvoke-cushion', 'celvoke-concentrate-serum'],
    bestSeller: false,
    active: true
  },
  {
    id: 'addiction-the-concealer',
    brand: 'ADDICTION',
    name: 'The Concealer',
    category: 'base-makeup',
    subcategory: 'Concealer',
    priceSGD: 45,
    stock: 9,
    art: { shape: 'tube', tone: 'sand' },
    images: [{ shape: 'tube', tone: 'sand' }, { shape: 'swatch', tone: 'sand' }],
    shortDescription: 'A flexible concealer that stays soft around the eyes.',
    description: 'A creamy, buildable concealer for under-eye shadow and small areas of unevenness. It stays flexible on the skin, so it does not crease into fine lines through the day.',
    whySelected: 'Most concealer problems are dryness, not coverage. This one keeps moving with the face, which is why atelierR recommends it to clients over forty and to anyone with fine lines under the eye.',
    bestFor: ['Under-eye shadow', 'Dry skin', 'Mature skin', 'Natural finish'],
    finish: 'Satin',
    howToUse: [
      'Apply after foundation, not before.',
      'Place three small dots in the inner corner triangle only.',
      'Tap — do not drag — with a warm fingertip or a small brush.',
      'Set with the lightest touch of powder if needed.'
    ],
    shadeInfo: {
      guide: 'Choose one step lighter than your foundation for under the eye, and an exact match for blemishes.',
      shades: [
        { name: 'Light', code: '001', hex: '#F2DAC5', note: 'Fair skin' },
        { name: 'Medium Light', code: '002', hex: '#E3C0A3', note: 'Light to medium' },
        { name: 'Medium', code: '003', hex: '#D0A483', note: 'Medium, warm' }
      ]
    },
    related: ['rmk-liquid-foundation', 'brownetoile-concealer-brush-m', 'rmk-face-powder'],
    bestSeller: false,
    active: true
  },
  {
    id: 'celvoke-cushion',
    brand: 'Celvoke',
    name: 'Reventive Cushion Foundation',
    category: 'base-makeup',
    subcategory: 'Cushion',
    priceSGD: 95,
    stock: 0,
    art: { shape: 'compact', tone: 'clay' },
    images: [{ shape: 'compact', tone: 'clay' }, { shape: 'swatch', tone: 'clay' }],
    shortDescription: 'A skincare-led cushion for light, portable coverage.',
    description: 'A cushion foundation formulated around botanical oils. Coverage is light to medium and the finish is fresh, making it easy to reapply through the day without building up.',
    whySelected: 'atelierR recommends this as a second base to carry, rather than a first base. It is the easiest way to refresh makeup at midday without a mirror and a full kit.',
    bestFor: ['Touch-ups', 'Lightweight makeup', 'Normal skin', 'Travel'],
    finish: 'Satin',
    howToUse: [
      'Press the puff into the cushion once — a small amount is enough.',
      'Pat over the areas that need refreshing, avoiding the whole face.',
      'Close the case firmly to keep the cushion from drying out.'
    ],
    shadeInfo: {
      guide: 'Two shades only. 01 suits fair to light skin, 02 suits light to medium.',
      shades: [
        { name: 'Light', code: '01', hex: '#EED4BC', note: 'Fair to light' },
        { name: 'Natural', code: '02', hex: '#DAB595', note: 'Light to medium' }
      ]
    },
    related: ['rmk-liquid-foundation', 'rmk-face-powder', 'celvoke-concentrate-serum'],
    bestSeller: false,
    active: true
  },

  /* ===================== POINT MAKEUP ===================== */
  {
    id: 'suqqu-signature-color-eyes',
    brand: 'SUQQU',
    name: 'Signature Color Eyes',
    category: 'point-makeup',
    subcategory: 'Eyeshadow',
    priceSGD: 86,
    stock: 5,
    art: { shape: 'compact', tone: 'clay' },
    images: [{ shape: 'compact', tone: 'clay' }, { shape: 'swatch', tone: 'clay' }, { shape: 'powder', tone: 'clay' }],
    shortDescription: 'A four-shade palette with a fine, skin-like texture.',
    description: 'Four coordinated eyeshadows in one compact — a wash, a definer, a deep shade and an accent. The powder is unusually finely milled, so it blends without hard edges and layers without becoming heavy.',
    whySelected: 'This is the single palette atelierR uses in almost every session. The shade relationships are already resolved, which means a complete eye takes three steps instead of six.',
    bestFor: ['Soft everyday makeup', 'Beginners', 'Natural finish', 'Mature skin', 'Monolid and hooded eyes'],
    finish: 'Satin',
    howToUse: [
      'Sweep the lightest shade across the whole lid with a flat brush.',
      'Place the second shade in the socket line and blend upward with a blending brush.',
      'Press the deepest shade close to the lashes with a small brush.',
      'Use the accent shade only on the centre of the lid, if you want more light.'
    ],
    shadeInfo: {
      guide: 'Warm browns suit most skin tones and are the safest first choice. Rose and plum tones flatter cool undertones. If you are unsure, choose the brown palette — it works with every other product in this shop.',
      shades: [
        { name: 'Kohbai', code: '01', hex: '#C89A8C', note: 'Soft rose brown — gentle, everyday' },
        { name: 'Nurebeni', code: '05', hex: '#A8695F', note: 'Warm red brown — adds depth' },
        { name: 'Shironeri', code: '08', hex: '#C6AC92', note: 'Neutral beige brown — most versatile' },
        { name: 'Tsuyakoubai', code: '12', hex: '#9A7B86', note: 'Plum brown — cool undertones' }
      ]
    },
    related: ['brownetoile-eyeshadow-brush-a', 'brownetoile-blending-brush', 'suqqu-moisture-glaze-lipstick'],
    bestSeller: true,
    active: true
  },
  {
    id: 'suqqu-blurring-color-blush',
    brand: 'SUQQU',
    name: 'Blurring Color Blush',
    category: 'point-makeup',
    subcategory: 'Blush',
    priceSGD: 72,
    stock: 7,
    art: { shape: 'compact', tone: 'rose' },
    images: [{ shape: 'compact', tone: 'rose' }, { shape: 'swatch', tone: 'rose' }, { shape: 'powder', tone: 'rose' }],
    shortDescription: 'A two-tone blush that blurs colour into the skin.',
    description: 'A duo of a sheer wash and a deeper tone that can be used separately or mixed. The finish is soft-focus rather than powdery, so colour looks as though it is coming from under the skin.',
    whySelected: 'Blush is where most makeup goes wrong. This one is difficult to over-apply, which is exactly why atelierR keeps it in the kit and recommends it to clients doing their own makeup at home.',
    bestFor: ['Soft everyday makeup', 'Natural finish', 'Beginners', 'Dry skin'],
    finish: 'Natural',
    howToUse: [
      'Swirl a blush brush over both shades together.',
      'Tap off the excess on the back of your hand — always.',
      'Smile lightly and sweep along the cheekbone, moving toward the temple.',
      'Build in thin layers if you want more colour.'
    ],
    shadeInfo: {
      guide: 'Warm coral and peach tones lift most skin tones in daylight. Rose and mauve tones suit cool undertones and evening makeup.',
      shades: [
        { name: 'Momotsuki', code: '01', hex: '#E0A092', note: 'Soft peach — universal' },
        { name: 'Akatsuki', code: '03', hex: '#CE8079', note: 'Warm rose — daily wear' },
        { name: 'Yuzuiro', code: '06', hex: '#D99C7E', note: 'Warm coral — brightening' }
      ]
    },
    related: ['brownetoile-blush-brush', 'suqqu-moisture-glaze-lipstick', 'rmk-face-powder'],
    bestSeller: true,
    active: true
  },
  {
    id: 'suqqu-moisture-glaze-lipstick',
    brand: 'SUQQU',
    name: 'Moisture Glaze Lipstick',
    category: 'point-makeup',
    subcategory: 'Lipstick',
    priceSGD: 65,
    stock: 11,
    art: { shape: 'lipstick', tone: 'rose' },
    images: [{ shape: 'lipstick', tone: 'rose' }, { shape: 'swatch', tone: 'rose' }],
    shortDescription: 'A cushioned lipstick with a clear, glossy finish.',
    description: 'A moisture-rich lipstick that wears like a balm and reads like a gloss. Colour is translucent and even, so it can be worn light with one pass or fuller with two.',
    whySelected: 'It solves the two problems clients raise most often: lipstick that dries the lips, and lipstick that looks heavier than the rest of the makeup. This does neither.',
    bestFor: ['Dry lips', 'Soft everyday makeup', 'Sheer finish', 'Quick makeup'],
    finish: 'Sheer',
    howToUse: [
      'Apply directly from the bullet to the centre of the lips.',
      'Press the lips together once to spread the colour outward.',
      'Trace the outer edge only if you want a more defined shape.'
    ],
    shadeInfo: {
      guide: 'Choose a shade one or two steps deeper than your natural lip for an everyday look. Rose and beige tones sit quietly with a soft eye; red tones are better when the eye makeup is kept simple.',
      shades: [
        { name: 'Suisen', code: '01', hex: '#C98C82', note: 'Soft rose beige — everyday' },
        { name: 'Kurenai', code: '04', hex: '#B5504C', note: 'Clear red — occasion' },
        { name: 'Hanakage', code: '07', hex: '#A96C74', note: 'Muted plum rose' },
        { name: 'Yuuhi', code: '10', hex: '#CC7863', note: 'Warm coral' }
      ]
    },
    related: ['suqqu-blurring-color-blush', 'suqqu-signature-color-eyes', 'three-velvet-lipstick'],
    bestSeller: true,
    active: true
  },
  {
    id: 'celvoke-indicate-eyebrow-powder',
    brand: 'Celvoke',
    name: 'Indicate Eyebrow Powder',
    category: 'point-makeup',
    subcategory: 'Brow',
    priceSGD: 48,
    stock: 8,
    art: { shape: 'compact', tone: 'ink' },
    images: [{ shape: 'compact', tone: 'ink' }, { shape: 'swatch', tone: 'clay' }],
    shortDescription: 'A soft brow powder for shape without hard lines.',
    description: 'A pressed brow powder in coordinated tones that can be mixed to match hair colour. It builds gradually, so the brow keeps a natural edge instead of a drawn outline.',
    whySelected: 'Powder is more forgiving than pencil for anyone doing their own brows. atelierR chose this palette because the tones stay soft on black and dark brown hair, which pencils often do not.',
    bestFor: ['Beginners', 'Sparse brows', 'Natural finish', 'Soft everyday makeup'],
    finish: 'Matte',
    howToUse: [
      'Start at the arch, not the front of the brow.',
      'Fill toward the tail with short, light strokes.',
      'Use whatever is left on the brush to shade the front of the brow.'
    ],
    shadeInfo: {
      guide: 'Choose one shade lighter than your hair for black or dark brown hair, and an exact match for lighter hair.',
      shades: [
        { name: 'Soft Brown', code: '01', hex: '#8A6B54', note: 'Brown hair' },
        { name: 'Grey Brown', code: '02', hex: '#6E5B50', note: 'Black hair — most chosen' }
      ]
    },
    related: ['brownetoile-eyebrow-brush', 'rmk-eye-defining-pencil', 'suqqu-signature-color-eyes'],
    bestSeller: true,
    active: true
  },
  {
    id: 'rmk-eye-defining-pencil',
    brand: 'RMK',
    name: 'Eye Defining Pencil',
    category: 'point-makeup',
    subcategory: 'Eyeliner',
    priceSGD: 38,
    stock: 14,
    art: { shape: 'pencil', tone: 'ink' },
    images: [{ shape: 'pencil', tone: 'ink' }, { shape: 'swatch', tone: 'ink' }],
    shortDescription: 'A soft pencil for definition close to the lash line.',
    description: 'A creamy pencil that draws without dragging on the lid. It sets after a moment, so it holds through the day but can still be softened with a brush immediately after application.',
    whySelected: 'atelierR uses this instead of liquid liner on most clients. Filling the lash line makes lashes look denser without the eye reading as "lined", which suits soft everyday makeup better.',
    bestFor: ['Soft everyday makeup', 'Sparse lashes', 'Beginners', 'Hooded eyes'],
    finish: 'Satin',
    howToUse: [
      'Look down into a mirror and lift the lid gently.',
      'Press the pencil into the gaps between the lashes rather than drawing a line above them.',
      'Soften the edge with a small brush within thirty seconds if you want it more diffuse.'
    ],
    shadeInfo: {
      guide: 'Black gives the most definition. Dark brown is softer and generally more flattering for daytime and for mature eyes.',
      shades: [
        { name: 'Black', code: '01', hex: '#20201F', note: 'Maximum definition' },
        { name: 'Dark Brown', code: '02', hex: '#4A3830', note: 'Softer, everyday' }
      ]
    },
    related: ['suqqu-signature-color-eyes', 'brownetoile-eyelash-curler', 'celvoke-indicate-eyebrow-powder'],
    bestSeller: true,
    active: true
  },
  {
    id: 'addiction-matte-lip-liquid',
    brand: 'ADDICTION',
    name: 'The Matte Lip Liquid',
    category: 'point-makeup',
    subcategory: 'Lip',
    priceSGD: 52,
    stock: 4,
    art: { shape: 'tube', tone: 'rose' },
    images: [{ shape: 'tube', tone: 'rose' }, { shape: 'swatch', tone: 'rose' }],
    shortDescription: 'A comfortable matte lip colour with full pigment.',
    description: 'A liquid lip colour that dries down to a soft matte without tightening. Pigment is dense, so one layer is enough for full colour.',
    whySelected: 'Chosen for clients who want their lip colour to last through a meal. It is the one matte formula atelierR has found that does not make dry lips look drier by the afternoon.',
    bestFor: ['Long wear', 'Matte finish', 'Evening makeup', 'Normal lips'],
    finish: 'Matte',
    howToUse: [
      'Start with lips that are smooth and free of balm.',
      'Draw the centre of the lips first, then follow the natural outline.',
      'Let it set for thirty seconds before pressing the lips together.'
    ],
    shadeInfo: {
      guide: 'Matte finishes read deeper than they look in the tube. Choose one step lighter than you would in a glossy formula.',
      shades: [
        { name: 'Dusty Rose', code: '004', hex: '#B4747A', note: 'Neutral, wearable' },
        { name: 'Terracotta', code: '011', hex: '#A75F4B', note: 'Warm undertones' },
        { name: 'Deep Berry', code: '017', hex: '#7E3F4C', note: 'Evening' }
      ]
    },
    related: ['suqqu-moisture-glaze-lipstick', 'three-velvet-lipstick', 'suqqu-blurring-color-blush'],
    bestSeller: false,
    active: true
  },
  {
    id: 'three-velvet-lipstick',
    brand: 'THREE',
    name: 'Velvet Last Lipstick',
    category: 'point-makeup',
    subcategory: 'Lipstick',
    priceSGD: 58,
    stock: 6,
    art: { shape: 'lipstick', tone: 'clay' },
    images: [{ shape: 'lipstick', tone: 'clay' }, { shape: 'swatch', tone: 'clay' }],
    shortDescription: 'A velvet-finish lipstick in quiet, earthy tones.',
    description: 'A cream lipstick with a velvet finish, formulated with botanical oils. It sits between matte and satin — muted, but never dry-looking.',
    whySelected: 'The shade range is unusually restrained, which makes it easy to wear with the natural bases atelierR builds. Good for anyone who finds most lipsticks too bright.',
    bestFor: ['Muted colour', 'Soft everyday makeup', 'Satin finish', 'Mature skin'],
    finish: 'Satin',
    howToUse: [
      'Apply one layer directly from the bullet.',
      'Blot once with a tissue for a softer, more diffused edge.',
      'Reapply only to the centre of the lips to refresh.'
    ],
    shadeInfo: {
      guide: 'Earthy neutrals suit warm undertones; muted rose suits cool undertones.',
      shades: [
        { name: 'Quiet Beige', code: '02', hex: '#BE8877', note: 'Neutral beige rose' },
        { name: 'Still Rose', code: '05', hex: '#AE6E74', note: 'Cool rose' },
        { name: 'Earth Red', code: '09', hex: '#9C5348', note: 'Warm brick' }
      ]
    },
    related: ['suqqu-moisture-glaze-lipstick', 'addiction-matte-lip-liquid', 'suqqu-blurring-color-blush'],
    bestSeller: false,
    active: true
  },

  /* ===================== SKINCARE ===================== */
  {
    id: 'noevir-herbal-skin-lotion',
    brand: 'NOEVIR',
    name: 'Herbal Skin Lotion',
    category: 'skincare',
    subcategory: 'Lotion',
    priceSGD: 88,
    stock: 10,
    art: { shape: 'bottle', tone: 'sage' },
    images: [{ shape: 'bottle', tone: 'sage' }, { shape: 'drops', tone: 'sage' }],
    shortDescription: 'A herbal-based lotion that prepares skin for everything after it.',
    description: 'A hydrating lotion built on a herbal extract base. It is used as the first step after cleansing, softening the skin so that the products applied afterward absorb evenly.',
    whySelected: 'Base makeup only ever looks as good as the skin under it. atelierR recommends starting here for clients whose foundation separates or clings by midday — the problem is usually hydration, not the foundation.',
    bestFor: ['Dry skin', 'Dehydrated skin', 'Sensitive skin', 'Daily use'],
    finish: '—',
    howToUse: [
      'Warm three to four pumps in the palms.',
      'Press into the face rather than wiping across it.',
      'Repeat a second layer on dry areas — cheeks and around the mouth.',
      'Follow with milk lotion or serum while the skin is still slightly damp.'
    ],
    shadeInfo: { guide: '', shades: [] },
    related: ['noevir-herbal-milk-lotion', 'three-cleansing-oil', 'skincare-set-starter'],
    bestSeller: false,
    active: true
  },
  {
    id: 'noevir-herbal-milk-lotion',
    brand: 'NOEVIR',
    name: 'Herbal Milk Lotion',
    category: 'skincare',
    subcategory: 'Emulsion',
    priceSGD: 92,
    stock: 7,
    art: { shape: 'bottle', tone: 'sage' },
    images: [{ shape: 'bottle', tone: 'sage' }, { shape: 'drops', tone: 'sage' }],
    shortDescription: 'A light emulsion that seals in hydration without weight.',
    description: 'A milky emulsion that follows the skin lotion and holds moisture in place. Light enough for humid weather, but rich enough to keep dry areas comfortable overnight.',
    whySelected: 'Paired with the Herbal Skin Lotion, this is the simplest two-step routine atelierR can recommend that visibly changes how base makeup sits the next morning.',
    bestFor: ['Dry skin', 'Normal skin', 'Humid weather', 'Daily use'],
    finish: '—',
    howToUse: [
      'Apply while the skin is still damp from lotion.',
      'Use a coin-sized amount, spread thinly over the whole face.',
      'Press the palms to the face for five seconds to finish.'
    ],
    shadeInfo: { guide: '', shades: [] },
    related: ['noevir-herbal-skin-lotion', 'celvoke-concentrate-serum', 'skincare-set-starter'],
    bestSeller: false,
    active: true
  },
  {
    id: 'three-cleansing-oil',
    brand: 'THREE',
    name: 'Balancing Cleansing Oil',
    category: 'skincare',
    subcategory: 'Cleanser',
    priceSGD: 76,
    stock: 9,
    art: { shape: 'bottle', tone: 'gold' },
    images: [{ shape: 'bottle', tone: 'gold' }, { shape: 'drops', tone: 'gold' }],
    shortDescription: 'A botanical cleansing oil that removes makeup gently.',
    description: 'A cleansing oil built on plant oils that dissolves base makeup, sunscreen and point makeup in one step, then rinses cleanly without leaving the skin tight.',
    whySelected: 'The most common cause of dull, rough-looking skin under makeup is incomplete cleansing. This removes everything without the stripping feeling that makes clients skip the step.',
    bestFor: ['All skin types', 'Makeup removal', 'Daily use', 'Sensitive skin'],
    finish: '—',
    howToUse: [
      'Use on dry hands and a dry face.',
      'Massage in circles for thirty seconds, longer around the eyes.',
      'Add a little water and keep massaging until the oil turns milky.',
      'Rinse with lukewarm water — never hot.'
    ],
    shadeInfo: { guide: '', shades: [] },
    related: ['noevir-herbal-skin-lotion', 'celvoke-concentrate-serum', 'skincare-set-complete'],
    bestSeller: false,
    active: true
  },
  {
    id: 'celvoke-concentrate-serum',
    brand: 'Celvoke',
    name: 'Concentrate Serum',
    category: 'skincare',
    subcategory: 'Serum',
    priceSGD: 128,
    stock: 5,
    art: { shape: 'bottle', tone: 'clay' },
    images: [{ shape: 'bottle', tone: 'clay' }, { shape: 'drops', tone: 'clay' }],
    shortDescription: 'A botanical serum for skin that looks tired or uneven.',
    description: 'A concentrated botanical serum used between hydration and emulsion. It targets uneven tone and the flat, tired look skin takes on after long days indoors under air conditioning.',
    whySelected: 'atelierR recommends this to clients who feel their skin has lost its light rather than its moisture. Results show in how foundation reflects, not in how much coverage is needed.',
    bestFor: ['Dull skin', 'Uneven tone', 'Mature skin', 'Evening routine'],
    finish: '—',
    howToUse: [
      'Use three to four drops after skin lotion.',
      'Press over the whole face, then a second pass on areas of unevenness.',
      'Follow with milk lotion to seal.'
    ],
    shadeInfo: { guide: '', shades: [] },
    related: ['noevir-herbal-milk-lotion', 'three-glow-primer', 'skincare-set-complete'],
    bestSeller: false,
    active: true
  },

  /* ===================== TOOLS ===================== */
  {
    id: 'brownetoile-eyeshadow-brush-a',
    brand: 'BROWN ÉTOILE',
    name: 'Eyeshadow Brush (A)',
    category: 'tools',
    subcategory: 'Eye brush',
    priceSGD: 33,
    stock: 15,
    art: { shape: 'brush', tone: 'stone' },
    images: [{ shape: 'brush', tone: 'stone' }],
    shortDescription: 'A flat brush for laying colour evenly across the lid.',
    description: 'A firm, flat brush that places eyeshadow rather than scattering it. Sized for the mobile lid, with a rounded edge so it never leaves a hard line.',
    whySelected: 'Most people already own a workable palette and simply cannot place the colour. This is the brush that changes that, and it is the first tool atelierR hands to a client.',
    bestFor: ['Beginners', 'Powder eyeshadow', 'Precise placement'],
    finish: '—',
    howToUse: [
      'Press the flat side into the powder — do not swirl.',
      'Lay the colour flat on the lid with a pressing motion.',
      'Wash monthly with a gentle soap and dry flat.'
    ],
    shadeInfo: { guide: '', shades: [] },
    related: ['brownetoile-blending-brush', 'suqqu-signature-color-eyes', 'brownetoile-concealer-brush-m'],
    bestSeller: false,
    active: true
  },
  {
    id: 'brownetoile-blending-brush',
    brand: 'BROWN ÉTOILE',
    name: 'Blending Brush',
    category: 'tools',
    subcategory: 'Eye brush',
    priceSGD: 33,
    stock: 13,
    art: { shape: 'brush', tone: 'sand' },
    images: [{ shape: 'brush', tone: 'sand' }],
    shortDescription: 'A soft tapered brush for diffusing edges.',
    description: 'A loosely packed, tapered brush used to soften the boundary between shades. It carries very little product, which is precisely what makes it useful.',
    whySelected: 'Blending is the difference between eye makeup that looks applied and eye makeup that looks lived in. This brush is soft enough to blend without lifting the colour underneath.',
    bestFor: ['Beginners', 'Soft everyday makeup', 'Diffused edges'],
    finish: '—',
    howToUse: [
      'Use with no product on the brush first.',
      'Move in small circles along the edge of the colour only.',
      'Never blend in the centre of the lid — that removes the colour you just placed.'
    ],
    shadeInfo: { guide: '', shades: [] },
    related: ['brownetoile-eyeshadow-brush-a', 'suqqu-signature-color-eyes', 'brownetoile-eyebrow-brush'],
    bestSeller: false,
    active: true
  },
  {
    id: 'brownetoile-eyebrow-brush',
    brand: 'BROWN ÉTOILE',
    name: 'Eyebrow Brush',
    category: 'tools',
    subcategory: 'Brow brush',
    priceSGD: 14,
    stock: 20,
    art: { shape: 'brush', tone: 'ink' },
    images: [{ shape: 'brush', tone: 'ink' }],
    shortDescription: 'A firm angled brush for shaping brows with powder.',
    description: 'A short, firm angled brush that makes a clean stroke in brow powder. The angle follows the natural direction of brow hair.',
    whySelected: 'A good brow depends more on the brush than the powder. This one is stiff enough to draw individual strokes instead of blocks of colour.',
    bestFor: ['Brow powder', 'Beginners', 'Sparse brows'],
    finish: '—',
    howToUse: [
      'Load only the tip of the angled edge.',
      'Draw short upward strokes, following the direction the hair grows.',
      'Brush through with a spoolie to soften.'
    ],
    shadeInfo: { guide: '', shades: [] },
    related: ['celvoke-indicate-eyebrow-powder', 'brownetoile-blending-brush', 'rmk-eye-defining-pencil'],
    bestSeller: false,
    active: true
  },
  {
    id: 'brownetoile-face-powder-brush',
    brand: 'BROWN ÉTOILE',
    name: 'Face Powder Brush',
    category: 'tools',
    subcategory: 'Face brush',
    priceSGD: 84,
    stock: 6,
    art: { shape: 'brushWide', tone: 'stone' },
    images: [{ shape: 'brushWide', tone: 'stone' }],
    shortDescription: 'A large, soft brush for setting powder lightly.',
    description: 'A generously sized powder brush with a rounded head. It holds a small amount of powder across a wide surface, which is how a base gets set without going flat.',
    whySelected: 'The size is the point. A large brush distributes powder so thinly that it is almost impossible to over-powder, even in a hurry.',
    bestFor: ['Loose powder', 'Pressed powder', 'Natural finish'],
    finish: '—',
    howToUse: [
      'Tap powder into the lid, press the brush in, then tap off the excess.',
      'Sweep across the centre of the face in one light pass.',
      'Use whatever remains on the brush for the outer face.'
    ],
    shadeInfo: { guide: '', shades: [] },
    related: ['rmk-face-powder', 'brownetoile-blush-brush', 'rmk-liquid-foundation'],
    bestSeller: false,
    active: true
  },
  {
    id: 'brownetoile-blush-brush',
    brand: 'BROWN ÉTOILE',
    name: 'Blush Brush',
    category: 'tools',
    subcategory: 'Face brush',
    priceSGD: 72,
    stock: 8,
    art: { shape: 'brushWide', tone: 'rose' },
    images: [{ shape: 'brushWide', tone: 'rose' }],
    shortDescription: 'A tapered brush that places blush exactly where you want it.',
    description: 'A medium, slightly tapered brush for powder blush. Soft enough to diffuse colour, shaped enough to keep it on the cheekbone.',
    whySelected: 'Round brushes drop blush in a circle; this shape follows the cheekbone. It is the reason blush looks intentional rather than applied.',
    bestFor: ['Powder blush', 'Soft everyday makeup', 'Precise placement'],
    finish: '—',
    howToUse: [
      'Load the brush and tap off the excess on the back of the hand.',
      'Start at the cheekbone and sweep toward the temple.',
      'Never start at the centre of the cheek.'
    ],
    shadeInfo: { guide: '', shades: [] },
    related: ['suqqu-blurring-color-blush', 'brownetoile-face-powder-brush', 'rmk-face-powder'],
    bestSeller: true,
    active: true
  },
  {
    id: 'brownetoile-concealer-brush-m',
    brand: 'BROWN ÉTOILE',
    name: 'Concealer Brush (M)',
    category: 'tools',
    subcategory: 'Face brush',
    priceSGD: 38,
    stock: 11,
    art: { shape: 'brush', tone: 'clay' },
    images: [{ shape: 'brush', tone: 'clay' }],
    shortDescription: 'A small flat brush for placing concealer precisely.',
    description: 'A compact, flat brush with a tapered tip. It applies concealer in a thin layer to a small area, so the product is not spread further than it needs to be.',
    whySelected: 'Fingers warm concealer and move it too far. This keeps coverage exactly where the shadow is, which means less product and a lighter result.',
    bestFor: ['Concealer', 'Under-eye area', 'Precise placement'],
    finish: '—',
    howToUse: [
      'Pick up concealer with the flat of the brush.',
      'Press it into place with the tip, tapping rather than sweeping.',
      'Use the clean edge to soften the boundary.'
    ],
    shadeInfo: { guide: '', shades: [] },
    related: ['addiction-the-concealer', 'brownetoile-eyeshadow-brush-a', 'rmk-liquid-foundation'],
    bestSeller: false,
    active: true
  },
  {
    id: 'brownetoile-eyelash-curler',
    brand: 'BROWN ÉTOILE',
    name: 'Eyelash Curler',
    category: 'tools',
    subcategory: 'Accessory',
    priceSGD: 12,
    stock: 18,
    art: { shape: 'curler', tone: 'stone' },
    images: [{ shape: 'curler', tone: 'stone' }],
    shortDescription: 'A gently curved curler that suits most eye shapes.',
    description: 'A lash curler with a shallower curve than most, designed to reach the full lash line on Asian eye shapes without pinching at the corners.',
    whySelected: 'The single cheapest change that makes the biggest difference. atelierR curls lashes on every client, often before deciding whether mascara is needed at all.',
    bestFor: ['Straight lashes', 'Monolid and hooded eyes', 'Quick makeup'],
    finish: '—',
    howToUse: [
      'Curl at the base of the lashes first and hold for five seconds.',
      'Move halfway up and press again, more lightly.',
      'Never curl after mascara — the lashes will break.'
    ],
    shadeInfo: { guide: '', shades: [] },
    related: ['rmk-eye-defining-pencil', 'suqqu-signature-color-eyes', 'brownetoile-eyeshadow-brush-a'],
    bestSeller: false,
    active: true
  },

  /* ===================== SETS ===================== */
  {
    id: 'base-makeup-set',
    brand: 'atelierR',
    name: 'Base Makeup Set',
    category: 'sets',
    subcategory: 'Makeup set',
    priceSGD: 260,
    stock: 4,
    art: { shape: 'set', tone: 'sand' },
    images: [{ shape: 'set', tone: 'sand' }, { shape: 'swatch', tone: 'sand' }, { shape: 'stone', tone: 'stone' }],
    shortDescription: 'A complete, flawless base — primer, foundation, powder and brush.',
    description: 'Everything needed for a finished base, in the order atelierR applies it during a session: primer, liquid foundation, translucent powder and the powder brush that sets it.',
    whySelected: 'Buying a base one product at a time is where most people stall. This set removes every decision except the foundation shade, and saves SGD 22 against buying the pieces separately.',
    bestFor: ['A complete base', 'Beginners', 'Natural finish', 'Gifting'],
    finish: 'Natural',
    howToUse: [
      'Primer on the high points of the face.',
      'Foundation from the centre outward, in a thin layer.',
      'Powder across the centre of the face only, using the brush provided.'
    ],
    shadeInfo: {
      guide: 'Only the foundation requires a shade choice. Select it on the RMK Liquid Foundation page, or start with Natural Beige 103, the shade most clients settle on.',
      shades: []
    },
    setContents: ['three-glow-primer', 'rmk-liquid-foundation', 'rmk-face-powder', 'brownetoile-face-powder-brush'],
    related: ['rmk-liquid-foundation', 'skincare-set-starter', 'rmk-face-powder'],
    bestSeller: true,
    active: true
  },
  {
    id: 'skincare-set-starter',
    brand: 'atelierR',
    name: 'Skincare Set — Starter',
    category: 'sets',
    subcategory: 'Skincare set',
    priceSGD: 180,
    stock: 6,
    art: { shape: 'setSkincare', tone: 'sage' },
    images: [{ shape: 'setSkincare', tone: 'sage' }, { shape: 'drops', tone: 'sage' }],
    shortDescription: 'The two-step routine that changes how makeup sits.',
    description: 'The Herbal Skin Lotion and Herbal Milk Lotion together — the shortest routine atelierR recommends, and the one most clients see a difference from within a week.',
    whySelected: 'Two products, two minutes, morning and night. Chosen because a routine only works if it is short enough to actually keep. Saves SGD 20 against buying both separately.',
    bestFor: ['Dry skin', 'Beginners', 'Daily use', 'Gifting'],
    finish: '—',
    howToUse: [
      'Skin lotion first, pressed in with the palms.',
      'Milk lotion second, while the skin is still damp.',
      'Both morning and night.'
    ],
    shadeInfo: { guide: '', shades: [] },
    setContents: ['noevir-herbal-skin-lotion', 'noevir-herbal-milk-lotion'],
    related: ['skincare-set-complete', 'noevir-herbal-skin-lotion', 'base-makeup-set'],
    bestSeller: true,
    active: true
  },
  {
    id: 'skincare-set-complete',
    brand: 'atelierR',
    name: 'Skincare Set — Complete',
    category: 'sets',
    subcategory: 'Skincare set',
    priceSGD: 440,
    stock: 3,
    art: { shape: 'setSkincare', tone: 'clay' },
    images: [{ shape: 'setSkincare', tone: 'clay' }, { shape: 'drops', tone: 'clay' }, { shape: 'stone', tone: 'sage' }],
    shortDescription: 'Cleanse, hydrate, treat and seal — the full routine.',
    description: 'The complete four-step routine: cleansing oil, herbal skin lotion, concentrate serum and herbal milk lotion. Everything from removing the day to sealing the night.',
    whySelected: 'For clients who have already found the two-step routine working and want to go further. The serum is what makes the difference here, and it is included at a saving of SGD 44.',
    bestFor: ['Mature skin', 'Dull skin', 'Complete routine', 'Gifting'],
    finish: '—',
    howToUse: [
      'Cleansing oil on dry skin, massaged and rinsed.',
      'Skin lotion pressed in with the palms.',
      'Serum on the whole face, then again where tone is uneven.',
      'Milk lotion last, to seal.'
    ],
    shadeInfo: { guide: '', shades: [] },
    setContents: ['three-cleansing-oil', 'noevir-herbal-skin-lotion', 'celvoke-concentrate-serum', 'noevir-herbal-milk-lotion'],
    related: ['skincare-set-starter', 'celvoke-concentrate-serum', 'base-makeup-set'],
    bestSeller: false,
    active: true
  }
];
