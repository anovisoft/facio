import React from 'react';
import {
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTranslation } from 'react-i18next';

import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

export type SessionMenuAction =
  | 'fullGuide'
  | 'editSession'
  | 'postpone'
  | 'skip'
  | 'finishCycle'
  | 'archive';

type Props = {
  visible: boolean;
  isDaily: boolean;
  canFinish: boolean;
  onAction: (action: SessionMenuAction) => void;
  onClose: () => void;
};

type Row = {
  action: SessionMenuAction;
  label: string;
  destructive?: boolean;
};

/**
 * Session kebab menu (bottom sheet) for iOS + Android.
 * Native header menu items need newer react-native-screens than 4.16.
 */
export function SessionMenuSheet({
  visible,
  isDaily,
  canFinish,
  onAction,
  onClose,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();

  const rows: Row[] = [
    { action: 'fullGuide', label: t('home.fullGuide') },
    { action: 'editSession', label: t('home.editSession') },
    ...(isDaily
      ? [{ action: 'postpone' as const, label: t('home.postponeTomorrow') }]
      : []),
    { action: 'skip', label: t('home.skip') },
    ...(canFinish
      ? [{ action: 'finishCycle' as const, label: t('home.finishCycle') }]
      : []),
    {
      action: 'archive',
      label: t('home.archive'),
      destructive: true,
    },
  ];

  const run = (action: SessionMenuAction) => {
    onClose();
    // Defer so the sheet dismisses before follow-up Alert/Modal.
    requestAnimationFrame(() => onAction(action));
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <Pressable
        style={[styles.backdrop, { backgroundColor: colors.overlay }]}
        onPress={onClose}
      >
        <Pressable
          style={[
            styles.sheet,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              paddingBottom: Math.max(insets.bottom, spacing.md),
            },
          ]}
          onPress={(e) => e.stopPropagation()}
        >
          <View style={styles.handleWrap}>
            <View
              style={[styles.handle, { backgroundColor: colors.border }]}
            />
          </View>
          {rows.map((row, index) => (
            <Pressable
              key={row.action}
              accessibilityRole="button"
              onPress={() => run(row.action)}
              style={({ pressed }) => [
                styles.row,
                index < rows.length - 1 && {
                  borderBottomWidth: StyleSheet.hairlineWidth,
                  borderBottomColor: colors.border,
                },
                pressed && { backgroundColor: colors.surfaceMuted },
              ]}
            >
              <Text
                style={[
                  styles.rowLabel,
                  { color: row.destructive ? colors.error : colors.text },
                ]}
              >
                {row.label}
              </Text>
            </Pressable>
          ))}
          <Pressable
            accessibilityRole="button"
            onPress={onClose}
            style={({ pressed }) => [
              styles.cancelRow,
              { backgroundColor: colors.surfaceMuted },
              pressed && { opacity: 0.88 },
            ]}
          >
            <Text style={[styles.cancelLabel, { color: colors.primary }]}>
              {t('common.cancel')}
            </Text>
          </Pressable>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  sheet: {
    borderTopLeftRadius: radii.lg,
    borderTopRightRadius: radii.lg,
    borderTopWidth: StyleSheet.hairlineWidth,
    overflow: 'hidden',
  },
  handleWrap: {
    alignItems: 'center',
    paddingTop: spacing.sm,
    paddingBottom: spacing.xs,
  },
  handle: {
    width: 36,
    height: 4,
    borderRadius: 2,
  },
  row: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    minHeight: 52,
    justifyContent: 'center',
  },
  rowLabel: {
    ...typography.subtitle,
    textAlign: 'center',
  },
  cancelRow: {
    marginTop: spacing.sm,
    marginHorizontal: spacing.md,
    borderRadius: radii.md,
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  cancelLabel: {
    ...typography.subtitle,
  },
});
