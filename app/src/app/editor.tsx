import { router, Stack } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Image, StyleSheet, Text, TextInput, View } from 'react-native';

import { ApiError, api } from '@/api/client';
import type { DayEntry, ExportFormat, LedgerMonth, PhotoChecks } from '@/api/types';
import { useDraft } from '@/draft/DraftProvider';
import { CheckList } from '@/editor/CheckList';
import { LedgerTable, type Field, type Row } from '@/editor/LedgerTable';
import { daysOf, findIssues, type PhotoFacts } from '@/lib/checks';
import { confirm } from '@/lib/confirm';
import { downloadFile } from '@/lib/download';
import { formatEuro, parseInput, runningBalances, sumCents, toCents, toInput } from '@/lib/money';
import { useAsync } from '@/lib/useAsync';
import { useSettings } from '@/settings/SettingsProvider';
import { Body, Button, Card, Notice, Screen, Select, Title } from '@/ui/components';
import { colors, font, space, touch } from '@/ui/theme';

type Rows = Record<string, Row>;

const FORMATS: ExportFormat[] = ['xlsx', 'ods', 'pdf', 'csv'];

function rowsFrom(ledger: LedgerMonth): Rows {
  return Object.fromEntries(
    ledger.entries.map((e) => [
      e.day,
      { income: toInput(e.income), expense: toInput(e.expense), reason: e.reason ?? '' },
    ]),
  );
}

const dayOfMonth = (isoDay: string) => Number(isoDay.slice(8, 10));

function factsFrom(checks: PhotoChecks): PhotoFacts {
  const cents = (v: string | null) => (v === null ? null : toCents(v));
  return {
    opening: cents(checks.opening),
    balances: Object.fromEntries(Object.entries(checks.balances).map(([d, v]) => [Number(d), toCents(v)])),
    totalIncome: cents(checks.total_income),
    totalExpense: cents(checks.total_expense),
    closing: cents(checks.closing),
    suspects: checks.suspects.map((s) => ({ ...s, read: s.read.map(toCents), struck: s.struck.map(toCents) })),
  };
}

