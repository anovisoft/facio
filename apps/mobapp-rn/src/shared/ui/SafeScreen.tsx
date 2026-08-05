import React, { useCallback, useEffect, useRef, type ReactNode } from 'react';
import {
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
  type ViewStyle,
} from 'react-native';
import Animated, {
  runOnUI,
  scrollTo,
  type AnimatedRef,
} from 'react-native-reanimated';
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
  /**
   * Optional Reanimated scroll ref (e.g. for nested drag auto-scroll).
   * When set with `scroll`, uses Animated.ScrollView.
   */
  scrollRef?: AnimatedRef<Animated.ScrollView>;
};

type ScrollMetrics = {
  offsetY: number;
  contentH: number;
  layoutH: number;
  insetTop: number;
  insetBottom: number;
};

export function SafeScreen({
  children,
  scroll,
  style,
  contentStyle,
  edges = ['left', 'right'],
  footer,
  footerStyle,
  scrollRef,
}: Props) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const localScrollRef = useRef<ScrollView>(null);
  const metricsRef = useRef<ScrollMetrics>({
    offsetY: 0,
    contentH: 0,
    layoutH: 0,
    insetTop: 0,
    insetBottom: 0,
  });

  const scrollToY = useCallback(
    (y: number) => {
      if (scrollRef) {
        runOnUI(() => {
          'worklet';
          scrollTo(scrollRef, 0, y, false);
        })();
        return;
      }
      localScrollRef.current?.scrollTo({ y, animated: false });
    },
    [scrollRef],
  );

  const clampScrollOffset = useCallback(() => {
    const { offsetY, contentH, layoutH, insetTop, insetBottom } =
      metricsRef.current;
    if (layoutH <= 0 || contentH <= 0) return;

    // Max offset accounts for keyboard / safe-area content insets.
    const maxOffset = Math.max(0, contentH - layoutH + insetTop + insetBottom);
    if (offsetY > maxOffset + 0.5) {
      metricsRef.current.offsetY = maxOffset;
      scrollToY(maxOffset);
      return;
    }
    if (offsetY < -0.5) {
      metricsRef.current.offsetY = 0;
      scrollToY(0);
    }
  }, [scrollToY]);

  useEffect(() => {
    if (!scroll) return;
    const hide = Keyboard.addListener('keyboardDidHide', () => {
      // Insets often clear a frame after hide; clamp once layout settles.
      requestAnimationFrame(() => {
        metricsRef.current.insetBottom = 0;
        metricsRef.current.insetTop = 0;
        clampScrollOffset();
      });
    });
    return () => hide.remove();
  }, [scroll, clampScrollOffset]);

  const onScroll = useCallback((e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const { contentOffset, contentSize, contentInset, layoutMeasurement } =
      e.nativeEvent;
    metricsRef.current = {
      offsetY: contentOffset.y,
      contentH: contentSize.height,
      layoutH: layoutMeasurement.height,
      insetTop: contentInset?.top ?? 0,
      insetBottom: contentInset?.bottom ?? 0,
    };
  }, []);

  const onContentSizeChange = useCallback(
    (_w: number, h: number) => {
      metricsRef.current.contentH = h;
      requestAnimationFrame(clampScrollOffset);
    },
    [clampScrollOffset],
  );

  const onLayout = useCallback(
    (e: { nativeEvent: { layout: { height: number } } }) => {
      metricsRef.current.layoutH = e.nativeEvent.layout.height;
      requestAnimationFrame(clampScrollOffset);
    },
    [clampScrollOffset],
  );

  const scrollProps = {
    style: styles.flex,
    contentContainerStyle: [styles.scrollContent, contentStyle],
    keyboardShouldPersistTaps: 'handled' as const,
    keyboardDismissMode: 'interactive' as const,
    // Keep keyboard insets on ScrollView so focused inputs (e.g. Manual Edit)
    // stay reachable. Sticky footer uses KAV separately; clampScrollOffset
    // recovers when insets clear or content shrinks past the current offset.
    automaticallyAdjustKeyboardInsets: true,
    // Bound scroll to content height — no flexGrow stretch / empty void.
    // Android: never overscroll into empty; iOS: bounce only when scrollable.
    bounces: true,
    overScrollMode: 'never' as const,
    alwaysBounceVertical: false,
    scrollEventThrottle: 16,
    onScroll,
    onContentSizeChange,
    onLayout,
  };

  const scrollView = scroll ? (
    scrollRef ? (
      <Animated.ScrollView ref={scrollRef} {...scrollProps}>
        {children}
      </Animated.ScrollView>
    ) : (
      <ScrollView ref={localScrollRef} {...scrollProps}>
        {children}
      </ScrollView>
    )
  ) : (
    <View style={[styles.content, contentStyle]}>{children}</View>
  );

  if (footer) {
    return (
      <SafeAreaView
        style={[styles.safe, { backgroundColor: colors.background }, style]}
        edges={edges}
      >
        {/*
          Scroll is NOT inside KeyboardAvoidingView padding — that combo
          inflated content size / left users stranded in empty rubber-band void
          (Guide + expanded PathList). Keyboard insets adjust the ScrollView;
          KAV only lifts the sticky footer.
        */}
        <View style={styles.flex}>{scrollView}</View>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
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
        scrollView
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
