import { useEffect, useRef, useState, type ReactNode } from 'react';
import {
  Animated,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type TextInputProps,
  type TextStyle,
  type ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path } from 'react-native-svg';

import { colors, fonts, radius, shadow, tint } from '@/theme';

import { Orb } from './Orb';

const useNative = Platform.OS !== 'web';

/** Screen shell: parchment, safe-area aware, content column capped for wide screens. Screen transitions: fade + 12px rise. */
export function Screen({ children, scroll = true, title, kicker }: { children: ReactNode; scroll?: boolean; title?: string; kicker?: string }) {
  const insets = useSafeAreaInsets();
  const enter = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(enter, { toValue: 1, duration: 380, useNativeDriver: useNative }).start();
  }, [enter]);
  const header = title ? (
    <View style={styles.header}>
      <View style={{ flex: 1 }}>
        {kicker ? <Micro>{kicker}</Micro> : null}
        <Text style={styles.screenTitle}>{title}</Text>
      </View>
      <Orb size={32} />
    </View>
  ) : null;
  const body = (
    <Animated.View
      style={[
        styles.column,
        { opacity: enter, transform: [{ translateY: enter.interpolate({ inputRange: [0, 1], outputRange: [12, 0] }) }] },
      ]}
    >
      {header}
      {children}
    </Animated.View>
  );
  return (
    <View style={[styles.screen, { paddingTop: insets.top }]}>
      {scroll ? (
        <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
          {body}
        </ScrollView>
      ) : (
        body
      )}
    </View>
  );
}

export function Micro({ children, color = colors.muted, style }: { children: ReactNode; color?: string; style?: StyleProp<TextStyle> }) {
  return <Text style={[styles.micro, { color }, style]}>{children}</Text>;
}

export function SectionLabel({ children, color = colors.terra }: { children: ReactNode; color?: string }) {
  return (
    <View style={styles.secLabel}>
      <Text style={[styles.micro, { color, letterSpacing: 2.2 }]}>{children}</Text>
      <View style={styles.secRule} />
    </View>
  );
}

export function Serif({ children, size = 20, italic, color = colors.ink, style }: { children: ReactNode; size?: number; italic?: boolean; color?: string; style?: StyleProp<TextStyle> }) {
  return (
    <Text style={[{ fontFamily: italic ? fonts.serifItalic : fonts.serifLight, fontSize: size, color, lineHeight: size * 1.3 }, style]}>
      {children}
    </Text>
  );
}

export function Body({ children, color = colors.muted, style }: { children: ReactNode; color?: string; style?: StyleProp<TextStyle> }) {
  return <Text style={[styles.body, { color }, style]}>{children}</Text>;
}

/** Cards press like warm stone: scale 0.97 on press, spring back. */
export function Card({ children, style, onPress, accent }: { children: ReactNode; style?: StyleProp<ViewStyle>; onPress?: () => void; accent?: string }) {
  const s = useRef(new Animated.Value(1)).current;
  const content = (
    <Animated.View style={[styles.card, accent ? { borderTopColor: accent, borderTopWidth: 2 } : null, style, { transform: [{ scale: s }] }]}>
      {children}
    </Animated.View>
  );
  if (!onPress) return content;
  return (
    <Pressable
      onPress={onPress}
      onPressIn={() => Animated.timing(s, { toValue: 0.97, duration: 150, useNativeDriver: useNative }).start()}
      onPressOut={() => Animated.spring(s, { toValue: 1, useNativeDriver: useNative }).start()}
    >
      {content}
    </Pressable>
  );
}

export function Tag({ label, color }: { label: string; color: string }) {
  return (
    <View style={[styles.tag, { backgroundColor: tint(color, 0.12) }]}>
      <Text style={[styles.tagText, { color }]}>{label}</Text>
    </View>
  );
}

export function Button({ label, onPress, kind = 'primary', disabled, style }: { label: string; onPress: () => void; kind?: 'primary' | 'secondary'; disabled?: boolean; style?: StyleProp<ViewStyle> }) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.button,
        kind === 'primary' ? styles.buttonPrimary : styles.buttonSecondary,
        pressed && { transform: [{ scale: 0.97 }], opacity: 0.9 },
        disabled && { opacity: 0.45 },
        style,
      ]}
      accessibilityRole="button"
    >
      <Text style={[styles.buttonText, { color: kind === 'primary' ? colors.buttonInk : colors.muted }]}>{label}</Text>
    </Pressable>
  );
}

/** Round check. Completion: fill + border color, never instant. */
export function Check({ done, color = colors.sage, size = 22 }: { done: boolean; color?: string; size?: number }) {
  const a = useRef(new Animated.Value(done ? 1 : 0)).current;
  useEffect(() => {
    Animated.timing(a, { toValue: done ? 1 : 0, duration: 250, useNativeDriver: false }).start();
  }, [done, a]);
  return (
    <Animated.View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        borderWidth: 1,
        borderColor: a.interpolate({ inputRange: [0, 1], outputRange: [colors.borderM, color] }),
        backgroundColor: a.interpolate({ inputRange: [0, 1], outputRange: ['rgba(255,255,255,0)', color] }),
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {done ? (
        <Svg width={size * 0.55} height={size * 0.55} viewBox="0 0 24 24">
          <Path d="M5 12.5l4.5 4.5L19 7.5" stroke={colors.parch} strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </Svg>
      ) : null}
    </Animated.View>
  );
}

