// Liste der Stellen, die nach dem Foto-Lesen nicht aufgehen. Jede lässt sich mit
// „Stimmt so“ bestätigen; korrigiert der Nutzer die Zahl, verschwindet sie von selbst.
import { View } from 'react-native';

import type { Issue } from '@/lib/checks';
import { formatEuro } from '@/lib/money';
import { useSettings } from '@/settings/SettingsProvider';
import { Body, Button, Notice } from '@/ui/components';
import { space } from '@/ui/theme';

export function CheckList({
  issues,
  month,
  firstMonth,
  carryMonth,
  current,
  confirmedCount,
  onConfirm,
}: {
  issues: Issue[];
  confirmedCount: number; // mit „Stimmt so“ bestätigte Abweichungen
  month: number;
  firstMonth: boolean;
  carryMonth: string | null; // z. B. "Oktober 2026"
  current: (day: number, field: 'income' | 'expense') => number | null; // Wert im Feld (Cent)
  onConfirm: (id: string) => void;
}) {
  const { t, fmt } = useSettings();
  if (issues.length === 0) {
    return (
      <Notice tone="ok">
        <Body style={{ fontWeight: '700' }}>{confirmedCount > 0 ? t.checks.allChecked : t.checks.allGood}</Body>
      </Notice>
    );
  }

  const mm = String(month).padStart(2, '0');
  const day = (d: number) => `${String(d).padStart(2, '0')}.${mm}.`;
  const column = (f: 'income' | 'expense') => (f === 'income' ? t.editor.income : t.editor.expense);
  const value = (cents: number | null) => (cents === null ? t.checks.empty : formatEuro(cents));

  function text(issue: Issue): string {
    switch (issue.kind) {
      case 'opening':
        return firstMonth
          ? fmt(t.checks.openingFirst, { photo: formatEuro(issue.photo), used: formatEuro(issue.used) })
          : fmt(t.checks.opening, {
              photo: formatEuro(issue.photo),
              used: formatEuro(issue.used),
              month: carryMonth ?? '',
            });
      case 'balance':
        return fmt(t.checks.balance, {
          days: issue.from === issue.to ? day(issue.to) : `${day(issue.from)} – ${day(issue.to)}`,
          photo: formatEuro(issue.photo),
          computed: formatEuro(issue.computed),
        });
      case 'closing':
        return fmt(t.checks.closing, { photo: formatEuro(issue.photo), computed: formatEuro(issue.computed) });
      case 'total':
        return fmt(t.checks.total, {
          column: column(issue.field),
          photo: formatEuro(issue.photo),
          computed: formatEuro(issue.computed),
        });
      case 'suspect': {
        const params = {
          day: day(issue.day),
          column: column(issue.field),
          struck: issue.struck.map(formatEuro).join(', '),
          read: issue.read.map(formatEuro).join(', '),
          value: value(current(issue.day, issue.field)),
        };
        return fmt(t.checks[issue.reason], params);
      }
    }
  }

  return (
    <Notice>
      <Body style={{ fontWeight: '800' }}>
        {issues.length === 1 ? t.checks.titleOne : fmt(t.checks.title, { n: issues.length })}
      </Body>
      <Body>{t.checks.intro}</Body>
      {issues.map((issue) => (
        <View
          key={issue.id}
          style={{ flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: space.s, marginTop: space.s }}
        >
          <Body style={{ flexGrow: 1, flexBasis: 320 }}>• {text(issue)}</Body>
          <Button label={t.checks.confirm} variant="secondary" onPress={() => onConfirm(issue.id)} />
        </View>
      ))}
    </Notice>
  );
}
