import React, { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { RootScreenProps } from '@/navigation/types';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { ThemeModeSwitcher } from '@/shared/ui/ThemeModeSwitcher';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

/** Thin Settings — theme for now (ChatGPT gear destination). */
export function SettingsScreen({ navigation }: RootScreenProps<'Settings'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const themeMode = useSessionStore((s) => s.themeMode);
  const setThemeMode = useSessionStore((s) => s.setThemeMode);

  useEffect(() => {
    navigation.setOptions({ title: t('settings.title') });
  }, [navigation, t]);

  return (
    <SafeScreen>
      <View style={styles.section}>
        <Text style={[styles.label, { color: colors.textSecondary }]}>
          {t('settings.theme')}
        </Text>
        <ThemeModeSwitcher value={themeMode} onChange={setThemeMode} />
      </View>
    </SafeScreen>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: spacing.sm,
  },
  label: {
    ...typography.caption,
  },
});
