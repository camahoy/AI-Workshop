import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Body, Card, Check, Field, Micro, ProgressBar, Screen, SectionLabel, Segmented, Serif, Tag } from '@/components/ui';
import { AB_FINISHER, PROGRESSIVE_OVERLOAD, restDayLabel, sessionOrder, workoutFor, type Exercise } from '@/data/fitness';
import { dateKey, type SetLog } from '@/lib/state';
import { useStore } from '@/lib/store';
import { colors, domainColor, fonts } from '@/theme';

const DAYS = [
  { value: 1, label: 'M' },
  { value: 2, label: 'T' },
  { value: 3, label: 'W' },
  { value: 4, label: 'T' },
  { value: 5, label: 'F' },
  { value: 6, label: 'S' },
  { value: 0, label: 'S' },
];

/** Date key for `weekday` in the current Monday-first week. */
function keyForWeekday(weekday: number): string {
  const now = new Date();
  const monday = new Date(now);
  monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));
  const d = new Date(monday);
  d.setDate(monday.getDate() + ((weekday + 6) % 7));
  return dateKey(d);
}

export default function Fitness() {
  const [weekday, setWeekday] = useState(new Date().getDay());
  const { day } = useStore();
  const workout = workoutFor(weekday);
  const key = keyForWeekday(weekday);
  const log = day(key);

  const all = workout ? [...workout.exercises, ...(workout.abFinisher ? AB_FINISHER : [])] : [];
  const totalSets = all.reduce((n, e) => n + e.sets, 0);
  const doneSets = all.reduce((n, e) => n + (log.sets[e.id]?.filter((s) => s.done).length ?? 0), 0);

  const ordered = workout ? sessionOrder(workout.exercises) : [];
  const firstCable = ordered.findIndex((e) => e.cable);

  return (
    <Screen title="Fitness" kicker="Your 6-day plan">
      <Segmented value={weekday} onChange={setWeekday} options={DAYS} />

      {workout ? (
        <>
          <View style={{ marginTop: 22, gap: 8 }}>
            <Serif size={30}>{workout.title}</Serif>
            <Tag label={workout.focus} color={domainColor[workout.domain]} />
          </View>
          <View style={{ marginTop: 16, gap: 6 }}>
            <View style={styles.rowBetween}>
              <Micro>Session</Micro>
              <Micro color={colors.terra}>
                {doneSets} / {totalSets} sets
              </Micro>
            </View>
            <ProgressBar value={totalSets ? doneSets / totalSets : 0} />
          </View>

          <SectionLabel color={colors.gold}>Warm-up</SectionLabel>
          <Card style={{ gap: 6 }}>
            {workout.warmup.map((w) => (
              <Body key={w}>— {w}</Body>
            ))}
          </Card>

          <SectionLabel>Session</SectionLabel>
          <View style={{ gap: 10 }}>
            {ordered.map((e, i) => (
              <View key={e.id}>
                {i === firstCable ? <Micro style={{ marginBottom: 8, marginTop: 6 }}>Cable station — grouped together</Micro> : null}
                <ExerciseCard exercise={e} index={i + 1} dateKeyStr={key} />
              </View>
            ))}
          </View>

          {workout.abFinisher ? (
            <>
              <SectionLabel color={colors.terra}>Ab finisher — Mon · Fri · Sat</SectionLabel>
              <View style={{ gap: 10 }}>
                {AB_FINISHER.map((e, i) => (
                  <ExerciseCard key={e.id} exercise={e} index={i + 1} dateKeyStr={key} />
                ))}
              </View>
            </>
          ) : null}

          <Card style={{ marginTop: 20, backgroundColor: 'rgba(181,84,46,0.04)', borderColor: 'rgba(181,84,46,0.15)' }}>
            <Micro color={colors.terra}>Progressive overload</Micro>
            <Body style={{ marginTop: 6 }}>{PROGRESSIVE_OVERLOAD}</Body>
          </Card>
        </>
      ) : (
        <Card style={{ marginTop: 24, alignItems: 'center', paddingVertical: 36 }}>
          <Serif italic size={22} color={colors.muted}>
            {restDayLabel(weekday)}
          </Serif>
          <Body style={{ marginTop: 8, textAlign: 'center' }}>Rest weeks don’t erase anything. Recovery is where the work lands.</Body>
        </Card>
      )}
    </Screen>
  );
}

function ExerciseCard({ exercise, index, dateKeyStr }: { exercise: Exercise; index: number; dateKeyStr: string }) {
  const { state, day, update } = useStore();
  const log = day(dateKeyStr);
  const last = state.lastWeight[exercise.id] ?? '';
  const sets: SetLog[] = Array.from({ length: exercise.sets }, (_, i) => log.sets[exercise.id]?.[i] ?? { weight: last, done: false });

  const write = (next: SetLog[], weight?: string) =>
    update((s) => {
      const d = s.days[dateKeyStr] ?? day(dateKeyStr);
      return {
        ...s,
        days: { ...s.days, [dateKeyStr]: { ...d, sets: { ...d.sets, [exercise.id]: next } } },
        lastWeight: weight !== undefined && weight !== '' ? { ...s.lastWeight, [exercise.id]: weight } : s.lastWeight,
      };
    });

  const setWeight = (i: number, weight: string) => {
    // A new weight on set 1 carries forward to the untouched sets below it.
    const next = sets.map((s, j) => (j === i || (i === 0 && j > 0 && !s.done && s.weight === sets[0].weight) ? { ...s, weight } : s));
    write(next, weight);
  };
  const toggleSet = (i: number) => write(sets.map((s, j) => (j === i ? { ...s, done: !s.done } : s)), sets[i].weight);

  const allDone = sets.every((s) => s.done);

  return (
    <Card style={{ paddingVertical: 14 }}>
      <View style={styles.exHeader}>
        <Text style={styles.exNum}>{index}</Text>
        <Text style={[styles.exName, allDone && { color: colors.muted, textDecorationLine: 'line-through' }]}>{exercise.name}</Text>
        <Text style={styles.exTarget}>
          {exercise.sets} × {exercise.target}
        </Text>
      </View>
      <View style={{ marginTop: 10, gap: 6 }}>
        {sets.map((s, i) => (
          <View key={i} style={styles.setRow}>
            <Micro style={{ width: 40 }}>Set {i + 1}</Micro>
            <Field
              value={s.weight}
              onChangeText={(t) => setWeight(i, t)}
              placeholder="weight"
              keyboardType="decimal-pad"
              style={styles.weight}
              accessibilityLabel={`${exercise.name} set ${i + 1} weight`}
            />
            <Text style={styles.reps}>{exercise.target}</Text>
            <Pressable onPress={() => toggleSet(i)} hitSlop={8} accessibilityRole="checkbox" accessibilityState={{ checked: s.done }}>
              <Check done={s.done} color={colors.terra} />
            </Pressable>
          </View>
        ))}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  exHeader: { flexDirection: 'row', alignItems: 'baseline', gap: 10 },
  exNum: { fontFamily: fonts.sansLight, fontSize: 10, color: colors.muted, width: 14 },
  exName: { flex: 1, fontFamily: fonts.sans, fontSize: 14, color: colors.ink },
  exTarget: { fontFamily: fonts.sansLight, fontSize: 11, color: colors.muted },
  setRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingLeft: 24 },
  weight: { width: 84, height: 36, paddingHorizontal: 10, paddingVertical: 0, fontSize: 15 },
  reps: { flex: 1, fontFamily: fonts.sansLight, fontSize: 11, color: colors.muted },
});
