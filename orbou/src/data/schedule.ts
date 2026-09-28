import type { Domain } from '@/theme';

export type DayMode = 'full' | 'light' | 'rest';

export type Block = {
  id: string;
  /** Minutes after midnight. */
  start: number;
  title: string;
  note: string;
  domain: Domain;
  /** What the block becomes on a light day. Omitted = unchanged. */
  light?: string;
  /** What the block becomes on a rest day. Omitted = unchanged. */
  rest?: string;
  /** Short line ORBOU says when this block is current. */
  voice: string;
  /** A domain screen with the detail for this block. */
  link?: '/fitness' | '/nutrition' | '/protocol';
};

const t = (h: number, m = 0) => h * 60 + m;

export const SCHEDULE: Block[] = [
  {
    id: 'wake', start: t(6), title: 'Wake. Water. Light.', domain: 'foundation',
    note: 'Open blinds. Step outside 2 min. Sets circadian rhythm — cortisol, skin, energy.',
    voice: 'Your morning is ready.',
  },
  {
    id: 'stillness', start: t(6, 10), title: 'Stillness.', domain: 'mind',
    note: '5–10 min. Breath, sitting, quiet. Before the day asks anything of you.',
    voice: 'Sit. Before the day asks anything of you.',
  },
  {
    id: 'move', start: t(6, 20), title: 'Move.', domain: 'fitness', link: '/fitness',
    note: '40 min weighted session. Your body is the foundation under everything.',
    light: 'A walk, or the first three exercises. Anything here counts.',
    rest: 'Gentle walk or stretch. Rest is part of the work.',
    voice: 'Move. Your body is the foundation.',
  },
  {
    id: 'shower', start: t(7), title: 'Shower. Skin. Presence.', domain: 'appearance', link: '/protocol',
    note: 'AM skincare sequence. Dress with intention — what you wear affects how you carry yourself.',
    voice: 'Skin, then presence. Dress with intention.',
  },
  {
    id: 'breakfast', start: t(7, 30), title: 'Breakfast.', domain: 'nutrition', link: '/nutrition',
    note: 'Morning tonic + supplements. Protein-forward. Your body just worked. Feed it.',
    voice: 'Your body just worked. Feed it.',
  },
  {
    id: 'work', start: t(8), title: 'Work.', domain: 'career',
    note: 'Until 4. Protect the end of this block as hard as the beginning. Lunch with actual protein.',
    rest: 'If it’s a day off — let it be one.',
    voice: 'Work. Protect the end as hard as the beginning.',
  },
  {
    id: 'reset', start: t(16), title: 'Hard reset.', domain: 'foundation',
    note: 'Walk outside. Change clothes. Water. Don’t go laptop to laptop.',
    voice: 'Walk outside. Don’t go laptop to laptop.',
  },
  {
    id: 'search', start: t(16, 15), title: 'Job search.', domain: 'career',
    note: '5–10 quality applications + 1 outreach. Decision fatigue lowest here — this is why it comes first.',
    light: 'One application, or one outreach. Anything here counts.',
    rest: 'Not today. The river keeps moving.',
    voice: 'Your clearest hours. Spend them here.',
  },
  {
    id: 'dinner', start: t(18, 15), title: 'Dinner.', domain: 'nutrition', link: '/nutrition',
    note: 'Soup, hot pot, or noodles. Light. Something that won’t make you heavy overnight.',
    voice: 'Something warm. Something light.',
  },
  {
    id: 'develop', start: t(18, 45), title: 'Career development.', domain: 'career',
    note: 'Stanford MS&E prep. GRE study. Skill building. Investment, not urgency.',
    light: 'Twenty minutes. One page, one problem.',
    rest: 'Rest. The investment compounds either way.',
    voice: 'Investment, not urgency.',
  },
  {
    id: 'yourself', start: t(20, 45), title: 'Yourself.', domain: 'mind',
    note: 'Two hours. Not whatever’s left. Protected. Content creation, sewing, reading.',
    voice: 'Two hours. Yours. Protected.',
  },
  {
    id: 'winddown', start: t(22, 45), title: 'Wind down.', domain: 'appearance', link: '/protocol',
    note: 'PM skincare. Edge oil. Magnesium. No screens. Your body needs the signal.',
    voice: 'Give your body the signal.',
  },
  {
    id: 'sleep', start: t(23), title: 'Sleep.', domain: 'foundation',
    note: 'All repair happens here. Hair. Skin. Gut. Brain. This is the most important protocol.',
    voice: 'All repair happens here.',
  },
];

/** End of a block in minutes (may exceed 24h for the sleep block). */
export function blockEnd(index: number): number {
  const next = SCHEDULE[index + 1];
  return next ? next.start : SCHEDULE[0].start + 24 * 60;
}

/** Index of the block that holds `minutes`. Before 6:00 still counts as last night's sleep. */
export function currentBlockIndex(minutes: number): number {
  if (minutes < SCHEDULE[0].start) return SCHEDULE.length - 1;
  let idx = 0;
  for (let i = 0; i < SCHEDULE.length; i++) if (SCHEDULE[i].start <= minutes) idx = i;
  return idx;
}

export function formatTime(minutes: number): string {
  const m = ((minutes % 1440) + 1440) % 1440;
  const h = Math.floor(m / 60);
  const mm = m % 60;
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${mm.toString().padStart(2, '0')}`;
}

export function blockText(block: Block, mode: DayMode): string {
  if (mode === 'light' && block.light) return block.light;
  if (mode === 'rest' && block.rest) return block.rest;
  return block.note;
}
