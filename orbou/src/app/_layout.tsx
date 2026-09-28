import { CormorantGaramond_300Light } from '@expo-google-fonts/cormorant-garamond/300Light';
import { CormorantGaramond_300Light_Italic } from '@expo-google-fonts/cormorant-garamond/300Light_Italic';
import { CormorantGaramond_400Regular } from '@expo-google-fonts/cormorant-garamond/400Regular';
import { CormorantGaramond_400Regular_Italic } from '@expo-google-fonts/cormorant-garamond/400Regular_Italic';
import { CormorantGaramond_500Medium } from '@expo-google-fonts/cormorant-garamond/500Medium';
import { Jost_200ExtraLight } from '@expo-google-fonts/jost/200ExtraLight';
import { Jost_300Light } from '@expo-google-fonts/jost/300Light';
import { Jost_400Regular } from '@expo-google-fonts/jost/400Regular';
import { Jost_500Medium } from '@expo-google-fonts/jost/500Medium';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { Orb } from '@/components/Orb';
import { StoreProvider, useStore } from '@/lib/store';
import { colors } from '@/theme';

function Splash() {
  return (
    <View style={{ flex: 1, backgroundColor: colors.parch, alignItems: 'center', justifyContent: 'center' }}>
      <Orb size={56} thinking />
    </View>
  );
}

function Gate() {
  const { ready } = useStore();
  if (!ready) return <Splash />;
  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.parch }, animation: 'fade' }}>
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="onboarding" />
    </Stack>
  );
}

export default function RootLayout() {
  // Both families load before any screen renders.
  const [loaded] = useFonts({
    CormorantGaramond_300Light,
    CormorantGaramond_300Light_Italic,
    CormorantGaramond_400Regular,
    CormorantGaramond_400Regular_Italic,
    CormorantGaramond_500Medium,
    Jost_200ExtraLight,
    Jost_300Light,
    Jost_400Regular,
    Jost_500Medium,
  });

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <StoreProvider>{loaded ? <Gate /> : <Splash />}</StoreProvider>
    </SafeAreaProvider>
  );
}
