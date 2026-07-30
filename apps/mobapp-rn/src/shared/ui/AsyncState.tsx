import React, { type ReactNode } from 'react';
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

type Props = {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyMessage?: string;
  loadingMessage?: string;
  retryLabel?: string;
  onRetry?: () => void;
  children: ReactNode;
};

/** Shared loading / error / empty chrome for list and detail screens. */
export function AsyncState({
  loading,
  error,
  empty,
  emptyMessage,
  loadingMessage,
  retryLabel,
  onRetry,
  children,
}: Props) {
  const { colors } = useTheme();

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
        {loadingMessage ? (
          <Text style={[styles.muted, { color: colors.textSecondary }]}>
            {loadingMessage}
          </Text>
        ) : null}
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
        {onRetry && retryLabel ? (
          <PrimaryButton label={retryLabel} onPress={onRetry} />
        ) : null}
      </View>
    );
  }

  if (empty) {
    return (
      <View style={styles.center}>
        <Text style={[styles.muted, { color: colors.textSecondary }]}>
          {emptyMessage}
        </Text>
      </View>
    );
  }

  return <>{children}</>;
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  muted: {
    ...typography.body,
    textAlign: 'center',
  },
  error: {
    ...typography.body,
    textAlign: 'center',
  },
});
