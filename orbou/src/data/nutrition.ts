export type SlotId = 'tonic' | 'breakfast' | 'lunch' | 'treat' | 'dinner' | 'tea';

export type Meal = {
  id: string;
  slot: SlotId;
  name: string;
  /** Ingredients as the brief lists them; used for the grocery list. */
  ingredients: string[];
  cal: number;
  /** Extra guidance from the brief (prep day, rotation, etc.). */
  note?: string;
  /** Make-ahead on Sunday. */
  sundayPrep?: boolean;
};

export type Slot = { id: SlotId; title: string; range: string; icon: string };

export const SLOTS: Slot[] = [
  { id: 'tonic', title: 'Morning Tonic', range: '~20–80 cal · rotate daily', icon: '🌅' },
  { id: 'breakfast', title: 'Breakfast', range: '250–350 cal', icon: '🍳' },
  { id: 'lunch', title: 'Lunch — biggest meal', range: '350–450 cal', icon: '🍱' },
  { id: 'treat', title: 'Afternoon treat', range: '100–150 cal · planned always', icon: '🍮' },
  { id: 'dinner', title: 'Dinner — soup system', range: '300–400 cal', icon: '🍲' },
  { id: 'tea', title: 'Night tea', range: '~0 cal · wind-down ritual', icon: '🌙' },
];

const m = (
  id: string, slot: SlotId, name: string, cal: number, ingredients: string[],
  extra: Partial<Pick<Meal, 'note' | 'sundayPrep'>> = {},
): Meal => ({ id, slot, name, cal, ingredients, ...extra });

export const MEALS: Meal[] = [
  // Morning tonic
  m('bright-beet', 'tonic', 'Bright Beet', 80, ['beet', 'carrot', 'berries', 'fresh ginger', 'lemon'],
    { note: '½ beet · 1 carrot · ½ cup berries · ginger · lemon · 10–12oz water · blend' }),
  m('ginger-pear', 'tonic', 'Ginger Pear', 70, ['asian pear', 'fresh ginger', 'lemon', 'honey'],
    { note: 'Asian pear · fresh ginger · lemon · water · 1 tsp honey' }),
  m('simple-tonic', 'tonic', 'Simple', 20, ['fresh ginger', 'lemon', 'honey'],
    { note: 'Warm water · ginger · lemon · 1 tsp honey · 12–16oz · always works' }),

  // Breakfast
  m('korean-bowl', 'breakfast', 'Korean Breakfast Bowl', 300,
    ['eggs', 'purple rice', 'spinach', 'green onion', 'kimchi', 'nori', 'black sesame'],
    { note: '2 eggs · ⅓ cup purple rice · spinach · green onion · kimchi · nori · black sesame' }),
  m('burrito', 'breakfast', 'Freezer Breakfast Burrito', 350,
    ['sourdough wraps', 'eggs', 'turkey bacon', 'potato', 'cheese', 'spinach'],
    { note: 'Sourdough wrap · 2 eggs · turkey bacon · ½ potato · cheese · spinach', sundayPrep: true }),
  m('overnight-oats', 'breakfast', 'Cinnamon Apple Overnight Oats', 300,
    ['oats', 'chia seeds', 'soy milk', 'apple', 'cinnamon', 'goji berries', 'black sesame'],
    { note: 'Oats · chia · soy milk · apple · cinnamon · goji · black sesame', sundayPrep: true }),
  m('choc-chia', 'breakfast', 'Chocolate Berry Chia', 300,
    ['chia seeds', 'soy milk', 'cocoa powder', 'berries', 'greek yogurt', 'honey'],
    { note: 'Chia · soy milk · cocoa · berries · Greek yogurt · honey', sundayPrep: true }),
  m('mayak-plate', 'breakfast', 'Mayak Egg Plate', 300,
    ['eggs', 'soy sauce', 'purple rice', 'kimchi', 'cucumber', 'nori', 'fruit'],
    { note: '2 mayak eggs · purple rice · kimchi · cucumber · nori · fruit', sundayPrep: true }),

  // Lunch
  m('sesame-noodle', 'lunch', 'Sesame Soy Noodle Bowl', 380,
    ['soba noodles', 'turkey or chicken', 'cabbage', 'sesame oil', 'soy sauce', 'fresh ginger', 'furikake', 'eggs'],
    { note: 'Soba/wheat noodles · turkey or chicken · cabbage or spinach · sesame oil + soy + ginger · furikake · soft egg' }),
  m('bibimbap', 'lunch', 'Bibimbap', 425,
    ['chicken', 'purple rice', 'carrot', 'spinach', 'mushrooms', 'cucumber', 'kimchi', 'gochujang'],
    { note: '4oz chicken · ½ cup purple rice · carrot ribbons · spinach · mushrooms · cucumber · kimchi · gochujang' }),
  m('black-bean-bowl', 'lunch', 'Black Bean Purple Rice Bowl', 400,
    ['black beans', 'purple rice', 'cilantro', 'lime', 'tomato', 'red onion', 'avocado'],
    { note: '½ cup black beans · ½ cup purple rice · cilantro · lime · tomato · pickled onion · ¼ avocado' }),
  m('miso-tofu-noodle', 'lunch', 'Creamy Miso Tofu Noodles', 380,
    ['soba noodles', 'silken tofu', 'white miso', 'gochujang', 'sesame oil', 'spinach', 'eggs'],
    { note: 'Soba/glass noodles · 1 block silken tofu · white miso · gochujang · sesame oil · spinach · soft egg' }),
  m('dakgalbi', 'lunch', 'Dakgalbi with Glass Noodles', 420,
    ['chicken thigh', 'glass noodles', 'carrot', 'sweet potato', 'cabbage', 'daikon', 'gochujang'],
    { note: 'Chicken thigh · glass noodles · carrots · sweet potato · cabbage · daikon · gochujang marinade' }),

  // Treat
  m('snow-fungus', 'treat', 'Snow Fungus Jelly', 55,
    ['tremella (snow fungus)', 'jujubes', 'goji berries', 'asian pear', 'fresh ginger', 'agar'],
    { note: 'Tremella · jujube · goji · pear · ginger · agar · ~55 per cup', sundayPrep: true }),
  m('choc-berries', 'treat', 'Dark Chocolate + Berries', 140, ['dark chocolate 70%+', 'berries'],
    { note: '2 squares 70%+ · handful fresh berries · planned, not a slip' }),

  // Dinner
  m('doenjang', 'dinner', 'Doenjang Hot Pot', 325,
    ['tofu', 'shrimp', 'napa cabbage', 'shiitake', 'enoki mushrooms', 'zucchini', 'bean sprouts', 'doenjang'],
    { note: 'Tofu · shrimp · napa · shiitake + enoki · zucchini · bean sprouts · doenjang broth' }),
  m('kimchi-jjigae', 'dinner', 'Kimchi Jjigae', 325,
    ['tofu', 'shrimp or chicken', 'kimchi', 'mushrooms', 'napa cabbage', 'green onion'],
    { note: 'Tofu · shrimp or chicken · kimchi · mushrooms · napa · green onion' }),
  m('creamy-tofu-noodle', 'dinner', 'Creamy Tofu Noodles', 375,
    ['soba noodles', 'silken tofu', 'white miso', 'nutritional yeast', 'mushrooms', 'spinach', 'shrimp'],
    { note: 'Small soba · silken tofu sauce · white miso · nutritional yeast · mushrooms · spinach · shrimp' }),
  m('enoki-beef', 'dinner', 'Enoki Beef Rolls', 350,
    ['shaved sirloin', 'enoki mushrooms', 'soy sauce', 'sesame oil', 'rice vinegar', 'sesame seeds', 'zucchini'],
    { note: 'Sirloin shaved thin · enoki · soy + sesame + rice vinegar · sesame seeds · steamed zucchini side' }),
  m('white-bean-soup', 'dinner', 'Creamy Chicken White Bean Soup', 350,
    ['chicken', 'cannellini beans', 'carrot', 'celery', 'garlic', 'spinach', 'broth'],
    { note: 'Chicken · cannellini beans · carrot · celery · garlic · spinach · broth · freeze in batches', sundayPrep: true }),

  // Night tea
  m('jujube-tea', 'tea', 'Jujube Chrysanthemum Ginger Tea', 0,
    ['chrysanthemum', 'jujubes', 'fresh ginger', 'asian pear'],
    { note: 'Chrysanthemum · 1–2 jujubes · ginger · Asian pear · hot water · steep 5–7 min. This is your wind-down. Not a detox.' }),
  m('boricha', 'tea', 'Boricha', 0, ['roasted barley tea'],
    { note: 'Roasted barley tea · huge pitcher cold · your default drink all day' }),
];

