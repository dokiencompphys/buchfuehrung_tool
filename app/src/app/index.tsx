import { router } from 'expo-router';
import { View } from 'react-native';

import { useSettings } from '@/settings/SettingsProvider';
import { Screen, Tile } from '@/ui/components';
import { space } from '@/ui/theme';

export default function Home() {
  const { t } = useSettings();
  return (
    <Screen>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.m }}>
        <Tile
          icon="📊"
          label={t.home.analysis}
          sub={t.home.analysisSub}
          onPress={() => router.push('/analysis')}
          color="#1B6B2F"
        />
        <Tile
          icon="✍️"
          label={t.home.newMonth}
          sub={t.home.newMonthSub}
          onPress={() => router.push('/new')}
        />
      </View>
      <Tile
        icon="🗂️"
        label={t.home.archive}
        sub={t.home.archiveSub}
        onPress={() => router.push('/archive')}
        color="#5B3E8C"
      />
    </Screen>
  );
}
