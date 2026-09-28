import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { Platform } from 'react-native';

const url = process.env.EXPO_PUBLIC_SUPABASE_URL;
const anonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

/** Null when Supabase isn't configured — the app then runs fully local. */
export const supabase: SupabaseClient | null =
  url && anonKey
    ? createClient(url, anonKey, {
        auth: {
          storage: AsyncStorage,
          autoRefreshToken: true,
          persistSession: true,
          // On web the magic link lands back on the site with the session in the URL.
          detectSessionInUrl: Platform.OS === 'web',
        },
      })
    : null;

export const TABLE = 'orbou_state';

export async function sendMagicLink(email: string): Promise<string | null> {
  if (!supabase) return 'Sync isn’t set up on this build.';
  const redirect = Platform.OS === 'web' && typeof window !== 'undefined' ? window.location.origin : undefined;
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: { emailRedirectTo: redirect },
  });
  return error ? error.message : null;
}
