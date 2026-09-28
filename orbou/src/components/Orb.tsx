import { useEffect, useMemo, useRef } from 'react';
import { Animated, Easing, Platform, View } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

import { colors } from '@/theme';

// Conic spectrum: Gold → Violet → Sage → Terra → Rose → Sky → Gold.
const STOPS = ['#B8893A', '#6E4E88', '#607D5A', '#B5542E', '#8A4860', '#4A6E8A', '#B8893A'];
const SEGMENTS = 90;
const useNative = Platform.OS !== 'web';

function mix(a: string, b: string, t: number): string {
  const pa = parseInt(a.slice(1), 16);
  const pb = parseInt(b.slice(1), 16);
  const ch = (shift: number) => Math.round(((pa >> shift) & 255) * (1 - t) + ((pb >> shift) & 255) * t);
  return `rgb(${ch(16)},${ch(8)},${ch(0)})`;
}

function colorAt(f: number): string {
  const pos = f * (STOPS.length - 1);
  const i = Math.min(Math.floor(pos), STOPS.length - 2);
  return mix(STOPS[i], STOPS[i + 1], pos - i);
}

type Props = {
  size?: number;
  /** Breathing pulse — the app is thinking. */
  thinking?: boolean;
  /** Background showing through the inner circle. */
  inner?: string;
};

/**
 * The guardian. A perfect circle, conic spectrum of every domain, parchment core at 73%.
 * Resting: a slow 20s turn. Thinking: breathes (scale 1 → 1.06, opacity 0.7 → 1).
 */
export function Orb({ size = 32, thinking = false, inner = colors.parch }: Props) {
  const spin = useRef(new Animated.Value(0)).current;
  const breath = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.timing(spin, { toValue: 1, duration: 20_000, easing: Easing.linear, useNativeDriver: useNative }),
    );
    loop.start();
    return () => loop.stop();
  }, [spin]);

  useEffect(() => {
    if (!thinking) {
      breath.setValue(0);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(breath, { toValue: 1, duration: 3000, easing: Easing.inOut(Easing.ease), useNativeDriver: useNative }),
        Animated.timing(breath, { toValue: 0, duration: 3000, easing: Easing.inOut(Easing.ease), useNativeDriver: useNative }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [thinking, breath]);

  const wedges = useMemo(() => {
    const c = 50;
    const r = 50;
    const out: { d: string; fill: string }[] = [];
    for (let i = 0; i < SEGMENTS; i++) {
      // Start at 200° like the brief's `conic-gradient(from 200deg …)`; overlap slightly to hide seams.
      const a0 = ((200 + (i * 360) / SEGMENTS - 90) * Math.PI) / 180;
      const a1 = ((200 + ((i + 1) * 360) / SEGMENTS + 0.6 - 90) * Math.PI) / 180;
      const x0 = c + r * Math.cos(a0);
      const y0 = c + r * Math.sin(a0);
      const x1 = c + r * Math.cos(a1);
      const y1 = c + r * Math.sin(a1);
      out.push({ d: `M${c},${c} L${x0.toFixed(3)},${y0.toFixed(3)} A${r},${r} 0 0 1 ${x1.toFixed(3)},${y1.toFixed(3)} Z`, fill: colorAt(i / SEGMENTS) });
    }
    return out;
  }, []);

  const rotate = spin.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });
  const scale = breath.interpolate({ inputRange: [0, 1], outputRange: [1, 1.06] });
  const opacity = thinking ? breath.interpolate({ inputRange: [0, 1], outputRange: [0.7, 1] }) : 1;

  return (
    <Animated.View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        opacity,
        transform: [{ scale }],
        shadowColor: colors.terra,
        shadowOpacity: 0.16,
        shadowRadius: size * 0.6,
        shadowOffset: { width: 0, height: size * 0.12 },
      }}
      accessibilityRole="image"
      accessibilityLabel={thinking ? 'ORBOU is thinking' : 'ORBOU'}
    >
      <Animated.View style={{ width: size, height: size, transform: [{ rotate }] }}>
        <Svg width={size} height={size} viewBox="0 0 100 100">
          {wedges.map((w, i) => (
            <Path key={i} d={w.d} fill={w.fill} />
          ))}
        </Svg>
      </Animated.View>
      <View style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, alignItems: 'center', justifyContent: 'center' }} pointerEvents="none">
        <Svg width={size} height={size} viewBox="0 0 100 100">
          <Circle cx={50} cy={50} r={36.5} fill={inner} />
        </Svg>
      </View>
    </Animated.View>
  );
}
