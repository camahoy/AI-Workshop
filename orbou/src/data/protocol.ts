export type SuppTiming = 'morning' | 'lunch' | 'evening';

export type Supplement = {
  id: string;
  name: string;
  timing: SuppTiming;
  when: string;
  why: string;
  dose: string;
};

const s = (id: string, name: string, timing: SuppTiming, when: string, why: string, dose: string): Supplement =>
  ({ id, name, timing, when, why, dose });

// Morning list is in taking order: probiotic always first, before the tonic.
export const SUPPLEMENTS: Supplement[] = [
  s('probiotic', 'Probiotic', 'morning', 'Empty stomach — always first', 'Before tonic. Gut-skin axis.', 'Before tonic'),
  s('collagen', 'Collagen Peptides', 'morning', 'In morning tonic', 'Rebuilds keratin heat destroys. Hair · skin · gut.', '10–15g'),
  s('omega3', 'Omega-3 EPA/DHA', 'morning', 'With tonic + fat', 'Seals hair cuticle. Master anti-inflammatory.', '2–3g'),
  s('d3k2', 'D3 + K2', 'morning', 'With omega-3', 'Hair follicle cycling. Immunity. Mood.', '2–5k IU + 100mcg'),
  s('saw-palmetto', 'Saw Palmetto', 'morning', 'With tonic', 'Edge thinning. DHT reduction. Best evidence-backed option.', '320mg'),
  s('silica', 'Silica / Horsetail', 'morning', 'With tonic', 'Strengthens shaft. Reduces breakage. Hardens nails.', '500mg'),
  s('b-complex', 'B-Complex', 'morning', 'With food', 'B5 moisture retention in hair shaft. Biotin baseline.', 'Daily'),
  s('black-seed', 'Black Seed Oil', 'morning', 'With tonic', 'Thymoquinone. Anti-inflammatory. Immunity. Skin.', '500mg cap'),
  s('vit-c', 'Vitamin C', 'morning', 'With tonic', 'Body can’t make collagen without it. Brightens hyperpigmentation.', '500–1000mg'),
  s('rhodiola', 'Rhodiola Rosea', 'morning', 'Morning only', 'Mental endurance. No crash. Disrupts sleep if taken late.', '200–400mg'),
  s('tremella', 'Tremella Mushroom', 'morning', 'In tonic', 'Nature’s hyaluronic acid. Deep skin hydration from within.', '½ tsp'),
  s('tocos', 'Tocos', 'morning', 'In tonic', 'Vitamin E rich. Combats heat + UV damage. Sheen.', '1 tbsp'),
  s('black-sesame', 'Black Sesame', 'morning', 'In tonic or blend', 'Zinc, copper, iron, fatty acids. Critical for follicle.', '1 tbsp'),
  s('turmeric', 'Turmeric + Black Pepper', 'morning', 'In tonic', 'Curcumin suppresses inflammation. Post-breakout dark spots.', '1 tsp + pinch'),
  s('ashwagandha', 'Ashwagandha KSM-66', 'morning', 'In tonic', 'Lowers cortisol. Hair · skin · gut · sleep destroyer when high.', '½ tsp'),
  s('lions-mane', 'Lion’s Mane + Reishi', 'morning', 'In tonic', 'NGF stimulation. Focus. Deep immune modulation.', '½ tsp each'),
  s('zinc', 'Zinc', 'lunch', 'With lunch — NOT with omega-3', 'Regulates sebum. Competes with other minerals — keep separate from morning.', '15–30mg'),
  s('magnesium', 'Magnesium Glycinate', 'evening', '30 min before sleep', 'All repair happens here.', '300–400mg'),
  s('schisandra', 'Schisandra Berry Tincture', 'evening', 'In warm water', 'Liver tonic. Clear skin ties directly to liver health.', '2ml'),
];

export const TIMING_LABEL: Record<SuppTiming, string> = {
  morning: 'Morning sequence',
  lunch: 'With lunch',
  evening: 'Evening',
};

export type Routine = { id: string; title: string; color: 'rose' | 'violet' | 'sage' | 'gold'; steps: { id: string; name: string; detail: string }[]; weekly?: boolean };

export const ROUTINES: Routine[] = [
  {
    id: 'am-skin', title: 'AM skin', color: 'rose',
    steps: [
      { id: 'vitc-serum', name: 'Vitamin C serum', detail: 'L-ascorbic acid 10–15%.' },
      { id: 'niacinamide-am', name: 'Niacinamide', detail: '10% niacinamide.' },
      { id: 'moisturiser-am', name: 'Moisturiser', detail: 'Ceramide + HA barrier moisturiser.' },
      { id: 'spf', name: 'SPF 30–50', detail: 'Mineral, tinted — non-negotiable. No SPF = hyperpigmentation gets worse regardless of everything else.' },
    ],
  },
  {
    id: 'pm-skin', title: 'PM skin', color: 'violet',
    steps: [
      { id: 'cleanse', name: 'Cleanse', detail: 'Gentle cleanse.' },
      { id: 'niacinamide-pm', name: 'Niacinamide', detail: '10% niacinamide.' },
      { id: 'retinoid', name: 'Retinol or Bakuchiol', detail: 'Bakuchiol if retinol is too strong — same results, no PIH risk for darker skin tones.' },
      { id: 'moisturiser-pm', name: 'Barrier moisturiser', detail: 'Seal it in.' },
    ],
  },
  {
    id: 'hair-nightly', title: 'Hair — nightly', color: 'sage',
    steps: [
      { id: 'edge-oil', name: 'Edge Oil Blend', detail: 'Jojoba or grapeseed base + 2–3 drops rosemary + 2–3 drops peppermint. Apply with a soft brush.' },
      { id: 'silk-scarf', name: 'Silk scarf', detail: 'Lay edges and wrap with silk.' },
    ],
  },
  {
    id: 'hair-weekly', title: 'Hair — weekly wash day', color: 'gold', weekly: true,
    steps: [
      { id: 'pre-poo', name: 'Pre-poo', detail: 'Squalane or argan — 20 min before shower.' },
      { id: 'bond-builder', name: 'Bond builder', detail: 'K18 or Olaplex No.3 — repairs disulfide bonds heat destroys.' },
    ],
  },
];
