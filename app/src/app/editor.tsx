import { router, Stack } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Image, StyleSheet, Text, TextInput, View } from 'react-native';

import { ApiError, api } from '@/api/client';
import type { DayEntry, ExportFormat, LedgerMonth } from '@/api/types';
import { useDraft } from '@/draft/DraftProvider';
import { confirm } from '@/lib/confirm';
import { downloadFile } from '@/lib/download';
import { formatCents, parseInput, sumCents, toInput } from '@/lib/money';
import { useSettings } from '@/settings/SettingsProvider';
import { Body, Button, Card, Notice, Screen, Select, Title } from '@/ui/components';
import { colors, font, space, touch } from '@/ui/theme';

type Field = 'income' | 'expense';
type Inputs = Record<string, { income: string; expense: string }>;

const FORMATS: ExportFormat[] = ['xlsx', 'ods', 'pdf', 'csv'];

function inputsFrom(ledger: LedgerMonth): Inputs {
  return Object.fromEntries(
    ledger.entries.map((e) => [e.day, { income: toInput(e.income), expense: toInput(e.expense) }]),
  );
}

export default function Editor() {
  const { t, fmt, settings } = useSettings();
  const { draft, setDraft } = useDraft();
  const [ledger, setLedger] = useState<LedgerMonth | null>(draft?.ledger ?? null);
  const [inputs, setInputs] = useState<Inputs>(() => (draft ? inputsFrom(draft.ledger) : {}));
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

  const parsed = useMemo(() => {
    const result: Record<string, { income: string | null | undefined; expense: string | null | undefined }> = {};
    for (const [day, v] of Object.entries(inputs)) {
      result[day] = { income: parseInput(v.income), expense: parseInput(v.expense) };
    }
    return result;
  }, [inputs]);

  if (!ledger) {
    return (
      <Screen>
        <Body>{t.common.error} –</Body>
        <Button label={t.common.back} onPress={() => router.replace('/new')} />
      </Screen>
    );
  }

  const values = Object.values(parsed);
  const hasInvalid = values.some((v) => v.income === undefined || v.expense === undefined);
  const income = sumCents(values.map((v) => v.income ?? null));
  const expense = sumCents(values.map((v) => v.expense ?? null));
  const hasValues = values.some((v) => v.income || v.expense);

  function setField(day: string, field: Field, text: string) {
    setSaved(null);
    setInputs((prev) => ({ ...prev, [day]: { ...prev[day], [field]: text } }));
  }

  async function changePeriod(year: number, month: number) {
    if (!ledger) return;
    if (hasValues) {
      const ok = await confirm(t.editor.changeMonthTitle, t.editor.changeMonthBody, t.common.ok, t.common.cancel);
      if (!ok) return;
    }
    const fresh = await api.blankDraft(year, month, ledger.region);
    setLedger({ ...fresh, source: ledger.source, photo_id: ledger.photo_id });
    setInputs(inputsFrom(fresh));
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
    }));
    const next = { ...ledger, entries };
    setSaving(true);
    try {
      if (!draft?.editingExisting && (await api.exists(next.year, next.month))) {
        const ok = await confirm(t.editor.create, t.editor.overwrite, t.editor.overwriteYes, t.common.cancel);
        if (!ok) return;
      }
      const res = await api.saveMonth(next);
      setLedger(res.ledger);
      setSaved(res.ledger);
      setDraft({ ledger: res.ledger, hints: [], recognizedDays: null, editingExisting: true });
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

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        <View style={[styles.row, styles.headRow]}>
          <Text style={[styles.head, styles.dateCol]}>{t.editor.date}</Text>
          <Text style={[styles.head, styles.numCol, { color: colors.income }]}>{t.editor.income}</Text>
          <Text style={[styles.head, styles.numCol, { color: colors.expense }]}>{t.editor.expense}</Text>
        </View>
        {ledger.entries.map((e) => {
          const date = new Date(`${e.day}T12:00:00`);
          const weekday = t.weekdays[(date.getDay() + 6) % 7];
          const closedLabel = e.closed ? (e.closed.kind === 'sunday' ? t.editor.sunday : e.closed.name) : null;
          const p = parsed[e.day];
          return (
            <View key={e.day} style={[styles.row, e.closed && styles.closedRow]}>
              <View style={styles.dateCol}>
                <Text style={[styles.dateText, e.closed && { color: colors.closedText }]}>
                  {weekday} {String(date.getDate()).padStart(2, '0')}.{String(ledger.month).padStart(2, '0')}.
                </Text>
                {closedLabel ? <Text style={styles.closedLabel}>{closedLabel}</Text> : null}
              </View>
              {(['income', 'expense'] as Field[]).map((field) => (
                <TextInput
                  key={field}
                  value={inputs[e.day]?.[field] ?? ''}
                  onChangeText={(text) => setField(e.day, field, text)}
                  keyboardType="decimal-pad"
                  placeholder={e.closed ? '' : '0,00'}
                  placeholderTextColor="#9A9A9A"
                  accessibilityLabel={`${field === 'income' ? t.editor.income : t.editor.expense} ${weekday} ${date.getDate()}.`}
                  style={[
                    styles.input,
                    styles.numCol,
                    e.closed && styles.closedInput,
                    p?.[field] === undefined && styles.invalid,
                  ]}
                />
              ))}
            </View>
          );
        })}
        <View style={[styles.row, styles.totalRow]}>
          <Text style={[styles.totalText, styles.dateCol]}>{t.editor.total}</Text>
          <Text style={[styles.totalText, styles.numCol, { color: colors.income }]}>{formatCents(income)} €</Text>
          <Text style={[styles.totalText, styles.numCol, { color: colors.expense }]}>{formatCents(expense)} €</Text>
        </View>
        <View style={[styles.row, styles.totalRow]}>
          <Text style={[styles.totalText, styles.dateCol]}>{t.editor.balance}</Text>
          <Text style={[styles.totalText, { flex: 2, textAlign: 'right', paddingRight: space.s }]}>
            {formatCents(income - expense)} €
          </Text>
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
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.s,
    paddingHorizontal: space.s,
    paddingVertical: space.xs,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E2E2',
  },
  headRow: { backgroundColor: '#EDEBE6' },
  head: { fontSize: font.body, fontWeight: '700', color: colors.text },
  dateCol: { flex: 1.1 },
  numCol: { flex: 1, textAlign: 'right' },
  dateText: { fontSize: font.body, fontWeight: '600', color: colors.text },
  closedRow: { backgroundColor: colors.closedBg },
  closedLabel: { fontSize: font.small - 2, color: colors.closedText },
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
  invalid: { borderColor: colors.danger, borderWidth: 3, backgroundColor: '#FBE9E7' },
  totalRow: { backgroundColor: '#EDEBE6', paddingVertical: space.s },
  totalText: { fontSize: font.large, fontWeight: '800', color: colors.text },
});
