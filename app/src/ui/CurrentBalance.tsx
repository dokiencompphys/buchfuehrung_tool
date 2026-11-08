import { Text, View } from 'react-native';

import { api } from '@/api/client';
import { formatEuro, toCents } from '@/lib/money';
import { useAsync } from '@/lib/useAsync';
import { useSettings } from '@/settings/SettingsProvider';

import { Body } from './components';
import { colors, font, space } from './theme';

/** Aktueller Saldo (Endsaldo des neuesten Monats). Lädt bei jedem Öffnen des Bildschirms neu. */
export function CurrentBalance() {
  const { t, fmt } = useSettings();
  const balance = useAsync(() => api.balance(), []);

  if (balance.error || balance.loading) return null;
  const b = balance.data;

  return (
    <View
      accessibilityRole="summary"
      style={{
        backgroundColor: colors.card,
        borderRadius: 16,
        borderLeftWidth: 10,
        borderLeftColor: b && toCents(b.amount) < 0 ? colors.expense : colors.primary,
        padding: space.m,
        flexDirection: 'row',
        flexWrap: 'wrap',
        alignItems: 'baseline',
        justifyContent: 'space-between',
        gap: space.s,
      }}
    >
      <Text style={{ fontSize: font.large, fontWeight: '700', color: colors.text }}>💶 {t.balance.current}</Text>
      {b ? (
        <View style={{ alignItems: 'flex-end' }}>
          <Text
            style={{
              fontSize: font.huge,
              fontWeight: '800',
              color: toCents(b.amount) < 0 ? colors.expense : colors.text,
            }}
          >
            {formatEuro(b.amount)}
          </Text>
          <Body muted>{fmt(t.balance.asOf, { month: `${t.months[b.month - 1]} ${b.year}` })}</Body>
        </View>
      ) : (
        <Body muted>{t.balance.none}</Body>
      )}
    </View>
  );
}
