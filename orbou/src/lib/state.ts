import type { DayMode } from '@/data/schedule';
import { defaultPlanFor, type SlotId } from '@/data/nutrition';

export type ChatTurn = { role: 'user' | 'assistant'; content: string };

export type Profile = {
  onboarded: boolean;
  name?: string;
  /** Identity statement shown at the top of Today. */
  vision?: string;
  /** Domains ORBOU heard in the onboarding conversation, in the order they matter. */
  domains: string[];
  /** A few short things ORBOU will hold for you. */
  holding: string[];
};

export type SetLog = { weight: string; done: boolean };

export type DayLog = {
  mode: DayMode;
  blocks: string[];
  supps: string[];
  /** `${routineId}:${stepId}` */
  routine: string[];
  /** Glasses of 250ml. */
  water: number;
  /** Exercise id → per-set logs. */
  sets: Record<string, SetLog[]>;
};

export type OrbState = {
  version: 1;
  /** Epoch ms of the last local change — drives last-write-wins sync. */
  updatedAt: number;
  profile: Profile;
  chat: ChatTurn[];
  days: Record<string, DayLog>;
  /** weekday (0–6) → slot → meal id */
  weekPlan: Record<number, Record<SlotId, string>>;
  macroSplit: { protein: number; carbs: number; fat: number };
  groceryChecked: string[];
  /** Last logged weight per exercise, so the field is pre-filled next session. */
  lastWeight: Record<string, string>;
};

export function emptyDay(): DayLog {
  return { mode: 'full', blocks: [], supps: [], routine: [], water: 0, sets: {} };
}

export function initialState(): OrbState {
  const weekPlan: OrbState['weekPlan'] = {};
  for (let d = 0; d < 7; d++) weekPlan[d] = defaultPlanFor(d);
  return {
    version: 1,
    updatedAt: 0,
    profile: { onboarded: false, domains: [], holding: [] },
    chat: [],
    days: {},
    weekPlan,
    macroSplit: { protein: 100, carbs: 120, fat: 40 },
    groceryChecked: [],
    lastWeight: {},
  };
}

/** Merge a stored blob over defaults so older/partial saves never crash the app. */
export function hydrate(raw: unknown): OrbState {
  const base = initialState();
  if (!raw || typeof raw !== 'object') return base;
  const r = raw as Partial<OrbState>;
  return {
    ...base,
    ...r,
    version: 1,
    profile: { ...base.profile, ...(r.profile ?? {}) },
    weekPlan: { ...base.weekPlan, ...(r.weekPlan ?? {}) },
    macroSplit: { ...base.macroSplit, ...(r.macroSplit ?? {}) },
    days: r.days ?? {},
    chat: r.chat ?? [],
    groceryChecked: r.groceryChecked ?? [],
    lastWeight: r.lastWeight ?? {},
    updatedAt: typeof r.updatedAt === 'number' ? r.updatedAt : 0,
  };
}

export function dateKey(d = new Date()): string {
  const y = d.getFullYear();
  const m = (d.getMonth() + 1).toString().padStart(2, '0');
  const day = d.getDate().toString().padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function toggle<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item];
}

/** A day "moved" if anything at all was done — the river counts presence, not perfection. */
export function dayMoved(log: DayLog | undefined): boolean {
  if (!log) return false;
  return (
    log.blocks.length > 0 || log.supps.length > 0 || log.routine.length > 0 || log.water > 0 ||
    Object.values(log.sets).some((sets) => sets.some((s) => s.done))
  );
}
