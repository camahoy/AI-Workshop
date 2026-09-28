import { useState } from 'react';
import { View } from 'react-native';

import { Card, CheckRow, Micro, ProgressBar, Screen, SectionLabel, Segmented } from '@/components/ui';
import { ROUTINES, SUPPLEMENTS, TIMING_LABEL, type SuppTiming } from '@/data/protocol';
import { toggle } from '@/lib/state';
import { useStore } from '@/lib/store';
import { colors } from '@/theme';

type Tab = 'supplements' | 'skin' | 'hair';

export default function Protocol() {
  const [tab, setTab] = useState<Tab>(() => (new Date().getHours() >= 17 ? 'skin' : 'supplements'));
  return (
    <Screen title="Protocol" kicker="Supplements · skin · hair">
      <Segmented<Tab>
        value={tab}
        onChange={setTab}
        color={colors.rose}
        options={[
          { value: 'supplements', label: 'Supplements' },
          { value: 'skin', label: 'Skin' },
          { value: 'hair', label: 'Hair' },
        ]}
      />
      {tab === 'supplements' ? <Supplements /> : <Routines ids={tab === 'skin' ? ['am-skin', 'pm-skin'] : ['hair-nightly', 'hair-weekly']} />}
    </Screen>
  );
}

function Supplements() {
  const { day, updateDay } = useStore();
  const taken = day().supps;
  const groups: SuppTiming[] = ['morning', 'lunch', 'evening'];
  const done = SUPPLEMENTS.filter((s) => taken.includes(s.id)).length;

  return (
    <View>
      <View style={{ marginTop: 18, gap: 6 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          <Micro>Today</Micro>
          <Micro color={colors.rose}>
            {done} / {SUPPLEMENTS.length}
          </Micro>
        </View>
        <ProgressBar value={done / SUPPLEMENTS.length} color={colors.rose} />
      </View>
      {groups.map((g) => (
        <View key={g}>
          <SectionLabel color={g === 'evening' ? colors.violet : g === 'lunch' ? colors.sage : colors.gold}>{TIMING_LABEL[g]}</SectionLabel>
          <Card style={{ paddingVertical: 4 }}>
            {SUPPLEMENTS.filter((s) => s.timing === g).map((s) => (
              <CheckRow
                key={s.id}
                done={taken.includes(s.id)}
                onPress={() => updateDay((d) => ({ ...d, supps: toggle(d.supps, s.id) }))}
                title={s.name}
                detail={`${s.when} — ${s.why}`}
                right={s.dose}
                color={colors.rose}
              />
            ))}
          </Card>
        </View>
      ))}
    </View>
  );
}

function Routines({ ids }: { ids: string[] }) {
  const { day, updateDay } = useStore();
  const done = day().routine;
  return (
    <View>
      {ROUTINES.filter((r) => ids.includes(r.id)).map((r) => {
        const color = colors[r.color];
        const count = r.steps.filter((s) => done.includes(`${r.id}:${s.id}`)).length;
        return (
          <View key={r.id}>
            <SectionLabel color={color}>
              {r.title} · {count}/{r.steps.length}
            </SectionLabel>
            <Card style={{ paddingVertical: 4 }}>
              {r.steps.map((s, i) => {
                const key = `${r.id}:${s.id}`;
                return (
                  <CheckRow
                    key={key}
                    done={done.includes(key)}
                    onPress={() => updateDay((d) => ({ ...d, routine: toggle(d.routine, key) }))}
                    title={`${i + 1}. ${s.name}`}
                    detail={s.detail}
                    color={color}
                  />
                );
              })}
            </Card>
            {r.weekly ? <Micro style={{ marginTop: 8 }}>Once a week, on wash day</Micro> : null}
          </View>
        );
      })}
    </View>
  );
}
