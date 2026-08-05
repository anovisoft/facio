import React, { useCallback, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { GestureDetector } from 'react-native-gesture-handler';
import Animated from 'react-native-reanimated';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { ApiError, type ProjectSummary } from '@/api/types';
import { listProjects } from '@/api/projects';
import { resolveGuideCover } from '@/features/continue/coverDisplay';
import {
  rankContinueSessions,
  type FocusReason,
} from '@/features/continue/focusEngine';
import { GuidesDrawer } from '@/features/continue/GuidesDrawer';
import {
  formatApproxMin,
  HeroBlockPreview,
} from '@/features/continue/heroPreview';
import {
  EDGE_WIDTH,
  useGuidesRevealGesture,
} from '@/features/continue/useGuidesRevealGesture';
import type { RootScreenProps } from '@/navigation/types';
import { trackProjectSwitched } from '@/services/beacons';
import { GlassFab } from '@/shared/ui/GlassFab';
import {
  GLASS_ICON_CHIP_SIZE,
  GlassIconButton,
} from '@/shared/ui/GlassIconButton';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

/** ChatGPT-style reveal width — Continue peeks on the right. */
const OPEN_RATIO = 0.82;
/**
 * iPhone continuous-corner feel when Guides is revealed (~48–55).
 * Always applied with overflow hidden — closed reads full-bleed on same bg.
 */
const MAIN_RADIUS = 52;

const REASON_I18N: Record<FocusReason, string> = {
  overdue: 'continue.reasonOverdue',
  lastDay: 'continue.reasonLastDay',
  short: 'continue.reasonShort',
};

/**
 * Facio 0.1 Continue (home).
 * Slice B2: Focus-ranked Hero Previews (attention queue only).
 * Guides drawer = compact inventory under this screen.
 */
export function ContinueScreen({ navigation }: RootScreenProps<'Continue'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { width: windowWidth } = useWindowDimensions();
  const openWidth = windowWidth * OPEN_RATIO;

  const {
    isOpen,
    openDrawer,
    closeDrawer,
    edgeGesture,
    closeGesture,
    mainLayerStyle,
  } = useGuidesRevealGesture({ openWidth });

  const setLastProjectId = useSessionStore((s) => s.setLastProjectId);
  const [sessions, setSessions] = useState<ProjectSummary[]>([]);
  const [openGuideCount, setOpenGuideCount] = useState(0);
  const [focusId, setFocusId] = useState<string | null>(null);
  const [focusReason, setFocusReason] = useState<FocusReason | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** After first fetch settles — silent revalidate on focus (P4). */
  const initialLoadDoneRef = useRef(false);
  const sessionsRef = useRef(sessions);
  sessionsRef.current = sessions;

  const load = useCallback(
    async (isRefresh = false) => {
      const hasCache = sessionsRef.current.length > 0;
      const cold =
        !isRefresh && !initialLoadDoneRef.current && !hasCache;
      if (isRefresh) setRefreshing(true);
      else if (cold) setLoading(true);
      // else: silent stale-while-revalidate — keep list visible (P4)
      if (!hasCache) setError(null);
      try {
        const rows = await listProjects('open');
        setOpenGuideCount(rows.length);
        const ranked = rankContinueSessions(rows);
        setSessions(ranked.ordered);
        setFocusId(ranked.focus?.id ?? null);
        setFocusReason(ranked.reason);
        setError(null);
      } catch (e) {
        const message =
          e instanceof ApiError ? e.message : t('continue.error');
        // Keep stale list on silent/pull failure; only hard-error when empty.
        if (sessionsRef.current.length === 0) {
          setError(message);
        }
      } finally {
        initialLoadDoneRef.current = true;
        setLoading(false);
        setRefreshing(false);
      }
    },
    [t],
  );

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const openSession = (guide: ProjectSummary) => {
    setLastProjectId(guide.id);
    trackProjectSwitched(guide.id);
    navigation.push('Session', { projectId: guide.id });
  };

  const emptyCopy =
    openGuideCount > 0
      ? t('continue.emptyAttention')
      : t('continue.empty');

  // Full-screen spinner only on cold empty first load — not every focus (P4).
  const showColdSpinner = loading && !refreshing && sessions.length === 0;

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <GuidesDrawer
        contentWidth={openWidth}
        interactive={isOpen}
        onClose={closeDrawer}
        navigation={navigation}
      />

      {/*
        Close pan wraps the main layer (enabled only when open).
        Edge open is a dedicated full-height strip — always mounted,
        enabled only when closed — so FlatList vertical scroll is untouched.
      */}
      <GestureDetector gesture={closeGesture}>
        <Animated.View
          style={[
            styles.mainLayer,
            mainLayerStyle,
            {
              backgroundColor: colors.background,
              borderRadius: MAIN_RADIUS,
              shadowColor: '#000',
              shadowOffset: { width: -2, height: 0 },
              shadowRadius: 14,
              elevation: isOpen ? 14 : 0,
            },
          ]}
          collapsable={false}
        >
          <View style={[styles.mainClip, { borderRadius: MAIN_RADIUS }]}>
            <SafeScreen style={styles.flex} edges={['top', 'left', 'right']}>
              <View style={styles.header}>
                <GlassIconButton
                  onPress={openDrawer}
                  accessibilityLabel={t('continue.openGuides')}
                  size={GLASS_ICON_CHIP_SIZE}
                >
                  <Ionicons name="menu-outline" size={22} color={colors.text} />
                </GlassIconButton>
                <Text style={[styles.title, { color: colors.text }]}>
                  {t('continue.title')}
                </Text>
                <View style={styles.headerSpacer} />
              </View>

              {showColdSpinner ? (
                <View style={styles.center}>
                  <ActivityIndicator color={colors.primary} />
                  <Text style={[styles.muted, { color: colors.textSecondary }]}>
                    {t('continue.loading')}
                  </Text>
                </View>
              ) : error && sessions.length === 0 ? (
                <View style={styles.center}>
                  <Text style={[styles.error, { color: colors.error }]}>
                    {error}
                  </Text>
                  <PrimaryButton
                    label={t('continue.retry')}
                    onPress={() => void load()}
                  />
                </View>
              ) : (
                <FlatList
                  data={sessions}
                  keyExtractor={(item) => item.id}
                  contentContainerStyle={
                    sessions.length === 0
                      ? styles.emptyContainer
                      : [styles.list, { paddingBottom: 100 }]
                  }
                  refreshControl={
                    <RefreshControl
                      refreshing={refreshing}
                      onRefresh={() => void load(true)}
                      tintColor={colors.primary}
                    />
                  }
                  ListEmptyComponent={
                    <View style={styles.emptyBlock}>
                      <Text
                        style={[styles.muted, { color: colors.textSecondary }]}
                      >
                        {emptyCopy}
                      </Text>
                      <PrimaryButton
                        label={
                          openGuideCount > 0
                            ? t('continue.emptyAttentionCta')
                            : t('continue.emptyCta')
                        }
                        onPress={() =>
                          openGuideCount > 0
                            ? openDrawer()
                            : navigation.navigate('Create')
                        }
                        style={styles.emptyCta}
                      />
                    </View>
                  }
                  style={styles.listFlex}
                  renderItem={({ item }) => {
                    const action = item.next_action;
                    if (!action) return null;
                    const isFocus = item.id === focusId;
                    const cover = resolveGuideCover(item);
                    const guideGrit =
                      item.title || item.outcome || item.raw_intent;
                    const gritLine = guideGrit
                      ? `${cover.emoji} ${guideGrit}`
                      : null;
                    const approx = formatApproxMin(action.estimate_min, t);
                    const reasonLabel =
                      isFocus && focusReason
                        ? t(REASON_I18N[focusReason])
                        : null;
                    return (
                      <Pressable
                        style={[
                          styles.card,
                          {
                            backgroundColor: colors.surface,
                            borderColor: colors.border,
                          },
                        ]}
                        onPress={() => openSession(item)}
                      >
                        <View style={styles.titleRow}>
                          <Text
                            style={[
                              styles.sessionTitle,
                              { color: colors.text },
                            ]}
                            numberOfLines={2}
                          >
                            {action.title}
                          </Text>
                          {reasonLabel ? (
                            <Text
                              style={[
                                styles.reasonChip,
                                {
                                  color: colors.primary,
                                  backgroundColor: colors.surfaceMuted,
                                },
                              ]}
                            >
                              {reasonLabel}
                            </Text>
                          ) : null}
                        </View>
                        <HeroBlockPreview action={action} colors={colors} />
                        {approx || gritLine ? (
                          <View
                            style={[
                              styles.cardFooter,
                              { borderTopColor: colors.border },
                            ]}
                          >
                            <Text
                              style={[
                                styles.footerLeft,
                                { color: colors.textMuted },
                              ]}
                              numberOfLines={1}
                            >
                              {approx ?? ''}
                            </Text>
                            {gritLine ? (
                              <Text
                                style={[
                                  styles.footerGrit,
                                  { color: colors.textMuted },
                                ]}
                                numberOfLines={1}
                                ellipsizeMode="tail"
                              >
                                {gritLine}
                              </Text>
                            ) : null}
                          </View>
                        ) : null}
                      </Pressable>
                    );
                  }}
                />
              )}
            </SafeScreen>

            <GlassFab onPress={() => navigation.navigate('Create')} />

            {isOpen ? (
              <Pressable
                style={styles.peekDismiss}
                onPress={closeDrawer}
                accessibilityLabel={t('common.dismiss')}
              />
            ) : null}

            {/* Dedicated edge strip — always mounted; enabled/pointerEvents when closed. */}
            <GestureDetector gesture={edgeGesture}>
              <Animated.View
                style={[styles.edgeStrip, { width: EDGE_WIDTH }]}
                pointerEvents={isOpen ? 'none' : 'auto'}
                collapsable={false}
              />
            </GestureDetector>
          </View>
        </Animated.View>
      </GestureDetector>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    overflow: 'hidden',
  },
  mainLayer: {
    flex: 1,
    zIndex: 1,
  },
  mainClip: {
    flex: 1,
    overflow: 'hidden',
  },
  edgeStrip: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    zIndex: 40,
  },
  peekDismiss: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 30,
  },
  flex: { flex: 1 },
  header: {
    zIndex: 50,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },
  headerSpacer: {
    width: 36,
  },
  title: {
    ...typography.hero,
    flex: 1,
    textAlign: 'center',
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
  },
  muted: {
    ...typography.body,
    textAlign: 'center',
  },
  error: {
    ...typography.body,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  listFlex: {
    flex: 1,
  },
  list: {
    gap: spacing.sm,
  },
  emptyContainer: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  emptyBlock: {
    alignItems: 'center',
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  emptyCta: {
    alignSelf: 'stretch',
  },
  card: {
    borderRadius: radii.md,
    borderWidth: 1,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  sessionTitle: {
    ...typography.subtitle,
    flex: 1,
  },
  reasonChip: {
    ...typography.label,
    overflow: 'hidden',
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.pill,
  },
  cardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  footerLeft: {
    ...typography.caption,
    flexShrink: 0,
  },
  footerGrit: {
    ...typography.caption,
    flex: 1,
    minWidth: 0,
    textAlign: 'right',
  },
});
