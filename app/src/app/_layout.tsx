import { router, Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Pressable, Text } from 'react-native';

import { DraftProvider } from '@/draft/DraftProvider';
import { SettingsProvider, useSettings } from '@/settings/SettingsProvider';
import { colors, font } from '@/ui/theme';

function SettingsButton() {
  const { t } = useSettings();
  return (
    <Pressable
      onPress={() => router.push('/settings')}
      accessibilityRole="button"
      accessibilityLabel={t.settings.title}
      style={{ paddingHorizontal: 16, minHeight: 56, justifyContent: 'center' }}
    >
      <Text style={{ fontSize: font.body, color: colors.primaryText, fontWeight: '700' }}>
        ⚙ {t.settings.title}
      </Text>
    </Pressable>
  );
}

function Navigator() {
  const { t } = useSettings();
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.primary },
        headerTintColor: colors.primaryText,
        headerTitleStyle: { fontSize: font.large, fontWeight: '700' },
        headerBackTitle: t.common.back,
        headerRight: () => <SettingsButton />,
        contentStyle: { backgroundColor: colors.bg },
      }}
    >
      <Stack.Screen name="index" options={{ title: t.appTitle }} />
      <Stack.Screen name="new" options={{ title: t.newMonth.title }} />
      <Stack.Screen name="editor" options={{ title: t.editor.titleNew }} />
      <Stack.Screen name="archive" options={{ title: t.archive.title }} />
      <Stack.Screen name="analysis" options={{ title: t.analysis.title }} />
      <Stack.Screen name="settings" options={{ title: t.settings.title, headerRight: () => null }} />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <SettingsProvider>
      <DraftProvider>
        <StatusBar style="light" />
        <Navigator />
      </DraftProvider>
    </SettingsProvider>
  );
}
