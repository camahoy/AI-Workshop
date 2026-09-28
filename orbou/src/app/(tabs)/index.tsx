import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Body, Button, Card, Check, Micro, ProgressBar, Screen, SectionLabel, Segmented, Serif, Tag } from '@/components/ui';
import { blockEnd, blockText, currentBlockIndex, formatTime, SCHEDULE, type DayMode } from '@/data/schedule';
import { dateKey, dayMoved, toggle } from '@/lib/state';
import { useNow, useStore } from '@/lib/store';
import { colors, domainColor, domainLabel, fonts, tint, type Domain } from '@/theme';

const MODE_VOICE: Record<DayMode, string> = {
  full: 'The plan is set. Just what’s next.',
  light: 'Pick one thing. Anything here counts.',
  rest: 'Rest is part of the work. The river keeps moving.',
};

const DONE_VOICE: Partial<Record<Domain, string>> = {
  fitness: 'Done. Your body remembers. ✦',
  nutrition: 'Done. Fed and steady. ✦',
  appearance: 'Done. Carried with intention. ✦',
  career: 'Done. It compounds. ✦',
  mind: 'Done. That was yours. ✦',
  foundation: 'Done. ✦',
};

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export default function Today() {
  const now = useNow();
  const { state, day, updateDay } = useStore();
  const today = day();
  const minutes = now.getHours() * 60 + now.getMinutes();
  const idx = currentBlockIndex(minutes);
  const block = SCHEDULE[idx];
  const start = block.start;
  const end = blockEnd(idx);
  // Sleep spans midnight: after-midnight minutes count as +24h.
  const m = minutes < SCHEDULE[0].start ? minutes + 1440 : minutes;
  const progress = Math.min(1, Math.max(0, (m - start) / (end - start)));
  const [open, setOpen] = useState<string | null>(null);
  const currentDone = today.blocks.includes(block.id);

  const setMode = (mode: DayMode) => updateDay((d) => ({ ...d, mode }));
  const toggleBlock = (id: string) => updateDay((d) => ({ ...d, blocks: toggle(d.blocks, id) }));

  const greeting =
    minutes < 12 * 60 ? 'Your morning is ready.' : minutes < 17 * 60 ? 'The afternoon holds.' : 'The evening is yours.';

  return (
    <Screen
      title={state.profile.name ? `Hello, ${state.profile.name}` : 'Today'}
      kicker={now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
    >
      {state.profile.vision ? (
        <View style={styles.vision}>
          <Serif italic size={17} color={colors.inkM} style={{ lineHeight: 26 }}>
            {state.profile.vision}
          </Serif>
        </View>
      ) : null}

      <Serif italic size={16} color={colors.muted} style={{ marginBottom: 14 }}>
        {greeting}
      </Serif>

      <Segmented<DayMode>
        value={today.mode}
        onChange={setMode}
        options={[
          { value: 'full', label: 'Full' },
          { value: 'light', label: 'Light' },
          { value: 'rest', label: 'Rest' },
        ]}
      />
      <Body style={{ marginTop: 8, marginBottom: 18, fontFamily: fonts.serifItalic, fontSize: 14 }}>{MODE_VOICE[today.mode]}</Body>

      {/* Current block hero */}
      <Card accent={domainColor[block.domain]} style={{ gap: 12, paddingVertical: 22 }}>
        <View style={styles.rowBetween}>
          <Micro color={domainColor[block.domain]}>Now · {formatTime(start)}–{formatTime(end)}</Micro>
          <Tag label={domainLabel[block.domain]} color={domainColor[block.domain]} />
        </View>
        <Text style={styles.heroTitle}>{block.title}</Text>
        <Serif italic size={16} color={colors.inkM}>
          {currentDone ? DONE_VOICE[block.domain] : block.voice}
        </Serif>
        <Body>{blockText(block, today.mode)}</Body>
        <ProgressBar value={progress} color={domainColor[block.domain]} />
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <Button
            label={currentDone ? 'Done ✦' : 'Mark done'}
            kind={currentDone ? 'secondary' : 'primary'}
            onPress={() => toggleBlock(block.id)}
            style={{ flex: 1 }}
          />
          {block.link ? (
            <Button label="Open" kind="secondary" onPress={() => router.push(block.link!)} style={{ paddingHorizontal: 22 }} />
          ) : null}
        </View>
      </Card>

      <WeekStrip />

      <SectionLabel>The day</SectionLabel>
      <View>
        {SCHEDULE.map((b, i) => {
          const done = today.blocks.includes(b.id);
          const past = i < idx && !(idx === SCHEDULE.length - 1 && minutes < SCHEDULE[0].start);
          const current = i === idx;
          const expanded = open === b.id;
          const color = domainColor[b.domain];
          return (
            <Pressable
              key={b.id}
              onPress={() => setOpen(expanded ? null : b.id)}
              style={[styles.blockRow, current && { backgroundColor: tint(color, 0.07) }, past && !current && { opacity: 0.55 }]}
            >
              <Text style={styles.time}>{formatTime(b.start)}</Text>
              <View style={[styles.dot, { backgroundColor: done ? color : 'transparent', borderColor: color }]} />
              <View style={{ flex: 1 }}>
                <Text style={[styles.blockTitle, done && styles.blockDone]}>{b.title}</Text>
                {expanded ? (
                  <View style={{ gap: 10, marginTop: 6 }}>
                    <Body>{blockText(b, today.mode)}</Body>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 16 }}>
                      <Pressable onPress={() => toggleBlock(b.id)} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                        <Check done={done} color={color} size={20} />
                        <Micro color={done ? color : colors.muted}>{done ? 'Done' : 'Mark done'}</Micro>
                      </Pressable>
                      {b.link ? (
                        <Pressable onPress={() => router.push(b.link!)}>
                          <Micro color={colors.terra}>Open {domainLabel[b.domain]} →</Micro>
                        </Pressable>
                      ) : null}
                    </View>
                  </View>
                ) : (
                  <Text style={styles.blockNote} numberOfLines={1}>
                    {blockText(b, today.mode)}
                  </Text>
                )}
              </View>
            </Pressable>
          );
        })}
      </View>
    </Screen>
  );
}

