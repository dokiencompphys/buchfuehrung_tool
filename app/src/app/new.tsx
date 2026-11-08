import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import { useState } from 'react';
import { Platform, View } from 'react-native';

import { ApiError, api, type PickedPhoto } from '@/api/client';
import { useDraft } from '@/draft/DraftProvider';
import { inform } from '@/lib/confirm';
import { useSettings } from '@/settings/SettingsProvider';
import { Body, Button, Loading, Notice, Screen, Tile } from '@/ui/components';
import { space } from '@/ui/theme';

export default function NewMonth() {
  const { t, settings } = useSettings();
  const { setDraft } = useDraft();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function startManual() {
    const now = new Date();
    await run(t.common.loading, async () => {
      const ledger = await api.blankDraft(now.getFullYear(), now.getMonth() + 1, settings.region);
      setDraft({ ledger, hints: [], recognizedDays: null, editingExisting: false });
      router.push('/editor');
    });
  }

  async function startPhoto(source: 'library' | 'camera') {
    if (source === 'camera') {
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) return inform(t.newMonth.camera, t.newMonth.cameraDenied);
    }
    const options: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.9 };
    const result =
      source === 'camera'
        ? await ImagePicker.launchCameraAsync(options)
        : await ImagePicker.launchImageLibraryAsync(options);
    if (result.canceled || !result.assets?.[0]) return;
    const asset = result.assets[0];
    const photo: PickedPhoto = {
      uri: asset.uri,
      name: asset.fileName ?? 'seite.jpg',
      mimeType: asset.mimeType ?? 'image/jpeg',
      webFile: asset.file,
    };
    await run(t.newMonth.reading, async () => {
      const reading = await api.photoDraft(photo, settings.region, settings.engine ?? undefined);
      setDraft({
        ledger: reading.ledger,
        hints: reading.hints,
        recognizedDays: reading.recognized_days,
        editingExisting: false,
      });
      router.push('/editor');
    });
  }

  async function run(label: string, fn: () => Promise<void>) {
    setError(null);
    setBusy(label);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof ApiError && e.status === 0 ? t.common.offline : `${t.common.error} ${String((e as Error).message)}`);
    } finally {
      setBusy(null);
    }
  }

  if (busy) return <Screen><Loading text={busy} /></Screen>;

  return (
    <Screen>
      {error ? (
        <Notice tone="error">
          <Body>{error}</Body>
        </Notice>
      ) : null}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.m }}>
        <Tile icon="🖼️" label={t.newMonth.photo} sub={t.newMonth.photoSub} onPress={() => startPhoto('library')} />
        {Platform.OS !== 'web' ? (
          <Tile icon="📷" label={t.newMonth.camera} sub={t.newMonth.cameraSub} onPress={() => startPhoto('camera')} />
        ) : null}
        <Tile icon="⌨️" label={t.newMonth.manual} sub={t.newMonth.manualSub} onPress={startManual} color="#5B3E8C" />
      </View>
      <Button label={t.common.back} variant="secondary" onPress={() => router.back()} />
    </Screen>
  );
}