export default function Editor() {
  const { t, fmt, settings } = useSettings();
  const { draft, setDraft } = useDraft();

  const [ledger, setLedger] = useState<LedgerMonth | null>(draft?.ledger ?? null);
  const [rows, setRows] = useState<Rows>(() => (draft ? rowsFrom(draft.ledger) : {}));
  // Anfangssaldo: immer der Übertrag aus dem Vormonat; nur im ersten Monat selbst eingetragen
  const [openingInput, setOpeningInput] = useState(toInput(draft?.ledger.opening_balance ?? null));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<LedgerMonth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPhoto, setShowPhoto] = useState(false);
  // Prüfung gegen das Foto: bestätigte Meldungen und bereits bearbeitete Zellen
  const [facts, setFacts] = useState<PhotoFacts | null>(() => (draft?.checks ? factsFrom(draft.checks) : null));
  const [confirmed, setConfirmed] = useState<Set<string>>(new Set());
  const [touched, setTouched] = useState<Set<string>>(new Set());

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
  const manual = carry === null; // nur der erste Monat hat keinen Übertrag (ADR 0004)
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

  // Live-Prüfung gegen das Foto
  const cellCents = (day: string, field: Field) => {
    const v = parsed[day]?.[field];
    return v ? toCents(v) : null; // leer oder ungültig → nichts
  };
  const issues = facts
    ? findIssues(
        facts,
        ledger.entries.map((e) => ({
          day: dayOfMonth(e.day),
          income: cellCents(e.day, 'income') ?? 0,
          expense: cellCents(e.day, 'expense') ?? 0,
        })),
        openingCents,
      ).filter(
        (i) => !confirmed.has(i.id) && !(i.kind === 'suspect' && touched.has(`${i.day}:${i.field}`)),
      )
    : [];
  const flaggedDays = new Set(issues.flatMap(daysOf));
  const flaggedCells = new Set(issues.flatMap((i) => (i.kind === 'suspect' ? [`${i.day}:${i.field}`] : [])));
  const isoOf = (day: number) => ledger.entries.find((e) => dayOfMonth(e.day) === day)?.day ?? '';

  function setField(day: string, field: keyof Row, text: string) {
    setSaved(null);
    setRows((prev) => ({ ...prev, [day]: { ...prev[day], [field]: text } }));
    if (field !== 'reason') setTouched((prev) => new Set(prev).add(`${dayOfMonth(day)}:${field}`));
  }

  function applyLedger(next: LedgerMonth) {
    setLedger(next);
    setRows(rowsFrom(next));
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
    setFacts(null); // Werte geleert → nichts mehr mit dem Foto zu vergleichen
    setSaved(null);
  }

  async function save() {
    if (!ledger) return;
    setError(null);
    if (hasInvalid) return setError(t.editor.invalid);
    if (issues.length > 0) {
      const ok = await confirm(
        t.checks.saveTitle,
        fmt(t.checks.saveBody, { n: issues.length }),
        t.checks.saveAnyway,
        t.common.cancel,
      );
      if (!ok) return;
    }
    const entries: DayEntry[] = ledger.entries.map((e) => ({
      ...e,
      income: parsed[e.day]?.income ?? null,
      expense: parsed[e.day]?.expense ?? null,
      reason: rows[e.day]?.reason.trim() ?? '',
    }));
    const opening_balance = manual ? (openingParsed ?? null) : null; // leer = 0
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
      setDraft({ ledger: res.ledger, hints: [], recognizedDays: null, checks: null, editingExisting: true });
    } catch (e) {
      setError(e instanceof ApiError && e.status === 0 ? t.common.offline : `${t.common.error} ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  const years = Array.from({ length: 12 }, (_, i) => new Date().getFullYear() - 8 + i);

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
            <Body muted>{t.editor.firstOpening}</Body>
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
              style={[styles.openingInput, openingParsed === undefined && styles.invalid]}
            />
          </>
        ) : (
          <View>
            <Text style={[styles.openingValue, openingCents < 0 && { color: colors.expense }]}>
              {formatEuro(openingCents)}
            </Text>
            <Body muted>{fmt(t.editor.carryOver, { month: monthName(carry!.year, carry!.month) })}</Body>
          </View>
        )}
      </Card>

      {draft?.recognizedDays != null ? (
        <Notice>
          <Body style={{ fontWeight: '700' }}>{fmt(t.editor.recognized, { n: draft.recognizedDays })}</Body>
          {draft.hints.map((h, i) => (
            <Body key={i}>• {fmt((t.hints as Record<string, string>)[h.code] ?? h.code, h.params)}</Body>
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

      {facts && !saved ? (
        <CheckList
          issues={issues}
          month={ledger.month}
          firstMonth={manual}
          carryMonth={carry ? monthName(carry.year, carry.month) : null}
          current={(day, field) => cellCents(isoOf(day), field)}
          confirmedCount={confirmed.size}
          onConfirm={(id) => setConfirmed((prev) => new Set(prev).add(id))}
        />
      ) : null}

      <LedgerTable
        entries={ledger.entries}
        month={ledger.month}
        rows={rows}
        isInvalid={(day, field) => parsed[day]?.[field] === undefined}
        balances={balances}
        flaggedDays={flaggedDays}
        flaggedCells={flaggedCells}
        totals={{ income, expense, closing }}
        onChange={setField}
      />

      <Card>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>{t.editor.closing}</Text>
          <Text style={[styles.summaryBig, closing < 0 && { color: colors.expense }]}>{formatEuro(closing)}</Text>
        </View>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>{t.editor.result}</Text>
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

const styles = StyleSheet.create({
  cardTitle: { fontSize: font.large, fontWeight: '800', color: colors.text },
  openingValue: { fontSize: font.huge, fontWeight: '800', color: colors.text },
  openingInput: {
    maxWidth: 320,
    minHeight: touch.min,
    borderWidth: 2,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: space.s,
    fontSize: font.large,
    textAlign: 'right',
    backgroundColor: colors.card,
    color: colors.text,
  },
  invalid: { borderColor: colors.danger, borderWidth: 3, backgroundColor: '#FBE9E7' },
  summaryRow: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'baseline', justifyContent: 'space-between', gap: space.s },
  summaryLabel: { fontSize: font.body, fontWeight: '700', color: colors.text },
  summaryBig: { fontSize: font.huge, fontWeight: '800', color: colors.text },
  summaryValue: { fontSize: font.large, fontWeight: '700', color: colors.text },
});
