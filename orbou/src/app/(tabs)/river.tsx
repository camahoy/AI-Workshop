import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { Body, Button, Card, Field, Micro, Screen, SectionLabel, Serif, Tag } from '@/components/ui';
import { dateKey, dayMoved } from '@/lib/state';
import { useStore } from '@/lib/store';
import { sendMagicLink, supabase } from '@/lib/supabase';
import { colors, domainColor, domainLabel, fonts, type Domain } from '@/theme';

const WEEKS = 12;

export default function River() {
  const { state, update, session, syncStatus, signOut, reset } = useStore();
  const [editing, setEditing] = useState(false);
  const [vision, setVision] = useState(state.profile.vision ?? '');

  // The river: last 12 weeks, Monday-first, oldest at top. Presence, not perfection.
  const now = new Date();
  const monday = new Date(now);
  monday.setDate(now.getDate() - ((now.getDay() + 6) % 7) - (WEEKS - 1) * 7);
  const todayKey = dateKey(now);
  const weeks = Array.from({ length: WEEKS }, (_, w) =>
    Array.from({ length: 7 }, (_, d) => {
      const date = new Date(monday);
      date.setDate(monday.getDate() + w * 7 + d);
      const key = dateKey(date);
      return { key, future: key > todayKey, log: state.days[key] };
    }),
  );
  const firstKey = Object.keys(state.days).sort()[0];
  const lived = weeks.flat().filter((d) => !d.future && firstKey && d.key >= firstKey);
  const moved = lived.filter((d) => dayMoved(d.log)).length;
  const pct = lived.length ? Math.round((moved / lived.length) * 100) : 0;

  return (
    <Screen title="The river" kicker="Still moving ✦">
      <Card style={{ gap: 14 }}>
        <View style={styles.river}>
          {weeks.map((week, w) => (
            <View key={w} style={styles.week}>
              {week.map((d) => {
                const isMoved = dayMoved(d.log);
                const rest = d.log?.mode === 'rest';
                return (
                  <View
                    key={d.key}
                    style={[
                      styles.drop,
                      isMoved && { backgroundColor: rest ? colors.sky : colors.sage, borderColor: 'transparent' },
                      !isMoved && rest && { borderColor: colors.sky },
                      d.future && { opacity: 0.25 },
                      d.key === todayKey && { borderColor: colors.terra, borderWidth: 1.5 },
                    ]}
                  />
                );
              })}
            </View>
          ))}
        </View>
        <Serif italic size={16} color={colors.inkM}>
          {lived.length ? `You moved on ${pct}% of your days. Rest weeks don’t erase anything.` : 'The river starts wherever you do.'}
        </Serif>
      </Card>

      <SectionLabel color={colors.violet}>Who you’re becoming</SectionLabel>
      {editing ? (
        <View style={{ gap: 10 }}>
          <Field value={vision} onChangeText={setVision} multiline placeholder="I am someone who…" />
          <Button
            label="Keep this"
            onPress={() => {
              update((s) => ({ ...s, profile: { ...s.profile, vision: vision.trim() || undefined } }));
              setEditing(false);
            }}
          />
        </View>
      ) : (
        <Card onPress={() => setEditing(true)}>
          <Serif italic size={17} color={state.profile.vision ? colors.inkM : colors.muted}>
            {state.profile.vision ?? 'Tap to write who you’re becoming.'}
          </Serif>
        </Card>
      )}
      {state.profile.domains.length ? (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 12 }}>
          {state.profile.domains.map((d) => (
            <Tag key={d} label={domainLabel[d as Domain] ?? d} color={domainColor[d as Domain] ?? colors.stone} />
          ))}
        </View>
      ) : null}
      {state.profile.holding.length ? (
        <View style={{ marginTop: 12, gap: 4 }}>
          {state.profile.holding.map((h, i) => (
            <Body key={i}>— {h}</Body>
          ))}
        </View>
      ) : null}

      <SectionLabel color={colors.sky}>Your data</SectionLabel>
      <Sync />

      <SectionLabel color={colors.stone}>Begin again</SectionLabel>
      <View style={{ gap: 10 }}>
        <Button
          label="Talk with ORBOU again"
          kind="secondary"
          onPress={() => {
            update((s) => ({ ...s, chat: [], profile: { ...s.profile, onboarded: false } }));
            router.replace('/onboarding');
          }}
        />
        <ConfirmReset onConfirm={() => { reset(); router.replace('/onboarding'); }} />
      </View>
      <Micro style={{ textAlign: 'center', marginTop: 28 }}>
        {session ? `Synced as ${session.user.email} · ${syncStatus}` : 'Stored on this device'}
      </Micro>
      <Body style={{ textAlign: 'center', fontFamily: fonts.serifItalic, marginTop: 6 }}>Ancient structure. Living nature. Your guardian. ✦</Body>
      {session ? (
        <Pressable onPress={signOut} style={{ alignSelf: 'center', marginTop: 12 }}>
          <Micro color={colors.terra}>Sign out</Micro>
        </Pressable>
      ) : null}
    </Screen>
  );
}

function Sync() {
  const { session, syncStatus } = useStore();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!supabase) {
    return (
      <Card>
        <Body>Everything lives on this device and works offline. Add Supabase keys to this build to sync across devices.</Body>
      </Card>
    );
  }
  if (session) {
    return (
      <Card>
        <Body>
          Synced to your private space as <Body color={colors.inkM}>{session.user.email}</Body>.{' '}
          {syncStatus === 'offline' ? 'Offline right now — changes are kept here and sync when you’re back.' : 'Every change is saved.'}
        </Body>
      </Card>
    );
  }
  return (
    <Card style={{ gap: 12 }}>
      <Body>Local-first, always. Sign in to keep your orb across devices — a link arrives by email, no password.</Body>
      {sent ? (
        <Serif italic size={16} color={colors.sage}>
          Check your email. The link brings you back here.
        </Serif>
      ) : (
        <>
          <Field value={email} onChangeText={setEmail} placeholder="your email" autoCapitalize="none" keyboardType="email-address" autoComplete="email" />
          <Button
            label="Send me a link"
            disabled={!email.includes('@')}
            onPress={async () => {
              setError(null);
              const err = await sendMagicLink(email.trim());
              if (err) setError(err);
              else setSent(true);
            }}
          />
          {error ? <Body color={colors.terra}>{error}</Body> : null}
        </>
      )}
    </Card>
  );
}

function ConfirmReset({ onConfirm }: { onConfirm: () => void }) {
  const [armed, setArmed] = useState(false);
  return armed ? (
    <View style={{ gap: 8 }}>
      <Body color={colors.terra}>This clears your logs, plan and orb on this device (and your synced copy). Are you sure.</Body>
      <View style={{ flexDirection: 'row', gap: 10 }}>
        <Button label="Keep everything" kind="secondary" onPress={() => setArmed(false)} style={{ flex: 1 }} />
        <Button label="Clear it all" onPress={onConfirm} style={{ flex: 1 }} />
      </View>
    </View>
  ) : (
    <Button label="Clear everything" kind="secondary" onPress={() => setArmed(true)} />
  );
}

const styles = StyleSheet.create({
  river: { gap: 6 },
  week: { flexDirection: 'row', justifyContent: 'space-between' },
  drop: { width: 16, height: 16, borderRadius: 8, borderWidth: 1, borderColor: colors.borderM },
});
