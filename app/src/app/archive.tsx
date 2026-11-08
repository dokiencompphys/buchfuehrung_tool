import { router } from 'expo-router';
import { Text, View } from 'react-native';

import { api } from '@/api/client';
import type { ExportFormat } from '@/api/types';
import { useDraft } from '@/draft/DraftProvider';
import { confirm } from '@/lib/confirm';
import { downloadFile } from '@/lib/download';
import { formatEuro } from '@/lib/money';
import { useAsync } from '@/lib/useAsync';
import { useSettings } from '@/settings/SettingsProvider';
import { Body, Button, Card, Loading, Screen } from '@/ui/components';
import { CurrentBalance } from '@/ui/CurrentBalance';
import { LoadError } from '@/ui/LoadError';
import { colors, font, space } from '@/ui/theme';

const FORMATS: ExportFormat[] = ['xlsx', 'ods', 'pdf'];

export default function Archive() {
  const { t, settings } = useSettings();
  const { setDraft } = useDraft();
  const items = useAsync(() => api.months(), []);
  const info = useAsync(() => api.info(), []);


  async function open(year: number, month: number) {
    const ledger = await api.month(year, month);
    setDraft({ ledger, hints: [], recognizedDays: null, checks: null, editingExisting: true });
    router.push('/editor');
  }

  async function remove(year: number, month: number) {
    const ok = await confirm(t.archive.delete, t.archive.deleteConfirm, t.archive.delete, t.common.cancel);
    if (!ok) return;
    await api.deleteMonth(year, month);
    items.reload();
  }

  return (
    <Screen>
      <CurrentBalance />
      {info.data ? (
        <Body muted>
          {t.archive.location} {info.data.data_dir}
        </Body>
      ) : null}
      {items.loading && !items.data ? <Loading /> : null}
      {items.error ? <LoadError error={items.error} onRetry={items.reload} /> : null}
      {items.data?.length === 0 ? <Body>{t.archive.empty}</Body> : null}

      {items.data?.map((it) => {
        const name = `${t.months[it.month - 1]} ${it.year}`;
        const period = `${it.year}-${String(it.month).padStart(2, '0')}`;
        return (
          <Card key={period}>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: space.s }}>
              <Text style={{ fontSize: font.large, fontWeight: '800', color: colors.text }}>📁 {name}</Text>
              <Body muted>
                {it.region} · {it.source === 'photo' ? t.archive.fromPhoto : t.archive.selfEntered}
              </Body>
            </View>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.l }}>
              <Body style={{ color: colors.income }}>
                {t.editor.income}: {formatEuro(it.totals.income)}
              </Body>
              <Body style={{ color: colors.expense }}>
                {t.editor.expense}: {formatEuro(it.totals.expense)}
              </Body>
              <Body>
                {t.archive.result}: {formatEuro(it.totals.result)}
              </Body>
            </View>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.l }}>
              <Body>
                {t.archive.opening}: {formatEuro(it.totals.opening)}
                {it.opening_is_manual ? ` (${t.archive.manual})` : ''}
              </Body>
              <Body style={{ fontWeight: '800', color: it.totals.closing.startsWith('-') ? colors.expense : colors.text }}>
                {t.archive.closing}: {formatEuro(it.totals.closing)}
              </Body>
            </View>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.s }}>
              <Button label={`✏️ ${t.archive.open}`} onPress={() => open(it.year, it.month)} style={{ flexGrow: 1 }} />
              {FORMATS.map((f) => (
                <Button
                  key={f}
                  label={`⬇ ${t.formats[f]}`}
                  variant="secondary"
                  style={{ flexGrow: 1 }}
                  onPress={() =>
                    downloadFile(api.exportUrl(it.year, it.month, f, settings.lang), `buchfuehrung_${period}.${f}`)
                  }
                />
              ))}
              <Button label={`🗑 ${t.archive.delete}`} variant="danger" onPress={() => remove(it.year, it.month)} />
            </View>
          </Card>
        );
      })}
    </Screen>
  );
}
