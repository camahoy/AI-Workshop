import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Body, Button, Card, CheckRow, Micro, ProgressBar, Screen, SectionLabel, Segmented, Serif, Tag } from '@/components/ui';
import { FORMULA, groceryList, MEAL_BY_ID, MEALS, SLOTS, TARGETS, type SlotId } from '@/data/nutrition';
import { toggle } from '@/lib/state';
import { useStore } from '@/lib/store';
import { colors, fonts, tint } from '@/theme';

type View_ = 'today' | 'week' | 'recipes' | 'grocery';
const WEEKDAYS = [
  { value: 1, label: 'Mon' },
  { value: 2, label: 'Tue' },
  { value: 3, label: 'Wed' },
  { value: 4, label: 'Thu' },
  { value: 5, label: 'Fri' },
  { value: 6, label: 'Sat' },
  { value: 0, label: 'Sun' },
];
const GLASS_L = 0.25;

export default function Nutrition() {
  const [view, setView] = useState<View_>('today');
  return (
    <Screen title="Nutrition" kicker={`${TARGETS.cal.toLocaleString()} cal · one formula`}>
      <Segmented<View_>
        value={view}
        onChange={setView}
        color={colors.sage}
        options={[
          { value: 'today', label: 'Today' },
          { value: 'week', label: 'Week' },
          { value: 'recipes', label: 'Recipes' },
          { value: 'grocery', label: 'Grocery' },
        ]}
      />
      <View style={{ height: 18 }} />
      {view === 'today' ? <TodayView /> : view === 'week' ? <WeekView /> : view === 'recipes' ? <Recipes /> : <Grocery />}
    </Screen>
  );
}

function TodayView() {
  const { state, day, updateDay, update } = useStore();
  const weekday = new Date().getDay();
  const plan = state.weekPlan[weekday];
  const planned = SLOTS.map((s) => MEAL_BY_ID[plan[s.id]]).filter(Boolean);
  const cal = planned.reduce((n, m) => n + m.cal, 0);
  const water = day().water;
  const glasses = Math.round(TARGETS.waterL / GLASS_L);
  const split = state.macroSplit;
  const splitCal = split.protein * 4 + split.carbs * 4 + split.fat * 9;

  const adjust = (k: keyof typeof split, delta: number) =>
    update((s) => ({ ...s, macroSplit: { ...s.macroSplit, [k]: Math.max(0, s.macroSplit[k] + delta) } }));

  return (
    <View>
      <Card style={{ gap: 14 }}>
        <View style={styles.macroGrid}>
          <Macro value={cal.toLocaleString()} label={`of ${TARGETS.cal.toLocaleString()} cal`} color={colors.terra} />
          <Macro value={`${split.protein}g`} label="Protein" color={colors.gold} onMinus={() => adjust('protein', -5)} onPlus={() => adjust('protein', 5)} />
          <Macro value={`${split.carbs}g`} label="Carbs" color={colors.sage} onMinus={() => adjust('carbs', -5)} onPlus={() => adjust('carbs', 5)} />
          <Macro value={`${split.fat}g`} label="Fat" color={colors.violet} onMinus={() => adjust('fat', -5)} onPlus={() => adjust('fat', 5)} />
        </View>
        <ProgressBar value={cal / TARGETS.cal} color={colors.sage} />
        <Body style={{ fontFamily: fonts.serifItalic, fontSize: 13 }}>
          Planned from today’s meals. Your split comes to ~{splitCal.toLocaleString()} cal — adjust with − / +.
        </Body>
      </Card>

      <SectionLabel color={colors.sky}>Water · {TARGETS.waterL}L</SectionLabel>
      <View style={styles.water}>
        {Array.from({ length: glasses }, (_, i) => {
          const full = i < water;
          return (
            <Pressable
              key={i}
              onPress={() => updateDay((d) => ({ ...d, water: full && d.water === i + 1 ? i : i + 1 }))}
              style={[styles.glass, full && { backgroundColor: tint(colors.sky, 0.55), borderColor: colors.sky }]}
              accessibilityLabel={`Glass ${i + 1}`}
            />
          );
        })}
      </View>
      <Micro style={{ marginTop: 8 }}>
        {(water * GLASS_L).toFixed(2).replace(/\.?0+$/, '')}L of {TARGETS.waterL}L · stop at 7:30pm
      </Micro>

      <SectionLabel color={colors.sage}>Today’s plate</SectionLabel>
      <View style={{ gap: 8 }}>
        {SLOTS.map((s) => {
          const meal = MEAL_BY_ID[plan[s.id]];
          return (
            <Card key={s.id} style={{ paddingVertical: 14 }}>
              <View style={styles.rowBetween}>
                <Micro>
                  {s.icon} {s.title}
                </Micro>
                <Micro color={colors.terra}>{meal ? `~${meal.cal}` : ''}</Micro>
              </View>
              <Serif size={19} style={{ marginTop: 4 }}>
                {meal?.name ?? '—'}
              </Serif>
            </Card>
          );
        })}
      </View>

      <Card style={{ marginTop: 16, backgroundColor: tint(colors.sage, 0.06), borderColor: tint(colors.sage, 0.2) }}>
        <Micro color={colors.sage}>The formula</Micro>
        <Body style={{ marginTop: 6, fontFamily: fonts.serifItalic, fontSize: 14 }}>{FORMULA}</Body>
      </Card>
    </View>
  );
}

