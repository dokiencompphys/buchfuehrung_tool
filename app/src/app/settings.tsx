import { router } from 'expo-router';

import { API_URL, api } from '@/api/client';
import { useAsync } from '@/lib/useAsync';
import { type Lang, useSettings } from '@/settings/SettingsProvider';
import { Body, Button, Card, Screen, Select } from '@/ui/components';
import { LoadError } from '@/ui/LoadError';

const LANGUAGES: { value: Lang; label: string }[] = [
  { value: 'de', label: '🇩🇪 Deutsch' },
  { value: 'vi', label: '🇻🇳 Tiếng Việt' },
];

export default function SettingsScreen() {
  const { t, settings, update } = useSettings();
  const regions = useAsync(() => api.regions(), []);
  const engines = useAsync(() => api.engines(), []);

  return (
    <Screen>
      <Card>
        <Select label={t.settings.language} value={settings.lang} options={LANGUAGES} onChange={(lang) => update({ lang })} />
      </Card>

      <Card>
        {regions.error ? <LoadError error={regions.error} onRetry={regions.reload} /> : null}
        <Select
          label={t.settings.region}
          value={settings.region}
          options={(regions.data ?? [{ code: settings.region, name: settings.region }]).map((r) => ({
            value: r.code,
            label: r.name,
          }))}
          onChange={(region) => update({ region })}
        />
      </Card>

      <Card>
        {engines.error ? <LoadError error={engines.error} onRetry={engines.reload} /> : null}
        <Select
          label={t.settings.engine}
          value={settings.engine ?? engines.data?.default ?? ''}
          options={(engines.data?.engines ?? []).map((e) => ({
            value: e.id,
            label: e.installed ? e.name : `${e.name} (${t.settings.notInstalled})`,
            disabled: !e.installed,
          }))}
          onChange={(engine) => update({ engine })}
        />
      </Card>

      <Body muted>
        {t.settings.server}: {API_URL}
      </Body>
      <Button label={t.common.back} variant="secondary" onPress={() => router.back()} />
    </Screen>
  );
}