/** This week, Monday first. Dots show days you moved — never a streak count. */
function WeekStrip() {
  const { state } = useStore();
  const now = new Date();
  const monday = new Date(now);
  monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d;
  });
  const todayKey = dateKey(now);
  return (
    <View style={styles.week}>
      {days.map((d) => {
        const key = dateKey(d);
        const moved = dayMoved(state.days[key]);
        const isToday = key === todayKey;
        const mode = state.days[key]?.mode;
        return (
          <View key={key} style={styles.weekDay}>
            <Micro color={isToday ? colors.terra : colors.muted}>{WEEKDAYS[d.getDay()]}</Micro>
            <View
              style={[
                styles.weekDot,
                moved && { backgroundColor: mode === 'rest' ? colors.sky : colors.sage, borderColor: 'transparent' },
                isToday && { borderColor: colors.terra, borderWidth: 1.5 },
              ]}
            />
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  vision: { borderLeftWidth: 2, borderLeftColor: colors.terra, paddingLeft: 14, paddingVertical: 4, marginBottom: 18 },
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  heroTitle: { fontFamily: fonts.serifLight, fontSize: 40, lineHeight: 44, color: colors.ink, letterSpacing: -0.8 },
  week: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 20, paddingHorizontal: 4 },
  weekDay: { alignItems: 'center', gap: 8 },
  weekDot: { width: 12, height: 12, borderRadius: 6, borderWidth: 1, borderColor: colors.borderM },
  blockRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 12, paddingVertical: 12, paddingHorizontal: 8, borderRadius: 12, borderBottomWidth: 1, borderBottomColor: colors.faint },
  time: { fontFamily: fonts.serif, fontSize: 15, color: colors.inkM, width: 46 },
  dot: { width: 9, height: 9, borderRadius: 5, borderWidth: 1, marginTop: 6 },
  blockTitle: { fontFamily: fonts.sans, fontSize: 13, color: colors.ink },
  blockDone: { color: colors.muted, textDecorationLine: 'line-through' },
  blockNote: { fontFamily: fonts.serifItalic, fontSize: 13, color: colors.muted, marginTop: 2 },
});