function Macro({ value, label, color, onMinus, onPlus }: { value: string; label: string; color: string; onMinus?: () => void; onPlus?: () => void }) {
  return (
    <View style={{ alignItems: 'center', flex: 1 }}>
      <Text style={[styles.macroVal, { color }]}>{value}</Text>
      <Micro>{label}</Micro>
      {onMinus ? (
        <View style={{ flexDirection: 'row', gap: 14, marginTop: 4 }}>
          <Pressable onPress={onMinus} hitSlop={8}>
            <Text style={styles.stepper}>−</Text>
          </Pressable>
          <Pressable onPress={onPlus} hitSlop={8}>
            <Text style={styles.stepper}>+</Text>
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

function WeekView() {
  const { state, update } = useStore();
  const [weekday, setWeekday] = useState(new Date().getDay());
  const plan = state.weekPlan[weekday];
  const assign = (slot: SlotId, mealId: string) =>
    update((s) => ({ ...s, weekPlan: { ...s.weekPlan, [weekday]: { ...s.weekPlan[weekday], [slot]: mealId } } }));

  return (
    <View>
      <Segmented value={weekday} onChange={setWeekday} options={WEEKDAYS} color={colors.sage} />
      <View style={{ gap: 12, marginTop: 16 }}>
        {SLOTS.map((slot) => (
          <Card key={slot.id} style={{ gap: 10 }}>
            <View style={styles.rowBetween}>
              <Serif size={18}>
                {slot.icon} {slot.title}
              </Serif>
              <Micro color={colors.terra}>{slot.range}</Micro>
            </View>
            <View style={styles.chips}>
              {MEALS.filter((m) => m.slot === slot.id).map((m) => {
                const on = plan[slot.id] === m.id;
                return (
                  <Pressable key={m.id} onPress={() => assign(slot.id, m.id)} style={[styles.chip, on && styles.chipOn]}>
                    <Text style={[styles.chipText, on && { color: colors.sage }]}>{m.name}</Text>
                  </Pressable>
                );
              })}
            </View>
          </Card>
        ))}
      </View>
    </View>
  );
}

function Recipes() {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <View>
      {SLOTS.map((slot) => (
        <View key={slot.id}>
          <SectionLabel color={colors.sage}>
            {slot.title} · {slot.range}
          </SectionLabel>
          <View style={{ gap: 8 }}>
            {MEALS.filter((m) => m.slot === slot.id).map((m) => {
              const expanded = open === m.id;
              return (
                <Card key={m.id} onPress={() => setOpen(expanded ? null : m.id)} style={{ paddingVertical: 14 }}>
                  <View style={styles.rowBetween}>
                    <Serif size={18} style={{ flex: 1 }}>
                      {m.name}
                    </Serif>
                    <Micro color={colors.terra}>~{m.cal} cal</Micro>
                  </View>
                  {expanded ? (
                    <View style={{ marginTop: 8, gap: 8 }}>
                      {m.note ? <Body>{m.note}</Body> : null}
                      {m.sundayPrep ? <Tag label="Make Sunday" color={colors.gold} /> : null}
                    </View>
                  ) : null}
                </Card>
              );
            })}
          </View>
        </View>
      ))}
    </View>
  );
}

function Grocery() {
  const { state, update } = useStore();
  const items = useMemo(() => {
    const ids = Object.values(state.weekPlan).flatMap((p) => Object.values(p));
    return groceryList(ids);
  }, [state.weekPlan]);
  const checked = state.groceryChecked;
  const remaining = items.filter((i) => !checked.includes(i.item)).length;

  return (
    <View>
      <Serif italic size={16} color={colors.muted}>
        From this week’s plan — {remaining} of {items.length} still to get.
      </Serif>
      <View style={{ marginTop: 12 }}>
        {items.map((i) => (
          <CheckRow
            key={i.item}
            done={checked.includes(i.item)}
            onPress={() => update((s) => ({ ...s, groceryChecked: toggle(s.groceryChecked, i.item) }))}
            title={i.item.charAt(0).toUpperCase() + i.item.slice(1)}
            detail={i.meals.join(' · ')}
          />
        ))}
      </View>
      <Button
        label="Start a fresh list"
        kind="secondary"
        onPress={() => update((s) => ({ ...s, groceryChecked: [] }))}
        style={{ marginTop: 18 }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  macroGrid: { flexDirection: 'row' },
  macroVal: { fontFamily: fonts.serifLight, fontSize: 26, lineHeight: 30 },
  stepper: { fontFamily: fonts.sansLight, fontSize: 16, color: colors.muted },
  water: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  glass: { width: 26, height: 34, borderRadius: 6, borderBottomLeftRadius: 10, borderBottomRightRadius: 10, borderWidth: 1, borderColor: colors.borderM },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 20, borderWidth: 1, borderColor: colors.border, backgroundColor: 'rgba(255,255,255,0.4)' },
  chipOn: { borderColor: tint(colors.sage, 0.5), backgroundColor: tint(colors.sage, 0.1) },
  chipText: { fontFamily: fonts.sansLight, fontSize: 12, color: colors.inkM },
});
