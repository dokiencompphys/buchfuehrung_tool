import { router, Stack } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Image, StyleSheet, Text, TextInput, useWindowDimensions, View } from 'react-native';

import { ApiError, api } from '@/api/client';
import type { DayEntry, ExportFormat, LedgerMonth } from '@/api/types';
import { useDraft } from '@/draft/DraftProvider';
import { confirm } from '@/lib/confirm';
import { downloadFile } from '@/lib/download';
import { formatCents, formatEuro, parseInput, runningBalances, sumCents, toCents, toInput } from '@/lib/money';
import { useAsync } from '@/lib/useAsync';
import { useSettings } from '@/settings/SettingsProvider';
import { Body, Button, Card, Notice, Screen, Select, Title } from '@/ui/components';
import { colors, font, space, touch } from '@/ui/theme';

type Field = 'income' | 'expense';
type Row = { income: string; expense: string; reason: string };
type Rows = Record<string, Row>;

const FORMATS: ExportFormat[] = ['xlsx', 'ods', 'pdf', 'csv'];
const WIDE = 900; // ab dieser Breite steht der Grund in derselben Zeile

function rowsFrom(ledger: LedgerMonth): Rows {
  return Object.fromEntries(
    ledger.entries.map((e) => [
      e.day,
      { income: toInput(e.income), expense: toInput(e.expense), reason: e.reason ?? '' },
    ]),
  );
}

