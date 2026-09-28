import { Redirect } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';
import { Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { FitnessIcon, NutritionIcon, ProtocolIcon, RiverIcon, TodayIcon } from '@/components/icons';
import { useStore } from '@/lib/store';
import { colors, fonts } from '@/theme';

export default function TabsLayout() {
  const { state } = useStore();
  const insets = useSafeAreaInsets();
  if (!state.profile.onboarded) return <Redirect href="/onboarding" />;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.terra,
        tabBarInactiveTintColor: colors.stone,
        tabBarStyle: {
          backgroundColor: 'rgba(240,232,220,0.86)',
          borderTopColor: colors.border,
          // 80px including the home-indicator safe area, per the nav spec.
          height: Math.max(80, 62 + insets.bottom),
          paddingTop: 8,
          paddingBottom: Math.max(insets.bottom, 14),
          position: 'absolute',
          ...(Platform.OS === 'web' ? ({ backdropFilter: 'blur(20px)' } as object) : null),
        },
        tabBarLabelStyle: { fontFamily: fonts.sansXLight, fontSize: 10 },
        sceneStyle: { backgroundColor: colors.parch, paddingBottom: Math.max(80, 62 + insets.bottom) },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Today', tabBarIcon: ({ color }) => <TodayIcon color={color} /> }} />
      <Tabs.Screen name="fitness" options={{ title: 'Fitness', tabBarIcon: ({ color }) => <FitnessIcon color={color} /> }} />
      <Tabs.Screen name="nutrition" options={{ title: 'Nutrition', tabBarIcon: ({ color }) => <NutritionIcon color={color} /> }} />
      <Tabs.Screen name="protocol" options={{ title: 'Protocol', tabBarIcon: ({ color }) => <ProtocolIcon color={color} /> }} />
      <Tabs.Screen name="river" options={{ title: 'River', tabBarIcon: ({ color }) => <RiverIcon color={color} /> }} />
    </Tabs>
  );
}
