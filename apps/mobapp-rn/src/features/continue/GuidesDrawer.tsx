import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTranslation } from 'react-i18next';
import type { NavigationProp } from '@react-navigation/native';

import { ApiError, type ProjectSummary } from '@/api/types';
import { listProjects } from '@/api/projects';
import { resolveGuideCover } from '@/features/continue/coverDisplay';
import type { RootStackParamList } from '@/navigation/types';
import { trackProjectSwitched } from '@/services/beacons';
import {
  GLASS_ICON_CHIP_SIZE,
  GlassIconButton,
} from '@/shared/ui/GlassIconButton';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  /** Width of the revealed Guides column (≈ windowWidth * OPEN_RATIO). */
  contentWidth: number;
  /** True when the drawer is open — enables taps; load stays warm on mount. */
  interactive: boolean;
  onClose: () => void;
  navigation: NavigationProp<RootStackParamList>;
};

/**
 * Guides inventory (Slice B2) — compact navigation under Continue.
 * Row = emoji/mark + title (+ thin draft/waiting status). No Cover twin cards.
 * Selecting a Guide (draft or active) opens the trust Guide surface — not Session.
 * Open/close motion lives in ContinueScreen (main layer slides right).
 */
export function GuidesDrawer({
  contentWidth,
  interactive,
  onClose,
  navigation,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const setLastProjectId = useSessionStore((s) => s.setLastProjectId);
  const [guides, setGuides] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await listProjects('open');
      setGuides(rows);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('continue.guidesError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  // Warm mount so edge-drag BEGAN never flash-loads and hitch mid-gesture.
  useEffect(() => {
    void load();
  }, [load]);

  const openGuide = (guide: ProjectSummary) => {
    setLastProjectId(guide.id);
    trackProjectSwitched(guide.id);
    onClose();
    navigation.navigate('Guide', { projectId: guide.id });
  };

  const goArchive = () => {
    onClose();
    navigation.navigate('Archive');
  };

  const goSettings = () => {
    onClose();
    navigation.navigate('Settings');
  };

  return (
    <View
      style={[
        styles.sheet,
        {
          width: contentWidth,
          backgroundColor: colors.background,
          paddingTop: insets.top + spacing.sm,
          paddingBottom: insets.bottom + spacing.sm,
        },
      ]}
      pointerEvents={interactive ? 'auto' : 'none'}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.text }]}>
          {t('continue.guidesTitle')}
        </Text>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : error ? (
        <View style={styles.center}>
          <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
          <PrimaryButton
            label={t('continue.retry')}
            onPress={() => void load()}
          />
        </View>
      ) : (
        <FlatList
          data={guides}
          keyExtractor={(item) => item.id}
          style={styles.listFlex}
          contentContainerStyle={
            guides.length === 0 ? styles.emptyContainer : styles.list
          }
          ListEmptyComponent={
            <Text style={[styles.muted, { color: colors.textSecondary }]}>
              {t('continue.guidesEmpty')}
            </Text>
          }
          renderItem={({ item }) => {
            const cover = resolveGuideCover(item);
            const waiting =
              item.status === 'active' && item.next_action == null;
            const statusLabel =
              item.status === 'draft'
                ? t('continue.draft')
                : waiting
                  ? t('continue.waitingStatus')
                  : null;
            return (
              <Pressable
                style={styles.row}
                onPress={() => openGuide(item)}
                accessibilityRole="button"
              >
                <Text style={styles.mark}>{cover.emoji}</Text>
                <Text
                  style={[styles.rowTitle, { color: colors.text }]}
                  numberOfLines={1}
                >
                  {item.title || item.outcome || item.raw_intent}
                </Text>
                {statusLabel ? (
                  <Text
                    style={[
                      styles.status,
                      {
                        color: colors.textMuted,
                        backgroundColor: colors.surfaceMuted,
                      },
                    ]}
                  >
                    {statusLabel}
                  </Text>
                ) : null}
              </Pressable>
            );
          }}
        />
      )}

      <View style={[styles.bottomBar, { borderTopColor: colors.border }]}>
        <Pressable
          onPress={goArchive}
          style={styles.archiveBtn}
          accessibilityRole="button"
          accessibilityLabel={t('continue.archive')}
        >
          <Text style={[styles.footerLink, { color: colors.primary }]}>
            {t('continue.archive')}
          </Text>
        </Pressable>
        <GlassIconButton
          onPress={goSettings}
          accessibilityLabel={t('settings.open')}
          size={GLASS_ICON_CHIP_SIZE}
        >
          <Ionicons name="settings-outline" size={22} color={colors.text} />
        </GlassIconButton>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  sheet: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    paddingHorizontal: spacing.md,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  title: {
    ...typography.hero,
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
    paddingBottom: spacing.md,
  },
  emptyContainer: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.sm + 2,
    paddingHorizontal: spacing.xs,
  },
  mark: {
    fontSize: 18,
    lineHeight: 22,
    width: 26,
    textAlign: 'center',
  },
  rowTitle: {
    ...typography.body,
    flex: 1,
    minWidth: 0,
  },
  status: {
    ...typography.label,
    overflow: 'hidden',
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.pill,
  },
  bottomBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: spacing.md,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  archiveBtn: {
    paddingVertical: spacing.sm,
    paddingRight: spacing.md,
  },
  footerLink: {
    ...typography.body,
  },
});
