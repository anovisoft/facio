import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { PanGestureHandler } from 'react-native-gesture-handler';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { ApiError, type ProjectSummary } from '@/api/types';
import { listProjects } from '@/api/projects';
import { blockTypeLabel } from '@/features/continue/blockTypeLabel';
import { GuidesDrawer } from '@/features/continue/GuidesDrawer';
import { orderContinueSessions } from '@/features/continue/naiveOrder';
import {
  EDGE_WIDTH,
  useGuidesRevealGesture,
} from '@/features/continue/useGuidesRevealGesture';
import type { RootScreenProps } from '@/navigation/types';
import { trackProjectSwitched } from '@/services/beacons';
import { GlassFab } from '@/shared/ui/GlassFab';
import { GlassIconButton } from '@/shared/ui/GlassIconButton';
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

/**
 * Facio 0.1 Continue (home).
 * Slice A: one Session card per active Guide; naive order in naiveOrder.ts.
 * Focus Engine ranking is Slice B — not here.
 *
 * Guides sits under this screen; opening translates the main layer right.
 * Peek = translateX + radius + shadow — no scale.
 * Reveal gesture: see useGuidesRevealGesture.ts (progress ∈ [0,1], edge strip open).
 */
export function ContinueScreen({ navigation }: RootScreenProps<'Continue'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { width: windowWidth } = useWindowDimensions();
  const openWidth = windowWidth * OPEN_RATIO;

  const {
    translateX,
    isOpen,
    openDrawer,
    closeDrawer,
    edgePanProps,
    closePanProps,
  } = useGuidesRevealGesture({ openWidth });

  const setLastProjectId = useSessionStore((s) => s.setLastProjectId);
  const [sessions, setSessions] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);
      try {
        const rows = await listProjects('open');
        setSessions(orderContinueSessions(rows));
      } catch (e) {
        const message =
          e instanceof ApiError ? e.message : t('continue.error');
        setError(message);
      } finally {
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
      <PanGestureHandler {...closePanProps}>
        <Animated.View
          style={[
            styles.mainLayer,
            {
              backgroundColor: colors.background,
              borderRadius: MAIN_RADIUS,
              transform: [{ translateX }],
              shadowColor: '#000',
              shadowOffset: { width: -2, height: 0 },
              shadowOpacity: isOpen ? 0.22 : 0,
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
                  size={36}
                >
                  <Ionicons name="menu-outline" size={20} color={colors.text} />
                </GlassIconButton>
                <Text style={[styles.title, { color: colors.text }]}>
                  {t('continue.title')}
                </Text>
                <View style={styles.headerSpacer} />
              </View>

              {loading && !refreshing ? (
                <View style={styles.center}>
                  <ActivityIndicator color={colors.primary} />
                  <Text style={[styles.muted, { color: colors.textSecondary }]}>
                    {t('continue.loading')}
                  </Text>
                </View>
              ) : error ? (
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
                        {t('continue.empty')}
                      </Text>
                      <PrimaryButton
                        label={t('continue.emptyCta')}
                        onPress={() => navigation.navigate('Create')}
                        style={styles.emptyCta}
                      />
                    </View>
                  }
                  style={styles.listFlex}
                  renderItem={({ item }) => {
                    const block = blockTypeLabel(item.next_action);
                    const statusLine = item.next_action?.title
                      ? item.next_action.title
                      : item.peek_action?.title
                        ? t('continue.waiting', {
                            title: item.peek_action.title,
                          })
                        : t('continue.noSession');
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
                        <Text
                          style={[styles.cardTitle, { color: colors.text }]}
                          numberOfLines={2}
                        >
                          {item.title || item.outcome || item.raw_intent}
                        </Text>
                        <Text
                          style={[
                            styles.cardMeta,
                            { color: colors.textSecondary },
                          ]}
                          numberOfLines={2}
                        >
                          {block ? `${block} · ${statusLine}` : statusLine}
                        </Text>
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
            <PanGestureHandler {...edgePanProps}>
              <Animated.View
                style={[styles.edgeStrip, { width: EDGE_WIDTH }]}
                pointerEvents={isOpen ? 'none' : 'auto'}
                collapsable={false}
              />
            </PanGestureHandler>
          </View>
        </Animated.View>
      </PanGestureHandler>
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
  cardTitle: {
    ...typography.subtitle,
  },
  cardMeta: {
    ...typography.caption,
    marginTop: spacing.xs,
  },
});
