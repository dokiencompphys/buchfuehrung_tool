import { type ReactNode, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type ViewStyle,
} from 'react-native';

import { useSettings } from '@/settings/SettingsProvider';

import { colors, font, space, touch } from './theme';

export function Screen({ children, scroll = true }: { children: ReactNode; scroll?: boolean }) {
  const content = <View style={styles.screenInner}>{children}</View>;
  return (
    <View style={styles.screen}>
      {scroll ? <ScrollView contentContainerStyle={styles.scroll}>{content}</ScrollView> : content}
    </View>
  );
}

export function Title({ children }: { children: ReactNode }) {
  return (
    <Text style={styles.title} accessibilityRole="header">
      {children}
    </Text>
  );
}

export function Body({ children, muted, style }: { children: ReactNode; muted?: boolean; style?: object }) {
  return <Text style={[styles.body, muted && { color: colors.muted }, style]}>{children}</Text>;
}

/** Große Kachel für die Startseite und Auswahl-Bildschirme. */
export function Tile({
  icon,
  label,
  sub,
  onPress,
  color = colors.primary,
}: {
  icon: string;
  label: string;
  sub?: string;
  onPress: () => void;
  color?: string;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [styles.tile, { backgroundColor: color, opacity: pressed ? 0.85 : 1 }]}
    >
      <Text style={styles.tileIcon}>{icon}</Text>
      <Text style={styles.tileLabel}>{label}</Text>
      {sub ? <Text style={styles.tileSub}>{sub}</Text> : null}
    </Pressable>
  );
}

export function Button({
  label,
  onPress,
  variant = 'primary',
  disabled,
  style,
}: {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  style?: ViewStyle;
}) {
  const bg = variant === 'primary' ? colors.primary : variant === 'danger' ? colors.danger : colors.card;
  const fg = variant === 'secondary' ? colors.primary : colors.primaryText;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: bg, opacity: disabled ? 0.5 : pressed ? 0.85 : 1 },
        variant === 'secondary' && { borderWidth: 2, borderColor: colors.primary },
        style,
      ]}
    >
      <Text style={[styles.buttonText, { color: fg }]}>{label}</Text>
    </Pressable>
  );
}

export type Option<T extends string | number> = { value: T; label: string; disabled?: boolean };

/** Auswahlfeld, das eine gut lesbare Liste großer Einträge öffnet (statt kleinem Dropdown). */
export function Select<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: Option<T>[];
  onChange: (value: T) => void;
}) {
  const [open, setOpen] = useState(false);
  const { t } = useSettings();
  const current = options.find((o) => o.value === value);
  return (
    <View style={{ gap: space.xs, flexGrow: 1 }}>
      <Text style={styles.label}>{label}</Text>
      <Pressable
        onPress={() => setOpen(true)}
        accessibilityRole="button"
        accessibilityLabel={`${label}: ${current?.label ?? ''}`}
        style={styles.select}
      >
        <Text style={styles.selectText}>{current?.label ?? '–'}</Text>
        <Text style={styles.selectText}>▾</Text>
      </Pressable>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.title}>{label}</Text>
            <ScrollView style={{ maxHeight: 520 }}>
              {options.map((o) => (
                <Pressable
                  key={String(o.value)}
                  disabled={o.disabled}
                  onPress={() => {
                    onChange(o.value);
                    setOpen(false);
                  }}
                  style={[
                    styles.option,
                    o.value === value && { backgroundColor: '#DCE9F5' },
                    o.disabled && { opacity: 0.45 },
                  ]}
                >
                  <Text style={styles.body}>
                    {o.value === value ? '✓ ' : ''}
                    {o.label}
                  </Text>
                </Pressable>
              ))}
            </ScrollView>
            <Button label={t.common.cancel} variant="secondary" onPress={() => setOpen(false)} />
          </View>
        </View>
      </Modal>
    </View>
  );
}

export function Loading({ text }: { text?: string }) {
  const { t } = useSettings();
  return (
    <View style={{ alignItems: 'center', gap: space.m, padding: space.xl }}>
      <ActivityIndicator size="large" color={colors.primary} />
      <Body style={{ textAlign: 'center' }}>{text ?? t.common.loading}</Body>
    </View>
  );
}

export function Notice({ children, tone = 'warn' }: { children: ReactNode; tone?: 'warn' | 'ok' | 'error' }) {
  const bg = tone === 'ok' ? '#DFF2E1' : tone === 'error' ? '#F9DEDC' : colors.warnBg;
  return <View style={[styles.notice, { backgroundColor: bg }]}>{children}</View>;
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  scroll: { flexGrow: 1 },
  screenInner: { width: '100%', maxWidth: 1100, alignSelf: 'center', padding: space.m, gap: space.m },
  title: { fontSize: font.title, fontWeight: '700', color: colors.text, marginBottom: space.s },
  body: { fontSize: font.body, color: colors.text, lineHeight: font.body * 1.35 },
  label: { fontSize: font.small, fontWeight: '600', color: colors.muted },
  tile: {
    flexGrow: 1,
    flexBasis: 320,
    minHeight: 220,
    borderRadius: 20,
    padding: space.l,
    justifyContent: 'center',
    alignItems: 'center',
    gap: space.s,
  },
  tileIcon: { fontSize: 64 },
  tileLabel: { fontSize: font.huge, fontWeight: '800', color: colors.primaryText, textAlign: 'center' },
  tileSub: { fontSize: font.body, color: colors.primaryText, textAlign: 'center' },
  button: {
    minHeight: touch.min,
    paddingHorizontal: space.l,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  buttonText: { fontSize: font.body, fontWeight: '700' },
  select: {
    minHeight: touch.min,
    borderWidth: 2,
    borderColor: colors.border,
    borderRadius: 12,
    backgroundColor: colors.card,
    paddingHorizontal: space.m,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.s,
  },
  selectText: { fontSize: font.body, color: colors.text },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: space.m,
  },
  modalCard: {
    backgroundColor: colors.card,
    borderRadius: 20,
    padding: space.l,
    width: '100%',
    maxWidth: 560,
    gap: space.m,
  },
  option: {
    minHeight: touch.min,
    justifyContent: 'center',
    paddingHorizontal: space.m,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E2E2',
  },
  notice: { borderRadius: 14, padding: space.m, gap: space.xs },
  card: { backgroundColor: colors.card, borderRadius: 16, padding: space.m, gap: space.s },
});
