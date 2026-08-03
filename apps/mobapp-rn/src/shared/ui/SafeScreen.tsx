import React, { type ReactNode } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
  type ViewStyle,
} from 'react-native';
import {
  SafeAreaView,
  useSafeAreaInsets,
  type Edge,
} from 'react-native-safe-area-context';

import { useTheme } from '@/theme/ThemeContext';
import { spacing } from '@/theme';

type Props = {
  children: ReactNode;
  scroll?: boolean;
  style?: ViewStyle;
  contentStyle?: ViewStyle;
  /**
   * Safe-area edges. Default omits `top` so stack screens with a nav header
   * don't double-apply the status-bar inset. Headerless screens (e.g. Continue)
   * should pass `['top', 'left', 'right']`.
   */
  edges?: Edge[];
  /**
   * Fixed content pinned below the scrollable area (e.g. sticky CTAs).
   * Only `children` above it participate in scrolling — the footer never
   * moves, and stays clear of the keyboard. Automatically padded for the
   * bottom safe-area inset.
   */
  footer?: ReactNode;
  footerStyle?: ViewStyle;
};

export function SafeScreen({
  children,
  scroll,
  style,
  contentStyle,
  edges = ['left', 'right'],
  footer,
  footerStyle,
}: Props) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();

  if (footer) {
    return (
      <SafeAreaView
        style={[styles.safe, { backgroundColor: colors.background }, style]}
        edges={edges}
      >
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          {scroll ? (
            <ScrollView
              style={styles.flex}
              contentContainerStyle={[styles.scrollContent, contentStyle]}
              keyboardShouldPersistTaps="handled"
              keyboardDismissMode="interactive"
              // Bound scroll to content — no flexGrow stretch / empty void.
              bounces
              overScrollMode="auto"
              alwaysBounceVertical={false}
            >
              {children}
            </ScrollView>
          ) : (
            <View style={[styles.content, contentStyle]}>{children}</View>
          )}
          <View
            style={[
              styles.footer,
              {
                borderTopColor: colors.border,
                backgroundColor: colors.background,
                paddingBottom: edges.includes('bottom')
                  ? spacing.md
                  : insets.bottom + spacing.md,
              },
              footerStyle,
            ]}
          >
            {footer}
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView
      style={[styles.safe, { backgroundColor: colors.background }, style]}
      edges={edges}
    >
      {scroll ? (
        <ScrollView
          style={styles.flex}
          contentContainerStyle={[styles.scrollContent, contentStyle]}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="interactive"
          automaticallyAdjustKeyboardInsets
          // Bound scroll to content — no flexGrow stretch / empty void.
          bounces
          overScrollMode="auto"
          alwaysBounceVertical={false}
        >
          {children}
        </ScrollView>
      ) : (
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <View style={[styles.content, contentStyle]}>{children}</View>
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
  },
  flex: {
    flex: 1,
  },
  content: {
    flex: 1,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  scrollContent: {
    // Do not set flexGrow:1 — that stretches short content and leaves a
    // rubber-band dead zone below the last item ("content flies away").
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.xxl,
    flexGrow: 0,
  },
  footer: {
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    gap: spacing.sm,
  },
});