export const MEAL_BY_ID: Record<string, Meal> = Object.fromEntries(MEALS.map((x) => [x.id, x]));

export const TARGETS = { cal: 1300, protein: 100, carbs: 120, fat: 40, waterL: 2.5 };

export const FORMULA =
  'Base (noodle or rice) + Protein (meat or tofu) + Vegetable (whatever you have) + Sauce (Korean-inspired) + Topping (egg · furikake · sesame). Stop at 7:30pm for water.';

/** Default week plan: rotate through each slot's options by weekday so nothing starts empty. */
export function defaultPlanFor(weekday: number): Record<SlotId, string> {
  const pick = (slot: SlotId) => {
    const opts = MEALS.filter((x) => x.slot === slot);
    return opts[weekday % opts.length].id;
  };
  return {
    tonic: pick('tonic'), breakfast: pick('breakfast'), lunch: pick('lunch'),
    treat: pick('treat'), dinner: pick('dinner'), tea: 'jujube-tea',
  };
}

/** De-duplicated grocery list for a set of meal ids, with which meals need each item. */
export function groceryList(mealIds: string[]): { item: string; meals: string[] }[] {
  const map = new Map<string, Set<string>>();
  for (const id of mealIds) {
    const meal = MEAL_BY_ID[id];
    if (!meal) continue;
    for (const raw of meal.ingredients) {
      const item = raw.trim().toLowerCase();
      if (!map.has(item)) map.set(item, new Set());
      map.get(item)!.add(meal.name);
    }
  }
  return [...map.entries()]
    .map(([item, meals]) => ({ item, meals: [...meals] }))
    .sort((a, b) => a.item.localeCompare(b.item));
}
