import { useSettings } from '@/settings/SettingsProvider';

import { Body, Button, Notice } from './components';

export function LoadError({ error, onRetry }: { error: string; onRetry: () => void }) {
  const { t } = useSettings();
  return (
    <Notice tone="error">
      <Body>{error === 'offline' ? t.common.offline : `${t.common.error} ${error}`}</Body>
      <Button label={t.common.retry} onPress={onRetry} style={{ alignSelf: 'flex-start' }} />
    </Notice>
  );
}
