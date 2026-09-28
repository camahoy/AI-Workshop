import type { ColorValue } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

// Thin line icons — never filled, never emoji in nav.
type P = { color: ColorValue; size?: number };
const base = { fill: 'none', strokeWidth: 1.2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };

export function TodayIcon({ color, size = 22 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Circle cx={12} cy={12} r={4} stroke={color} {...base} />
      <Path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4" stroke={color} {...base} />
    </Svg>
  );
}

export function NutritionIcon({ color, size = 22 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M3.5 11h17a8.5 8.5 0 0 1-17 0z" stroke={color} {...base} />
      <Path d="M9 8c0-1.5 1-2 1-3.5M13 8c0-1.5 1-2 1-3.5" stroke={color} {...base} />
    </Svg>
  );
}

export function FitnessIcon({ color, size = 22 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M6 8v8M3.5 10v4M18 8v8M20.5 10v4M6 12h12" stroke={color} {...base} />
    </Svg>
  );
}

export function ProtocolIcon({ color, size = 22 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M12 3.5c3 4 5.5 7 5.5 10a5.5 5.5 0 0 1-11 0c0-3 2.5-6 5.5-10z" stroke={color} {...base} />
    </Svg>
  );
}

export function RiverIcon({ color, size = 22 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M3 9c3-2 6 2 9 0s6-2 9 0M3 15c3-2 6 2 9 0s6-2 9 0" stroke={color} {...base} />
    </Svg>
  );
}

export function SendIcon({ color, size = 18 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M5 12h13M13 6l6 6-6 6" stroke={color} {...base} strokeWidth={1.5} />
    </Svg>
  );
}