export default function Editor() {
  const { t, fmt, settings } = useSettings();
  const { draft, setDraft } = useDraft();
  const { width } = useWindowDimensions();
  const wide = width >= WIDE;

  const [ledger, setLedger] = useState<LedgerMonth | null>(draft?.ledger ?? null);
  const [rows, setRows] = useState<Rows>(() => (draft ? rowsFrom(draft.ledger) : {}));
  // Anfangssaldo: entweder Übertrag aus dem Vormonat oder manuell eingetragen
  const [openingManual, setOpeningManual] = useState(draft?.ledger.opening_balance != null);
  const [openingInput, setOpeningInput] = useState(toInput(draft?.ledger.opening_balance ?? null));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<LedgerMonth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPhoto, setShowPhoto] = useState(false);

  // Bundesland in den Einstellungen geändert → Ruhetage neu laden, Werte behalten
  const lastRegion = useRef(settings.region);
  useEffect(() => {
    if (!ledger || settings.region === lastRegion.current) return;
    lastRegion.current = settings.region;
    api.refreshDraft({ ...ledger, region: settings.region }).then(setLedger).catch(() => {});
  }, [settings.region, ledger]);

  // Liegt für den gewählten Monat schon eine (andere) Buchführung in der Ablage?
  // Der gerade geöffnete, abgelegte Monat selbst zählt nicht.
  const ownPeriod = draft?.editingExisting ? { year: draft.ledger.year, month: draft.ledger.month } : null;
  const isOwn = (y: number, m: number) => ownPeriod?.year === y && ownPeriod?.month === m;
  const period = ledger ? { year: ledger.year, month: ledger.month } : null;
  const existing = useAsync(
    () => (period && !isOwn(period.year, period.month) ? api.stored(period.year, period.month) : Promise.resolve(null)),
    [period?.year, period?.month, ownPeriod?.year, ownPeriod?.month],
  );

  const parsed = useMemo(() => {
    const result: Record<string, { income: string | null | undefined; expense: string | null | undefined }> = {};
    for (const [day, v] of Object.entries(rows)) {
      result[day] = { income: parseInput(v.income), expense: parseInput(v.expense) };
    }
    return result;
  }, [rows]);

  if (!ledger) {
    return (
      <Screen>
        <Body>{t.common.error} –</Body>
        <Button label={t.common.back} onPress={() => router.replace('/new')} />
      </Screen>
    );
  }

  const carry = ledger.carry_over;
  const manual = openingManual || carry === null; // ohne Vormonat immer selbst eintragen
  const openingParsed = manual ? parseInput(openingInput, { allowNegative: true }) : carry?.amount ?? null;
  const openingCents = toCents(openingParsed ?? null);
  const days = ledger.entries.map((e) => [parsed[e.day]?.income ?? null, parsed[e.day]?.expense ?? null] as [string | null, string | null]);
  const balances = runningBalances(openingCents, days);
  const income = sumCents(days.map((d) => d[0]));
  const expense = sumCents(days.map((d) => d[1]));
  const closing = openingCents + income - expense;

  const values = Object.values(parsed);
  const hasInvalid =
    values.some((v) => v.income === undefined || v.expense === undefined) || openingParsed === undefined;
  const hasValues = values.some((v) => v.income || v.expense) || Object.values(rows).some((r) => r.reason);
  const monthName = (year: number, month: number) => `${t.months[month - 1]} ${year}`;

  function setField(day: string, field: keyof Row, text: string) {
    setSaved(null);
    setRows((prev) => ({ ...prev, [day]: { ...prev[day], [field]: text } }));
  }

  function applyLedger(next: LedgerMonth) {
    setLedger(next);
    setRows(rowsFrom(next));
    setOpeningManual(next.opening_balance !== null);
    setOpeningInput(toInput(next.opening_balance));
  }

  async function changePeriod(year: number, month: number) {
    if (!ledger) return;
    if (hasValues) {
      const ok = await confirm(t.editor.changeMonthTitle, t.editor.changeMonthBody, t.common.ok, t.common.cancel);
      if (!ok) return;
    }
    const fresh = await api.blankDraft(year, month, ledger.region);
    applyLedger({ ...fresh, source: ledger.source, photo_id: ledger.photo_id });
    setSaved(null);
  }

  async function save() {
    if (!ledger) return;
    setError(null);
    if (hasInvalid) return setError(t.editor.invalid);
    const entries: DayEntry[] = ledger.entries.map((e) => ({
      ...e,
      income: parsed[e.day]?.income ?? null,
      expense: parsed[e.day]?.expense ?? null,
      reason: rows[e.day]?.reason.trim() ?? '',
    }));
    // Manuell, aber leer gelassen: beim ersten Monat = 0 (null), sonst ausdrücklich 0,00
    const opening_balance = manual ? (openingParsed ?? (carry ? '0.00' : null)) : null;
    const next: LedgerMonth = { ...ledger, entries, opening_balance };
    setSaving(true);
    try {
      let res;
      try {
        res = await api.saveMonth(next, { replace: isOwn(next.year, next.month) });
      } catch (e) {
        // 409: Für den Monat liegt schon eine andere Buchführung in der Ablage
        if (!(e instanceof ApiError && e.status === 409)) throw e;
        const ok = await confirm(
          t.editor.overwriteTitle,
          fmt(t.editor.overwrite, { month: monthName(next.year, next.month) }),
          t.editor.overwriteYes,
          t.common.cancel,
        );
        if (!ok) return;
        res = await api.saveMonth(next, { replace: true });
      }
      applyLedger(res.ledger);
      setSaved(res.ledger);
      setDraft({ ledger: res.ledger, hints: [], recognizedDays: null, editingExisting: true });
    } catch (e) {
      setError(e instanceof ApiError && e.status === 0 ? t.common.offline : `${t.common.error} ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  const years = Array.from({ length: 12 }, (_, i) => new Date().getFullYear() - 8 + i);
  const balanceStyle = (cents: number) => [styles.balance, cents < 0 && { color: colors.expense }];

  return (
    <Screen>
      <Stack.Screen options={{ title: draft?.editingExisting ? t.editor.titleEdit : t.editor.titleNew }} />

      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.m }}>
        <Select
          label={t.editor.month}
          value={ledger.month}
          options={t.months.map((label, i) => ({ value: i + 1, label }))}
          onChange={(m) => changePeriod(ledger.year, m)}
        />
        <Select
          label={t.editor.year}
          value={ledger.year}
          options={years.map((y) => ({ value: y, label: String(y) }))}
          onChange={(y) => changePeriod(y, ledger.month)}
        />
      </View>

      {existing.data?.totals && !saved ? (
        <Notice>
          <Body style={{ fontWeight: '700' }}>
            {fmt(t.editor.existsTitle, { month: monthName(existing.data.year, existing.data.month) })}
          </Body>
          <Body>
            {fmt(t.editor.existsBody, {
              income: formatEuro(existing.data.totals.income),
              expense: formatEuro(existing.data.totals.expense),
              closing: formatEuro(existing.data.totals.closing),
            })}
          </Body>
          <Body>{t.editor.existsHint}</Body>
        </Notice>
      ) : null}

      {/* Anfangssaldo */}
      <Card>
        <Text style={styles.cardTitle}>{t.editor.opening}</Text>
        {manual ? (
          <>
            {carry === null ? <Body muted>{t.editor.firstOpening}</Body> : <Body muted>{t.editor.openingHelp}</Body>}
            <TextInput
              value={openingInput}
              onChangeText={(text) => {
                setSaved(null);
                setOpeningInput(text);
              }}
              keyboardType="numbers-and-punctuation"
              placeholder="0,00"
              placeholderTextColor="#9A9A9A"
              accessibilityLabel={t.editor.opening}
              style={[styles.input, styles.openingInput, openingParsed === undefined && styles.invalid]}
            />
            {carry ? (
              <Button
                label={fmt(t.editor.useCarryOver, { amount: formatEuro(carry.amount) })}
                variant="secondary"
                style={{ alignSelf: 'flex-start' }}
                onPress={() => {
                  setSaved(null);
                  setOpeningManual(false);
                }}
              />
            ) : null}
          </>
        ) : (
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: space.m }}>
            <View style={{ flexGrow: 1 }}>
              <Text style={[styles.openingValue, openingCents < 0 && { color: colors.expense }]}>
                {formatEuro(openingCents)}
              </Text>
              <Body muted>{fmt(t.editor.carryOver, { month: monthName(carry!.year, carry!.month) })}</Body>
            </View>
            <Button
              label={`✏️ ${t.editor.changeOpening}`}
              variant="secondary"
              onPress={() => {
                setOpeningManual(true);
                setOpeningInput(toInput(carry!.amount));
              }}
            />
          </View>
        )}
      </Card>

      {draft?.recognizedDays != null ? (
        <Notice>
          <Body style={{ fontWeight: '700' }}>{fmt(t.editor.recognized, { n: draft.recognizedDays })}</Body>
          {draft.hints.map((h, i) => (
            <Body key={i}>• {fmt((t.hints as Record<string, string>)[h.code] ?? h.code, formatHintParams(h.params))}</Body>
          ))}
          {ledger.photo_id ? (
            <Button
              label={t.editor.showPhoto}
              variant="secondary"
              onPress={() => setShowPhoto((s) => !s)}
              style={{ alignSelf: 'flex-start' }}
            />
          ) : null}
        </Notice>
      ) : null}

      {showPhoto && ledger.photo_id ? (
        <Image
          source={{ uri: api.photoUrl(ledger.photo_id) }}
          style={{ width: '100%', height: 600, borderRadius: 12 }}
          resizeMode="contain"
          accessibilityLabel={t.editor.showPhoto}
        />
      ) : null}

      {/* Tabelle: Datum | Einnahmen | Ausgaben | Saldo | Grund */}
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        <View style={[styles.row, styles.headRow]}>
          <Text style={[styles.head, styles.dateCol]}>{t.editor.date}</Text>
          <Text style={[styles.head, styles.numCol, { color: colors.income }]}>{t.editor.income}</Text>
          <Text style={[styles.head, styles.numCol, { color: colors.expense }]}>{t.editor.expense}</Text>
          <Text style={[styles.head, styles.numCol]}>{t.editor.balance}</Text>
          {wide ? <Text style={[styles.head, styles.reasonCol]}>{t.editor.reason}</Text> : null}
        </View>
        {ledger.entries.map((e, i) => {
          const date = new Date(`${e.day}T12:00:00`);
          const weekday = t.weekdays[(date.getDay() + 6) % 7];
          const dayLabel = `${weekday} ${date.getDate()}.`;
          const closedLabel = e.closed ? (e.closed.kind === 'sunday' ? t.editor.sunday : e.closed.name) : null;
          const p = parsed[e.day];
          const reasonInput = (
            <TextInput
              value={rows[e.day]?.reason ?? ''}
              onChangeText={(text) => setField(e.day, 'reason', text)}
              placeholder={t.editor.reasonPlaceholder}
              placeholderTextColor="#9A9A9A"
              accessibilityLabel={`${t.editor.reason} ${dayLabel}`}
              style={[styles.input, styles.reasonInput, wide && styles.reasonCol, e.closed && styles.closedInput]}
            />
          );
          return (
            <View key={e.day} style={[styles.dayBlock, e.closed && styles.closedRow]}>
              <View style={styles.row}>
                <View style={styles.dateCol}>
                  <Text style={[styles.dateText, e.closed && { color: colors.closedText }]}>
                    {weekday} {String(date.getDate()).padStart(2, '0')}.{String(ledger.month).padStart(2, '0')}.
                  </Text>
                  {closedLabel ? <Text style={styles.closedLabel}>{closedLabel}</Text> : null}
                </View>
                {(['income', 'expense'] as Field[]).map((field) => (
                  <TextInput
                    key={field}
                    value={rows[e.day]?.[field] ?? ''}
                    onChangeText={(text) => setField(e.day, field, text)}
                    keyboardType="decimal-pad"
                    placeholder={e.closed ? '' : '0,00'}
                    placeholderTextColor="#9A9A9A"
                    accessibilityLabel={`${field === 'income' ? t.editor.income : t.editor.expense} ${dayLabel}`}
                    style={[
                      styles.input,
                      styles.numCol,
                      e.closed && styles.closedInput,
                      p?.[field] === undefined && styles.invalid,
                    ]}
                  />
                ))}
                <Text
                  style={[styles.numCol, ...balanceStyle(balances[i])]}
                  accessibilityLabel={`${t.editor.balance} ${dayLabel}: ${formatEuro(balances[i])}`}
                >
                  {formatCents(balances[i])}
                </Text>
                {wide ? reasonInput : null}
              </View>
              {wide ? null : <View style={styles.reasonLine}>{reasonInput}</View>}
            </View>
          );
        })}
        <View style={[styles.row, styles.totalRow]}>
          <Text style={[styles.totalText, styles.dateCol]}>{t.editor.total}</Text>
          <Text style={[styles.totalText, styles.numCol, { color: colors.income }]}>{formatCents(income)}</Text>
          <Text style={[styles.totalText, styles.numCol, { color: colors.expense }]}>{formatCents(expense)}</Text>
          <Text style={[styles.totalText, styles.numCol, closing < 0 && { color: colors.expense }]}>
            {formatCents(closing)}
          </Text>
          {wide ? <View style={styles.reasonCol} /> : null}
        </View>
        <View style={[styles.row, styles.totalRow]}>
          <Text style={[styles.summaryLabel, { flex: 1 }]}>{t.editor.closing}</Text>
          <Text style={[styles.totalText, closing < 0 && { color: colors.expense }]}>{formatEuro(closing)}</Text>
        </View>
        <View style={[styles.row, styles.totalRow]}>
          <Text style={[styles.summaryLabel, { flex: 1 }]}>{t.editor.result}</Text>
          <Text style={styles.summaryValue}>{formatEuro(income - expense)}</Text>
        </View>
      </Card>

      {error ? (
        <Notice tone="error">
          <Body>{error}</Body>
        </Notice>
      ) : null}

      {saved ? (
        <Card>
          <Notice tone="ok">
            <Body style={{ fontWeight: '700' }}>✓ {t.editor.created}</Body>
          </Notice>
          <Title>{t.editor.download}</Title>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.s }}>
            {FORMATS.map((f) => (
              <Button
                key={f}
                label={`⬇ ${t.formats[f]}`}
                style={{ flexGrow: 1, flexBasis: 240 }}
                onPress={() =>
                  downloadFile(
                    api.exportUrl(saved.year, saved.month, f, settings.lang),
                    `buchfuehrung_${saved.year}-${String(saved.month).padStart(2, '0')}.${f}`,
                  ).catch((e) => setError(`${t.common.error} ${(e as Error).message}`))
                }
              />
            ))}
          </View>
          <Button label={`🗂️ ${t.archive.title}`} variant="secondary" onPress={() => router.push('/archive')} />
        </Card>
      ) : (
        <Button
          label={saving ? t.editor.saving : draft?.editingExisting ? t.editor.save : t.editor.create}
          onPress={save}
          disabled={saving}
          style={{ minHeight: 80 }}
        />
      )}
    </Screen>
  );
}

function formatHintParams(params: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = { ...params };
  for (const key of ['photo', 'computed']) {
    if (params[key]) out[key] = toInput(params[key]);
  }
  return out;
}

const styles = StyleSheet.create({
  cardTitle: { fontSize: font.large, fontWeight: '800', color: colors.text },
  openingValue: { fontSize: font.huge, fontWeight: '800', color: colors.text },
  openingInput: { maxWidth: 320, fontSize: font.large, textAlign: 'right' },
  dayBlock: { borderBottomWidth: 1, borderBottomColor: '#E2E2E2' },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.s,
    paddingHorizontal: space.s,
    paddingVertical: space.xs,
  },
  reasonLine: { paddingHorizontal: space.s, paddingBottom: space.s },
  headRow: { backgroundColor: '#EDEBE6' },
  head: { fontSize: font.body, fontWeight: '700', color: colors.text },
  dateCol: { flex: 1.1 },
  numCol: { flex: 1, textAlign: 'right' },
  reasonCol: { flex: 2 },
  dateText: { fontSize: font.body, fontWeight: '600', color: colors.text },
  closedRow: { backgroundColor: colors.closedBg },
  closedLabel: { fontSize: font.small - 2, color: colors.closedText },
  balance: { fontSize: font.body, fontWeight: '700', color: colors.text, paddingRight: space.xs },
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
  reasonInput: { textAlign: 'left' },
  closedInput: { backgroundColor: '#ECECEC', borderColor: '#B0B0B0' },
  invalid: { borderColor: colors.danger, borderWidth: 3, backgroundColor: '#FBE9E7' },
  totalRow: { backgroundColor: '#EDEBE6', paddingVertical: space.s, borderTopWidth: 1, borderTopColor: '#D0CEC8' },
  totalText: { fontSize: font.large, fontWeight: '800', color: colors.text },
  summaryLabel: { fontSize: font.body, fontWeight: '700', color: colors.text },
  summaryValue: { fontSize: font.large, fontWeight: '700', color: colors.text },
});