/** A tappable row with a check and strikethrough-on-done label. */
export function CheckRow({ done, onPress, title, detail, right, color }: { done: boolean; onPress: () => void; title: string; detail?: string; right?: string; color?: string }) {
  return (
    <Pressable onPress={onPress} style={styles.checkRow} accessibilityRole="checkbox" accessibilityState={{ checked: done }}>
      <Check done={done} color={color} />
      <View style={{ flex: 1 }}>
        <Text style={[styles.rowTitle, done && styles.rowDone]}>{title}</Text>
        {detail ? <Text style={styles.rowDetail}>{detail}</Text> : null}
      </View>
      {right ? <Text style={[styles.rowRight, { color: color ?? colors.terra }]}>{right}</Text> : null}
    </Pressable>
  );
}

export function ProgressBar({ value, color = colors.terra, height = 3 }: { value: number; color?: string; height?: number }) {
  const w = useRef(new Animated.Value(value)).current;
  useEffect(() => {
    Animated.timing(w, { toValue: value, duration: 300, useNativeDriver: false }).start();
  }, [value, w]);
  return (
    <View style={{ height, borderRadius: height, backgroundColor: colors.faint, overflow: 'hidden' }}>
      <Animated.View
        style={{
          height,
          borderRadius: height,
          backgroundColor: color,
          width: w.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'], extrapolate: 'clamp' }),
        }}
      />
    </View>
  );
}

/** Pill segmented control (Full / Light / Rest, weekday pickers…). */
export function Segmented<T extends string | number>({ options, value, onChange, color = colors.terra }: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; color?: string }) {
  return (
    <View style={styles.segment}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Pressable
            key={String(o.value)}
            onPress={() => onChange(o.value)}
            style={[styles.segmentItem, active && { backgroundColor: colors.surfaceS, borderColor: tint(color, 0.3) }]}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
          >
            <Text style={[styles.segmentText, { color: active ? color : colors.muted }]}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

/** Inputs feel like writing: Cormorant italic, stone border that warms to terra on focus. */
export function Field(props: TextInputProps & { multiline?: boolean }) {
  const [focused, setFocused] = useState(false);
  return (
    <TextInput
      placeholderTextColor={colors.muted}
      {...props}
      onFocus={(e) => {
        setFocused(true);
        props.onFocus?.(e);
      }}
      onBlur={(e) => {
        setFocused(false);
        props.onBlur?.(e);
      }}
      style={[
        styles.field,
        props.multiline && { minHeight: 80, textAlignVertical: 'top' },
        Platform.OS === 'web' && ({ outlineStyle: 'none' } as unknown as TextStyle),
        props.style,
        focused && { borderColor: colors.terra },
      ]}
    />
  );
}

export function Row({ children, style, gap = 10 }: { children: ReactNode; style?: StyleProp<ViewStyle>; gap?: number }) {
  return <View style={[{ flexDirection: 'row', alignItems: 'center', gap }, style]}>{children}</View>;
}

export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.parch },
  scrollContent: { paddingBottom: 48 },
  column: { width: '100%', maxWidth: 640, alignSelf: 'center', paddingHorizontal: 18 },
  header: { flexDirection: 'row', alignItems: 'center', paddingTop: 20, paddingBottom: 22, gap: 12 },
  screenTitle: { fontFamily: fonts.serifLight, fontSize: 38, color: colors.ink, letterSpacing: -0.8, lineHeight: 44 },
  micro: { fontFamily: fonts.sansLight, fontSize: 9, letterSpacing: 1.6, textTransform: 'uppercase' },
  secLabel: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 28, marginBottom: 12 },
  secRule: { flex: 1, height: 1, backgroundColor: colors.border },
  body: { fontFamily: fonts.sansLight, fontSize: 12, lineHeight: 19 },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.card,
    paddingVertical: 18,
    paddingHorizontal: 18,
    ...shadow.card,
  },
  tag: { alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 2, borderRadius: radius.pill },
  tagText: { fontFamily: fonts.sans, fontSize: 8, letterSpacing: 1.2, textTransform: 'uppercase' },
  button: { height: 52, borderRadius: radius.button, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 20 },
  buttonPrimary: { backgroundColor: colors.gold, borderWidth: 1, borderColor: colors.goldDeep },
  buttonSecondary: { backgroundColor: 'transparent', borderWidth: 1, borderColor: 'rgba(42,26,14,0.12)' },
  buttonText: { fontFamily: fonts.sans, fontSize: 11, letterSpacing: 1.1, textTransform: 'uppercase' },
  checkRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.faint },
  rowTitle: { fontFamily: fonts.sans, fontSize: 13, color: colors.ink },
  rowDone: { color: colors.muted, textDecorationLine: 'line-through' },
  rowDetail: { fontFamily: fonts.sansLight, fontSize: 11, color: colors.muted, marginTop: 2, lineHeight: 16 },
  rowRight: { fontFamily: fonts.sansLight, fontSize: 11 },
  segment: { flexDirection: 'row', gap: 6, backgroundColor: colors.faint, borderRadius: radius.pill, padding: 3 },
  segmentItem: { flex: 1, paddingVertical: 8, borderRadius: radius.pill, alignItems: 'center', borderWidth: 1, borderColor: 'transparent' },
  segmentText: { fontFamily: fonts.sans, fontSize: 9, letterSpacing: 1.4, textTransform: 'uppercase' },
  field: {
    backgroundColor: 'rgba(255,255,255,0.5)',
    borderWidth: 1,
    borderColor: colors.stone,
    borderRadius: radius.compact,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontFamily: fonts.serifItalic,
    fontSize: 16,
    color: colors.ink,
  },
});
