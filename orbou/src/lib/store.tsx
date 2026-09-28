import AsyncStorage from '@react-native-async-storage/async-storage';
import type { Session } from '@supabase/supabase-js';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

import { dateKey, emptyDay, hydrate, initialState, type DayLog, type OrbState } from './state';
import { supabase, TABLE } from './supabase';

const STORAGE_KEY = 'orbou:state:v1';

export type SyncStatus = 'local' | 'syncing' | 'synced' | 'offline';

type Store = {
  state: OrbState;
  ready: boolean;
  /** Apply a change. Every change is persisted locally and, when signed in, synced. */
  update: (fn: (s: OrbState) => OrbState) => void;
  /** Change one day's log (today by default). */
  updateDay: (fn: (d: DayLog) => DayLog, key?: string) => void;
  day: (key?: string) => DayLog;
  reset: () => void;
  session: Session | null;
  syncStatus: SyncStatus;
  signOut: () => Promise<void>;
};

const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<OrbState>(initialState);
  const [ready, setReady] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>('local');
  // updatedAt of the version we last pulled from or pushed to Supabase.
  const syncedAt = useRef(0);

  // Load local state first — the app works offline from the first frame.
  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((raw) => {
        if (raw) setState(hydrate(JSON.parse(raw)));
      })
      .catch(() => {})
      .finally(() => setReady(true));
  }, []);

  // Persist locally on every change.
  useEffect(() => {
    if (!ready) return;
    AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(state)).catch(() => {});
  }, [state, ready]);

  // Track the Supabase session.
  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = supabase.auth.onAuthStateChange((_event, s) => setSession(s));
    return () => data.subscription.unsubscribe();
  }, []);

  // On sign-in: pull the remote copy; newest side wins.
  const userId = session?.user.id;
  useEffect(() => {
    if (!supabase || !ready || !userId) {
      setSyncStatus('local');
      return;
    }
    let cancelled = false;
    setSyncStatus('syncing');
    supabase
      .from(TABLE)
      .select('data')
      .eq('user_id', userId)
      .maybeSingle()
      .then(({ data, error }) => {
        if (cancelled) return;
        if (error) {
          setSyncStatus('offline');
          return;
        }
        const remote = data?.data ? hydrate(data.data) : null;
        setState((local) => {
          if (remote && remote.updatedAt > local.updatedAt) {
            syncedAt.current = remote.updatedAt;
            return remote;
          }
          return local;
        });
        setSyncStatus('synced');
      });
    return () => {
      cancelled = true;
    };
  }, [ready, userId]);

  // Push local changes (debounced) while signed in.
  useEffect(() => {
    if (!supabase || !ready || !userId) return;
    if (state.updatedAt <= syncedAt.current) return;
    const client = supabase;
    const snapshot = state;
    const timer = setTimeout(async () => {
      setSyncStatus('syncing');
      const { error } = await client
        .from(TABLE)
        .upsert({ user_id: userId, data: snapshot, updated_at: new Date(snapshot.updatedAt).toISOString() });
      if (error) {
        setSyncStatus('offline');
      } else {
        syncedAt.current = snapshot.updatedAt;
        setSyncStatus('synced');
      }
    }, 1200);
    return () => clearTimeout(timer);
  }, [state, ready, userId]);

  const update = useCallback((fn: (s: OrbState) => OrbState) => {
    setState((s) => ({ ...fn(s), updatedAt: Date.now() }));
  }, []);

  const updateDay = useCallback(
    (fn: (d: DayLog) => DayLog, key = dateKey()) => {
      update((s) => ({ ...s, days: { ...s.days, [key]: fn(s.days[key] ?? emptyDay()) } }));
    },
    [update],
  );

  const day = useCallback((key = dateKey()) => state.days[key] ?? emptyDay(), [state.days]);

  const reset = useCallback(() => {
    setState({ ...initialState(), updatedAt: Date.now() });
  }, []);

  const signOut = useCallback(async () => {
    await supabase?.auth.signOut();
  }, []);

  const value = useMemo<Store>(
    () => ({ state, ready, update, updateDay, day, reset, session, syncStatus, signOut }),
    [state, ready, update, updateDay, day, reset, session, syncStatus, signOut],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore(): Store {
  const s = useContext(Ctx);
  if (!s) throw new Error('useStore outside StoreProvider');
  return s;
}

/** Re-renders every `ms` so time-based views (current block, progress) stay live. */
export function useNow(ms = 30_000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), ms);
    return () => clearInterval(id);
  }, [ms]);
  return now;
}
