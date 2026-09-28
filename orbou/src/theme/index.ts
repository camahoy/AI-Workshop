// ORBOU design tokens — straight from the living brief.

export const colors = {
  parch: '#F0E8DC',
  parchD: '#E6D8C6',
  surface: 'rgba(255,255,255,0.60)',
  surfaceS: 'rgba(255,255,255,0.90)',
  border: 'rgba(42,26,14,0.09)',
  borderM: 'rgba(42,26,14,0.16)',
  ink: '#2A1A0E',
  inkM: '#5A3E28',
  muted: 'rgba(42,26,14,0.42)',
  faint: 'rgba(42,26,14,0.05)',
  terra: '#B5542E',
  sage: '#607D5A',
  gold: '#B8893A',
  goldDeep: '#8A6020',
  violet: '#6E4E88',
  sky: '#4A6E8A',
  rose: '#8A4860',
  stone: '#A89880',
  buttonInk: '#1A1008',
} as const;

export type Domain = 'foundation' | 'mind' | 'fitness' | 'appearance' | 'nutrition' | 'career';

export const domainColor: Record<Domain, string> = {
  foundation: colors.gold,
  mind: colors.violet,
  fitness: colors.terra,
  appearance: colors.rose,
  nutrition: colors.sage,
  career: colors.sky,
};

export const domainLabel: Record<Domain, string> = {
  foundation: 'Foundation',
  mind: 'Mind',
  fitness: 'Fitness',
  appearance: 'Appearance',
  nutrition: 'Nutrition',
  career: 'Career',
};

/** Hex → rgba with alpha, for the tinted tag/card backgrounds the brief uses everywhere. */
export function tint(hex: string, alpha: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
}

// Font family names as registered in the root layout.
export const fonts = {
  serifLight: 'CormorantGaramond_300Light',
  serif: 'CormorantGaramond_400Regular',
  serifMedium: 'CormorantGaramond_500Medium',
  serifItalic: 'CormorantGaramond_400Regular_Italic',
  serifLightItalic: 'CormorantGaramond_300Light_Italic',
  sansXLight: 'Jost_200ExtraLight',
  sansLight: 'Jost_300Light',
  sans: 'Jost_400Regular',
  sansMedium: 'Jost_500Medium',
} as const;

export const radius = { card: 16, compact: 12, pill: 20, button: 14 } as const;

export const shadow = {
  card: {
    shadowColor: colors.terra,
    shadowOpacity: 0.06,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 4 },
  },
} as const;
