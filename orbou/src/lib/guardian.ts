import type { ChatTurn } from './state';

export const OPENING = 'Hey. What’s been on your mind lately.';
export const ORGANIZE_ASK = 'Want me to organize this into your orb?';

export type OrganizedOrb = {
  name: string | null;
  vision: string;
  domains: string[];
  holding: string[];
  message: string;
};

const API_BASE = process.env.EXPO_PUBLIC_API_BASE ?? '';

async function call<T>(body: object): Promise<T> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`chat ${res.status}`);
  return res.json() as Promise<T>;
}

export async function guardianReply(chat: ChatTurn[]): Promise<string> {
  const { reply } = await call<{ reply: string }>({ mode: 'chat', messages: chat });
  return reply;
}

export async function organizeOrb(chat: ChatTurn[]): Promise<OrganizedOrb> {
  const { orb } = await call<{ orb: OrganizedOrb }>({ mode: 'organize', messages: chat });
  return orb;
}

// ——— Offline fallback ———
// When the chat API isn't reachable (no key yet, offline, local dev without `vercel dev`),
// ORBOU still has a conversation — shorter, scripted, same voice — so onboarding never blocks.

const FALLBACK_PROMPTS = [
  'Stay with that a moment. Who are you becoming, underneath all of it.',
  'And your body — how does it feel to live in it right now.',
  'What about the work. Where is it taking you, and where do you want it to.',
  'When the day is done, what do you want to have protected.',
];

export function fallbackReply(chat: ChatTurn[]): string {
  const userTurns = chat.filter((t) => t.role === 'user').length;
  if (userTurns > FALLBACK_PROMPTS.length) return ORGANIZE_ASK;
  const last = chat[chat.length - 1]?.content ?? '';
  const echo = last.split(/[.!?\n]/)[0].trim();
  const prefix = echo && echo.length < 80 ? `“${echo}.” I hear that. ` : 'I hear that. ';
  return prefix + FALLBACK_PROMPTS[userTurns - 1];
}

const KEYWORDS: Record<string, RegExp> = {
  fitness: /\b(gym|workout|train|lift|body|glute|strong|fit|exercise|weight)/i,
  nutrition: /\b(food|eat|meal|cook|diet|calorie|protein|nutrition|bloat)/i,
  career: /\b(job|career|work|stanford|gre|apply|application|interview|school)/i,
  appearance: /\b(skin|hair|edge|acne|look|style|dress|glow)/i,
  mind: /\b(stress|anxious|calm|mind|read|creative|sew|content|peace|quiet)/i,
  foundation: /\b(sleep|tired|energy|routine|morning|rest)/i,
};

export function fallbackOrganize(chat: ChatTurn[]): OrganizedOrb {
  const said = chat.filter((t) => t.role === 'user').map((t) => t.content).join(' ');
  const domains = Object.entries(KEYWORDS)
    .filter(([, re]) => re.test(said))
    .map(([d]) => d);
  return {
    name: null,
    vision: 'I am someone who shows up for my life — in any form, at my own pace.',
    domains: domains.length ? domains : ['foundation', 'fitness', 'nutrition', 'career'],
    holding: ['Your daily rhythm, from wake to sleep.', 'Your six-day plan and every weight you lift.', 'Your meals, your protocol, your river.'],
    message: 'Your orb is ready.',
  };
}
