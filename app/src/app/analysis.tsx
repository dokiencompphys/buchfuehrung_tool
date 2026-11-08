import { useState } from 'react';
import { Text, View } from 'react-native';

import { api } from '@/api/client';
import type { MonthPoint } from '@/api/types';
import { formatEuro, toCents } from '@/lib/money';
import { useAsync } from '@/lib/useAsync';
import { useSettings } from '@/settings/SettingsProvider';
import { Body, Card, Loading, Screen, Select, Title } from '@/ui/components';
import { LoadError } from '@/ui/LoadError';
import { colors, font, space } from '@/ui/theme';

export default function Analysis() {
  const { t, fmt } = useSettings();
  const thisYear = new Date().getFullYear();
  const [year, setYear] = useState(thisYear);
  const metrics = useAsync(() => api.analytics(year), [year]);

  const m = metrics.data;
  const monthName = (p: MonthPoint | null | undefined) => (p ? `${t.months[p.month - 1]} ${p.year}` : '–');

  return (
    <Screen>
      <View style={{ maxWidth: 360 }}>
        <Select
          label={t.analysis.year}
          value={year}
          options={Array.from({ length: 10 }, (_, i) => ({ value: thisYear - i, label: String(thisYear - i) }))}
          onChange={setYear}
        />
      </View>

      {metrics.loading && !m ? <Loading /> : null}
      {metrics.error ? <LoadError error={metrics.error} onRetry={metrics.reload} /> : null}
      {m && m.months_recorded === 0 ? <Body>{t.analysis.empty}</Body> : null}

      {m && m.months_recorded > 0 ? (
        <>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.m }}>
            <Kpi label={t.analysis.incomeYtd} value={formatEuro(m.income_ytd)} color={colors.income} big />
            <Kpi label={t.analysis.expenseYtd} value={formatEuro(m.expense_ytd)} color={colors.expense} big />
            <Kpi label={t.analysis.balanceYtd} value={formatEuro(m.balance_ytd)} big />
          </View>

          {m.latest ? (
            <Card>
              <Text style={styles.kpiLabel}>
                {fmt(t.analysis.vsPrevious, { month: monthName(m.latest.current) })}
              </Text>
              <Text style={[styles.kpiValue, { color: trendColor(m.latest.income_change) }]}>
                {formatEuro(m.latest.current.income)}
              </Text>
              {m.latest.previous ? (
                <Body style={{ color: trendColor(m.latest.income_change), fontWeight: '700' }}>
                  {arrow(m.latest.income_change)} {signed(m.latest.income_change)} €
                  {m.latest.income_change_pct ? `  (${signedPct(m.latest.income_change_pct)} %)` : ''}
                  {'   '}
                  <Text style={{ color: colors.muted, fontWeight: '400' }}>
                    {monthName(m.latest.previous)}: {formatEuro(m.latest.previous.income)}
                  </Text>
                </Body>
              ) : (
                <Body muted>{t.analysis.noPrevious}</Body>
              )}
            </Card>
          ) : null}

          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.m }}>
            <Kpi label={t.analysis.avgMonth} value={formatEuro(m.avg_income_per_month)} />
            <Kpi label={t.analysis.avgDay} value={formatEuro(m.avg_income_per_open_day)} />
            <Kpi
              label={t.analysis.bestMonth}
              value={formatEuro(m.best_month?.income)}
              sub={monthName(m.best_month)}
            />
            <Kpi
              label={t.analysis.worstMonth}
              value={formatEuro(m.worst_month?.income)}
              sub={monthName(m.worst_month)}
            />
            <Kpi label={t.analysis.prevYear} value={formatEuro(m.income_previous_year_same_period)} />
            {m.latest ? (
              <Kpi
                label={fmt(t.analysis.sameMonthLastYear, { month: t.months[m.latest.current.month - 1] })}
                value={formatEuro(m.same_month_last_year?.income)}
              />
            ) : null}
            <Kpi label={t.analysis.months} value={String(m.months_recorded)} />
          </View>

          <Card>
            <Title>{t.analysis.chart}</Title>
            <BarChart series={m.series} monthNames={t.months} />
            <View style={{ flexDirection: 'row', gap: space.l }}>
              <Body style={{ color: colors.income }}>■ {t.editor.income}</Body>
              <Body style={{ color: colors.expense }}>■ {t.editor.expense}</Body>
            </View>
          </Card>
        </>
      ) : null}
    </Screen>
  );
}

function Kpi({ label, value, sub, color = colors.text, big }: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
  big?: boolean;
}) {
  return (
    <Card style={{ flexGrow: 1, flexBasis: big ? 300 : 240 }}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={[styles.kpiValue, { color, fontSize: big ? font.huge : font.title }]}>{value}</Text>
      {sub ? <Body muted>{sub}</Body> : null}
    </Card>
  );
}

/** Einfaches Säulendiagramm ohne Zusatzbibliothek: Einnahmen und Ausgaben pro Monat. */
function BarChart({ series, monthNames }: { series: MonthPoint[]; monthNames: string[] }) {
  const max = Math.max(1, ...series.flatMap((p) => [toCents(p.income), toCents(p.expense)]));
  const height = 260;
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: space.s, height: height + 40 }}>
      {series.map((p) => (
        <View key={p.month} style={{ flex: 1, alignItems: 'center', gap: 4 }}>
          <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 3, height }}>
            <View
              accessibilityLabel={`${monthNames[p.month - 1]}: ${formatEuro(p.income)}`}
              style={{ width: 18, height: (toCents(p.income) / max) * height, backgroundColor: colors.income, borderRadius: 4 }}
            />
            <View
              accessibilityLabel={`${monthNames[p.month - 1]}: ${formatEuro(p.expense)}`}
              style={{ width: 18, height: (toCents(p.expense) / max) * height, backgroundColor: colors.expense, borderRadius: 4 }}
            />
          </View>
          <Text style={{ fontSize: font.small - 2, color: colors.muted }}>{monthNames[p.month - 1].slice(0, 3)}</Text>
        </View>
      ))}
    </View>
  );
}

const trendColor = (change: string | null) =>
  change === null ? colors.text : change.startsWith('-') ? colors.expense : colors.income;
const arrow = (change: string | null) => (change === null ? '' : change.startsWith('-') ? '▼' : '▲');
const signed = (v: string | null) => {
  if (v === null) return '';
  const s = formatEuro(v).replace(' €', '');
  return v.startsWith('-') ? s : `+${s}`;
};
const signedPct = (v: string) => (v.startsWith('-') ? v.replace('-', '−') : `+${v}`).replace('.', ',');

const styles = {
  kpiLabel: { fontSize: font.body, color: colors.muted, fontWeight: '600' as const },
  kpiValue: { fontSize: font.huge, fontWeight: '800' as const },
};
