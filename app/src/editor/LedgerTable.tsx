// Monatstabelle: Datum | Einnahmen | Ausgaben | Saldo | Grund.
// Drei Anordnungen je nach verfügbarer Breite, damit Datum und Saldo nie gequetscht werden:
//   breit  (≥ 980 px): alles in einer Zeile
//   mittel (≥ 640 px): Zahlen in einer Zeile, Grund darunter
//   schmal (Handy):    pro Tag ein Block – Datum + Saldo, darunter Einnahme/Ausgabe, darunter Grund
import { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import type { DayEntry } from '@/api/types';
import { formatCents, formatEuro } from '@/lib/money';
import { useSettings } from '@/settings/SettingsProvider';
import { colors, font, space, touch } from '@/ui/theme';

export type Field = 'income' | 'expense';
export type Row = { income: string; expense: string; reason: string };

type Layout = 'wide' | 'medium' | 'narrow';

const DATE_W = 150;
const BALANCE_W = 170;
// Text in Eingabefeldern beginnt nach Rand + Innenabstand; Überschriften und Saldo
// bekommen denselben Abstand, damit alle Zahlen rechts bündig untereinander stehen.
const INSET = space.s + 2;

export function LedgerTable({
  entries,
  month,
  rows,
  isInvalid,
  balances,
  flaggedDays,
  flaggedCells,
  totals,
  onChange,
}: {
  entries: DayEntry[];
  month: number;
  rows: Record<string, Row>;
  isInvalid: (day: string, field: Field) => boolean;
  balances: number[];
  flaggedDays: Set<number>;
  flaggedCells: Set<string>; // "Tag:Feld"
  totals: { income: number; expense: number; closing: number };
  onChange: (day: string, field: keyof Row, text: string) => void;
}) {
  const { t } = useSettings();
  const [width, setWidth] = useState(0);
  const layout: Layout = width >= 980 ? 'wide' : width >= 640 ? 'medium' : 'narrow';
  const mm = String(month).padStart(2, '0');

  return (
    <View onLayout={(e) => setWidth(e.nativeEvent.layout.width)} style={styles.table}>
      {layout !== 'narrow' ? (
        <View style={[styles.line, styles.head]}>
          <Text style={[styles.headText, styles.dateCol]}>{t.editor.date}</Text>
          <Text style={[styles.headText, styles.numCol, styles.num, { color: colors.income }]}>{t.editor.income}</Text>
          <Text style={[styles.headText, styles.numCol, styles.num, { color: colors.expense }]}>
            {t.editor.expense}
          </Text>
          <Text style={[styles.headText, styles.balanceCol, styles.num]}>{t.editor.balance}</Text>
          {layout === 'wide' ? <Text style={[styles.headText, styles.reasonCol]}>{t.editor.reason}</Text> : null}
        </View>
      ) : null}

      {entries.map((e, i) => {
        const date = new Date(`${e.day}T12:00:00`);
        const dayNo = date.getDate();
        const weekday = t.weekdays[(date.getDay() + 6) % 7];
        const dateLabel = `${weekday} ${String(dayNo).padStart(2, '0')}.${mm}.`;
        const closedLabel = e.closed ? (e.closed.kind === 'sunday' ? t.editor.sunday : e.closed.name) : null;
        const flagged = flaggedDays.has(dayNo);

        const amountInput = (field: Field) => (
          <TextInput
            value={rows[e.day]?.[field] ?? ''}
            onChangeText={(text) => onChange(e.day, field, text)}
            keyboardType="decimal-pad"
            placeholder={e.closed ? '' : '0,00'}
            placeholderTextColor="#9A9A9A"
            accessibilityLabel={`${field === 'income' ? t.editor.income : t.editor.expense} ${dateLabel}`}
            style={[
              styles.input,
              styles.numInput,
              layout === 'narrow' ? styles.grow : styles.numCol,
              e.closed && styles.closedInput,
              flaggedCells.has(`${dayNo}:${field}`) && styles.flaggedInput,
              isInvalid(e.day, field) && styles.invalid,
            ]}
          />
        );
        const reasonInput = (
          <TextInput
            value={rows[e.day]?.reason ?? ''}
            onChangeText={(text) => onChange(e.day, 'reason', text)}
            placeholder={t.editor.reasonPlaceholder}
            placeholderTextColor="#9A9A9A"
            accessibilityLabel={`${t.editor.reason} ${dateLabel}`}
            style={[styles.input, layout === 'wide' ? styles.reasonCol : styles.grow, e.closed && styles.closedInput]}
          />
        );
        const date_ = (
          <View style={layout === 'narrow' ? styles.grow : styles.dateCol}>
            <Text style={[styles.dateText, e.closed && { color: colors.closedText }]}>{dateLabel}</Text>
            {closedLabel ? <Text style={styles.closedLabel}>{closedLabel}</Text> : null}
          </View>
        );
        const balance = (
          <View style={styles.balanceCol}>
            {layout === 'narrow' ? <Text style={[styles.smallLabel, styles.num]}>{t.editor.balance}</Text> : null}
            <Text
              style={[styles.balance, balances[i] < 0 && { color: colors.expense }]}
              accessibilityLabel={`${t.editor.balance} ${dateLabel}: ${formatEuro(balances[i])}`}
            >
              {formatCents(balances[i])}
            </Text>
          </View>
        );

        return (
          <View key={e.day} style={[styles.day, e.closed && styles.closedDay, flagged && styles.flaggedDay]}>
            {layout === 'narrow' ? (
              <>
                <View style={styles.line}>
                  {date_}
                  {balance}
                </View>
                <View style={styles.line}>
                  <View style={styles.grow}>
                    <Text style={[styles.smallLabel, { color: colors.income }]}>{t.editor.income}</Text>
                    {amountInput('income')}
                  </View>
                  <View style={styles.grow}>
                    <Text style={[styles.smallLabel, { color: colors.expense }]}>{t.editor.expense}</Text>
                    {amountInput('expense')}
                  </View>
                </View>
                <View style={styles.line}>{reasonInput}</View>
              </>
            ) : (
              <>
                <View style={styles.line}>
                  {date_}
                  {amountInput('income')}
                  {amountInput('expense')}
                  {balance}
                  {layout === 'wide' ? reasonInput : null}
                </View>
                {layout === 'medium' ? <View style={[styles.line, { paddingLeft: DATE_W + 2 * space.s }]}>{reasonInput}</View> : null}
              </>
            )}
          </View>
        );
      })}

      {layout !== 'narrow' ? (
        <View style={[styles.line, styles.total]}>
          <Text style={[styles.totalText, styles.dateCol]}>{t.editor.total}</Text>
          <Text style={[styles.totalText, styles.numCol, styles.num, { color: colors.income }]}>
            {formatCents(totals.income)}
          </Text>
          <Text style={[styles.totalText, styles.numCol, styles.num, { color: colors.expense }]}>
            {formatCents(totals.expense)}
          </Text>
          <Text style={[styles.totalText, styles.balanceCol, styles.num, totals.closing < 0 && { color: colors.expense }]}>
            {formatCents(totals.closing)}
          </Text>
          {layout === 'wide' ? <View style={styles.reasonCol} /> : null}
        </View>
      ) : (
        <View style={styles.total}>
          <SumLine label={`${t.editor.total} ${t.editor.income}`} cents={totals.income} color={colors.income} />
          <SumLine label={`${t.editor.total} ${t.editor.expense}`} cents={totals.expense} color={colors.expense} />
        </View>
      )}
    </View>
  );
}

function SumLine({ label, cents, color }: { label: string; cents: number; color: string }) {
  return (
    <View style={styles.line}>
      <Text style={[styles.summaryLabel, styles.grow]}>{label}</Text>
      <Text style={[styles.totalText, { color }]}>{formatCents(cents)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  table: { backgroundColor: colors.card, borderRadius: 16, overflow: 'hidden' },
  line: { flexDirection: 'row', alignItems: 'center', gap: space.s, paddingHorizontal: space.s, paddingVertical: space.xs },
  head: { backgroundColor: '#EDEBE6', paddingVertical: space.s, borderLeftWidth: 8, borderLeftColor: 'transparent' },
  headText: { fontSize: font.body, fontWeight: '700', color: colors.text },
  dateCol: { width: DATE_W },
  numCol: { flex: 1, minWidth: 0 },
  balanceCol: { width: BALANCE_W, alignItems: 'flex-end' },
  reasonCol: { flex: 1.5, minWidth: 0 },
  grow: { flex: 1, minWidth: 0 },
  num: { textAlign: 'right', paddingRight: INSET },
  numInput: { textAlign: 'right' },
  // Linker Balken immer 8 px breit (sonst unsichtbar), damit markierte Zeilen nicht verrutschen
  day: {
    borderBottomWidth: 1,
    borderBottomColor: '#E2E2E2',
    borderLeftWidth: 8,
    borderLeftColor: 'transparent',
    paddingVertical: space.xs,
  },
  closedDay: { backgroundColor: colors.closedBg },
  flaggedDay: { backgroundColor: colors.warnBg, borderLeftColor: colors.focus },
  dateText: { fontSize: font.body, fontWeight: '700', color: colors.text },
  closedLabel: { fontSize: font.small - 2, color: colors.closedText },
  smallLabel: { fontSize: font.small - 2, fontWeight: '600', color: colors.muted, marginBottom: 2 },
  balance: { fontSize: font.body, fontWeight: '700', color: colors.text, paddingRight: INSET },
  input: {
    minHeight: touch.min - 6,
    borderWidth: 2,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: space.s,
    fontSize: font.body,
    backgroundColor: colors.card,
    color: colors.text,
  },
  closedInput: { backgroundColor: '#ECECEC', borderColor: '#B0B0B0' },
  flaggedInput: { borderColor: colors.focus, borderWidth: 4 },
  invalid: { borderColor: colors.danger, borderWidth: 3, backgroundColor: '#FBE9E7' },
  total: {
    backgroundColor: '#EDEBE6',
    paddingVertical: space.s,
    borderTopWidth: 1,
    borderTopColor: '#D0CEC8',
    borderLeftWidth: 8,
    borderLeftColor: 'transparent',
  },
  totalText: { fontSize: font.large, fontWeight: '800', color: colors.text },
  summaryLabel: { fontSize: font.body, fontWeight: '700', color: colors.text },
});
